"""
주행 통계 모듈 — 인게이지/디스인게이지/수동개입을 트립 단위로 기록

로그 위치: /data/stats/drive_stats/
100Hz 루프에 부하 최소화: 카운터 증가만 하고, 파일 I/O는 디스인게이지 시에만 발생
"""
import os
import json
import time
from datetime import datetime

from selfdrive.controls.lib.events import ET, EVENT_NAME

STATS_DIR = "/data/stats/drive_stats"


class DriveStats:
  def __init__(self):
    self._ensure_dir()

    # 트립 전체 통계
    self.trip_start = time.monotonic()
    self.trip_engagements = []  # 각 인게이지 세션 기록

    # 현재 인게이지 세션
    self._session = None

    # 이전 프레임 상태 (전환 감지용)
    self._prev_enabled = False

  def _ensure_dir(self):
    try:
      os.makedirs(STATS_DIR, exist_ok=True)
    except OSError:
      pass

  def update(self, enabled, CS, events):
    """매 프레임(100Hz) 호출. 상태 전환 감지 + 개입 카운트"""
    # 인게이지 전환 감지
    if enabled and not self._prev_enabled:
      self._on_engage(CS)
    elif not enabled and self._prev_enabled:
      self._on_disengage(CS, events)

    # 인게이지 중 수동 개입 카운팅
    if enabled and self._session is not None:
      if CS.steeringPressed:
        self._session["steering_overrides"] += 1
      if CS.brakePressed:
        self._session["brake_interventions"] += 1
      if getattr(CS, 'gasPressed', False):
        self._session["gas_overrides"] += 1
      self._session["frames"] += 1
      self._session["max_speed"] = max(self._session["max_speed"], CS.vEgo * 3.6)

    self._prev_enabled = enabled

  def _on_engage(self, CS):
    """인게이지 시작"""
    self._session = {
      "engage_time": _now_str(),
      "engage_speed_kph": round(CS.vEgo * 3.6, 1),
      "disengage_time": None,
      "disengage_speed_kph": None,
      "disengage_reason": None,
      "disengage_events": [],
      "duration_sec": 0,
      "frames": 0,
      "max_speed": 0,
      "steering_overrides": 0,
      "brake_interventions": 0,
      "gas_overrides": 0,
    }

  def _on_disengage(self, CS, events):
    """디스인게이지 — 세션 마감 + 원인 기록"""
    if self._session is None:
      return

    self._session["disengage_time"] = _now_str()
    self._session["disengage_speed_kph"] = round(CS.vEgo * 3.6, 1)
    self._session["duration_sec"] = round(self._session["frames"] / 100.0, 1)

    # 디스인게이지 원인 분류
    reason, event_names = _classify_disengage(events)
    self._session["disengage_reason"] = reason
    self._session["disengage_events"] = event_names

    self.trip_engagements.append(self._session)
    self._session = None

    # 매 디스인게이지마다 파일에 flush
    self._save()

  def _save(self):
    """트립 통계를 JSON 파일로 저장"""
    try:
      summary = self.get_summary()
      filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
      filepath = os.path.join(STATS_DIR, filename)

      # 최근 파일이 같은 트립이면 덮어쓰기
      existing = _find_latest_file(STATS_DIR)
      if existing and (time.monotonic() - self.trip_start) < 7200:
        filepath = existing

      with open(filepath, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    except Exception:
      pass  # 통계 저장 실패가 주행을 방해하면 안 됨

  def get_summary(self):
    """현재 트립 요약"""
    total_engaged_sec = sum(s["duration_sec"] for s in self.trip_engagements)
    total_steering = sum(s["steering_overrides"] for s in self.trip_engagements)
    total_brake = sum(s["brake_interventions"] for s in self.trip_engagements)

    # 디스인게이지 원인별 집계
    reason_counts = {}
    for s in self.trip_engagements:
      r = s.get("disengage_reason", "unknown")
      reason_counts[r] = reason_counts.get(r, 0) + 1

    return {
      "trip_start": self.trip_engagements[0]["engage_time"] if self.trip_engagements else _now_str(),
      "total_engagements": len(self.trip_engagements),
      "total_engaged_sec": round(total_engaged_sec, 1),
      "total_steering_overrides": total_steering,
      "total_brake_interventions": total_brake,
      "disengage_reasons": reason_counts,
      "sessions": self.trip_engagements,
    }


def _classify_disengage(events):
  """이벤트 목록에서 디스인게이지 원인 분류"""
  event_names = []
  reason = "unknown"

  for e in events.names:
    name = EVENT_NAME.get(e, str(e))
    event_names.append(name)

  # 우선순위: user > immediate > soft
  if events.any(ET.USER_DISABLE):
    reason = "user"  # 운전자가 직접 해제 (버튼, 브레이크)
  elif events.any(ET.IMMEDIATE_DISABLE):
    reason = "error"  # 시스템 오류 (CAN, 센서 등)
  elif events.any(ET.SOFT_DISABLE):
    reason = "soft_error"  # 점진적 해제 (과열, 카메라 등)
  elif events.any(ET.NO_ENTRY):
    reason = "no_entry"

  return reason, event_names


def _now_str():
  return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _find_latest_file(directory):
  """디렉토리에서 가장 최근 JSON 파일 반환"""
  try:
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".json")]
    if not files:
      return None
    return max(files, key=os.path.getmtime)
  except OSError:
    return None
