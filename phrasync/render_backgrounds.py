from __future__ import annotations

import math
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .render_utils import clamp, hex_color


class DynamicBackground:
    def __init__(self, width: int, height: int, style: dict[str, Any], visual: str):
        max_side = 640
        ratio = min(1.0, max_side / max(width, height))
        self.low_width = max(240, int(round(width * ratio)))
        self.low_height = max(240, int(round(height * ratio)))
        self.width = width
        self.height = height
        self.style = style
        self.visual = visual
        self.primary = np.array(hex_color(style.get("backgroundColor"), (8, 8, 18)), dtype=np.float32)
        self.accent = np.array(hex_color(style.get("accentColor"), (223, 92, 255)), dtype=np.float32)
        self.secondary = np.array(hex_color(style.get("secondaryColor"), (92, 215, 255)), dtype=np.float32)
        y, x = np.mgrid[0 : self.low_height, 0 : self.low_width]
        self.x = x.astype(np.float32) / max(1, self.low_width - 1)
        self.y = y.astype(np.float32) / max(1, self.low_height - 1)
        rng = np.random.default_rng(6127)
        count = max(40, int((self.low_width * self.low_height) / 9000))
        self.particles = np.column_stack(
            (
                rng.random(count),
                rng.random(count),
                rng.uniform(0.15, 0.65, count),
                rng.uniform(0.5, 2.2, count),
            )
        )

    def _aurora_array(self, t: float, intensity: float, pulse: float = 0.0) -> np.ndarray:
        base = np.zeros((self.low_height, self.low_width, 3), dtype=np.float32)
        base[:] = self.primary
        # The beat swells the blobs, which is what makes the field feel scored
        # to the track rather than idly drifting.
        swell = 1.0 + 0.26 * pulse
        centers = [
            (0.18 + 0.13 * math.sin(t * 0.31), 0.24 + 0.19 * math.cos(t * 0.23), self.accent, 0.26, 0.95),
            (0.79 + 0.14 * math.cos(t * 0.27), 0.40 + 0.17 * math.sin(t * 0.19), self.secondary, 0.32, 0.82),
            (0.48 + 0.21 * math.sin(t * 0.17), 0.82 + 0.11 * math.cos(t * 0.29), self.accent, 0.36, 0.72),
            (0.62 + 0.17 * math.cos(t * 0.21), 0.16 + 0.12 * math.sin(t * 0.25), self.secondary, 0.24, 0.58),
        ]
        for cx, cy, color, sigma, strength in centers:
            distance = ((self.x - cx) ** 2 + (self.y - cy) ** 2) / max(0.01, sigma * swell)
            glow = np.exp(-distance * 3.2)[..., None]
            # Blend toward the colour rather than adding to it: additive light
            # washes overlapping blobs out to pastel and kills lyric contrast.
            weight = np.clip(glow * strength * (0.34 + intensity * 0.42) * (1.0 + 0.18 * pulse), 0, 1)
            base = base * (1.0 - weight) + color * weight
            base += (glow**3) * color * 0.18 * intensity
        vignette = 1.0 - 0.46 * ((self.x - 0.5) ** 2 + (self.y - 0.5) ** 2)
        base *= np.clip(vignette[..., None], 0.58, 1.0)
        return np.clip(base, 0, 255).astype(np.uint8)

    def render(
        self, t: float, amplitude: float, frame_index: int, pulse: float = 0.0
    ) -> Image.Image:
        intensity = float(self.style.get("visualIntensity", 0.9))
        pulse = max(pulse, amplitude * 0.8)
        if self.visual == "particles":
            arr = self._aurora_array(t * 0.4, intensity * 0.6, pulse)
            image = Image.fromarray(arr, "RGB")
            draw = ImageDraw.Draw(image, "RGBA")
            for px, py, speed, radius in self.particles:
                x = int(((px + t * speed * 0.018) % 1.05) * self.low_width)
                y = int(((py - t * speed * 0.012) % 1.05) * self.low_height)
                r = radius * (0.9 + amplitude * 1.8 + pulse * 0.7)
                color = tuple(int(v) for v in self.accent) + (int(120 + amplitude * 120),)
                draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
        elif self.visual == "grid":
            arr = self._aurora_array(t * 0.18, intensity * 0.45, pulse)
            image = Image.fromarray(arr, "RGB")
            draw = ImageDraw.Draw(image, "RGBA")
            horizon = int(self.low_height * 0.58)
            color = tuple(int(v) for v in self.accent) + (int(min(255, 150 + pulse * 80)),)
            center = self.low_width / 2
            for i in range(-12, 13):
                bottom_x = center + i * self.low_width / 12
                draw.line((center, horizon, bottom_x, self.low_height), fill=color, width=1)
            phase = (t * 0.55) % 1.0
            for row in range(18):
                z = (row + phase) / 18
                y = horizon + int((z**2) * (self.low_height - horizon))
                alpha = int(50 + z * 150)
                draw.line((0, y, self.low_width, y), fill=(*color[:3], alpha), width=1)
        else:
            arr = self._aurora_array(t, intensity, pulse)
            image = Image.fromarray(arr, "RGB")
            if self.visual == "equalizer":
                draw = ImageDraw.Draw(image, "RGBA")
                bars = 36
                gap = max(2, self.low_width // 240)
                bar_width = max(2, (self.low_width - gap * (bars - 1)) // bars)
                total_width = bars * bar_width + (bars - 1) * gap
                x0 = (self.low_width - total_width) // 2
                base_y = int(self.low_height * 0.90)
                for index in range(bars):
                    wave = 0.32 + 0.68 * abs(math.sin(index * 0.63 + t * 3.1))
                    value = clamp((amplitude * 1.1 + wave * 0.26) * (1 + pulse * 0.22))
                    height = int((self.low_height * 0.32) * value)
                    alpha = int(110 + value * 145)
                    color = tuple(int(v) for v in (self.accent * (0.6 + 0.4 * index / bars))) + (alpha,)
                    x = x0 + index * (bar_width + gap)
                    draw.rounded_rectangle((x, base_y - height, x + bar_width, base_y), radius=bar_width // 2, fill=color)

        # Low-cost film grain at the generator resolution.
        grain_amount = float(self.style.get("grain", 0.14))
        if grain_amount > 0:
            rng = np.random.default_rng(frame_index + 113)
            noise = rng.normal(128, 26, (self.low_height, self.low_width)).clip(0, 255).astype(np.uint8)
            noise_image = Image.fromarray(noise, "L").convert("RGB")
            image = Image.blend(image, noise_image, clamp(grain_amount * 0.18, 0, 0.12))
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.Resampling.BILINEAR)
        return image
