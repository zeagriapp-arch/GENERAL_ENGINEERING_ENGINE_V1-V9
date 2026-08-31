#!/usr/bin/env python3
"""
Empaqueta GENERAL_ENGINEERING_ENGINE completo en un .zip descargable,
excluyendo artefactos de build/test (venvs, __pycache__, caches, *.db)
que no aportan nada al paquete y solo inflan su tamaño.

Uso:
    python tools/package_project.py [ruta_salida.zip]
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT.parent / "GENERAL_ENGINEERING_ENGINE_V1-V9.zip"

EXCLUDE_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", ".hypothesis", ".import_linter_cache", ".git"}
EXCLUDE_SUFFIXES = {".pyc", ".db"}
EXCLUDE_FILE_SUFFIXES_LITERAL = {".egg-info"}


def _should_skip(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    if any(part.endswith(".egg-info") for part in path.parts):
        return True
    return False


def package(output_path: Path) -> None:
    files_written = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if path.is_dir():
                continue
            if _should_skip(path):
                continue
            arcname = Path(ROOT.name) / path.relative_to(ROOT)
            zf.write(path, arcname)
            files_written += 1

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Empaquetado: {output_path} ({files_written} archivos, {size_mb:.2f} MB)")


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    package(output)
