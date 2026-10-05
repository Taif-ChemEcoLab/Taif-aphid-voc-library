"""Generate or verify hashes for the curated runtime scientific assets."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "checksums" / "runtime_scientific_assets.sha256"
ASSET_ROOTS = (
    ROOT / "data" / "v1",
    ROOT / "data" / "docking",
    ROOT / "docking_v1",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def current_lines() -> list[str]:
    files = sorted(path for directory in ASSET_ROOTS for path in directory.rglob("*") if path.is_file())
    return [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    lines = current_lines()
    if args.check:
        expected = MANIFEST.read_text(encoding="utf-8").splitlines()
        if lines != expected:
            print("FAIL runtime scientific checksum manifest differs")
            return 1
        print(f"PASS {len(lines)} runtime scientific asset hashes")
        return 0
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"WROTE {len(lines)} runtime scientific asset hashes to {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
