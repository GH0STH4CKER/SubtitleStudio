# 🎬 SubtitleStudio v3

A Windows desktop application for automatically generating, editing, and burning subtitles into videos. SubtitleStudio uses local AI speech recognition with **faster-whisper** and FFmpeg for video and audio processing.

> **Languages:** Transcribes **English or Sinhala** speech. English uses the standard Whisper models; Sinhala can use dedicated, fine-tuned **SinhaSpeech** models for much better accuracy. This version does not translate subtitles between languages.

---

## ✨ Features

- 🎥 Import videos in MP4, MKV, MOV, AVI, and M4V formats.
- 🧠 Transcribe English or Sinhala speech, with auto-detect or a forced language.
- 🇱🇰 **New in v3:** dedicated Sinhala models (SinhaSpeech Whisper-small fine-tunes) alongside the English Whisper models, selectable from one dropdown.
- ⚡ Choose a Whisper model: `small`, `medium`, or `large-v3`, or a Sinhala model, or your own model folder.
- 🏎️ Fast mode (quicker, slightly less accurate) and automatic NVIDIA GPU use for transcription when available.
- 🎵 Optional Music / singing mode to help capture vocals over music.
- ✏️ Review and edit subtitle text and timestamps.
- ➕ Add or delete subtitle entries and set their start/end times using the video playhead.
- 🎨 Customize font, size, bold/italic, text colour, outline, shadow, and background box.
- ↔️ Choose text alignment and reposition subtitles by dragging them in the preview.
- 📄 Export subtitles as an `.srt` file.
- 🎞️ Burn subtitles into a new MP4 video, with automatic GPU encoding (NVIDIA, Intel, or AMD) when available and CPU fallback.
- 🌗 Light and dark themes, plus an About dialog (ⓘ).
- 💻 Speech recognition runs locally after the selected model has been downloaded.

## 🖥️ Requirements

- Windows 10 or Windows 11 (64-bit recommended).
- Python installed.
- FFmpeg and FFprobe (the app can also offer to download them for you).
- An internet connection for the initial model download.
- Enough free disk space for the selected model and video exports.
- **For Sinhala models only:** `transformers` and `torch`, needed once to convert each Sinhala model (see below).

## 🚀 Installation

### 1. Download the project

Clone the repository:

```powershell
git clone https://github.com/GH0STH4CKER/SubtitleStudio.git
cd SubtitleStudio
```

Or download the repository as a ZIP file from GitHub and extract it.

### 2. Install Python dependencies

It is recommended to use a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you want to use the Sinhala models, also install the one-time conversion packages:

```powershell
pip install transformers torch
```

Optional: `pip install truststore` helps downloads work behind antivirus software or proxies that inspect HTTPS traffic (SubtitleStudio uses the Windows certificate store when it is installed).

### 3. Set up FFmpeg

FFmpeg is required to read video files, extract audio, prepare previews, and export subtitled videos.

**Easiest:** launch the app. If FFmpeg is not found, it asks whether to download it for you (about 80 MB, one time) into the `ffmpeg` folder.

**Manual setup:**

1. Open the [FFmpeg Builds website](https://www.gyan.dev/ffmpeg/builds/).
2. Download **[ffmpeg-git-essentials.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z)**.
3. Extract the downloaded archive. You can use 7-Zip if needed.
4. Open the extracted folder and locate its `bin` directory.
5. Copy `ffmpeg.exe` and `ffprobe.exe` into a new folder named `ffmpeg` in the SubtitleStudio project directory.

Your project should look like this:

```text
SubtitleStudio/
│
├── requirements.txt
├── subtitle_studiov3.py
│
└── ffmpeg/
    ├── ffmpeg.exe
    └── ffprobe.exe
```

**Important:** The folder must be named exactly `ffmpeg`, and both executable files must be inside it. SubtitleStudio checks this project-local folder automatically (and falls back to FFmpeg on your PATH). The FFmpeg build must include subtitle rendering support (libass).

### 4. Launch SubtitleStudio

From the project directory, run:

```powershell
python subtitle_studiov3.py
```

---

## 🧠 Models and first-time download

Speech-recognition models are not included in the project. The selected model is downloaded automatically the first time you generate subtitles, into `%LOCALAPPDATA%\SubtitleStudio\models`, and reused on later runs. Downloads show live progress with size, speed, and time remaining, and can resume if interrupted.

### English (and general) models: Whisper

| Model | Approx. size | Notes |
|---|---|---|
| `small` | 480 MB | Default. Good starting point. |
| `medium` | 1.5 GB | More accurate, slower. |
| `large-v3` | 3 GB | Most resource-hungry. |

### Sinhala models: SinhaSpeech

These are fine-tuned for Sinhala only and are listed in a separate group in the **Model** dropdown:

| Model | Reported WER |
|---|---|
| `whisper-small-sinhala-run12-best` (recommended) | 15.5% |
| `whisper-small-sinhala-run11` | 16.4% |
| `whisper-small-sinhala-run10` | 17.2% |
| `whisper-small-sinhala-run13` | untested |

WER is the test word error rate reported by the model publisher; lower is better.

On first use, a Sinhala model is downloaded (about 1 GB) and then **converted once** to a fast-inference format, which takes roughly 1 to 2 minutes and requires `pip install transformers torch`. If those packages are missing, the app tells you the exact command to run. After the conversion, the model loads quickly like any other.

Selecting a Sinhala model automatically sets the spoken language to Sinhala, and it always transcribes as Sinhala.

### Custom folder

Choose **Custom folder…** at the bottom of the dropdown to use a faster-whisper model folder you downloaded yourself (it must contain `model.bin`).

### Notes on the first run

The first download can take several minutes or longer depending on your connection. The progress bar may show an indeterminate state while a model is loaded. **This is expected — allow it to finish.** An internet connection is needed once per model; after that, transcription is performed entirely on your computer.

**Which model should I choose?** For English, start with `small`, and try `medium` or `large-v3` if your computer can handle them. For Sinhala, use the SinhaSpeech `run12-best` model.

---

## 📖 How to use

### 1. Import a video

- Click **Import Video** or drag and drop a video into the application.
- Supported formats: MP4, MKV, MOV, AVI, and M4V.
- Wait for the video information and preview to load.

### 2. Generate subtitles

- Select a model from the **Model** dropdown (Whisper for English, SinhaSpeech for Sinhala).
- Set **Spoken language** to Auto, English, or Sinhala. Use a forced language if auto-detect gets it wrong.
- Enable **Music / singing** when the video contains singing or vocals over background music.
- Leave **Fast mode** off for best accuracy, or turn it on for speed.
- Click **Generate Subtitles**.

### 3. Review and edit

Open the **Subtitles** tab to review the generated entries.

- Double-click a subtitle's text to edit it.
- Double-click a start or end timestamp to change it.
- Use **Add at playhead** to create a subtitle at the current video position.
- Select an entry and use **Start = playhead** or **End = playhead** to update its timing.
- Use **Delete** to remove selected entries.
- Click **Save SRT…** to save a separate SubRip subtitle file.

Timestamps use the format `H:MM:SS.mmm`.

### 4. Customize subtitle appearance

Open the **Style** tab to adjust:

- Font, font size, bold, and italic.
- Text colour and outline colour/thickness.
- Shadow distance and intensity.
- Optional background box, its colour, and opacity.
- Horizontal alignment and vertical position.

You can also **drag the subtitle directly in the video preview** to reposition it.

### 5. Export the subtitled video

- Open the **Export** tab.
- Choose the output resolution: Auto, Original, 1080p, 720p, or 480p.
- Choose the quality setting.
- Leave **Use GPU encoding** enabled to use NVIDIA, Intel, or AMD hardware encoding when available.
- Click **Export MP4** and select an output filename.

The application creates a **new MP4 with subtitles permanently burned into the video**. Your original video is not modified. Exporting can take time depending on the video length, resolution, quality setting, and computer performance.

---

## 🛠️ Troubleshooting

| Problem | What to check |
|---|---|
| FFmpeg not found | Accept the app's download prompt, or confirm `ffmpeg.exe` and `ffprobe.exe` are inside the project's `ffmpeg` folder. |
| Video cannot be opened | Check that the video is supported and is not damaged. |
| No subtitles are generated | Make sure the video has an audio stream and that speech is audible. |
| First generation seems stuck | The model may still be downloading, converting, or loading. Wait for it to finish. |
| Model download fails | Check your internet, VPN/proxy, or antivirus. Installing `truststore` can help behind TLS-inspecting software. |
| Sinhala model asks for extra packages | Run `pip install transformers torch`, then generate again. This is only needed for the one-time conversion. |
| Sinhala output is poor | Use the SinhaSpeech `run12-best` model rather than a general Whisper model, and check that the language is set to Sinhala. |
| Subtitle rendering/export fails | Make sure your FFmpeg build supports the `ass` video filter (libass). |
| Sinhala characters do not display correctly | Try a Windows font that supports Sinhala, such as Nirmala UI. |

For MKV and AVI files, SubtitleStudio may create a temporary MP4 preview. The original video remains unchanged.

## 🧰 Built with

- [Python](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython-6/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [SinhaSpeech](https://huggingface.co/SinhaSpeech) Sinhala Whisper models
- [FFmpeg](https://ffmpeg.org/)

## 📌 Notes

- SubtitleStudio currently transcribes English and Sinhala speech; it does not translate subtitles into another language.
- AI-generated subtitles may contain recognition or timing errors. Review the subtitles before exporting.
- Video processing and transcription are performed locally. Model files are downloaded on first use.
- The original input video is not overwritten by the export process.

## 📜 License

Add your preferred project license here.

## 🔗 Repository

[GH0STH4CKER/SubtitleStudio](https://github.com/GH0STH4CKER/SubtitleStudio)

Created by Dimuth De Zoysa.
