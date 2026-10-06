"""Shared rate control for every export engine (Mbps in saved projects)."""
from __future__ import annotations

import math


def bitrate_bps(project: dict) -> int | None:
    value = project.get("export", {}).get("bitrateMbps")
    if value in (None, ""):
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        raise ValueError("Video bitrate must be a positive number in Mbps") from None
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("Video bitrate must be a positive number in Mbps")
    result = round(rate * 1_000_000)
    if result < 1 or result > 2_147_483_647:
        raise ValueError("Video bitrate exceeds the encoder's supported range")
    return result


def rate_control_args(project: dict) -> list[str]:
    rate = bitrate_bps(project)
    if rate is None:
        return ["-crf", str(project.get("export", {}).get("crf", 18))]
    # CBR with filler: simple scenes must not silently fall far below the user's rate.
    return ["-b:v", str(rate), "-minrate", str(rate), "-maxrate", str(rate),
            "-bufsize", str(rate), "-x264-params", "nal-hrd=cbr:filler=1"]
