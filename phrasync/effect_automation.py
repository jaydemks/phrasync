"""Validate bounded, deterministic effect automation from saved projects."""
import math

MODES = {'beat', 'transient', 'audio', 'constant', 'off'}


def validate_automation(background, limits):
    def number(value, name, minimum, maximum):
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f'Invalid effect {name}') from None
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f'Invalid effect {name}')
        return value

    settings = background.get('effectSettings', {})
    if settings is None: settings = {}
    if not isinstance(settings, dict):
        raise ValueError('Invalid global effect timing settings')
    for kind, item in settings.items():
        if kind not in limits or kind == 'bpm' or not isinstance(item, dict) or item.get('mode') not in MODES:
            raise ValueError('Unknown global effect timing')
        number(item.get('division', 1), 'beat division', .25, 8)
    clips = background.get('effectClips', [])
    if clips is None: clips = []
    if not isinstance(clips, list) or len(clips) > 256:
        raise ValueError('Use at most 256 timeline effects')
    identifiers = set()
    for clip in clips:
        if not isinstance(clip, dict) or clip.get('kind') not in limits or clip['kind'] == 'bpm':
            raise ValueError('Unknown timeline effect')
        identifier = clip.get('id')
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 128 or identifier in identifiers:
            raise ValueError('Invalid or duplicate timeline effect ID')
        identifiers.add(identifier)
        start = number(clip.get('start'), 'start', 0, 86400)
        end = number(clip.get('end'), 'end', 0, 86400)
        if end <= start:
            raise ValueError('Effect end must follow its start')
        number(clip.get('amount'), 'intensity', 0, limits[clip['kind']])
        number(clip.get('division', 1), 'beat division', .25, 8)
        number(clip.get('attack', .025), 'fade in', 0, 86400)
        number(clip.get('release', (end-start)*.8), 'fade out', 0, 86400)
        if clip.get('mode', 'one-shot') not in MODES | {'one-shot'}:
            raise ValueError('Unknown timeline effect trigger')
        if type(clip.get('track', 0)) is not int or not 0 <= clip.get('track', 0) < 4:
            raise ValueError('Unknown effect track')
        if not isinstance(clip.get('enabled', True), bool):
            raise ValueError('Invalid effect enabled state')
