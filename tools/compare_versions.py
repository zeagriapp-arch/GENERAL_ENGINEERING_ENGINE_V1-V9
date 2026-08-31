#!/usr/bin/env python3
"""
Compara dos versiones: qué archivos se añadieron, cuáles cambiaron de
contenido, y la diferencia en número de tests.

Uso:
    python tools/compare_versions.py v04_design v05_optimization
"""
from __future__ import annotations

import argparse
import filecmp
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS_DIR = ROOT / "versions"

IGNORE_PATTERNS = {"__pycache__", ".pytest_cache", ".hypothesis", "*.pyc", "*.db", ".import_linter_cache"}


def collect_files(version_dir: Path) -> set[str]:
    files = set()
    for p in version_dir.rglob("*"):
        if p.is_file() and not any(part in IGNORE_PATTERNS for part in p.parts):
            files.add(str(p.relative_to(version_dir)))
    return files


def count_tests(version_dir: Path) -> str:
    import os

    env = {**os.environ, "PYTHONPATH": str(version_dir)}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"],
        cwd=version_dir, env=env, capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if "tests collected" in line or "test collected" in line:
            return line.strip()
    return "(no se pudo determinar)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_a")
    parser.add_argument("version_b")
    args = parser.parse_args()

    dir_a = VERSIONS_DIR / args.version_a
    dir_b = VERSIONS_DIR / args.version_b
    for d in (dir_a, dir_b):
        if not d.is_dir():
            print(f"Versión no encontrada: {d}", file=sys.stderr)
            sys.exit(1)

    files_a = collect_files(dir_a)
    files_b = collect_files(dir_b)

    only_in_b = sorted(files_b - files_a)
    only_in_a = sorted(files_a - files_b)
    common = files_a & files_b

    changed = []
    for rel in sorted(common):
        if not filecmp.cmp(dir_a / rel, dir_b / rel, shallow=False):
            changed.append(rel)

    print(f"=== {args.version_a} -> {args.version_b} ===\n")
    print(f"Archivos nuevos en {args.version_b} ({len(only_in_b)}):")
    for f in only_in_b:
        print(f"  + {f}")
    if only_in_a:
        print(f"\nArchivos presentes en {args.version_a} pero AUSENTES en {args.version_b} ({len(only_in_a)}):")
        for f in only_in_a:
            print(f"  - {f}")
    print(f"\nArchivos modificados ({len(changed)}):")
    for f in changed:
        print(f"  ~ {f}")

    print(f"\nTests {args.version_a}: {count_tests(dir_a)}")
    print(f"Tests {args.version_b}: {count_tests(dir_b)}")


if __name__ == "__main__":
    main()
