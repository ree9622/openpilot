import math
from collections import deque

from cereal import log
from common.numpy_fast import interp
from selfdrive.controls.lib.latcontrol import LatControl, MIN_STEER_SPEED
from selfdrive.controls.lib.pid import PIDController
from selfdrive.controls.lib.drive_helpers import apply_deadzone
from selfdrive.controls.lib.vehicle_model import ACCELERATION_DUE_TO_GRAVITY

from common.params import Params

# At higher speeds (25+mph) we can assume:
# Lateral acceleration achieved by a specific car correlates to
# torque applied to the steering rack. It does not correlate to
# wheel slip, or to speed.

# This controller applies torque to achieve desired lateral
# accelerations. To compensate for the low speed effects we
# use a LOW_SPEED_FACTOR in the error. Additionally, there is
# friction in the steering wheel that needs to be overcome to
# move it at all, this is compensated for too.


FRICTION_THRESHOLD = 0.2

# Jerk feedforward: improves transient response during steering transitions
# From stock openpilot — scales the rate of change of desired lateral accel
# Default loaded from Params("TorqueJerkGain"), fallback to 0.05
JERK_GAIN_DEFAULT = 0.05

# Delay compensation: compare measurement against past request
# instead of current request, eliminating phase lag oscillation
DT_CTRL = 0.01  # 100Hz control loop

# Live torque learning constants (adapted from stock torqued)
LEARNING_MIN_SPEED = 15.0        # m/s (~54 km/h) - only learn at highway speeds
LEARNING_MIN_TORQUE = 0.02       # minimum torque threshold
LEARNING_MAX_LAT_ACCEL = 1.0     # exclude extreme maneuvers
LEARNING_MIN_POINTS = 200        # minimum points before updating
LEARNING_DECAY = 0.995           # exponential moving average decay
LEARNING_MAX_DRIFT = 0.3         # max 30% drift from offline values


class LiveTorqueLearner:
  """Lightweight live learner for friction and lateral accel factor.

  Collects (output_torque, actual_lateral_accel) pairs during engaged driving,
  then fits a simple linear relationship: lat_accel = factor * torque + offset.
  The residual spread estimates friction. Adapted from stock openpilot's torqued
  TLS-SVD algorithm, simplified to run inline without a separate daemon.
  """
  def __init__(self, initial_friction, initial_kf):
    self.initial_friction = initial_friction
    self.initial_kf = initial_kf
    self.friction = initial_friction
    self.kf_factor = 1.0  # multiplier on kf (1.0 = no change)

    self.torques = deque(maxlen=2000)
    self.lat_accels = deque(maxlen=2000)
    self.valid_count = 0
    self.engaged_frames = 0

  def add_point(self, active, steer_override, v_ego, output_torque, actual_lat_accel):
    """Collect a data point if conditions are met."""
    if not active or steer_override:
      self.engaged_frames = 0
      return

    self.engaged_frames += 1
    # Wait 2 seconds after engagement for transients to settle
    if self.engaged_frames < 200:
      return

    if (v_ego < LEARNING_MIN_SPEED or
        abs(output_torque) < LEARNING_MIN_TORQUE or
        abs(actual_lat_accel) > LEARNING_MAX_LAT_ACCEL):
      return

    self.torques.append(output_torque)
    self.lat_accels.append(actual_lat_accel)
    self.valid_count += 1

  def get_learned_params(self):
    """Compute learned friction and kf adjustment.

    Returns (friction, kf_factor) where kf_factor is a multiplier
    on the base kf value. Returns initial values if not enough data.
    """
    if self.valid_count < LEARNING_MIN_POINTS:
      return self.friction, self.kf_factor

    # Simple linear regression: lat_accel = slope * torque + intercept
    n = len(self.torques)
    sum_t = sum(self.torques)
    sum_a = sum(self.lat_accels)
    sum_tt = sum(t * t for t in self.torques)
    sum_ta = sum(t * a for t, a in zip(self.torques, self.lat_accels))

    denom = n * sum_tt - sum_t * sum_t
    if abs(denom) < 1e-10:
      return self.friction, self.kf_factor

    slope = (n * sum_ta - sum_t * sum_a) / denom

    # Friction from residual spread (std of residuals perpendicular to fit)
    intercept = (sum_a - slope * sum_t) / n
    residuals = [abs(a - slope * t - intercept) for t, a in zip(self.torques, self.lat_accels)]
    mean_residual = sum(residuals) / n
    # Friction estimate: 1.5x mean absolute residual (matches stock FRICTION_FACTOR)
    new_friction = mean_residual * 1.5

    # Clamp to +-30% of initial values
    new_friction = max(self.initial_friction * (1 - LEARNING_MAX_DRIFT),
                       min(self.initial_friction * (1 + LEARNING_MAX_DRIFT), new_friction))

    # kf adjustment: if slope differs from expected, adjust kf proportionally
    if abs(slope) > 0.1:
      # Higher slope means car is more responsive → need less gain
      new_kf_factor = 1.0 / max(0.5, min(2.0, abs(slope)))
      new_kf_factor = max(1 - LEARNING_MAX_DRIFT, min(1 + LEARNING_MAX_DRIFT, new_kf_factor))
    else:
      new_kf_factor = self.kf_factor

    # Smooth update with exponential moving average
    self.friction = LEARNING_DECAY * self.friction + (1 - LEARNING_DECAY) * new_friction
    self.kf_factor = LEARNING_DECAY * self.kf_factor + (1 - LEARNING_DECAY) * new_kf_factor

    return self.friction, self.kf_factor


class LatControlTorque(LatControl):
  def __init__(self, CP, CI):
    super().__init__(CP, CI)
    self.CP = CP

    self.mpc_frame = 0
    self.params = Params()

    self.kf = CP.lateralTuning.torque.kf

    self.pid = PIDController(CP.lateralTuning.torque.kp, CP.lateralTuning.torque.ki,
                             k_f=self.kf, pos_limit=self.steer_max, neg_limit=-self.steer_max)
    self.get_steer_feedforward = CI.get_steer_feedforward_function()
    self.use_steering_angle = CP.lateralTuning.torque.useSteeringAngle
    self.friction = CP.lateralTuning.torque.friction
    self.steering_angle_deadzone_deg = CP.lateralTuning.torque.steeringAngleDeadzoneDeg

    self.live_tune_enabled = False

    self.lt_timer = 0

    # --- Delay compensation buffer ---
    # Buffer past desired curvature requests; compare measurement against
    # what was requested steerActuatorDelay seconds ago to eliminate phase lag
    delay_seconds = CP.steerActuatorDelay
    self.delay_frames = max(1, int(round(delay_seconds / DT_CTRL)))
    self.curvature_request_buffer = deque([0.0] * (self.delay_frames + 1), maxlen=200)

    # --- Jerk feedforward state ---
    self.prev_desired_lateral_accel = 0.0
    # Read jerk gain from Params (int * 0.01), fallback to default
    try:
      self.jerk_gain = int(self.params.get("TorqueJerkGain", encoding="utf8")) * 0.01
    except (TypeError, ValueError):
      self.jerk_gain = JERK_GAIN_DEFAULT

    # --- Live torque learning ---
    self.live_learning_enabled = self.params.get_bool("TorqueLiveLearning")
    self.learner = LiveTorqueLearner(self.friction, self.kf)
    self.learning_update_timer = 0

  def live_tune(self, CP):
    self.mpc_frame += 1
    if self.mpc_frame % 300 == 0:
      self.max_lat_accel = int(self.params.get("TorqueMaxLatAccel", encoding="utf8")) * 0.1
      self.kp = int(self.params.get("TorqueKp", encoding="utf8")) * 0.1 / self.max_lat_accel
      self.kf = int(self.params.get("TorqueKf", encoding="utf8")) * 0.1 / self.max_lat_accel
      self.ki = int(self.params.get("TorqueKi", encoding="utf8")) * 0.1 / self.max_lat_accel
      self.friction = int(self.params.get("TorqueFriction", encoding="utf8")) * 0.001
      self.use_steering_angle = self.params.get_bool('TorqueUseAngle')
      self.steering_angle_deadzone_deg = int(self.params.get("TorqueAngDeadZone", encoding="utf8")) * 0.1
      self.pid = PIDController(self.kp, self.ki,
                              k_f=self.kf, pos_limit=1.0, neg_limit=-1.0)

      # Re-sync learner with new manual values
      self.learner.initial_friction = self.friction
      self.learner.initial_kf = self.kf

      # Read jerk gain and live learning toggle
      try:
        self.jerk_gain = int(self.params.get("TorqueJerkGain", encoding="utf8")) * 0.01
      except (TypeError, ValueError):
        self.jerk_gain = JERK_GAIN_DEFAULT
      self.live_learning_enabled = self.params.get_bool("TorqueLiveLearning")

      self.mpc_frame = 0

  def update(self, active, CS, CP, VM, params, last_actuators, desired_curvature, desired_curvature_rate, llk):
    self.lt_timer += 1
    if self.lt_timer > 100:
      self.lt_timer = 0
      self.live_tune_enabled = self.params.get_bool("OpkrLiveTunePanelEnable")
    if self.live_tune_enabled:
      self.live_tune(CP)

    pid_log = log.ControlsState.LateralTorqueState.new_message()

    if CS.vEgo < MIN_STEER_SPEED or not active:
      output_torque = 0.0
      pid_log.active = False
      self.prev_desired_lateral_accel = 0.0
    else:
      if self.use_steering_angle:
        actual_curvature = -VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
        curvature_deadzone = abs(VM.calc_curvature(math.radians(self.steering_angle_deadzone_deg), CS.vEgo, 0.0))
      else:
        actual_curvature_vm = -VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
        actual_curvature_llk = llk.angularVelocityCalibrated.value[2] / CS.vEgo
        actual_curvature = interp(CS.vEgo, [2.0, 5.0], [actual_curvature_vm, actual_curvature_llk])
        curvature_deadzone = 0.0
      desired_lateral_accel = desired_curvature * CS.vEgo ** 2
      actual_lateral_accel = actual_curvature * CS.vEgo ** 2
      lateral_accel_deadzone = curvature_deadzone * CS.vEgo ** 2

      # --- Delay compensation ---
      # Buffer curvature, pull the request from steerActuatorDelay seconds ago
      self.curvature_request_buffer.append(desired_curvature)
      delayed_curvature = self.curvature_request_buffer[-self.delay_frames - 1]
      delayed_lateral_accel = delayed_curvature * CS.vEgo ** 2

      # --- Jerk feedforward ---
      # Rate of change of desired lateral accel improves transient response
      desired_lateral_jerk = (desired_lateral_accel - self.prev_desired_lateral_accel) / DT_CTRL
      self.prev_desired_lateral_accel = desired_lateral_accel

      # --- Live torque learning ---
      # Apply learned params only when learning is on and manual live tune is off
      use_learning = self.live_learning_enabled and not self.live_tune_enabled
      if use_learning:
        learned_friction, learned_kf_factor = self.learner.get_learned_params()
        effective_friction = learned_friction
        effective_kf = self.kf * learned_kf_factor
      else:
        effective_friction = self.friction
        effective_kf = self.kf

      # Use delayed curvature for error calculation (delay compensation)
      low_speed_factor = interp(CS.vEgo, [0, 10, 20], [500, 500, 200])
      setpoint = delayed_lateral_accel + low_speed_factor * delayed_curvature
      measurement = actual_lateral_accel + low_speed_factor * actual_curvature
      error = setpoint - measurement
      pid_log.error = error

      ff = desired_lateral_accel - params.roll * ACCELERATION_DUE_TO_GRAVITY
      # Jerk term: anticipate steering transitions
      ff += self.jerk_gain * desired_lateral_jerk
      # Convert friction into lateral accel units for feedforward
      friction_compensation = interp(apply_deadzone(error, lateral_accel_deadzone), [-FRICTION_THRESHOLD, FRICTION_THRESHOLD], [-effective_friction, effective_friction])
      ff += friction_compensation / effective_kf
      freeze_integrator = CS.steeringRateLimited or CS.steeringPressed or CS.vEgo < 5
      output_torque = self.pid.update(error,
                                      feedforward=ff,
                                      speed=CS.vEgo,
                                      freeze_integrator=freeze_integrator)

      # Feed data to live learner (only when learning is enabled)
      if use_learning:
        self.learner.add_point(active, CS.steeringPressed, CS.vEgo, output_torque, actual_lateral_accel)

      pid_log.active = True
      pid_log.p = self.pid.p
      pid_log.i = self.pid.i
      pid_log.d = self.pid.d
      pid_log.f = self.pid.f
      pid_log.output = -output_torque
      pid_log.saturated = self._check_saturation(self.steer_max - abs(output_torque) < 1e-3, CS)
      pid_log.actualLateralAccel = actual_lateral_accel
      pid_log.desiredLateralAccel = desired_lateral_accel

    # TODO left is positive in this convention
    return -output_torque, 0.0, pid_log
