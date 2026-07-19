#!/usr/bin/env python3
import os
import signal
import subprocess
import textwrap
from pathlib import Path
from typing import List, Optional

# NOTE: Do NOT import anything here that needs be built (e.g. params)
from common.basedir import BASEDIR
from common.spinner import Spinner
from common.text_window import TextWindow
from selfdrive.hardware import TICI
from selfdrive.swaglog import cloudlog, add_file_handler
from selfdrive.version import is_dirty

MAX_CACHE_SIZE = 4e9 if "CI" in os.environ else 2e9
CACHE_DIR = Path("/data/scons_cache" if TICI else "/tmp/scons_cache")

TOTAL_SCONS_NODES = 2405
MAX_BUILD_PROGRESS = 100
PREBUILT = os.path.exists(os.path.join(BASEDIR, 'prebuilt'))
SIGKILL_RETURN_CODE = -getattr(signal, 'SIGKILL', 9)


def _build_jobs(cpu_count: Optional[int]) -> List[int]:
  initial_jobs = max(1, (cpu_count or 2) - 1)
  return list(dict.fromkeys((initial_jobs, (initial_jobs + 1) // 2, 1)))


def _is_oom_failure(returncode: int, output: List[bytes]) -> bool:
  error_output = b'\n'.join(output).lower()
  oom_markers = (
    b'out of memory',
    b'cannot allocate memory',
    b'virtual memory exhausted',
    b'killed signal',
    b'fatal error: killed',
    b'internal compiler error: killed',
    b'unable to execute command: killed',
  )
  return returncode == SIGKILL_RETURN_CODE or any(marker in error_output for marker in oom_markers)


def build(spinner: Spinner, dirty: bool = False) -> None:
  env = os.environ.copy()
  env['SCONS_PROGRESS'] = "1"
  job_counts = _build_jobs(os.cpu_count())
  compile_output: List[bytes] = []

  # C2 can run out of memory during parallel builds. Preserve the existing
  # initial parallelism and only retry OOM failures with fewer workers.
  for attempt, jobs in enumerate(job_counts):
    compile_output.clear()
    scons = subprocess.Popen(["scons", f"-j{jobs}", "--cache-populate"], cwd=BASEDIR, env=env, stderr=subprocess.PIPE)
    assert scons.stderr is not None

    # Read progress from stderr and update spinner
    while scons.poll() is None:
      try:
        line = scons.stderr.readline()
        if line is None:
          continue
        line = line.rstrip()

        prefix = b'progress: '
        if line.startswith(prefix):
          i = int(line[len(prefix):])
          spinner.update_progress(MAX_BUILD_PROGRESS * min(1., i / TOTAL_SCONS_NODES), 100.)
        elif len(line):
          compile_output.append(line)
          print(line.decode('utf8', 'replace'))
      except Exception:
        pass

    compile_output += [line for line in scons.stderr.read().split(b'\n') if line]
    if scons.returncode == 0:
      break

    if attempt == len(job_counts) - 1 or not _is_oom_failure(scons.returncode, compile_output):
      break

    print(f"scons build ran out of memory with -j{jobs}; retrying with -j{job_counts[attempt + 1]}")

  if scons.returncode != 0:
    # Build failed log errors
    decoded_output = [line.decode('utf8', 'replace') for line in compile_output]
    errors = [line for line in decoded_output
              if any(err in line.lower() for err in ['error: ', 'not found, needed by target', 'out of memory', 'killed'])]
    if not errors:
      errors = decoded_output[-20:]
    error_s = "\n".join(errors)
    add_file_handler(cloudlog)
    cloudlog.error("scons build failed\n" + error_s)

    # Show TextWindow
    spinner.close()
    if not os.getenv("CI"):
      error_s = "\n \n".join("\n".join(textwrap.wrap(e, 65)) for e in errors)
      with TextWindow("openpilot failed to build\n \n" + error_s) as t:
        t.wait_for_exit()
    exit(1)

  # enforce max cache size
  cache_files = [f for f in CACHE_DIR.rglob('*') if f.is_file()]
  cache_files.sort(key=lambda f: f.stat().st_mtime)
  cache_size = sum(f.stat().st_size for f in cache_files)
  for f in cache_files:
    if cache_size < MAX_CACHE_SIZE:
      break
    cache_size -= f.stat().st_size
    f.unlink()


if __name__ == "__main__" and not PREBUILT:
  spinner = Spinner()
  spinner.update_progress(0, 100)
  build(spinner, is_dirty())
