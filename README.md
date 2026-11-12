# 🎬 SubtitleStudio

A Windows desktop application for automatically generating, editing, and burning subtitles into videos. SubtitleStudio uses local AI speech recognition with **faster-whisper** and FFmpeg for video and audio processing.

> **Languages:** Automatically detects and transcribes **English or Sinhala** speech. This version does not translate subtitles between languages.

---

## ✨ Features

- 🎥 Import videos in MP4, MKV, MOV, AVI, and M4V formats.
- 🧠 Automatically detect and transcribe English or Sinhala speech.
- ⚡ Choose a Whisper model: `small`, `medium`, or `large-v3`.
- 🎵 Optional Music / singing mode to help capture vocals over music.
- ✏️ Review and edit subtitle text and timestamps.
- ➕ Add or delete subtitle entries and set their start/end times using the video playhead.
- 🎨 Customize font, size, bold/italic, text colour, outline, shadow, and background box.
- ↔️ Choose text alignment and reposition subtitles by dragging them in the preview.
- 📄 Export subtitles as an `.srt` file.
- 🎞️ Burn subtitles into a new MP4 video.
- 💻 Speech recognition runs locally after the selected model has been downloaded.

## 🖥️ Requirements

- Windows 10 or Windows 11 (64-bit recommended).
- Python installed.
- FFmpeg and FFprobe.
- An internet connection for the initial Whisper model download.
- Enough free disk space for the selected model and video exports.

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

### 3. Download and set up FFmpeg

FFmpeg is required to read video files, extract audio, prepare previews, and export subtitled videos.

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
├── subtitle_studio.py
│
└── ffmpeg/
    ├── ffmpeg.exe
    └── ffprobe.exe
```

**Important:** The folder must be named exactly `ffmpeg`, and both executable files must be inside it. SubtitleStudio checks this project-local folder automatically. The FFmpeg build should include subtitle rendering support (libass).

### 4. Launch SubtitleStudio

From the project directory, run:

```powershell
python subtitle_studio.py
```

---

## 🧠 First launch: Whisper model download

SubtitleStudio uses **faster-whisper** for AI speech recognition. The speech-recognition models are not included in the project, so the selected model is downloaded automatically the first time you generate subtitles.

- **small** — the default model; approximately **500 MB**.
- **medium** — a larger model that may take more time and storage.
- **large-v3** — a much larger model; approximately **3 GB**.

The first download can take several minutes or longer depending on your internet connection. During this step, the application may show an indeterminate progress indicator or appear to pause while the model is being downloaded and loaded. **This is expected — allow it to finish.**

After the model has been downloaded, faster-whisper keeps it in its local model cache. The same model can be reused on later runs, so it normally does not need to be downloaded again. Selecting a different model for the first time will require downloading that model too.

An internet connection is therefore needed for the initial download of each model. Once the model is available locally, transcription is performed on your computer.

**Which model should I choose?** Start with `small`. Choose `medium` or `large-v3` if you want to experiment with a larger model and your computer has enough memory and processing power. Larger models generally require more resources and can take longer to run.

---

## 📖 How to use

### 1. Import a video

- Click **Import Video** or drag and drop a video into the application.
- Supported formats: MP4, MKV, MOV, AVI, and M4V.
- Wait for the video information and preview to load.

### 2. Generate subtitles

- Select a Whisper model from the **Model** dropdown.
- Enable **Music / singing** when the video contains singing or vocals over background music.
- Click **Generate Subtitles**.
- SubtitleStudio extracts the audio and transcribes the speech. It automatically detects whether the speech is English or Sinhala.

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
- Choose the output resolution: Original, 1080p, 720p, or 480p.
- Choose the quality setting.
- Click **Export MP4** and select an output filename.

The application creates a **new MP4 with subtitles permanently burned into the video**. Your original video is not modified. Exporting can take time depending on the video length, resolution, quality setting, and computer performance.

---

## 🛠️ Troubleshooting

| Problem | What to check |
|---|---|
| FFmpeg not found | Confirm that `ffmpeg.exe` and `ffprobe.exe` are inside the project's `ffmpeg` folder. |
| Video cannot be opened | Check that the video is supported and is not damaged. |
| No subtitles are generated | Make sure the video has an audio stream and that speech is audible. |
| First generation seems stuck | The selected Whisper model may still be downloading or loading. Wait for it to finish. |
| Model download fails | Check your internet connection and try again. |
| Subtitle rendering/export fails | Make sure your FFmpeg build supports the `ass` video filter (libass). |
| Sinhala characters do not display correctly | Try a Windows font that supports Sinhala, such as Nirmala UI. |

For MKV and AVI files, SubtitleStudio may create a temporary MP4 preview. The original video remains unchanged.

## 🧰 Built with

- [Python](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython-6/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [FFmpeg](https://ffmpeg.org/)

## 📌 Notes

- SubtitleStudio currently transcribes English and Sinhala speech; it does not translate English subtitles into another language.
- AI-generated subtitles may contain recognition or timing errors. Review the subtitles before exporting.
- Video processing and transcription are performed locally. Whisper model files are downloaded on first use.
- The original input video is not overwritten by the export process.

## 📜 License

Add your preferred project license here.

## 🔗 Repository

[GH0STH4CKER/SubtitleStudio](https://github.com/GH0STH4CKER/SubtitleStudio)
