#!/usr/bin/env python3
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import selfdrive.manager.build as manager_build


class FakeProcess:
  def __init__(self, returncode, output=b''):
    self.returncode = returncode
    self.stderr = io.BytesIO(output)

  def poll(self):
    return self.returncode


class FakeSpinner:
  def update_progress(self, *args):
    pass

  def close(self):
    pass


class TestBuildRetry(unittest.TestCase):
  def test_build_jobs(self):
    self.assertEqual(manager_build._build_jobs(None), [1])
    self.assertEqual(manager_build._build_jobs(1), [1])
    self.assertEqual(manager_build._build_jobs(4), [3, 2, 1])
    self.assertEqual(manager_build._build_jobs(8), [7, 4, 1])

  def test_oom_detection(self):
    self.assertTrue(manager_build._is_oom_failure(manager_build.SIGKILL_RETURN_CODE, []))
    self.assertTrue(manager_build._is_oom_failure(1, [b'c++: fatal error: Killed signal terminated program cc1plus']))
    self.assertTrue(manager_build._is_oom_failure(1, [b'virtual memory exhausted: Cannot allocate memory']))
    self.assertTrue(manager_build._is_oom_failure(1, [b'internal compiler error: Killed (program cc1plus)']))
    self.assertTrue(manager_build._is_oom_failure(1, [b'clang: error: unable to execute command: Killed']))
    self.assertFalse(manager_build._is_oom_failure(1, [b'file.cc:10: error: unknown symbol']))

  @patch("selfdrive.manager.build.os.cpu_count", return_value=4)
  @patch("selfdrive.manager.build.subprocess.Popen")
  def test_oom_retries_with_fewer_jobs(self, popen_mock, cpu_mock):
    popen_mock.side_effect = [
      FakeProcess(1, b'c++: fatal error: Killed signal terminated program cc1plus'),
      FakeProcess(0),
    ]
    with tempfile.TemporaryDirectory() as cache_dir, \
         patch.object(manager_build, "CACHE_DIR", Path(cache_dir)):
      manager_build.build(FakeSpinner())

    self.assertEqual(popen_mock.call_count, 2)
    self.assertEqual(popen_mock.call_args_list[0].args[0][1], '-j3')
    self.assertEqual(popen_mock.call_args_list[1].args[0][1], '-j2')

  @patch.dict("os.environ", {"CI": "1"})
  @patch("selfdrive.manager.build.add_file_handler")
  @patch("selfdrive.manager.build.cloudlog.error")
  @patch("selfdrive.manager.build.os.cpu_count", return_value=4)
  @patch("selfdrive.manager.build.subprocess.Popen")
  def test_oom_retries_down_to_single_job(self, popen_mock, cpu_mock, cloudlog_mock, handler_mock):
    oom = b'internal compiler error: Killed (program cc1plus)'
    popen_mock.side_effect = [FakeProcess(1, oom), FakeProcess(1, oom), FakeProcess(1, oom)]
    with self.assertRaises(SystemExit):
      manager_build.build(FakeSpinner())

    self.assertEqual([call.args[0][1] for call in popen_mock.call_args_list], ['-j3', '-j2', '-j1'])

  @patch.dict("os.environ", {"CI": "1"})
  @patch("selfdrive.manager.build.add_file_handler")
  @patch("selfdrive.manager.build.cloudlog.error")
  @patch("selfdrive.manager.build.os.cpu_count", return_value=4)
  @patch("selfdrive.manager.build.subprocess.Popen")
  def test_non_oom_error_does_not_retry(self, popen_mock, cpu_mock, cloudlog_mock, handler_mock):
    popen_mock.return_value = FakeProcess(1, b'file.cc:10: error: unknown symbol')
    with self.assertRaises(SystemExit):
      manager_build.build(FakeSpinner())

    self.assertEqual(popen_mock.call_count, 1)


if __name__ == "__main__":
  unittest.main()
