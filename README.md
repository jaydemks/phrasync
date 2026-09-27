<p align="center"><img src="docs/media/phrasync-mark.svg" alt="Phrasync" width="76"></p>

# Phrasync

Phrasync helps you turn songs into lyric videos and long recordings into subtitles. You can correct the words and their timing, choose a look, preview the result, and export an MP4. Your media and transcription stay on your computer; the speech model is downloaded once when you first need it.

Phrasync is free and open source, made by [jaydemks](https://github.com/jaydemks). The Windows app is available on the [Microsoft Store](https://apps.microsoft.com/detail/9NF9JBG2PKHX). Store updates can arrive after the matching source release while Microsoft completes certification.

## What has changed

Since the first GitHub release, Phrasync has gained a proper Windows app window, an English/Italian interface, clearer model-download progress, and automatic NVIDIA GPU support where available. The editor now handles longer subtitle projects, offers richer 3D scenes (including **Lost in the Ocean**), and gives you more control over lyric timing and text perspective.

Recent fixes also make MP4 export easier: choose a destination before rendering, open either the chosen or default renders folder, save the finished video, and render Japanese text with a suitable font. Version **0.4.3** addresses unresponsive controls after an in-place Store update and adds an in-app update check plus a diagnostics panel for sharing useful error, Windows, and hardware details with support.

If you installed an earlier Store version, uninstall it **once** and install the new version from the Store to clear old app data. Back up any important projects first. Later Store updates can be checked from **Settings → App updates** inside Phrasync. The update-installation flow still needs verification against a subsequent Store release.

For individual changes and known limits, see [release notes](RELEASE_NOTES.md).

## Run from source

On Windows, install Python 3.11 or 3.12, clone this repository, and run `run_windows.bat`. The first launch sets up the local environment. Linux and macOS launch scripts are included, but the current desktop release is tested on Windows.

Phrasync uses local Faster-Whisper transcription and FFmpeg for export. Downloading dependencies and speech models needs an internet connection; editing and rendering do not require a cloud account. Transcription and alignment can still need human correction, especially with expressive vocals or difficult audio.

## License

The code is licensed under [Apache-2.0](LICENSE). Keep [NOTICE](NOTICE) and the applicable [third-party notices](THIRD_PARTY_NOTICES.md) when redistributing the software. Videos you create remain yours, subject to your rights in the music, footage, images, and fonts you use.
