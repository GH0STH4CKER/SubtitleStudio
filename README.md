# 🎬 SubtitleStudio

A Windows desktop application for generating, editing, styling, and exporting subtitles for videos. SubtitleStudio uses local AI speech recognition and FFmpeg to process your videos on your own PC.

<p align="center">
  <a href="https://github.com/GH0STH4CKER/SubtitleStudio/releases/download/v1.0.0/SubtitleStudio-Setup.exe">
    <img src="https://img.shields.io/badge/Download-Windows%20Installer-635BFF?style=for-the-badge&logo=windows&logoColor=white" alt="Download SubtitleStudio for Windows">
  </a>
  <a href="https://github.com/GH0STH4CKER/SubtitleStudio/releases">
    <img src="https://img.shields.io/badge/View-All%20Releases-222222?style=for-the-badge&logo=github" alt="View all releases">
  </a>
</p>

<p align="center">
  <strong>Windows 10 / 11 · 64-bit</strong>
</p>

## ✨ Features

- 🎥 Import videos in MP4, MKV, MOV, AVI, and M4V formats.
- 🧠 Generate English or Sinhala subtitles using local AI speech recognition.
- 🇱🇰 Use dedicated SinhaSpeech models for Sinhala transcription.
- ⚡ Choose Whisper models: `small`, `medium`, or `large-v3`, or select a Sinhala model.
- 🏎️ Fast mode for quicker transcription and automatic NVIDIA GPU use when available.
- 🎵 Optional Music / singing mode to help capture vocals over music.
- ✏️ Review and edit subtitle text and timestamps.
- ➕ Add or delete subtitle entries and adjust timings using the video playhead.
- 🎨 Customize font, size, bold/italic, text colour, outline, shadow, and background.
- ↔️ Reposition subtitles by dragging them in the video preview.
- 📄 Export subtitles as `.srt` files.
- 🎞️ Export a new MP4 with subtitles permanently burned into the video.
- ⚙️ Automatic GPU video encoding when supported, with CPU fallback.
- 🌗 Light and dark themes.
- 🔒 Video and audio processing happens locally on your computer. Nothing is uploaded.

## ⬇️ Download and install

### Windows installer (recommended)

1. Click the **Download Windows Installer** button above, or [download SubtitleStudio-Setup.exe directly](https://github.com/GH0STH4CKER/SubtitleStudio/releases/download/v1.0.0/SubtitleStudio-Setup.exe).
2. Run `SubtitleStudio-Setup.exe`.
3. Follow the setup instructions to install the application.
4. Launch SubtitleStudio from the Start menu or desktop shortcut, if created.

You can also visit the [Releases page](https://github.com/GH0STH4CKER/SubtitleStudio/releases) to see all available versions.

**Note:** The installer includes the application. Speech-recognition models are downloaded the first time you use them, so an internet connection is required for the initial model download. FFmpeg is also required for video processing; the application can offer to download it if it is not found.

### Run from source (optional)

If you prefer to run the Python source code:

1. Clone the repository:

   ```powershell
   git clone https://github.com/GH0STH4CKER/SubtitleStudio.git
   cd SubtitleStudio
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   python -m pip install --upgrade pip
   ```

3. Install the dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Run the application:

   ```powershell
   python subtitle_studiov3.py
   ```

## 🧠 Models and first-time download

Models are not bundled with the source project. The selected model is downloaded automatically the first time you generate subtitles and reused on later runs.

### English: Whisper

| Model | Approx. download size | Notes |
|---|---:|---|
| `small` | 480 MB | Default; a good starting point |
| `medium` | 1.5 GB | More accurate, but slower |
| `large-v3` | 3 GB | Most resource-intensive |

### Sinhala: SinhaSpeech

Sinhala models are fine-tuned for Sinhala speech and are available in the **Model** dropdown.

| Model | Reported WER |
|---|---:|
| `whisper-small-sinhala-run12-best` | 15.5% |
| `whisper-small-sinhala-run11` | 16.4% |
| `whisper-small-sinhala-run10` | 17.2% |
| `whisper-small-sinhala-run13` | Untested |

Lower WER (word error rate) is better. The `run12-best` model is the recommended starting point.

On first use, a Sinhala model is downloaded and converted once for faster inference. Running from source requires the additional packages:

```powershell
pip install transformers torch
```

Selecting a Sinhala model automatically sets the spoken language to Sinhala.

### Where are models saved?

Downloaded model files are stored in:

```text
%LOCALAPPDATA%\SubtitleStudio\models
```

This normally resolves to:

```text
C:\Users\YOUR_USERNAME\AppData\Local\SubtitleStudio\models
```

The models are kept on your PC and reused on future runs.

## 🎞️ How to use

### 1. Import a video

- Click **Import Video** or drag and drop a video into the application.
- Supported formats: MP4, MKV, MOV, AVI, and M4V.
- Wait for the video preview to load.

### 2. Generate subtitles

- Choose a model from the **Model** dropdown.
- Set **Spoken language** to Auto, English, or Sinhala.
- Enable **Music / singing** if the video contains singing or vocals over background music.
- Enable **Fast mode** if you prefer quicker generation.
- Click **Generate Subtitles**.

### 3. Review and edit subtitles

Open the **Subtitles** tab to review the generated entries.

- Edit subtitle text and timestamps.
- Add or delete subtitle entries.
- Use the video playhead to adjust subtitle timing.
- Save a separate `.srt` subtitle file when needed.

### 4. Customize subtitle appearance

Open the **Style** tab to customize the subtitle appearance, including font, size, text colour, outline, shadow, background, alignment, and position. You can also drag subtitles in the video preview to reposition them.

### 5. Export the video

- Open the **Export** tab.
- Choose the output resolution and quality.
- Keep GPU encoding enabled to use supported NVIDIA, Intel, or AMD hardware when available.
- Click **Export MP4** and choose where to save the new video.

SubtitleStudio creates a new MP4 with subtitles burned into the video. Your original video is not overwritten.

## 🛠️ FFmpeg

SubtitleStudio needs FFmpeg and FFprobe for video processing.

If the application cannot find FFmpeg, it can offer to download it. You can also install it manually:

1. Visit [FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/).
2. Download [ffmpeg-git-essentials.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z).
3. Extract the archive using 7-Zip.
4. Open the extracted `bin` folder.
5. Copy `ffmpeg.exe` and `ffprobe.exe` into a folder named `ffmpeg` in the project directory.

The FFmpeg build must include subtitle-rendering support (libass).

## 🛠️ Troubleshooting

| Problem | What to check |
|---|---|
| FFmpeg not found | Allow the app to download it, or check that `ffmpeg.exe` and `ffprobe.exe` are available. |
| First generation takes a long time | The model may still be downloading, converting, or loading. Wait for it to finish. |
| Model download fails | Check your internet connection, VPN/proxy, or antivirus settings. |
| Sinhala model asks for extra packages | If running from source, install `transformers` and `torch`. |
| Sinhala transcription is inaccurate | Try the SinhaSpeech `run12-best` model and make sure Sinhala is selected. |
| Video export fails | Check that FFmpeg is installed and supports the `ass` video filter (libass). |
| Sinhala characters do not display correctly | Try a Windows font that supports Sinhala, such as Nirmala UI. |

## 🧰 Built with

- [Python](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython-6/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [SinhaSpeech](https://huggingface.co/SinhaSpeech)
- [FFmpeg](https://ffmpeg.org/)

## 📌 Notes

- SubtitleStudio transcribes English and Sinhala speech. It does not translate English subtitles into other languages.
- AI-generated subtitles may contain recognition or timing errors. Review them before exporting.
- Model downloads require an internet connection the first time. Transcription is performed locally after the model is available.
- The original input video is not overwritten during export.

## 🔗 Links

- **[Download Windows Installer](https://github.com/GH0STH4CKER/SubtitleStudio/releases/download/v1.0.0/SubtitleStudio-Setup.exe)**
- [All releases](https://github.com/GH0STH4CKER/SubtitleStudio/releases)
- [Source code](https://github.com/GH0STH4CKER/SubtitleStudio)

Created by **Dimuth De Zoysa**.
