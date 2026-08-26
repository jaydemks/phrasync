# Phrasync v0.1.1

Released 2026-08-27.

This patch removes the final-export limitation for Odyssey and world-space typography.

## Highlights

- Odyssey 3D MP4 export now uses the same Three.js/WebGL scene engine as the live preview instead of being blocked by preflight.
- World-space 3D typography exports as real volumetric WebGL geometry over Odyssey, built-in dynamic visuals, images, and videos.
- Flat kinetic typography over Odyssey keeps the WebGL environment and is composited during the final H.264 pass.
- Chrome or Edge runs headlessly for deterministic frame generation; WebCodecs produces H.264 and FFmpeg muxes the original audio into the final MP4.
- Odyssey Flat retains a deterministic CPU raster export path for systems and projects that do not need the WebGL scene.
- The critic now reports the selected WebGL export path as an informational note instead of raising the former preview-only blocking errors.
- Added an explicit `websockets` runtime dependency for the local Chrome DevTools connection.

## Verified for this release

- Real MP4 smoke renders pass for Odyssey 3D with 3D text, Odyssey 3D with flat text, and Aurora with 3D text.
- Every smoke output decodes successfully through FFmpeg.
- The complete suite reports **52 passing tests**.
- The updated server was verified on Windows 11 with OCR, Faster-Whisper, and CUDA still available after restart.

## Current limits

- WebGL MP4 export requires a local Chrome or Edge installation with WebCodecs support.
- Long high-resolution WebGL exports can use substantial browser memory while the encoded H.264 stream is assembled.
- Odyssey Flat is a CPU raster interpretation; choose Odyssey 3D when preview-faithful lighting and geometry are required.
- Linux and macOS launchers remain source-level supported but were not physically verified for this patch.

---

# Phrasync v0.1.0

This is the first public release: useful today, intentionally honest about what still needs engineering.

## Highlights

- Two first-class project modes: **Lyric Video** for music and **Subtitles** for spoken audio or video.
- A video selected in Subtitles mode becomes the transcription source, preview footage, render background, and final audio source without duplicate setup.
- Hierarchical local Faster-Whisper transcription: ten-second language mapping, confidence and silence filtering, stable span smoothing, quiet-boundary snapping, language-locked span decoding, phrase-level language verification, selective corrective re-reading, adaptive fallback, and persisted gauntlet diagnostics.
- Auto follows language changes across a track; one code locks a language, comma-separated codes restrict the candidate set, and `single` keeps one automatically detected language.
- Language metadata is preserved on cues and returned as a dominant language, ordered language list, editable API-level span map, confidence, and diagnostics.
- Seven kinetic 2D typography presets with browser/Python timing parity.
- Seven separately named and tuned 3D typography personalities with independent world-space X/Y offsets.
- Grounded world-space 3D text: phrases are planted on the scene floor and the camera travels past them like other meshes.
- Odyssey 3D environments for Japan, Italy, China, and the USA.
- Manual rain, snow, fog, storms, falling leaves, dawn, day, sunset, night, and four seasons.
- **Automatic journey** mode crossfades daytime and seasonal colour while selecting deterministic weather from the playback clock.
- Image, video, and dynamic backgrounds; local project save/load; critic preflight; cancellable render jobs; H.264 MP4 download and postflight decoding.

## Verified for this release

- 50 automated tests pass in the current release environment.
- A real short MP4 render passes with one video file used for both picture and audio in Subtitles mode.
- Chrome smoke coverage passes for every 2D/3D text composition state over Odyssey 3D, a 2D dynamic visual, image, and video modes; actual MP4 decoding is covered by the integration render above.
- 3D text remains world-planted and completes its fly-past at scene speeds of 20%, 100%, and 260%.
- Weather, daytime, seasons, automatic state changes, project-mode copy, and the 3D preset catalogue pass in the live browser with zero captured exceptions.
- Repeated 244.9-second `large-v3` Auto runs map Italian, Portuguese, French, Spanish, English, and Japanese; recover the opening lyrics; preserve Japanese writing; follow late line-level switches; and produce no false outro after the final vocal.
- Development and physical testing were performed on Windows 11, Ryzen 9 3900X, 32 GB RAM, and RTX 3090 24 GB. Linux and macOS launchers are included but not physically release-tested yet.

## Known limits

- Odyssey Flat, Odyssey 3D, and 3D typography are preview-only in v0.1.0. MP4 preflight blocks them explicitly because the Python renderer does not yet reproduce WebGL output faithfully.
- Full song-length output has not yet been rendered. Current verification uses short engineering renders; complete music videos will be added after publication.
- Projects reference media in the local Phrasync workspace rather than embedding it into a portable archive.
- Browser video preview is intentionally limited to MP4 and WebM; convert MOV, MKV, AVI, and unusual codecs before import.
- The transcription workflow performs strongly on the tested songs, but expressive singing, unusual pronunciation, effects, and closely related languages can still need human review.
- There is no signed installer, automatic updater, or hosted web version.

## Evaluated next-step technology

- Troika Three Text for SDF-quality, multilingual 3D typography.
- JASSUB/libass for professional ASS subtitle parity in browser preview.
- Three.js Sky for physically based atmosphere when deterministic export parity is ready.
- three.quarks only if future VFX outgrow the lightweight deterministic weather system.

Phrasync is created by jaydemks and distributed under Apache-2.0 with attribution preserved through `NOTICE`. Output belongs to its creator, subject to the rights they hold in the source music, text, footage, images, and fonts.
