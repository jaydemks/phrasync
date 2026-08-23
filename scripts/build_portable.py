from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
separator = ";" if os.name == "nt" else ":"


def main() -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "Phrasync",
        "--add-data",
        f"{ROOT / 'static'}{separator}static",
        "--add-data",
        f"{ROOT / 'assets'}{separator}assets",
        "--add-data",
        f"{ROOT / 'LICENSE'}{separator}.",
        "--add-data",
        f"{ROOT / 'NOTICE'}{separator}.",
        "--add-data",
        f"{ROOT / 'THIRD_PARTY_NOTICES.md'}{separator}.",
        "--collect-all",
        "imageio_ffmpeg",
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.protocols.websockets.auto",
        str(ROOT / "app.py"),
    ]
    print("Building a portable folder for the current operating system…")
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"Done: {ROOT / 'dist' / 'Phrasync'}")
    print("Build separately on Windows, macOS and Linux for native binaries on each platform.")


if __name__ == "__main__":
    main()
