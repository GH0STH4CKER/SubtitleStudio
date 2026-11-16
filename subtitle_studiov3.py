"""SubtitleStudio - offline English/Sinhala subtitle generator, editor and burner.
Stack: PySide6 (UI), faster-whisper (local speech recognition), FFmpeg (audio/video/subtitle rendering).
v3: English models (Whisper) + fine-tuned Sinhala models (SinhaSpeech) in one app.
The Sinhala models are downloaded once and converted once; that one-time conversion needs: pip install transformers torch"""
import sys, os, json, time, shutil, tempfile, subprocess
import urllib.request, urllib.error
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QSettings, QThread, Signal, QUrl, QRectF, QPointF, QSizeF
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPalette, QPixmap, QLinearGradient, QIcon, QBrush
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

APP_NAME, APP_VERSION = "SubtitleStudio", "3.0"
APP_AUTHOR, APP_YEAR = "Dimuth De Zoysa", "2026"
APP_GITHUB = "https://github.com/GH0STH4CKER"
APP_DIR = Path(sys.argv[0]).resolve().parent
NOWIN = 0x08000000 if os.name == "nt" else 0
NO_FFMPEG = ("FFmpeg not found. Install it (winget install Gyan.FFmpeg) or put ffmpeg.exe and "
             "ffprobe.exe in an 'ffmpeg' folder next to this app. Use a build with libass/HarfBuzz (gyan.dev).")


_wf = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts").replace("\\", "/")
FONTS_DIR = "'" + _wf.replace(":", "\\:") + "'"   # quoted + escaped for FFmpeg filter syntax


FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def ffmpeg_ok():
    try:
        r = subprocess.run([tool("ffmpeg"), "-version"], capture_output=True, text=True, creationflags=NOWIN)
        return r.returncode == 0 and "libass" in r.stdout   # libass is needed to burn subtitles
    except Exception:
        return False


def download_ffmpeg(w):
    import zipfile
    dest = APP_DIR / "ffmpeg"; dest.mkdir(exist_ok=True); z = os.path.join(tempfile.gettempdir(), "ffmpeg_dl.zip")
    with hf_open(FFMPEG_URL) as r, open(z, "wb") as f:
        total, got = int(r.headers.get("Content-Length") or 0), 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk: break
            if w.cancel: raise RuntimeError("Cancelled.")
            f.write(chunk); got += len(chunk)
            if total: w.progress.emit(int(got * 100 / total), f"Downloading FFmpeg… {got >> 20} / {total >> 20} MB")
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            if n.endswith(("/bin/ffmpeg.exe", "/bin/ffprobe.exe")):
                (dest / os.path.basename(n)).write_bytes(zf.read(n))
    os.remove(z)


def tool(name):
    local = APP_DIR / "ffmpeg" / f"{name}.exe"
    return str(local) if local.exists() else (shutil.which(name) or name)


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NOWIN)
    except FileNotFoundError:
        raise RuntimeError(NO_FFMPEG)


def probe(path):
    r = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height:format=duration", "-of", "json", path])
    try:
        d = json.loads(r.stdout)
        return int(d["streams"][0]["width"]), int(d["streams"][0]["height"]), float(d["format"]["duration"])
    except Exception:
        raise RuntimeError("Could not read this video:\n" + r.stderr[-400:])


def fmt(ms):
    ms = max(0, int(ms)); h, r = divmod(ms, 3600000); m, r = divmod(r, 60000); s, r = divmod(r, 1000)
    return f"{h}:{m:02d}:{s:02d}.{r:03d}"


def parse_t(s):
    try:
        v = 0.0
        for p in s.strip().replace(",", ".").split(":"):
            v = v * 60 + float(p)
        return int(v * 1000)
    except ValueError:
        return None


@dataclass
class Style:
    font: str = "Nirmala UI"      # supports Sinhala + Latin on Windows 10/11
    size: float = 5.0             # % of video height
    bold: bool = True
    italic: bool = False
    color: str = "#ffffff"
    out_color: str = "#000000"
    outline: float = 2.5          # px at 1080p
    shadow: float = 2.0           # distance, px at 1080p
    sh_op: float = 60             # shadow opacity %
    box: bool = False
    box_color: str = "#000000"
    box_op: float = 55
    align: str = "center"         # anchor of text at the position point: left/center/right
    px: float = 0.5
    py: float = 0.88


def ass_color(hexc, opacity=100):
    c = QColor(hexc); a = round(255 * (1 - opacity / 100))
    return f"&H{a:02X}{c.blue():02X}{c.green():02X}{c.red():02X}"


def build_ass(subs, st, W, H):
    k = H / 1080; fs = st.size / 100 * H; an = {"left": 4, "center": 5, "right": 6}[st.align]
    x, y = round(st.px * W), round(st.py * H); mg = int(W * 0.05); b = -1 if st.bold else 0; i = -1 if st.italic else 0
    L = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0",
         "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
         "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
         "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
         f"Style: Text,{st.font},{fs:.1f},{ass_color(st.color)},{ass_color(st.color)},{ass_color(st.out_color)},"
         f"{ass_color('#000000', st.sh_op)},{b},{i},0,0,100,100,0,0,1,{st.outline * k:.1f},{st.shadow * k:.1f},{an},{mg},{mg},0,1",
         f"Style: Box,{st.font},{fs:.1f},&HFF000000,&HFF000000,{ass_color(st.box_color, st.box_op)},&HFF000000,"
         f"{b},{i},0,0,100,100,0,0,3,{fs * 0.25:.1f},0,{an},{mg},{mg},0,1",
         "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    t = lambda ms: f"{ms // 3600000}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000 // 10:02d}"
    for a, e, txt in subs:
        txt = txt.replace("{", "(").replace("}", ")").replace("\n", "\\N")
        if not txt.strip():
            continue
        if st.box:
            L.append(f"Dialogue: 0,{t(a)},{t(e)},Box,,0,0,0,,{{\\pos({x},{y})}}{txt}")
        L.append(f"Dialogue: 1,{t(a)},{t(e)},Text,,0,0,0,,{{\\pos({x},{y})}}{txt}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- background jobs
class Worker(QThread):
    progress = Signal(int, str); done = Signal(object); failed = Signal(str)

    def __init__(self, fn):
        super().__init__(); self.fn = fn; self.cancel = False

    def run(self):
        try:
            self.done.emit(self.fn(self))
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


def load_job(path, tmp, w):
    W, H, dur = probe(path); proxy = None
    if Path(path).suffix.lower() not in (".mp4", ".mov", ".m4v"):   # make MKV/AVI reliably previewable
        w.progress.emit(5, "Preparing preview (original is untouched)…")
        proxy = os.path.join(tmp, "preview.mp4")
        r = run([tool("ffmpeg"), "-y", "-i", path, "-vf", "scale=-2:540", "-c:v", "libx264", "-preset", "ultrafast",
                 "-crf", "28", "-pix_fmt", "yuv420p", "-c:a", "aac", "-strict", "-2", "-b:a", "128k", proxy])
        if r.returncode: raise RuntimeError("Preview creation failed:\n" + r.stderr[-400:])
    return path, proxy, W, H, dur


def split_words(words, maxc=42, maxs=5.0, gap=0.8):
    out, cur = [], []
    def flush():
        if cur:
            out.append([int(cur[0].start * 1000), int(cur[-1].end * 1000), "".join(x.word for x in cur).strip()]); cur.clear()
    for wd in words:
        if cur and (len("".join(x.word for x in cur) + wd.word) > maxc or wd.end - cur[0].start > maxs or wd.start - cur[-1].end > gap):
            flush()
        cur.append(wd)
        if wd.word.strip()[-1:] in ".?!။" and len("".join(x.word for x in cur)) > 15:
            flush()
    flush(); return out


MODEL_REPOS = {n: f"Systran/faster-whisper-{n}" for n in ("tiny", "base", "small", "medium", "large-v3")}
MODELS_DIR = Path(os.environ.get("LOCALAPPDATA", str(APP_DIR))) / "SubtitleStudio" / "models"
SINHALA_PREFIX = "SinhaSpeech/"
SINHALA_MODELS = {   # label -> repo.  WER = test word error rate reported on each model card/collection
    "SinhaSpeech/whisper-small-sinhala-run12-best  (best, WER 15.5%)": "SinhaSpeech/whisper-small-sinhala-run12-best",
    "SinhaSpeech/whisper-small-sinhala-run11  (WER 16.4%)": "SinhaSpeech/whisper-small-sinhala-run11",
    "SinhaSpeech/whisper-small-sinhala-run10  (WER 17.2%)": "SinhaSpeech/whisper-small-sinhala-run10",
    "SinhaSpeech/whisper-small-sinhala-run13  (untested)": "SinhaSpeech/whisper-small-sinhala-run13",
}
ENGLISH_MODELS = ["small  (≈ 480 MB)", "medium  (≈ 1.5 GB)", "large-v3  (≈ 3 GB)"]
SKIP = {"optimizer.pt", "scheduler.pt", "training_args.bin", "rng_state.pth", "trainer_state.json"}


def hf_open(req, timeout=30):
    """Open a URL with a proper User-Agent and the Windows certificate store (works behind antivirus / proxy TLS inspection)."""
    if isinstance(req, str): req = urllib.request.Request(req)
    req.add_header("User-Agent", "SubtitleStudio/3.0")
    try:
        import ssl, truststore
        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        ctx = None
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def wanted(files):
    has_st = any(n.endswith(".safetensors") for n, _ in files); out = []
    for n, sz in files:
        if "/" in n or n in SKIP or n.startswith("."): continue
        if n.endswith((".json", ".txt", ".safetensors", ".model")) or (n.endswith(".bin") and n.startswith("pytorch_model") and not has_st):
            out.append((n, sz))
    return out


def fetch_files(repo, files, dest, w, label):
    """Resumable download with live size / speed / ETA."""
    dest.mkdir(parents=True, exist_ok=True); total = sum(sz for _, sz in files)
    have = lambda f, sz: (dest / f).exists() and (not sz or (dest / f).stat().st_size == sz)
    finished = sum(sz for f, sz in files if have(f, sz)); sess = 0; t0 = last = time.time()
    for f, sz in files:
        if have(f, sz): continue
        part = dest / (f + ".part"); pos = part.stat().st_size if part.exists() else 0
        req = urllib.request.Request(f"https://huggingface.co/{repo}/resolve/main/{f}", headers={"Range": f"bytes={pos}-"} if pos else {})
        try:
            r = hf_open(req)
        except urllib.error.HTTPError as e:
            if e.code == 416: part.replace(dest / f); finished += sz; continue   # already complete
            raise RuntimeError(f"Download failed ({e.code}) for {f}")
        if pos and r.status != 206: pos = 0   # server ignored the resume request
        got = pos
        with r, open(part, "ab" if pos else "wb") as out:
            while True:
                chunk = r.read(1 << 17)
                if not chunk: break
                if w.cancel: raise RuntimeError("Cancelled.")
                out.write(chunk); got += len(chunk); sess += len(chunk)
                if time.time() - last > 0.25:
                    last = time.time(); cur = finished + got; sp = sess / max(last - t0, 0.5); left = (total - cur) / sp if sp else 0
                    w.progress.emit(max(1, int(cur * 85 / max(total, 1))),
                                    f"{label}: {cur >> 20} / {total >> 20} MB  •  {sp / 1e6:.1f} MB/s  •  about {int(left // 60)}m {int(left % 60)}s left")
        part.replace(dest / f); finished += got


def sinhala_model(repo, w):
    """Download the HF model once, convert it to CTranslate2, return the folder faster-whisper can load."""
    name = repo.split("/")[-1]; root = MODELS_DIR / "sinhala"; out = root / name; src = root / ("_src_" + name)
    if (out / ".complete").exists(): return str(out)
    try:
        w.progress.emit(2, f"Checking '{name}' online…")
        with hf_open(f"https://huggingface.co/api/models/{repo}?blobs=true") as r:
            files = wanted([(x["rfilename"], x.get("size") or 0) for x in json.load(r)["siblings"]])
    except Exception as e:
        raise RuntimeError(f"Could not reach huggingface.co ({type(e).__name__}: {e}).\n\nCheck your internet, VPN/proxy or antivirus.")
    if not any(n.endswith((".safetensors", ".bin")) for n, _ in files):
        raise RuntimeError(f"'{name}' has no model weights in its top-level files, so it can't be used.")
    w.progress.emit(3, f"'{name}' is about {sum(s for _, s in files) >> 20} MB (one-time download)…")
    fetch_files(repo, files, src, w, f"Downloading '{name}'")
    w.progress.emit(90, "Converting the model for fast inference (one time, about 1-2 minutes)…")
    try:
        import torch, transformers   # noqa: F401  (needed by the converter)
        from ctranslate2.converters import TransformersConverter
    except ImportError:
        raise RuntimeError("The one-time conversion needs two extra packages. Run this, then try again:\n\n    pip install transformers torch")
    copy = [f for f in ("tokenizer.json", "preprocessor_config.json") if (src / f).exists()]
    TransformersConverter(str(src), copy_files=copy).convert(str(out), quantization="float16", force=True)
    if not (out / "tokenizer.json").exists():
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(str(src)).backend_tokenizer.save(str(out / "tokenizer.json"))
    (out / ".complete").write_text("ok"); shutil.rmtree(src, ignore_errors=True)
    return str(out)


def ensure_model(name, w):
    """Folder path -> used as is. Sinhala model -> downloaded + converted once. English name -> downloaded once into MODELS_DIR (resumable)."""
    if name.startswith(SINHALA_PREFIX) and not os.path.isdir(name): return sinhala_model(name, w)
    if os.path.isdir(name) or name not in MODEL_REPOS: return name
    repo, dest = MODEL_REPOS[name], MODELS_DIR / name
    if (dest / ".complete").exists(): return str(dest)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        w.progress.emit(2, f"Checking model '{name}' online…")
        with hf_open(f"https://huggingface.co/api/models/{repo}?blobs=true") as r:
            files = [(x["rfilename"], x.get("size") or 0) for x in json.load(r)["siblings"]
                     if x["rfilename"] in ("config.json", "model.bin", "tokenizer.json", "preprocessor_config.json") or x["rfilename"].startswith("vocabulary")]
    except Exception as e:
        raise RuntimeError(f"Could not reach huggingface.co ({type(e).__name__}: {e}).\n\nCheck your internet, VPN/proxy or antivirus, or choose Model > 'Custom folder…' "
                           "and point it to a model you downloaded manually.")
    total = sum(sz for _, sz in files)
    w.progress.emit(3, f"Model '{name}' needs a one-time download of {total >> 20} MB…")
    fetch_files(repo, files, dest, w, f"Downloading '{name}' model (one time)")
    (dest / ".complete").write_text("ok"); return str(dest)


def transcribe_job(video, model_name, tmp, w, music=False, fast=True, force=None):
    wav = os.path.join(tmp, "audio.wav")
    w.progress.emit(2, "Extracting audio…")
    r = run([tool("ffmpeg"), "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav])
    if r.returncode: raise RuntimeError("Audio extraction failed (does the video have sound?):\n" + r.stderr[-400:])
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")
    w.progress.emit(-1, "Loading speech model. First use downloads it (Whisper small ≈ 500 MB, large-v3 ≈ 3 GB, Sinhala models ≈ 1 GB + one-time conversion)…")
    import wave
    import numpy as np
    with wave.open(wav, "rb") as wf:   # decode ourselves so faster-whisper never calls PyAV
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    is_si = model_name.startswith(SINHALA_PREFIX)
    if is_si: force = "si"   # fine-tuned Sinhala models only make sense for Sinhala audio
    model_name = ensure_model(model_name, w)
    try:
        import ctranslate2
        gpu = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        gpu = False

    def pipeline(model):
        w.progress.emit(10, "Model ready. Starting transcription…")
        go = lambda lang: model.transcribe(audio, language=lang, vad_filter=not music, vad_parameters=dict(min_silence_duration_ms=1500),
                                           beam_size=1 if fast else 5, word_timestamps=True, condition_on_previous_text=False)
        segs, info = go(force); lang = force or info.language
        if not force and lang not in ("en", "si"):   # only English / Sinhala are expected: pick the likelier of the two
            probs = dict(info.all_language_probs or [])
            lang = max(("en", "si"), key=lambda l: probs.get(l, 0)); segs, info = go(lang)
        out, dur = [], info.duration or 1
        for s in segs:
            if w.cancel: raise RuntimeError("Cancelled.")
            out += split_words(s.words) if s.words else [[int(s.start * 1000), int(s.end * 1000), s.text.strip()]]
            w.progress.emit(10 + int(88 * min(s.end / dur, 1)), f"Transcribing ({'Sinhala' if lang == 'si' else 'English'})…")
        return lang, out

    if gpu:   # NVIDIA GPU found: use it, but fall back to CPU if CUDA libraries are missing/broken
        try:
            w.progress.emit(5, "NVIDIA GPU detected, using it for transcription…")
            return pipeline(WhisperModel(model_name, device="cuda", compute_type="float16"))
        except Exception:
            if w.cancel: raise
            w.progress.emit(5, "GPU not usable, switching to CPU…")
    return pipeline(WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=min(os.cpu_count() or 4, 8)))


_ENC = {}


def hw_encoder(crf):
    """Find a working GPU H.264 encoder (NVIDIA, Intel, AMD). Returns (ffmpeg args, label) or (None, 'CPU')."""
    if "n" not in _ENC:
        _ENC["n"] = None
        for name in ("h264_nvenc", "h264_qsv", "h264_amf"):
            r = run([tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2,format=yuv420p",
                     "-c:v", name, "-f", "null", "-"])
            if r.returncode == 0: _ENC["n"] = name; break
    q = str(max(crf - 2, 10))   # GPU encoders are a bit softer at equal settings, so aim higher
    return {None: (None, "CPU"),
            "h264_nvenc": (["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", q, "-b:v", "0"], "NVIDIA NVENC"),
            "h264_qsv": (["-c:v", "h264_qsv", "-global_quality", q, "-preset", "medium"], "Intel Quick Sync"),
            "h264_amf": (["-c:v", "h264_amf", "-rc", "cqp", "-qp_i", q, "-qp_p", q, "-quality", "quality"], "AMD AMF")}[_ENC["n"]]


def export_job(video, out, subs, st, W, H, dur, crf, tmp, w, hw=True):
    open(os.path.join(tmp, "s.ass"), "w", encoding="utf-8").write(build_ass(subs, st, W, H))
    sw = ["-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast"]

    def attempt(venc, label):
        # text is drawn AFTER scaling, at the final resolution, so it stays pixel-sharp
        cmd = [tool("ffmpeg"), "-y", "-i", os.path.abspath(video), "-map", "0:v:0", "-map", "0:a:0?",
               "-vf", f"scale={W}:{H}:flags=lanczos,ass=s.ass:fontsdir={FONTS_DIR},format=yuv420p", *venc,
               "-c:a", "aac", "-strict", "-2", "-b:a", "192k", "-movflags", "+faststart",
               "-progress", "pipe:1", "-nostats", os.path.abspath(out)]
        log = open(os.path.join(tmp, "ff.log"), "w", encoding="utf-8")
        try:
            p = subprocess.Popen(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=log, text=True, creationflags=NOWIN)
        except FileNotFoundError:
            raise RuntimeError(NO_FFMPEG)
        t0 = time.time()
        for line in p.stdout:
            if w.cancel:
                p.kill(); raise RuntimeError("Export cancelled.")
            if line.startswith(("out_time_us=", "out_time_ms=")):
                try:
                    done = int(line.split("=")[1]) / 1e6 / dur
                except ValueError:
                    continue
                if done > 0.005:
                    eta = (time.time() - t0) * (1 - done) / done
                    w.progress.emit(int(done * 100), f"Exporting ({label})… {int(done * 100)}%  •  about {int(eta // 60)}m {int(eta % 60)}s left")
        rc = p.wait(); log.close()
        return rc == 0, open(os.path.join(tmp, "ff.log"), encoding="utf-8").read()[-600:]

    w.progress.emit(0, "Checking for GPU encoder…")
    venc, label = hw_encoder(crf) if hw else (None, "CPU")
    ok, err = attempt(venc or sw, label)
    if not ok and venc:   # GPU encoder failed -> automatic CPU fallback
        w.progress.emit(0, "GPU encoder failed, using CPU…")
        ok, err = attempt(sw, "CPU")
    if not ok: raise RuntimeError("FFmpeg failed:\n" + err)
    return out


# ---------------------------------------------------------------- preview widgets
class SubItem(QGraphicsItem):
    """Subtitle overlay drawn exactly in video-pixel space; drag to reposition."""
    def __init__(self, on_moved):
        super().__init__(); self.text = ""; self.W = self.H = 0; self.on_moved = on_moved; self.k = 1
        self.path = QPainterPath(); self.box = QRectF(); self.st = Style()
        self.setFlag(QGraphicsItem.ItemIsMovable); self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.SizeAllCursor); self.setZValue(10)

    def rebuild(self, text, st, W, H):
        self.prepareGeometryChange(); self.text, self.st, self.W, self.H, self.k = text, st, W, H, H / 1080
        f = QFont(st.font); f.setPixelSize(max(4, int(st.size / 100 * H))); f.setBold(st.bold); f.setItalic(st.italic)
        fm = QFontMetricsF(f); lines = []
        for para in text.split("\n"):
            cur = ""
            for word in para.split(" "):
                t = (cur + " " + word) if cur else word
                if cur and fm.horizontalAdvance(t) > W * 0.9: lines.append(cur); cur = word
                else: cur = t
            lines.append(cur)
        lh = fm.lineSpacing(); wmax = max(fm.horizontalAdvance(l) for l in lines); tot = lh * len(lines)
        ax = {"left": 0, "center": -wmax / 2, "right": -wmax}[st.align]; p = QPainterPath()
        for n, l in enumerate(lines):
            d = wmax - fm.horizontalAdvance(l); x = ax + {"left": 0, "center": d / 2, "right": d}[st.align]
            p.addText(x, -tot / 2 + n * lh + fm.ascent(), f, l)
        pad = st.size / 100 * H * 0.25 if st.box else 0
        self.path = p; self.box = QRectF(ax, -tot / 2, wmax, tot).adjusted(-pad, -pad, pad, pad)
        self.setPos(st.px * W, st.py * H); self.update()

    def boundingRect(self):
        m = (self.st.outline + self.st.shadow) * self.k + 6
        return self.box.adjusted(-m, -m, m, m)

    def paint(self, p, opt, w):
        if not self.text.strip(): return
        st, k = self.st, self.k; p.setRenderHint(QPainter.Antialiasing)
        if st.box:
            c = QColor(st.box_color); c.setAlphaF(st.box_op / 100); p.fillRect(self.box, c)
        pen = lambda c: QPen(c, 2 * st.outline * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        if st.shadow > 0:
            c = QColor(0, 0, 0); c.setAlphaF(st.sh_op / 100); p.save(); p.translate(st.shadow * k, st.shadow * k)
            if st.outline > 0: p.strokePath(self.path, pen(c))
            p.fillPath(self.path, c); p.restore()
        if st.outline > 0: p.strokePath(self.path, pen(QColor(st.out_color)))
        p.fillPath(self.path, QColor(st.color))

    def itemChange(self, ch, val):
        if ch == QGraphicsItem.ItemPositionChange and self.W:
            return QPointF(min(max(val.x(), 0), self.W), min(max(val.y(), 0), self.H))
        return super().itemChange(ch, val)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self.W: self.on_moved(self.x() / self.W, self.y() / self.H)


class View(QGraphicsView):
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self.sceneRect().isEmpty(): self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)


THEMES = {
    "dark": dict(bg="#0e1018", surface="#161923", surface2="#1f2331", border="#2b3042", text="#e9ecf5", muted="#8b93a9", accent="#6c8cff", accent2="#b46cff"),
    "light": dict(bg="#f1f3f9", surface="#ffffff", surface2="#eef1f8", border="#dde2ee", text="#1b2030", muted="#667089", accent="#4f6bff", accent2="#9b5cff"),
}
GRAD = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 @accent,stop:1 @accent2)"
QSS = """
QWidget{background:transparent;color:@text;font-family:"Segoe UI";font-size:13px}
QMainWindow,#root{background:@bg}
QDialog,QMessageBox{background:@surface}
#header{background:@surface;border-bottom:1px solid @border}
#title{font-size:19px;font-weight:700}
#h1{font-size:18px;font-weight:700}
#muted{color:@muted}
#card{background:@surface;border:1px solid @border;border-radius:16px}
#drop{border:2px dashed @border;border-radius:14px;background:@bg}
QLabel#step{padding:6px 14px;border-radius:15px;color:@muted;background:@surface2}
QLabel#step[state="active"]{color:white;font-weight:600;background:@grad}
QLabel#step[state="done"]{color:@accent}
QPushButton{background:@surface2;border:1px solid @border;border-radius:10px;padding:7px 14px}
QPushButton:hover{border-color:@accent}
QPushButton:disabled{color:@muted;background:@bg}
QPushButton#primary{color:white;font-weight:600;border:0;padding:9px 20px;background:@grad}
QPushButton#primary:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 @accent2,stop:1 @accent)}
QPushButton#primary:disabled{background:@surface2;color:@muted}
QPushButton#icon{min-width:38px;max-width:38px;min-height:38px;max-height:38px;padding:0;border-radius:19px;font-size:15px}
QTabWidget::pane{border:0;top:8px}
QTabBar::tab{padding:8px 14px;margin-right:4px;border-radius:10px;color:@muted}
QTabBar::tab:selected{background:@surface2;color:@text;font-weight:600}
QTabBar::tab:hover{color:@text}
QTableWidget{background:@surface;border:1px solid @border;border-radius:10px;selection-background-color:@accent;selection-color:white;outline:0}
QTableWidget::item{padding:4px}
QHeaderView::section{background:@surface2;color:@muted;border:0;padding:8px;font-weight:600}
QTableCornerButton::section{background:@surface2;border:0}
QLineEdit,QComboBox,QDoubleSpinBox{background:@surface2;border:1px solid @border;border-radius:9px;padding:6px 10px;min-height:20px}
QComboBox:hover,QDoubleSpinBox:hover,QLineEdit:focus{border-color:@accent}
QAbstractItemView{background:@surface;color:@text;selection-background-color:@accent;border:1px solid @border}
QComboBox::drop-down{border:0;width:30px}
QComboBox::down-arrow{image:url(@down);width:12px;height:12px}
QDoubleSpinBox{padding-right:26px}
QDoubleSpinBox::up-button{subcontrol-origin:border;subcontrol-position:top right;width:24px;border:0;background:transparent}
QDoubleSpinBox::down-button{subcontrol-origin:border;subcontrol-position:bottom right;width:24px;border:0;background:transparent}
QDoubleSpinBox::up-arrow{image:url(@up);width:10px;height:10px}
QDoubleSpinBox::down-arrow{image:url(@down);width:10px;height:10px}
QCheckBox{spacing:8px}
QCheckBox::indicator{width:18px;height:18px;border-radius:5px;border:1px solid @border;background:@surface2}
QCheckBox::indicator:checked{background:@accent;border-color:@accent}
QProgressBar{background:@surface2;border:0;border-radius:7px;min-height:14px;max-height:14px;text-align:center;font-size:10px}
QProgressBar::chunk{border-radius:7px;background:@grad}
QStatusBar{background:@surface;border-top:1px solid @border}
QScrollBar:vertical{background:transparent;width:10px;margin:0}
QScrollBar::handle:vertical{background:@border;border-radius:5px;min-height:30px}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}
QSplitter::handle{background:transparent}
QToolTip{background:@surface;color:@text;border:1px solid @border;padding:4px}
"""


def arrow_png(color, up=False):
    d = Path(tempfile.gettempdir()) / "substudio_ui"; d.mkdir(exist_ok=True)
    f = d / f"arrow_{color.lstrip('#')}_{'up' if up else 'down'}.png"
    if not f.exists():
        pm = QPixmap(24, 24); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(color), 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); y1, y2 = (16, 8) if up else (8, 16)
        p.drawPolyline([QPointF(6, y1), QPointF(12, y2), QPointF(18, y1)]); p.end(); pm.save(str(f))
    return str(f).replace("\\", "/")


def qss(t):
    t = dict(t, down=arrow_png(t["text"]), up=arrow_png(t["text"], True))
    out = QSS.replace("@grad", GRAD)
    for k in sorted(t, key=len, reverse=True): out = out.replace("@" + k, t[k])
    return out


ASSETS = Path(getattr(sys, "_MEIPASS", APP_DIR)) / "assets"   # also works inside a PyInstaller exe


_LOGO = {}


def find_logo():
    """Logo PNG next to the script (or bundled in the exe). Exact name 'SubtitleStudio_Logo.png' is preferred."""
    for base in (APP_DIR, Path(getattr(sys, "_MEIPASS", APP_DIR))):
        for pat in ("SubtitleStudio_Logo.png", "SubtitleStudio*Logo*.png", "*Neon*Logo*.png", "logo.png"):
            for f in sorted(base.glob(pat)): return str(f)
    return None


def make_logo(sz=256):
    """Square rounded app icon cropped from the logo file (clapperboard + bubble, no wordmark); drawn fallback if no file."""
    f = find_logo(); src = QPixmap(f) if f else QPixmap()
    if src.isNull(): return draw_logo(sz)
    if "icon" not in _LOGO:
        k = src.width() / 1254; n = int(840 * k); bg = src.toImage().pixelColor(4, 4)
        pm = QPixmap(n, n); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath(); clip.addRoundedRect(QRectF(0, 0, n, n), n * .22, n * .22); p.setClipPath(clip); p.fillRect(0, 0, n, n, bg)
        p.drawPixmap(0, int(80 * k), src.copy(int(230 * k), int(130 * k), n, int(680 * k))); p.end(); _LOGO["icon"] = pm
    return _LOGO["icon"].scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def draw_logo(sz=256):
    f = ASSETS / "icon.png"
    if f.exists():
        pm = QPixmap(str(f))
        if not pm.isNull(): return pm.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return _draw_logo(sz)


def _draw_logo(sz=256):
    pm = QPixmap(sz, sz); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
    g = QLinearGradient(0, 0, sz, sz); g.setColorAt(0, QColor("#6c8cff")); g.setColorAt(1, QColor("#b46cff"))
    p.setBrush(QBrush(g)); p.drawRoundedRect(QRectF(0, 0, sz, sz), sz * .24, sz * .24)
    b = QPainterPath(); b.addRoundedRect(QRectF(sz * .17, sz * .22, sz * .66, sz * .46), sz * .1, sz * .1)
    tail = QPainterPath(); tail.moveTo(sz * .33, sz * .64); tail.lineTo(sz * .29, sz * .82); tail.lineTo(sz * .52, sz * .64); tail.closeSubpath()
    p.setBrush(QColor("white")); p.drawPath(b.united(tail)); p.setBrush(QColor("#6c5cff"))
    p.drawRoundedRect(QRectF(sz * .27, sz * .33, sz * .46, sz * .075), sz * .035, sz * .035)
    p.drawRoundedRect(QRectF(sz * .27, sz * .47, sz * .30, sz * .075), sz * .035, sz * .035)
    p.end(); return pm


def make_splash():
    f = find_logo()
    if f and not QPixmap(f).isNull(): return QPixmap(f).scaled(560, 560, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    f = ASSETS / "logo.png"
    if f.exists():   # your full logo (with the SubtitleStudio wordmark) as the splash
        pm = QPixmap(str(f))
        if not pm.isNull(): return pm.scaled(560, 560, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    W, H = 640, 380; pm = QPixmap(W, H); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
    g = QLinearGradient(0, 0, W, H); g.setColorAt(0, QColor("#0d1030")); g.setColorAt(1, QColor("#2b1458")); p.fillRect(0, 0, W, H, QBrush(g))
    p.drawPixmap((W - 124) // 2, 62, make_logo(256).scaled(124, 124, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    f = QFont("Segoe UI", 30); f.setBold(True); p.setFont(f); p.setPen(QColor("white")); p.drawText(QRectF(0, 200, W, 56), Qt.AlignCenter, "SubtitleStudio")
    p.setFont(QFont("Segoe UI", 11)); p.setPen(QColor("#aab0dd")); p.drawText(QRectF(0, 256, W, 30), Qt.AlignCenter, "AI subtitles for English & Sinhala  •  offline  •  open source")
    p.end(); return pm


class Timeline(QWidget):
    seek = Signal(int)
    def __init__(self):
        super().__init__(); self.setFixedHeight(38); self.dur = 1; self.pos = 0; self.subs = []; self.bg, self.seg, self.head = "#1f2331", "#6c8cff", "#ff5a7a"

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen); p.setBrush(QColor(self.bg)); p.drawRoundedRect(self.rect(), 9, 9); w = self.width()
        for a, b, _ in self.subs:
            p.fillRect(QRectF(a / self.dur * w, 6, max(2, (b - a) / self.dur * w), self.height() - 12), QColor(self.seg))
        x = int(self.pos / self.dur * w); p.setPen(QPen(QColor(self.head), 2)); p.drawLine(x, 0, x, self.height())

    def _m(self, e): self.seek.emit(int(min(max(e.position().x() / max(self.width(), 1), 0), 1) * self.dur))
    mousePressEvent = mouseMoveEvent = _m


# ---------------------------------------------------------------- main window
class Main(QMainWindow):
    STEPS = ("1  Import", "2  Generate", "3  Edit & Style", "4  Export")

    def __init__(self):
        super().__init__(); self.setWindowTitle("SubtitleStudio"); self.resize(1450, 880); self.setAcceptDrops(True)
        self.st = Style(); self.subs = []; self.video = None; self.W = self.H = 0; self.dur = 1.0
        self.worker = None; self._fill = False; self.cur = -2; self.tmp = tempfile.mkdtemp(prefix="substudio_")
        self.player = QMediaPlayer(); self.audio = QAudioOutput(); self.player.setAudioOutput(self.audio)
        self.scene = QGraphicsScene(); self.vitem = QGraphicsVideoItem(); self.scene.addItem(self.vitem)
        self.player.setVideoOutput(self.vitem)
        self.sitem = SubItem(self.moved); self.scene.addItem(self.sitem)
        self.view = View(self.scene); self.view.setBackgroundBrush(QColor("#0b0b0e")); self.view.setFrameShape(QFrame.NoFrame)

        self.setWindowIcon(QIcon(make_logo(256)))
        self.b_imp = QPushButton("＋  Import Video"); self.b_imp.setObjectName("primary")
        self.b_gen = QPushButton("✨  Generate Subtitles"); self.b_gen.setObjectName("primary")
        self.b_exp = QPushButton("⬇  Export MP4"); self.b_exp.setObjectName("primary")
        self.b_can = QPushButton("Cancel"); self.b_can.setVisible(False)
        self.b_theme = QPushButton(); self.b_theme.setObjectName("icon"); self.b_theme.setToolTip("Switch light / dark theme")
        self.b_about = QPushButton("ⓘ"); self.b_about.setObjectName("icon"); self.b_about.setToolTip(f"About {APP_NAME} — created by {APP_AUTHOR}")
        self.b_about.clicked.connect(self.show_about)
        self.b_imp.clicked.connect(self.pick_video); self.b_gen.clicked.connect(self.generate); self.b_exp.clicked.connect(self.export)
        self.b_can.clicked.connect(self.cancel); self.b_theme.clicked.connect(lambda: self.apply_theme("light" if self.theme == "dark" else "dark"))
        self.model = QComboBox(); self.model.addItems(ENGLISH_MODELS); self.model.insertSeparator(self.model.count()); self.model.addItems(list(SINHALA_MODELS)); self.model.insertSeparator(self.model.count()); self.model.addItem("Custom folder…"); self._last_model = self.model.itemText(0)
        self.model.setToolTip("Whisper models (top group) work for English and Sinhala. SinhaSpeech models (second group) are fine-tuned for Sinhala only. "
                              "Models download once, with a progress bar. 'Custom folder…' uses a model you downloaded yourself.")
        self.model.currentTextChanged.connect(self.model_changed)
        self.fast = QCheckBox("Fast mode (quicker, slightly less accurate)"); self.fast.setChecked(True)
        self.lang = QComboBox(); self.lang.addItems(["Auto", "English", "Sinhala"]); self.lang.setToolTip("Force a language if auto-detect gets it wrong")
        self.music = QCheckBox("Music / singing (don't skip vocals over music)"); self.music.setChecked(True)

        hdr = QFrame(); hdr.setObjectName("header"); hl = QHBoxLayout(hdr); hl.setContentsMargins(22, 12, 22, 12); hl.setSpacing(10)
        lg = QLabel(); lg.setPixmap(make_logo(256).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        tt = QLabel("SubtitleStudio"); tt.setObjectName("title")
        hl.addWidget(lg); hl.addWidget(tt); hl.addSpacing(18); hl.addWidget(self.b_imp); hl.addStretch()
        self.steps = []
        for i, name in enumerate(self.STEPS):
            if i: sep = QLabel("›"); sep.setObjectName("muted"); hl.addWidget(sep)
            l = QLabel(name); l.setObjectName("step"); self.steps.append(l); hl.addWidget(l)
        hl.addStretch(); hl.addWidget(self.b_can); hl.addWidget(self.b_exp); hl.addWidget(self.b_theme); hl.addWidget(self.b_about)

        self.stack = QStackedWidget(); self.stack.addWidget(self.drop_zone()); self.stack.addWidget(self.view)
        self.play = QPushButton("▶"); self.play.setObjectName("icon"); self.play.clicked.connect(self.toggle)
        self.tl = Timeline(); self.tl.seek.connect(self.player.setPosition); self.clock = QLabel("0:00:00.000"); self.clock.setObjectName("muted")
        ctl = QHBoxLayout(); ctl.setSpacing(12); ctl.addWidget(self.play); ctl.addWidget(self.tl, 1); ctl.addWidget(self.clock)
        left = QFrame(); left.setObjectName("card"); lv = QVBoxLayout(left); lv.setContentsMargins(12, 12, 12, 12); lv.addWidget(self.stack, 1); lv.addLayout(ctl)

        self.tabs = QTabWidget()
        for page, name in ((self.gen_tab(), "✨ Generate"), (self.subs_tab(), "📝 Subtitles"), (self.style_tab(), "🎨 Style"), (self.export_tab(), "⬇ Export")):
            self.tabs.addTab(page, name)
        right = QFrame(); right.setObjectName("card"); rl = QVBoxLayout(right); rl.setContentsMargins(16, 12, 16, 14); rl.addWidget(self.tabs)
        sp = QSplitter(); sp.addWidget(left); sp.addWidget(right); sp.setSizes([1100, 560]); sp.setHandleWidth(16)
        bw = QWidget(); bl = QVBoxLayout(bw); bl.setContentsMargins(18, 16, 18, 12); bl.addWidget(sp)
        root = QWidget(); root.setObjectName("root"); rv = QVBoxLayout(root); rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(0)
        rv.addWidget(hdr); rv.addWidget(bw, 1); self.setCentralWidget(root)

        self.bar = QProgressBar(); self.bar.setFixedWidth(280); self.status = QLabel("Drop a video anywhere in the window, or click Import Video.")
        self.statusBar().addWidget(self.status, 1); self.statusBar().addPermanentWidget(self.bar)
        self.credit = QLabel(f"v{APP_VERSION}  ·  by {APP_AUTHOR}"); self.credit.setObjectName("muted"); self.statusBar().addPermanentWidget(self.credit)
        self.player.positionChanged.connect(self.on_pos); self.player.durationChanged.connect(lambda d: setattr(self.tl, "dur", max(d, 1)))
        self.player.playbackStateChanged.connect(lambda s: self.play.setText("⏸" if s == QMediaPlayer.PlayingState else "▶"))
        self.player.errorOccurred.connect(lambda e, s: self.status.setText("Preview error: " + s))
        self.apply_theme(str(QSettings("SubtitleStudio", "app").value("theme", "dark"))); self.set_step(0)
        self.refresh(); QTimer.singleShot(400, self.check_ffmpeg)

    def show_about(self):
        QMessageBox.about(self, f"About {APP_NAME}",
            f"<h3>{APP_NAME} v{APP_VERSION}</h3>"
            "<p>Offline English / Sinhala subtitle generator, editor and burner.</p>"
            f"<p>Created by <b>{APP_AUTHOR}</b><br>"
            f"GitHub: <a href='{APP_GITHUB}'>{APP_GITHUB.split('//')[1]}</a></p>"
            f"<p>&copy; {APP_YEAR} {APP_AUTHOR}. All rights reserved.</p>"
            "<p><small>Built with PySide6 (Qt), faster-whisper and FFmpeg. "
            "FFmpeg is a trademark of Fabrice Bellard; see ffmpeg.org for its license.</small></p>")

    def apply_theme(self, name):
        self.theme = name if name in THEMES else "dark"; t = THEMES[self.theme]; pal = QPalette()
        for role, key in ((QPalette.Window, "bg"), (QPalette.Base, "surface"), (QPalette.AlternateBase, "surface2"), (QPalette.Button, "surface2"),
                          (QPalette.WindowText, "text"), (QPalette.Text, "text"), (QPalette.ButtonText, "text"), (QPalette.ToolTipBase, "surface"), (QPalette.ToolTipText, "text")):
            pal.setColor(role, QColor(t[key]))
        pal.setColor(QPalette.Highlight, QColor(t["accent"])); pal.setColor(QPalette.HighlightedText, QColor("white"))
        app = QApplication.instance(); app.setPalette(pal); app.setStyleSheet(qss(t))
        self.b_theme.setText("☀" if self.theme == "dark" else "🌙"); self.tl.bg, self.tl.seg = t["surface2"], t["accent"]; self.tl.update()
        QSettings("SubtitleStudio", "app").setValue("theme", self.theme)

    def set_step(self, n):
        for i, l in enumerate(self.steps):
            st = "done" if i < n else "active" if i == n else "todo"
            l.setText(("✓  " if st == "done" else "") + self.STEPS[i]); l.setProperty("state", st); l.style().unpolish(l); l.style().polish(l)

    def drop_zone(self):
        dz = QFrame(); dz.setObjectName("drop"); v = QVBoxLayout(dz); v.setAlignment(Qt.AlignCenter); v.setSpacing(10)
        ic = QLabel(); ic.setPixmap(make_logo(256).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)); ic.setAlignment(Qt.AlignCenter)
        t = QLabel("Drop your video here"); t.setObjectName("h1"); t.setAlignment(Qt.AlignCenter)
        sub = QLabel("MP4 · MKV · MOV · AVI   —   English & Sinhala subtitles, made on your PC"); sub.setObjectName("muted"); sub.setAlignment(Qt.AlignCenter)
        b = QPushButton("Browse files…"); b.setObjectName("primary"); b.clicked.connect(self.pick_video)
        for x in (ic, t, sub): v.addWidget(x)
        v.addSpacing(8); v.addWidget(b, 0, Qt.AlignCenter); return dz

    def gen_tab(self):
        w = QWidget(); v = QVBoxLayout(w); v.setSpacing(12)
        h = QLabel("Generate subtitles"); h.setObjectName("h1"); v.addWidget(h)
        for text in ("Speech is recognised on your own PC. Nothing is uploaded.",):
            l = QLabel(text); l.setObjectName("muted"); l.setWordWrap(True); v.addWidget(l)
        f = QFormLayout(); f.setSpacing(10); f.addRow("Model", self.model); f.addRow("Spoken language", self.lang); v.addLayout(f)
        v.addWidget(self.music); v.addWidget(self.fast); v.addSpacing(6); v.addWidget(self.b_gen)
        tip = QLabel("Tip: for English use a Whisper model (small / medium / large-v3). For Sinhala pick a SinhaSpeech model (run12 is the most accurate); "
                     "the first use downloads and converts it once (needs: pip install transformers torch). You can fix any mistakes in the Subtitles tab afterwards.")
        tip.setObjectName("muted"); tip.setWordWrap(True); v.addWidget(tip); v.addStretch(); return w

    def model_name(self): return self.model.currentText().split("  (")[0].strip()

    def model_changed(self, t):
        if t.startswith(SINHALA_PREFIX): self.lang.setCurrentText("Sinhala")   # Sinhala-only model
        elif self.lang.currentText() == "Sinhala" and t in ENGLISH_MODELS and self._last_model.startswith(SINHALA_PREFIX): self.lang.setCurrentText("Auto")
        if t != "Custom folder…": self._last_model = t; return
        d = QFileDialog.getExistingDirectory(self, "Choose a faster-whisper model folder (contains model.bin)")
        if d: self.model.insertItem(self.model.count() - 1, d); self.model.setCurrentText(d)
        else: self.model.setCurrentText(self._last_model)

    def check_ffmpeg(self):
        if ffmpeg_ok(): return
        if QMessageBox.question(self, "FFmpeg needed", "FFmpeg (with subtitle support) was not found.\nDownload it now (~80 MB, one time)?") == QMessageBox.Yes:
            self.start(download_ffmpeg, lambda _: self.status.setText("FFmpeg installed. Ready."), "Downloading FFmpeg…")

    # ---- tabs
    def subs_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        h = self.table.horizontalHeader(); h.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 36); self.table.setColumnWidth(1, 100); self.table.setColumnWidth(2, 100)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.verticalHeader().setVisible(False); self.table.setShowGrid(False); self.table.setWordWrap(True)
        self.table.itemChanged.connect(self.cell); self.table.itemSelectionChanged.connect(self.row_selected)
        v.addWidget(self.table, 1); r = QHBoxLayout()
        for text, fn in (("＋ Add at playhead", self.add), ("🗑 Delete", self.delete), ("Start = playhead", lambda: self.stamp(1)),
                         ("End = playhead", lambda: self.stamp(2)), ("Save SRT…", self.save_srt)):
            b = QPushButton(text); b.clicked.connect(fn); r.addWidget(b)
        v.addLayout(r); v.addWidget(QLabel("Tip: double-click a time or text to edit. Times accept H:MM:SS.mmm"))
        return w

    def spin(self, attr, lo, hi, step=1.0, suf=""):
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setSingleStep(step); s.setSuffix(suf); s.setValue(getattr(self.st, attr))
        s.valueChanged.connect(lambda v: self.setst(attr, v)); return s

    def chk(self, attr, text):
        c = QCheckBox(text); c.setChecked(getattr(self.st, attr)); c.toggled.connect(lambda v: self.setst(attr, v)); return c

    def colorbtn(self, attr):
        b = QPushButton(); b.setFixedWidth(70); paint = lambda: b.setStyleSheet(f"background:{getattr(self.st, attr)};border:1px solid #888;")
        def pick():
            c = QColorDialog.getColor(QColor(getattr(self.st, attr)), self)
            if c.isValid(): self.setst(attr, c.name()); paint()
        paint(); b.clicked.connect(pick); return b

    def style_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.font = QFontComboBox(); self.font.setEditable(False); self.font.setCurrentFont(QFont(self.st.font)); self.font.currentFontChanged.connect(lambda x: self.setst("font", x.family()))
        f.addRow("Font", self.font); r = QHBoxLayout(); r.addWidget(self.chk("bold", "Bold")); r.addWidget(self.chk("italic", "Italic")); f.addRow("Style", r)
        f.addRow("Size", self.spin("size", 1.5, 15, 0.1, " % of height")); f.addRow("Text color", self.colorbtn("color"))
        f.addRow("Outline color", self.colorbtn("out_color")); f.addRow("Outline thickness", self.spin("outline", 0, 15, 0.5, " px"))
        f.addRow("Shadow distance", self.spin("shadow", 0, 15, 0.5, " px")); f.addRow("Shadow intensity", self.spin("sh_op", 0, 100, 5, " %"))
        f.addRow(self.chk("box", "Background box")); f.addRow("Box color", self.colorbtn("box_color")); f.addRow("Box opacity", self.spin("box_op", 0, 100, 5, " %"))
        self.align = QComboBox(); self.align.addItems(["Left", "Center", "Right"]); self.align.setCurrentText("Center")
        self.align.currentTextChanged.connect(self.set_align); f.addRow("Horizontal alignment", self.align)
        r = QHBoxLayout()
        for name, y in (("Top", 0.1), ("Center", 0.5), ("Bottom", 0.88)):
            b = QPushButton(name); b.clicked.connect(lambda _=0, y=y: self.setst("py", y)); r.addWidget(b)
        f.addRow("Vertical position", r); f.addRow(QLabel("You can also drag the subtitle directly in the preview."))
        return w

    def export_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.res = QComboBox(); self.res.addItems(["Auto (sharp text)", "Original", "1080p", "720p", "480p"]); f.addRow("Resolution", self.res)
        self.qual = QComboBox(); self.qual.addItems(["High (CRF 18)", "Balanced (CRF 23)", "Small file (CRF 28)"]); f.addRow("Quality", self.qual)
        self.hw = QCheckBox("Use GPU encoding when available (auto-detected)"); self.hw.setChecked(True); f.addRow(self.hw)
        f.addRow(QLabel("Subtitles are burned into a new MP4.\nYour original file is never modified."))
        return w

    # ---- style / preview
    def setst(self, a, v): setattr(self.st, a, v); self.refresh()

    def set_align(self, t):
        self.st.align = t.lower(); self.st.px = {"left": 0.05, "center": 0.5, "right": 0.95}[self.st.align]; self.refresh()

    def moved(self, px, py): self.st.px, self.st.py = px, py

    def active(self, ms):
        for i, (a, b, _) in enumerate(self.subs):
            if a <= ms < b: return i
        return -1

    def refresh(self):
        if not self.W: return
        i = self.active(self.player.position())
        text = self.subs[i][2] if i >= 0 else ("Sample subtitle • සිංහල උපසිරැසි" if not self.subs else "")
        self.sitem.rebuild(text, self.st, self.W, self.H); self.tl.update()

    def on_pos(self, ms):
        self.tl.pos = ms; self.clock.setText(fmt(ms)); i = self.active(ms)
        if i != self.cur:
            self.cur = i; self.refresh()
            if i >= 0 and self.player.playbackState() == QMediaPlayer.PlayingState:
                self.table.blockSignals(True); self.table.selectRow(i); self.table.blockSignals(False)
        self.tl.update()

    def toggle(self):
        if not self.W: return
        self.player.pause() if self.player.playbackState() == QMediaPlayer.PlayingState else self.player.play()

    # ---- subtitle table
    def refill(self):
        self._fill = True; t = self.table; t.setRowCount(len(self.subs))
        for r, (a, b, x) in enumerate(self.subs):
            for c, v in enumerate((str(r + 1), fmt(a), fmt(b), x)):
                it = QTableWidgetItem(v)
                if c == 0: it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                t.setItem(r, c, it)
        t.resizeRowsToContents(); self._fill = False; self.tl.subs = self.subs; self.cur = -2; self.refresh()

    def cell(self, it):
        if self._fill: return
        r, c = it.row(), it.column()
        if c == 3: self.subs[r][2] = it.text(); self.cur = -2; self.refresh(); return
        v = parse_t(it.text())
        if v is not None: self.subs[r][c - 1] = v; self.subs.sort(key=lambda s: s[0])
        self.refill()

    def row_selected(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.subs) and self.player.playbackState() != QMediaPlayer.PlayingState:
            self.player.setPosition(self.subs[r][0] + 1)

    def add(self):
        p = self.player.position(); self.subs.append([p, p + 2000, "New subtitle"]); self.subs.sort(key=lambda s: s[0]); self.refill()

    def delete(self):
        for r in sorted({i.row() for i in self.table.selectedItems()}, reverse=True): del self.subs[r]
        self.refill()

    def stamp(self, col):
        r = self.table.currentRow()
        if r >= 0: self.subs[r][col - 1] = self.player.position(); self.refill(); self.table.selectRow(r)

    def save_srt(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save SRT", str(Path(self.video or "subs").with_suffix(".srt")), "SubRip (*.srt)")
        if not p: return
        f = lambda ms: fmt(ms).replace(".", ",").rjust(12, "0")
        with open(p, "w", encoding="utf-8-sig") as fh:
            for n, (a, b, x) in enumerate(self.subs, 1): fh.write(f"{n}\n{f(a)} --> {f(b)}\n{x}\n\n")

    # ---- jobs
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if Path(u.toLocalFile()).suffix.lower() in (".mp4", ".mkv", ".mov", ".avi", ".m4v"): return self.open_video(u.toLocalFile())
        QMessageBox.warning(self, "Unsupported file", "Please drop an MP4, MKV, MOV or AVI video.")

    def pick_video(self):
        p, _ = QFileDialog.getOpenFileName(self, "Import video", "", "Video (*.mp4 *.mkv *.mov *.avi *.m4v)")
        if p: self.open_video(p)

    def start(self, fn, done, label):
        if self.worker and self.worker.isRunning(): return
        w = Worker(fn); w.progress.connect(self.on_prog)
        w.done.connect(done); w.failed.connect(self.fail); w.finished.connect(lambda: self.busy(False))
        self.worker = w; self.busy(True); self.bar.setValue(0); self.status.setText(label); w.start()

    def on_prog(self, p, m):
        self.bar.setRange(0, 0) if p < 0 else (self.bar.setRange(0, 100), self.bar.setValue(p))
        self.status.setText(m)

    def busy(self, b):
        if not b: self.bar.setRange(0, 100)
        for x in (self.b_imp, self.b_gen, self.b_exp): x.setEnabled(not b)
        self.b_can.setEnabled(b); self.b_can.setVisible(b)

    def cancel(self):
        if self.worker: self.worker.cancel = True

    def fail(self, msg):
        self.status.setText("Failed."); QMessageBox.critical(self, "Something went wrong", msg)

    def open_video(self, path): self.start(lambda w: load_job(path, self.tmp, w), self.loaded, "Reading video…")

    def loaded(self, r):
        self.video, proxy, self.W, self.H, self.dur = r; self.subs = []
        self.scene.setSceneRect(0, 0, self.W, self.H); self.vitem.setSize(QSizeF(self.W, self.H))
        self.player.setSource(QUrl.fromLocalFile(proxy or self.video)); self.player.pause()
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio); self.refill(); self.bar.setValue(100); self.stack.setCurrentIndex(1); self.set_step(1); self.tabs.setCurrentIndex(0)
        self.status.setText(f"Loaded {Path(self.video).name}  ({self.W}×{self.H}). Next: Generate Subtitles.")

    def generate(self):
        if not self.video: return QMessageBox.information(self, "No video", "Import a video first.")
        if self.subs and QMessageBox.question(self, "Replace subtitles?", "This replaces the current subtitles. Continue?") != QMessageBox.Yes: return
        self.start(lambda w: transcribe_job(self.video, self.model_name(), self.tmp, w, self.music.isChecked(), self.fast.isChecked(), {"English": "en", "Sinhala": "si"}.get(self.lang.currentText())), self.generated, "Starting…")

    def generated(self, r):
        lang, self.subs = r; self.refill(); self.bar.setValue(100); self.set_step(2); self.tabs.setCurrentIndex(1)
        self.status.setText(f"Done: {len(self.subs)} subtitles, detected {'Sinhala' if lang == 'si' else 'English'}. Review the text, then export.")

    def export(self):
        if not self.video: return QMessageBox.information(self, "No video", "Import a video first.")
        if not self.subs: return QMessageBox.information(self, "No subtitles", "Generate or add subtitles first.")
        out, _ = QFileDialog.getSaveFileName(self, "Export MP4", str(Path(self.video).with_name(Path(self.video).stem + "_subtitled.mp4")), "MP4 (*.mp4)")
        if not out: return
        if os.path.abspath(out) == os.path.abspath(self.video): return QMessageBox.warning(self, "Choose another name", "Output must differ from the original video.")
        rs = self.res.currentText()   # target = shorter side; Auto lifts small videos to 720p so subtitles are crisp
        tgt = (720 if min(self.W, self.H) < 720 else None) if rs.startswith("Auto") else {"Original": None, "1080p": 1080, "720p": 720, "480p": 480}[rs]
        sc = tgt / min(self.W, self.H) if tgt else 1.0   # upscaling allowed: text is drawn at the output size, so it stays sharp
        W = round(self.W * sc / 2) * 2; H = round(self.H * sc / 2) * 2; crf = (18, 23, 28)[self.qual.currentIndex()]
        subs = [list(s) for s in self.subs]; st = Style(**self.st.__dict__)
        self.start(lambda w: export_job(self.video, out, subs, st, W, H, self.dur, crf, self.tmp, w, self.hw.isChecked()),
                   lambda o: (self.bar.setValue(100), self.set_step(4), self.status.setText("Export complete: " + o)), "Exporting…")

    def closeEvent(self, e):
        self.player.stop(); shutil.rmtree(self.tmp, ignore_errors=True); super().closeEvent(e)


def main():
    try:
        import ctypes; ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SubtitleStudio.App")   # own taskbar icon
    except Exception:
        pass
    app = QApplication(sys.argv); app.setStyle("Fusion"); app.setWindowIcon(QIcon(make_logo(256)))
    def hook(t, v, tb):
        import traceback
        QMessageBox.critical(None, "Unexpected error", "".join(traceback.format_exception(t, v, tb))[-1500:])
    sys.excepthook = hook
    splash = QSplashScreen(make_splash(), Qt.WindowStaysOnTopHint); splash.show(); t0 = time.time()
    def note(m): splash.showMessage(m, Qt.AlignBottom | Qt.AlignHCenter, QColor("#c8cdf5")); app.processEvents()
    note("Loading interface…"); w = Main(); note("Ready")
    while time.time() - t0 < 1.8: app.processEvents(); time.sleep(0.01)
    w.showMaximized(); splash.finish(w); sys.exit(app.exec())


if __name__ == "__main__":
    main()