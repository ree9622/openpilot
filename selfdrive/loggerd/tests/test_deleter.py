#!/usr/bin/env python3
import unittest
from unittest.mock import patch

from selfdrive.loggerd.deleter import deleter_thread


class ExitAfterFirstWait:
  def __init__(self):
    self.done = False
    self.waits = []

  def is_set(self):
    return self.done

  def wait(self, seconds):
    self.waits.append(seconds)
    self.done = True


class TestDeleterBackoff(unittest.TestCase):
  @patch("selfdrive.loggerd.deleter.listdir_by_creation", return_value=["route"])
  @patch("selfdrive.loggerd.deleter.get_available_percent", return_value=0)
  @patch("selfdrive.loggerd.deleter.get_available_bytes", return_value=0)
  @patch("selfdrive.loggerd.deleter.os.listdir", return_value=["rlog.lock"])
  def test_locked_routes_back_off(self, listdir_mock, bytes_mock, percent_mock, routes_mock):
    exit_event = ExitAfterFirstWait()
    deleter_thread(exit_event)
    self.assertEqual(exit_event.waits, [30])

  @patch("selfdrive.loggerd.deleter.shutil.rmtree")
  @patch("selfdrive.loggerd.deleter.os.path.isfile", return_value=False)
  @patch("selfdrive.loggerd.deleter.listdir_by_creation", return_value=["route"])
  @patch("selfdrive.loggerd.deleter.get_available_percent", return_value=0)
  @patch("selfdrive.loggerd.deleter.get_available_bytes", return_value=0)
  @patch("selfdrive.loggerd.deleter.os.listdir", return_value=["rlog.bz2"])
  def test_deleted_route_continues_quickly(self, listdir_mock, bytes_mock, percent_mock,
                                           routes_mock, isfile_mock, rmtree_mock):
    exit_event = ExitAfterFirstWait()
    deleter_thread(exit_event)
    self.assertEqual(exit_event.waits, [.1])
    rmtree_mock.assert_called_once()

  @patch("selfdrive.loggerd.deleter.listdir_by_creation", return_value=["route"])
  @patch("selfdrive.loggerd.deleter.get_available_percent", return_value=0)
  @patch("selfdrive.loggerd.deleter.get_available_bytes", return_value=0)
  @patch("selfdrive.loggerd.deleter.os.listdir", side_effect=FileNotFoundError)
  def test_route_removed_by_manual_cleanup_does_not_crash(self, listdir_mock, bytes_mock,
                                                           percent_mock, routes_mock):
    exit_event = ExitAfterFirstWait()
    deleter_thread(exit_event)
    self.assertEqual(exit_event.waits, [30])


if __name__ == "__main__":
  unittest.main()
