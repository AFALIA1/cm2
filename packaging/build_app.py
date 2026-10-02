"""Builds the standalone cm2 app (Python + all deps, no Python needed on the
target machine) into dist/cm2/ with PyInstaller. Same command on every OS:

    python packaging/build_app.py

Run it with the Python that has cm2 + pyinstaller installed (e.g. the venv's).
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    shutil.rmtree(ROOT / "build" / "pyinstaller", ignore_errors=True)
    shutil.rmtree(ROOT / "dist" / "cm2", ignore_errors=True)
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--console",
        "--name", "cm2",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build" / "pyinstaller"),
        "--paths", str(ROOT / "src"),
        # cm2 imports some of its own modules lazily; onvif/zeep load WSDL files at runtime.
        "--collect-submodules", "cm2",
        "--collect-all", "onvif",
        "--collect-all", "zeep",
        "--collect-all", "questionary",
        str(ROOT / "packaging" / "cm2_entry.py"),
    ])
    print(f"Built {ROOT / 'dist' / 'cm2'}")


if __name__ == "__main__":
    main()
