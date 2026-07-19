#!/usr/bin/env python3
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from common.conversions import Conversions as CV
from selfdrive.car.hyundai.carstate import CarState
from selfdrive.car.hyundai.values import Buttons


class FakeSubMaster:
  def __init__(self, v_cruise):
    self.v_cruise = v_cruise

  def update(self, timeout):
    pass

  def __getitem__(self, service):
    return SimpleNamespace(vCruise=self.v_cruise)


def make_car_state(local_speed=80, base_kph=80, controls_speed=70, stock_speed=70,
                   button=Buttons.NONE, previous_button=Buttons.NONE, previous_local_button=False,
                   active=True, standstill=False, five=False, held_frames=0, vehicle_speed=70,
                   is_mph=False, saved_unit_is_mph=False):
  cs = CarState.__new__(CarState)
  cs.sm = FakeSubMaster(controls_speed)
  cs.cruise_set_speed_kph = local_speed
  cs.cruise_set_speed_kph_base = base_kph
  cs.cruise_set_speed_is_mph = saved_unit_is_mph
  cs.VSetDis = stock_speed
  cs.cruise_buttons = button
  cs.prev_cruise_buttons = previous_button
  cs.prev_cruise_btn = previous_local_button
  cs.cruise_buttons_time = held_frames
  cs.cruise_active = active
  cs.cruiseState_standstill = standstill
  cs.set_spd_five = five
  cs.clu_Vanz = vehicle_speed
  cs.is_set_speed_in_mph = is_mph
  cs.cruise_set_mode = 1
  cs.prev_acc_set_btn = True
  cs.acc_active = True
  return cs


class TestHyundaiCruiseLifecycle(unittest.TestCase):
  def test_dynamic_target_does_not_rebase_driver_maximum(self):
    cs = make_car_state(button=Buttons.RES_ACCEL)
    self.assertEqual(cs.cruise_speed_button(), 81)

    cs.cruise_buttons = Buttons.NONE
    cs.prev_cruise_btn = Buttons.RES_ACCEL
    self.assertEqual(cs.cruise_speed_button(), 81)

  def test_restart_restores_ignition_scoped_maximum(self):
    cs = make_car_state(local_speed=0, base_kph=80, saved_unit_is_mph=None)
    self.assertEqual(cs.cruise_speed_button(), 80)

  def test_display_unit_change_preserves_canonical_speed(self):
    cs = make_car_state(is_mph=True)
    cs.restore_cruise_speed_unit()
    self.assertEqual(cs.cruise_set_speed_kph, round(80 * CV.KPH_TO_MPH))

    cs.is_set_speed_in_mph = False
    cs.restore_cruise_speed_unit()
    self.assertEqual(cs.cruise_set_speed_kph, 80)

  @patch("selfdrive.car.hyundai.carstate.put_nonblocking")
  def test_physical_change_persists_in_kph(self, put_mock):
    cs = make_car_state(local_speed=51, is_mph=True, saved_unit_is_mph=True,
                        button=Buttons.RES_ACCEL)
    cs.persist_cruise_speed()

    put_mock.assert_called_once_with("OpkrCruiseMaxSpeed", "{:.3f}".format(51 * CV.MPH_TO_KPH))

  def test_standstill_resume_does_not_change_maximum(self):
    cs = make_car_state(button=Buttons.RES_ACCEL, standstill=True)
    self.assertEqual(cs.cruise_speed_button(), 80)

  def test_long_press_adopts_stock_cluster_value(self):
    cs = make_car_state(button=Buttons.RES_ACCEL, held_frames=59, stock_speed=75)
    self.assertEqual(cs.cruise_speed_button(), 75)

  def test_existing_five_unit_behavior_is_preserved(self):
    cs = make_car_state(local_speed=82, base_kph=82, button=Buttons.RES_ACCEL, five=True)
    self.assertEqual(cs.cruise_speed_button(), 85)


if __name__ == "__main__":
  unittest.main()
