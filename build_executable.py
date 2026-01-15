"""
Build script for creating standalone executable.

Usage:
    python build_executable.py

This will create:
    - dist/run_suites/run_suites.exe  (Windows)
    - dist/run_suites/run_suites      (Linux)

The dist/run_suites/ folder contains everything needed to run
without Python installed on the target machine.
"""

import subprocess
import sys
import shutil
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True


def build_executable(onefile=False):
    """Build the executable using PyInstaller."""

    project_dir = Path(__file__).parent

    # Core modules to include
    modules = [
        'run_suites.py',
        'manifest_loader.py',
        'config_loader.py',
        'file_processor.py',
        'csv_processor.py',
        'csv_modifier.py',
        'excel_processor.py',
        'excel_modifier.py',
        'validator.py',
        'reporter.py',
        'aggregate_reporter.py',
        'batch_executor.py',
    ]

    # Verify all modules exist
    for module in modules:
        if not (project_dir / module).exists():
            print(f"ERROR: Module not found: {module}")
            return False

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "run_suites",
        "--console",  # CLI application
        "--noconfirm",  # Overwrite without asking
        # Hidden imports for SQLAlchemy dialects
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "sqlalchemy.dialects.postgresql",
        "--hidden-import", "sqlalchemy.dialects.mysql",
        # Paramiko
        "--hidden-import", "paramiko",
        # Excel support
        "--hidden-import", "openpyxl",
        "--hidden-import", "xlrd",
        # Exclude unnecessary packages
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "pytest",
    ]

    if onefile:
        cmd.append("--onefile")  # Single executable (slower startup)
    else:
        cmd.append("--onedir")   # Folder with executable (faster startup)

    cmd.append("run_suites.py")

    print("Building executable...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=project_dir)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        if onefile:
            exe_path = project_dir / "dist" / ("run_suites.exe" if sys.platform == "win32" else "run_suites")
            print(f"Executable: {exe_path}")
        else:
            dist_dir = project_dir / "dist" / "run_suites"
            print(f"Output folder: {dist_dir}")
            print()
            print("Copy the entire 'dist/run_suites' folder to target machine.")
        print()
        print("Usage on target machine:")
        print("  run_suites manifest.yaml")
        print("  run_suites manifest.yaml --suite 'My Suite'")
        return True
    else:
        print("BUILD FAILED!")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build standalone executable")
    parser.add_argument("--onefile", action="store_true",
                       help="Create single executable file (slower startup, easier to distribute)")
    args = parser.parse_args()

    print("PASS Flow Testing Engine - Executable Builder")
    print("=" * 60)

    if not check_pyinstaller():
        sys.exit(1)

    if build_executable(onefile=args.onefile):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
