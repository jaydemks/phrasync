"""Microsoft Store updates for the packaged Windows application.

This module deliberately does not fetch installers from third-party URLs. The
Store remains responsible for selecting, downloading and installing packages.
"""

from __future__ import annotations

import ctypes
import sys
from typing import Any


class StoreUpdateUnavailable(RuntimeError):
    pass


def package_identity() -> str | None:
    """Return the active MSIX identity, or None for the portable preview."""
    if sys.platform != "win32":
        return None
    length = ctypes.c_uint32(0)
    get_name = ctypes.windll.kernel32.GetCurrentPackageFullName
    result = get_name(ctypes.byref(length), None)
    if result != 122 or not length.value:  # ERROR_INSUFFICIENT_BUFFER
        return None
    buffer = ctypes.create_unicode_buffer(length.value)
    if get_name(ctypes.byref(length), buffer) != 0:
        return None
    return buffer.value


def _context() -> Any:
    if not package_identity():
        raise StoreUpdateUnavailable("Store updates are available in the Microsoft Store installation of Phrasync.")
    try:
        from winrt.windows.services.store import StoreContext
        return StoreContext.get_default()
    except (ImportError, OSError, RuntimeError) as exc:
        raise StoreUpdateUnavailable("The Microsoft Store update service is unavailable on this device.") from exc


async def check_updates() -> dict[str, Any]:
    context = _context()
    try:
        updates = await context.get_app_and_optional_store_package_updates_async()
    except (OSError, RuntimeError) as exc:
        raise StoreUpdateUnavailable("Could not check Microsoft Store for updates. Try again later or open the Store listing.") from exc
    return {"available": len(updates) > 0, "count": len(updates)}


async def install_updates() -> dict[str, Any]:
    """Re-query before installing; never trust a previous UI check."""
    context = _context()
    try:
        updates = await context.get_app_and_optional_store_package_updates_async()
        if not updates:
            return {"available": False, "state": "up-to-date"}
        result = await context.request_download_and_install_store_package_updates_async(updates)
        state = str(result.overall_state).split(".")[-1].lower()
        return {"available": True, "state": state}
    except (OSError, RuntimeError) as exc:
        raise StoreUpdateUnavailable("The Microsoft Store could not install the update. Open its listing and try again.") from exc
