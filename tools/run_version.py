#!/usr/bin/env python3
"""
Ejecuta los tests y/o el script de demo de una versión específica, con
el PYTHONPATH correctamente aislado a esa carpeta (para garantizar que
no hay fuga de imports entre versiones).

Uso:
    python tools/run_version.py v04_design                 # tests
    python tools/run_version.py v04_design --demo          # script de demo principal
    python tools/run_version.py v04_design --demo <script>  # script de demo específico
    python tools/run_version.py --list                     # lista versiones disponibles
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS_DIR = ROOT / "versions"

# Script principal de demo por versión (el más representativo de esa fase).
DEFAULT_DEMO = {
    "v01_core": "scripts/run_first_experiment.py",
    "v02_knowledge": "scripts/run_first_experiment.py",
    "v03_physics": "scripts/run_phase3_vertical_slice.py",
    "v04_design": "scripts/run_phase4_vertical_slice.py",
    "v05_optimization": "scripts/run_phase5_vertical_slice.py",
    "v06_agents": "scripts/run_phase6_vertical_slice.py",
    "v07_propulsion_domain": "scripts/run_phase6_vertical_slice.py",
    "v08_discovery_report": "scripts/run_phase7_8_vertical_slice.py",
    "v09_advanced_ai": "scripts/run_phase7_8_vertical_slice.py",
}


def list_versions() -> list[str]:
    return sorted(p.name for p in VERSIONS_DIR.iterdir() if p.is_dir())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="ej. v04_design")
    parser.add_argument("--demo", nargs="?", const="__default__", help="corre el script de demo en vez de los tests")
    parser.add_argument("--list", action="store_true", help="lista las versiones disponibles")
    args = parser.parse_args()

    if args.list or not args.version:
        print("Versiones disponibles:")
        for v in list_versions():
            print(f"  {v}")
        return

    version_dir = VERSIONS_DIR / args.version
    if not version_dir.is_dir():
        print(f"Versión '{args.version}' no encontrada. Usa --list para ver las disponibles.", file=sys.stderr)
        sys.exit(1)

    env = {"PYTHONPATH": str(version_dir)}
    import os

    full_env = {**os.environ, **env}

    if args.demo:
        script = args.demo if args.demo != "__default__" else DEFAULT_DEMO.get(args.version)
        if not script:
            print(f"No hay script de demo por defecto para {args.version}.", file=sys.stderr)
            sys.exit(1)
        script_path = version_dir / script
        if not script_path.is_file():
            print(f"Script no encontrado: {script_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Ejecutando {script} en {args.version}...\n")
        subprocess.run([sys.executable, str(script_path)], cwd=version_dir, env=full_env, check=False)
    else:
        print(f"Corriendo tests de {args.version}...\n")
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=version_dir, env=full_env, check=False)


if __name__ == "__main__":
    main()
