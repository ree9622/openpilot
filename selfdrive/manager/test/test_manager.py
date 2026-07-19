#!/usr/bin/env python3
import os
import signal
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import selfdrive.manager.manager as manager
from selfdrive.hardware import EON, TICI, HARDWARE
from selfdrive.manager.process import DaemonProcess, NativeProcess
from selfdrive.manager.process_config import managed_processes

os.environ['FAKEUPLOAD'] = "1"

# TODO: make eon fast
MAX_STARTUP_TIME = 30 if EON else 15
ALL_PROCESSES = [p.name for p in managed_processes.values() if (type(p) is not DaemonProcess) and p.enabled and (p.name not in ['updated', 'pandad'])]


class TestManager(unittest.TestCase):
  def setUp(self):
    os.environ['PASSIVE'] = '0'
    HARDWARE.set_power_save(False)

  def tearDown(self):
    manager.manager_cleanup()

  def test_manager_prepare(self):
    os.environ['PREPAREONLY'] = '1'
    manager.main()

  def test_startup_time(self):
    for _ in range(10):
      start = time.monotonic()
      os.environ['PREPAREONLY'] = '1'
      manager.main()
      t = time.monotonic() - start
      assert t < MAX_STARTUP_TIME, f"startup took {t}s, expected <{MAX_STARTUP_TIME}s"

  def test_ui_watchdog_config(self):
    expected_watchdog = 10 if EON else (5 if TICI else None)
    self.assertEqual(managed_processes['ui'].watchdog_max_dt, expected_watchdog)
    self.assertEqual(managed_processes['ui'].watchdog_offroad_only, EON)

  def test_offroad_only_watchdog_policy(self):
    proc = NativeProcess("test", ".", ["true"], watchdog_max_dt=1, watchdog_offroad_only=True)
    proc.proc = SimpleNamespace(pid=123, exitcode=None)
    proc.watchdog_seen = True
    with patch("builtins.open", side_effect=OSError), \
         patch("selfdrive.manager.process.sec_since_boot", return_value=10), \
         patch("selfdrive.manager.process.ENABLE_WATCHDOG", True), \
         patch.object(proc, "restart") as restart_mock:
      proc.check_watchdog(started=True)
      restart_mock.assert_not_called()

      proc.check_watchdog(started=False)
      restart_mock.assert_called_once()

  def test_default_watchdog_onroad_policy_is_preserved(self):
    proc = NativeProcess("test", ".", ["true"], watchdog_max_dt=1)
    proc.proc = SimpleNamespace(pid=123, exitcode=None)
    proc.watchdog_seen = True
    with patch("builtins.open", side_effect=OSError), \
         patch("selfdrive.manager.process.sec_since_boot", return_value=10), \
         patch("selfdrive.manager.process.ENABLE_WATCHDOG", True), \
         patch.object(proc, "restart") as restart_mock:
      proc.check_watchdog(started=True)
      restart_mock.assert_called_once()

  # ensure all processes exit cleanly
  def test_clean_exit(self):
    HARDWARE.set_power_save(False)
    manager.manager_prepare()
    for p in ALL_PROCESSES:
      managed_processes[p].start()

    time.sleep(10)

    for p in reversed(ALL_PROCESSES):
      state = managed_processes[p].get_process_state_msg()
      self.assertTrue(state.running, f"{p} not running")

      exit_code = managed_processes[p].stop(retry=False)
      if (TICI and p in ['ui', 'navd']) or (EON and p == 'logcatd'):
        # TODO: make Qt UI exit gracefully
        continue

      # Make sure the process is actually dead
      managed_processes[p].stop()

      # TODO: interrupted blocking read exits with 1 in cereal. use a more unique return code
      exit_codes = [0, 1]
      if managed_processes[p].sigkill:
        exit_codes = [-signal.SIGKILL]
      assert exit_code in exit_codes, f"{p} died with {exit_code}"


if __name__ == "__main__":
  unittest.main()
