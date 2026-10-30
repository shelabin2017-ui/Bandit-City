# zeroMER — channel branding

This folder contains the channel identity assets only. It is separate from the Bandit City game source.

## Deliverables
- `01-youtube-banner/zeroMER-banner.svg` — YouTube banner, 2560×1440.
- `02-youtube-avatar/zeroMER-avatar.svg` — channel avatar, 1024×1024.
- `03-obs/zeroMER-obs-overlay.svg` — OBS overlay, 1920×1080 with transparent gameplay area.

## Art direction
- Exact brand spelling: **zeroMER**.
- Theme: SAMP / GTA, sunset city, palm trees, sports car, street culture.
- Palette: asphalt black, sunset orange, warm cream, muted burgundy.
- Stream target: Full HD 1920×1080.
- Intro/outro: planned as separate animated exports for Runway.

## Quality and export
All three master assets are SVG vector files. They are resolution-independent and can be scaled without pixelation. Keep the SVG files as masters.
- YouTube banner: export to PNG at 2560×1440. Keep important text/logo inside the central YouTube safe area (1546×423).
- Avatar: export to PNG at 1024×1024 (YouTube will crop it to a circle).
- OBS overlay: use SVG directly if your OBS build supports it; otherwise export a transparent PNG at 1920×1080.
- For Runway, export the logo and background separately as PNG where possible; do not use a screenshot of a preview as the source.

## OBS setup
Add the overlay as an Image source above Game Capture. Put the webcam source in the lower-left frame and the chat browser source in the right-side panel. Resize/reposition the sources to fit the frames. The SVG supplies the decorative overlay only; it does not contain a working chat, webcam feed, or animated elements.

## Not included yet
These are polished, editable static vector masters. Animated intro/outro MP4 files, music, sound effects, and final raster PNG exports are not included yet; those are the next production stage in Runway/editor.
