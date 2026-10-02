"""PyInstaller entry point for the packaged cm2 app.

The packaged binary is both the CLI and the background stream worker: the
manager re-launches it with a hidden `__worker__` first argument (see
cm2.streaming.manager._worker_cmd), since a frozen app has no `python -m`.
"""
import os
import sys

if getattr(sys, "frozen", False):
    # Windows/macOS installers ship ffmpeg + ffprobe next to the cm2 binary;
    # put that directory first on PATH so they're found (and inherited by workers).
    app_dir = os.path.dirname(os.path.realpath(sys.executable))
    os.environ["PATH"] = app_dir + os.pathsep + os.environ.get("PATH", "")

if len(sys.argv) > 1 and sys.argv[1] == "__worker__":
    del sys.argv[1]
    from cm2.streaming import worker
    worker.main()
else:
    from cm2.cli import main
    main()
