# Third-Party Licenses

SubtitleStudio uses the components below. Each remains under its own license, and
none of them is covered by the SubtitleStudio license (see `LICENSE`).

## FFmpeg

SubtitleStudio ships the unmodified `ffmpeg.exe` and `ffprobe.exe` programs in the
`ffmpeg` folder and runs them as separate programs. It does not link to FFmpeg
libraries.

- Website and legal page: https://ffmpeg.org/legal.html
- Build used: gyan.dev "essentials" build, version 2026-11-11-git-23c4540053
  (Build page: https://www.gyan.dev/ffmpeg/builds/)
- Source code: https://ffmpeg.org/download.html and https://git.ffmpeg.org/ffmpeg.git (commit 23c4540053)
- License of this build: **GNU General Public License (GPL) version 3**
  (configured with `--enable-gpl --enable-version3`, without `--enable-nonfree`)

FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project.
The FFmpeg project is licensed under the LGPL v2.1 or later. The build shipped here
includes GPL-licensed parts, so this build as a whole is distributed under the GPL v3.
The full license text is in the `ffmpeg\licenses` folder next to the app (`LICENSE`,
copied unchanged from the gyan.dev download).

**Source code offer.** As required by the GPL/LGPL, the complete corresponding source
code of the FFmpeg version shipped with SubtitleStudio is available at the Source
code link above. If that link is unavailable, contact the SubtitleStudio maintainer
via the GitHub repository and the source will be provided on request, for at least
three years after the release.

You may replace `ffmpeg.exe` and `ffprobe.exe` in the `ffmpeg` folder with your own
builds of FFmpeg.

## OpenAI Whisper

Speech-recognition models and code by OpenAI. License: MIT.
https://github.com/openai/whisper

## faster-whisper / CTranslate2

Optimised Whisper inference by SYSTRAN. License: MIT.
https://github.com/SYSTRAN/faster-whisper
https://github.com/OpenNMT/CTranslate2

## Sinhala speech models

**[FILL IN: model name, author and license, e.g. SinhalaSpeech run12, from its model page.]**
Models are downloaded on first use and are not part of the SubtitleStudio
installer. Their licenses may restrict commercial use.

## Python and other libraries

**[FILL IN from your `requirements.txt`: each package, its license and link.]**
You can list them with: `pip install pip-licenses` then `pip-licenses --format=markdown`

## Installer

Created with Inno Setup (c) Jordan Russell and Martijn Laan.
License: https://jrsoftware.org/files/is/license.txt
