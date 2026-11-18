# Third-Party Licenses

SubtitleStudio relies on the following third-party components. Full license texts can be found in the referenced documentation or web sources.

---

## 1. FFmpeg (External Binary)
* **Component:** Unmodified `ffmpeg.exe` and `ffprobe.exe` run as separate external processes via `subprocess` without linking to FFmpeg libraries.
* **License:** GNU General Public License (GPL) version 3 (Gyan.dev essentials build `2026-11-11-git-23c4540053`).
* **Source Code & Legal:** Available at [FFmpeg Legal](https://ffmpeg.org) and [FFmpeg Download](https://ffmpeg.org). Users may replace the binaries with their own builds. A 3-year source code offer is available via maintainer `Dimuth De Zoysa` (https://github.com).

---

## 2. PySide6 (Qt for Python)
* **Component:** Dynamically linked GUI framework (`PySide6`, `PySide6_Addons`, `PySide6_Essentials`).
* **License:** GNU Lesser General Public License (LGPL) version 3 (The Qt Company Ltd.).

---

## 3. Speech Recognition & Inference Libraries (MIT License)
The following Python packages are bundled under the MIT License:
* **faster-whisper** — Copyright (c) 2023 SYSTRAN (https://github.com)
* **CTranslate2** — Copyright (c) 2020–2026 OpenNMT (https://github.com)
* **truststore** — Copyright (c) 2022 Seth Michael Larson (https://github.com)
* **OpenAI Whisper** (Architecture) — Copyright (c) 2022 OpenAI

---

## 4. NumPy
* **Component:** Audio waveform processing.
* **License:** BSD 3-Clause License (Copyright (c) 2005–2026, NumPy Developers).

---

## 5. Python Runtime
* **Component:** Bundled Python interpreter and standard library.
* **License:** Python Software Foundation License Version 2 (PSF).

---

## 6. Speech Recognition Models (On-Demand Download)
* **Models:** Downloaded directly by the user from Hugging Face upon first use (not pre-bundled):
  * English / Multilingual Whisper Models (`Systran/faster-whisper-*`): MIT License
  * Sinhala Fine-Tuned Models (`SinhaSpeech/whisper-small-sinhala-*`): Governed by respective Hugging Face model terms
