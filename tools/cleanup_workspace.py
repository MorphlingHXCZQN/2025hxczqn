"""Utility to clear ignored binary artefacts from the workspace.

This script removes the ``outputs`` directory contents and any cached files under
``data`` that are ignored by Git, helping keep the repository free of binaries
before preparing a pull request.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

IGNORED_FOLDERS = (Path("outputs"), Path("data"))
PRESERVED_NAMES = {".gitkeep", "README.md"}


def purge_folder(folder: Path, dry_run: bool = False) -> None:
    if not folder.exists():
        return
    for child in folder.iterdir():
        if child.name in PRESERVED_NAMES:
            continue
        if child.name.startswith("."):
            continue
        if child.is_dir():
            if dry_run:
                print(f"Would remove directory: {child}")
            else:
                shutil.rmtree(child)
        else:
            if dry_run:
                print(f"Would remove file: {child}")
            else:
                child.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean ignored binary artefacts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the files that would be removed without deleting them.",
    )
    args = parser.parse_args()

    for folder in IGNORED_FOLDERS:
        purge_folder(folder, dry_run=args.dry_run)


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
