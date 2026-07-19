#!/usr/bin/env python3
import os
import tempfile
import unittest
from pathlib import Path

from selfdrive.loggerd.clear_logs import clear_driving_logs


class OffroadSequence:
  def __init__(self, *states):
    self.states = list(states)

  def __call__(self):
    return self.states.pop(0)


class TestClearDrivingLogs(unittest.TestCase):
  def setUp(self):
    self.tempdir = tempfile.TemporaryDirectory()
    self.root = Path(self.tempdir.name) / "realdata"
    self.root.mkdir()

  def tearDown(self):
    self.tempdir.cleanup()

  def make_route(self, name, *files):
    route = self.root / name
    route.mkdir()
    for filename in files:
      (route / filename).write_bytes(b"log")
    return route

  def test_deletes_routes_hidden_entries_and_top_level_files(self):
    self.make_route("route", "rlog.bz2")
    self.make_route(".hidden-route", "qlog.bz2")
    (self.root / ".stale").write_bytes(b"stale")

    result = clear_driving_logs(self.root, lambda: True)

    self.assertEqual(result.deleted, 3)
    self.assertFalse(any(self.root.iterdir()))
    self.assertEqual(result.errors, 0)

  def test_preserves_boot_crash_and_locked_active_route(self):
    self.make_route("boot", "bootlog")
    self.make_route("crash", "error.txt")
    locked_route = self.make_route("active", "rlog.lock")
    old_route = self.make_route("old", "rlog.bz2")

    result = clear_driving_logs(self.root, lambda: True)

    self.assertTrue((self.root / "boot").exists())
    self.assertTrue((self.root / "crash").exists())
    self.assertTrue(locked_route.exists())
    self.assertFalse(old_route.exists())
    self.assertEqual((result.deleted, result.locked, result.preserved), (1, 1, 2))

  def test_aborts_before_next_deletion_when_vehicle_goes_onroad(self):
    self.make_route("a", "rlog.bz2")
    self.make_route("b", "rlog.bz2")

    result = clear_driving_logs(self.root, OffroadSequence(True, False))

    self.assertTrue(result.aborted)
    self.assertEqual(result.deleted, 1)
    self.assertEqual(len(list(self.root.iterdir())), 1)

  @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
  def test_refuses_root_and_top_level_symlinks(self):
    outside = Path(self.tempdir.name) / "outside"
    outside.mkdir()
    outside_log = outside / "outside.log"
    outside_log.write_bytes(b"keep")
    link = self.root / "linked-route"
    try:
      os.symlink(str(outside), str(link), target_is_directory=True)
    except OSError as error:
      self.skipTest(f"symlink creation unavailable: {error}")

    result = clear_driving_logs(self.root, lambda: True)
    self.assertEqual(result.errors, 1)
    self.assertTrue(outside_log.exists())

    root_link = Path(self.tempdir.name) / "realdata-link"
    os.symlink(str(self.root), str(root_link), target_is_directory=True)
    linked_result = clear_driving_logs(root_link, lambda: True)
    self.assertEqual(linked_result.errors, 1)
    self.assertTrue(outside_log.exists())


if __name__ == "__main__":
  unittest.main()
