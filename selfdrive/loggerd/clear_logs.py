#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path
from typing import Callable, NamedTuple


LOG_ROOT = Path("/data/media/0/realdata")
PRESERVED = {"boot", "crash"}


class ClearResult(NamedTuple):
  deleted: int
  locked: int
  preserved: int
  errors: int
  aborted: bool


def _path_exists(path: Path) -> bool:
  return os.path.lexists(str(path))


def clear_driving_logs(root: Path, is_offroad: Callable[[], bool]) -> ClearResult:
  deleted = locked = preserved = errors = 0

  if root.is_symlink():
    return ClearResult(deleted, locked, preserved, 1, False)
  if not root.exists():
    return ClearResult(deleted, locked, preserved, errors, False)

  try:
    root_resolved = root.resolve(strict=True)
    if not root_resolved.is_dir():
      return ClearResult(deleted, locked, preserved, 1, False)
    entries = list(root.iterdir())
  except OSError:
    return ClearResult(deleted, locked, preserved, 1, False)

  for entry in entries:
    if entry.name in PRESERVED:
      preserved += 1
      continue

    try:
      # Never follow or remove links from the log root.
      if entry.is_symlink() or entry.resolve(strict=False).parent != root_resolved:
        errors += 1
        continue

      if entry.is_dir() and any(child.name.endswith(".lock") for child in entry.iterdir()):
        locked += 1
        continue

      # Recheck immediately before each removal so an onroad transition aborts
      # between routes. A locked active route is never selected above.
      if not is_offroad():
        return ClearResult(deleted, locked, preserved, errors, True)

      if entry.is_dir():
        shutil.rmtree(str(entry))
      else:
        entry.unlink()
      deleted += 1
    except FileNotFoundError:
      # The persistent low-space deleter may have won the same route race.
      deleted += 1
    except OSError:
      if not _path_exists(entry):
        deleted += 1
      else:
        errors += 1

  return ClearResult(deleted, locked, preserved, errors, False)


def _device_is_offroad() -> bool:
  from common.params import Params
  return Params().get_bool("IsOffroad")


def main() -> int:
  if LOG_ROOT.is_symlink():
    result = ClearResult(0, 0, 0, 1, False)
  elif not LOG_ROOT.exists():
    result = ClearResult(0, 0, 0, 0, False)
  else:
    try:
      valid_root = LOG_ROOT.resolve(strict=True) == LOG_ROOT and LOG_ROOT.is_dir()
    except OSError:
      valid_root = False
    result = clear_driving_logs(LOG_ROOT, _device_is_offroad) if valid_root else ClearResult(0, 0, 0, 1, False)

  print(f"DELETED={result.deleted} LOCKED={result.locked} PRESERVED={result.preserved} "
        f"ERRORS={result.errors} ABORTED={int(result.aborted)}")
  if result.aborted:
    return 2
  return 3 if result.errors else 0


if __name__ == "__main__":
  sys.exit(main())
