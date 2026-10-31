#!/usr/bin/env python3
"""Post-exec repair helper for Githeri-generated FastAPI projects.

Runs a boot/import check on the generated app. If the failure is a module
importing from itself (common circular import in app/database.py), removes
the self-import and, for the known FastAPI/SQLAlchemy layout, replaces the
file with a minimal database module. Re-checks after repair.
"""
import subprocess
import sys
from pathlib import Path


def run_import_check(code_dir: Path, entrypoint: str = "app/main.py") -> tuple[bool, str]:
    module = entrypoint.replace("/", ".").removesuffix(".py")
    proc = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=str(code_dir),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def self_import_file(code_dir: Path, output: str) -> Path | None:
    # Pattern: cannot import name ... from partially initialized module 'X' ... X.py
    import re
    m = re.search(r"partially initialized module '([^']+)'", output)
    if not m:
        return None
    mod = m.group(1)
    if not mod.endswith(".database"):
        return None
    path = code_dir / (mod.replace(".", "/") + ".py")
    if not path.is_file():
        return None
    content = path.read_text(encoding="utf-8")
    if f"from {mod} import" in content or f"import {mod}" in content:
        return path
    return None


def repair_database(path: Path) -> None:
    path.write_text(
        "import os\n\n"
        "from sqlalchemy import create_engine\n"
        "from sqlalchemy.orm import declarative_base, sessionmaker\n\n"
        'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")\n\n'
        "engine = create_engine(DATABASE_URL, connect_args={\"check_same_thread\": False})\n"
        "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n"
        "Base = declarative_base()\n\n\n"
        "def get_db():\n"
        "    db = SessionLocal()\n"
        "    try:\n"
        "        yield db\n"
        "    finally:\n"
        "        db.close()\n",
        encoding="utf-8",
    )


def main() -> int:
    code_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    entrypoint = sys.argv[2] if len(sys.argv) > 2 else "app/main.py"

    ok, output = run_import_check(code_dir, entrypoint)
    if ok:
        print("Boot check passed.")
        return 0

    print("Boot check failed:")
    print(output)

    target = self_import_file(code_dir, output)
    if target is None:
        # General circular import warning
        if "circular import" in output.lower() or "partially initialized module" in output.lower():
            print("WARNING: Possible circular import detected. Review import order in the failing module.")
        print("No automatic self-import repair available. Escalating.")
        return 1

    print(f"WARNING: Circular import detected in {target}")
    print("Offending import will be removed and the module regenerated.")
    print(f"Repairing self-import in {target}...")
    repair_database(target)

    ok, output = run_import_check(code_dir, entrypoint)
    if ok:
        print("Boot check passed after repair.")
        return 0

    print("Repair failed:")
    print(output)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())