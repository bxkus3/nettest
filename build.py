#!/usr/bin/env python3
"""Build helper. Runs pyinstaller with the spec file."""
import subprocess, sys, os

here = os.path.dirname(os.path.abspath(__file__))
spec = os.path.join(here, "nettest.spec")

subprocess.run([sys.executable, "-m", "PyInstaller", spec, "--clean", "--noconfirm"])
print("Done. Check dist/ folder.")
