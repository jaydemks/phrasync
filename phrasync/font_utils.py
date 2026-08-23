from __future__ import annotations

import os
import platform
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}

_PRESET_NAMES = {
    "impact": [
        "impact.ttf",
        "Impact.ttf",
        "Anton-Regular.ttf",
        "Arial Narrow Bold.ttf",
        "DejaVuSansCondensed-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "condensed": [
        "ARIALNB.TTF",
        "ARIALN.TTF",
        "Arial Narrow Bold.ttf",
        "Arial Narrow.ttf",
        "DejaVuSansCondensed-Bold.ttf",
        "LiberationSansNarrow-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "modern": [
        "arialbd.ttf",
        "arial.ttf",
        "Arial Bold.ttf",
        "Arial.ttf",
        "Helvetica.ttc",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "serif": [
        "timesbd.ttf",
        "georgiab.ttf",
        "Times New Roman Bold.ttf",
        "Georgia Bold.ttf",
        "DejaVuSerif-Bold.ttf",
        "LiberationSerif-Bold.ttf",
    ],
    "bebas": [
        "BebasNeue-Regular.otf",
        "BebasNeue-Regular.ttf",
        "BebasKai.ttf",
        "Anton-Regular.ttf",
        "Oswald-Bold.ttf",
        "DIN Condensed Bold.ttf",
        "DejaVuSansCondensed-Bold.ttf",
        "LiberationSansNarrow-Bold.ttf",
    ],
    "geometric": [
        "Montserrat-Black.ttf",
        "Montserrat-ExtraBold.ttf",
        "Montserrat-Bold.ttf",
        "Futura.ttc",
        "Poppins-Black.otf",
        "ariblk.ttf",
        "Arial Black.ttf",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "rounded": [
        "Poppins-Black.otf",
        "Poppins-Black.ttf",
        "Poppins-ExtraBold.otf",
        "Quicksand-Bold.ttf",
        "Nunito-Black.ttf",
        "VarelaRound-Regular.ttf",
        "CenturyGothic.ttf",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "poster": [
        "NexaBlack.otf",
        "NexaHeavy.otf",
        "seguibl.ttf",
        "ariblk.ttf",
        "Arial Black.ttf",
        "Helvetica.ttc",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "techno": [
        "DINPro-CondBlack.otf",
        "DINPro-CondBold.otf",
        "DIN Condensed Bold.ttf",
        "DINCondensed-Bold.ttf",
        "bahnschrift.ttf",
        "Oswald-Bold.ttf",
        "DejaVuSansCondensed-Bold.ttf",
        "LiberationSansNarrow-Bold.ttf",
    ],
    "script": [
        "segoescb.ttf",
        "segoesc.ttf",
        "Bradley Hand Bold.ttf",
        "Noteworthy.ttc",
        "Caveat-Bold.ttf",
        "Gabriola.ttf",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ],
    "jgothic": [
        "YuGothB.ttc",
        "YuGothM.ttc",
        "meiryob.ttc",
        "msgothic.ttc",
        "HiraginoSans-W7.ttc",
        "NotoSansJP-Bold.otf",
        "DejaVuSans-Bold.ttf",
    ],
    "mono": [
        "consolab.ttf",
        "consola.ttf",
        "Consolas Bold.ttf",
        "Menlo.ttc",
        "DejaVuSansMono-Bold.ttf",
        "LiberationMono-Bold.ttf",
    ],
}


def font_directories() -> list[Path]:
    home = Path.home()
    system = platform.system().lower()
    directories: list[Path] = []
    if system == "windows":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        directories.extend([windir / "Fonts", home / "AppData/Local/Microsoft/Windows/Fonts"])
    elif system == "darwin":
        directories.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
                Path("/Library/Fonts"),
                home / "Library/Fonts",
            ]
        )
    else:
        directories.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                home / ".fonts",
                home / ".local/share/fonts",
            ]
        )
    return [path for path in directories if path.exists()]


@lru_cache(maxsize=1)
def index_fonts() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for directory in font_directories():
        try:
            for path in directory.rglob("*"):
                if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS:
                    result.setdefault(path.name.lower(), path)
        except (OSError, PermissionError):
            continue
    return result


def resolve_font_path(preset: str = "impact", custom_path: Path | None = None) -> Path | None:
    if custom_path and custom_path.exists() and custom_path.suffix.lower() in FONT_EXTENSIONS:
        return custom_path
    index = index_fonts()
    candidates = _PRESET_NAMES.get(preset, _PRESET_NAMES["modern"])
    for candidate in candidates:
        found = index.get(candidate.lower())
        if found:
            return found
    # Last resort: pick any bold font, then any font. This still gives a useful export.
    for name, path in index.items():
        if "bold" in name and "emoji" not in name:
            return path
    return next(iter(index.values()), None)


@lru_cache(maxsize=256)
def _load_font_cached(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, max(8, int(size)))
    except Exception:
        return ImageFont.load_default()


def load_font(size: int, preset: str = "impact", custom_path: Path | None = None):
    resolved = resolve_font_path(preset, custom_path)
    if resolved:
        return _load_font_cached(str(resolved), max(8, int(size)))
    return ImageFont.load_default()


def font_status() -> dict:
    fonts = index_fonts()
    return {
        "count": len(fonts),
        "presets": {name: str(resolve_font_path(name) or "") for name in _PRESET_NAMES},
    }
