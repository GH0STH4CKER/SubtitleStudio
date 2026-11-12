"""SubtitleStudio - offline English/Sinhala subtitle generator, editor and burner.
Stack: PySide6 (UI), faster-whisper (local speech recognition), FFmpeg (audio/video/subtitle rendering)."""
import sys, os, json, time, shutil, tempfile, subprocess
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QRectF, QPointF, QSizeF
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPalette
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

APP_DIR = Path(sys.argv[0]).resolve().parent
NOWIN = 0x08000000 if os.name == "nt" else 0
NO_FFMPEG = ("FFmpeg not found. Install it (winget install Gyan.FFmpeg) or put ffmpeg.exe and "
             "ffprobe.exe in an 'ffmpeg' folder next to this app. Use a build with libass/HarfBuzz (gyan.dev).")


_wf = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts").replace("\\", "/")
FONTS_DIR = "'" + _wf.replace(":", "\\:") + "'"   # quoted + escaped for FFmpeg filter syntax


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


def transcribe_job(video, model_name, tmp, w, music=False):
    wav = os.path.join(tmp, "audio.wav")
    w.progress.emit(2, "Extracting audio…")
    r = run([tool("ffmpeg"), "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav])
    if r.returncode: raise RuntimeError("Audio extraction failed (does the video have sound?):\n" + r.stderr[-400:])
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")
    w.progress.emit(-1, "Loading speech model. FIRST USE DOWNLOADS IT (small ≈ 500 MB, large-v3 ≈ 3 GB) – this can take minutes with no progress shown…")
    import wave
    import numpy as np
    with wave.open(wav, "rb") as wf:   # decode ourselves so faster-whisper never calls PyAV
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(model_name, device="auto", compute_type="auto")
    w.progress.emit(10, "Model ready. Starting transcription…")
    go = lambda lang: model.transcribe(audio, language=lang, vad_filter=not music, vad_parameters=dict(min_silence_duration_ms=1500), beam_size=5,
                                       word_timestamps=True, condition_on_previous_text=False)
    segs, info = go(None); lang = info.language
    if lang not in ("en", "si"):   # only English / Sinhala are expected: pick the likelier of the two
        probs = dict(info.all_language_probs or [])
        lang = max(("en", "si"), key=lambda l: probs.get(l, 0)); segs, info = go(lang)
    out, dur = [], info.duration or 1
    for s in segs:
        if w.cancel: raise RuntimeError("Cancelled.")
        out += split_words(s.words) if s.words else [[int(s.start * 1000), int(s.end * 1000), s.text.strip()]]
        w.progress.emit(10 + int(88 * min(s.end / dur, 1)), f"Transcribing ({'Sinhala' if lang == 'si' else 'English'})…")
    return lang, out


def export_job(video, out, subs, st, W, H, dur, crf, tmp, w):
    open(os.path.join(tmp, "s.ass"), "w", encoding="utf-8").write(build_ass(subs, st, W, H))
    cmd = [tool("ffmpeg"), "-y", "-i", os.path.abspath(video), "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", f"scale={W}:{H}:flags=lanczos,ass=s.ass:fontsdir={FONTS_DIR}", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-strict", "-2", "-b:a", "192k", "-movflags", "+faststart",
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
                w.progress.emit(int(done * 100), f"Exporting… {int(done * 100)}%  •  about {int(eta // 60)}m {int(eta % 60)}s left")
    if p.wait() != 0:
        log.close(); raise RuntimeError("FFmpeg failed:\n" + open(os.path.join(tmp, "ff.log"), encoding="utf-8").read()[-600:])
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


class Timeline(QWidget):
    seek = Signal(int)
    def __init__(self):
        super().__init__(); self.setFixedHeight(34); self.dur = 1; self.pos = 0; self.subs = []

    def paintEvent(self, e):
        p = QPainter(self); p.fillRect(self.rect(), QColor("#1a1a20")); w = self.width()
        for a, b, _ in self.subs:
            p.fillRect(QRectF(a / self.dur * w, 6, max(2, (b - a) / self.dur * w), self.height() - 12), QColor("#4f8cff"))
        x = int(self.pos / self.dur * w); p.setPen(QPen(QColor("#ff5a5a"), 2)); p.drawLine(x, 0, x, self.height())

    def _m(self, e): self.seek.emit(int(min(max(e.position().x() / max(self.width(), 1), 0), 1) * self.dur))
    mousePressEvent = mouseMoveEvent = _m


# ---------------------------------------------------------------- main window
class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("SubtitleStudio"); self.resize(1450, 880); self.setAcceptDrops(True)
        self.st = Style(); self.subs = []; self.video = None; self.W = self.H = 0; self.dur = 1.0
        self.worker = None; self._fill = False; self.cur = -2; self.tmp = tempfile.mkdtemp(prefix="substudio_")
        self.player = QMediaPlayer(); self.audio = QAudioOutput(); self.player.setAudioOutput(self.audio)
        self.scene = QGraphicsScene(); self.vitem = QGraphicsVideoItem(); self.scene.addItem(self.vitem)
        self.player.setVideoOutput(self.vitem)
        self.sitem = SubItem(self.moved); self.scene.addItem(self.sitem)
        self.view = View(self.scene); self.view.setBackgroundBrush(QColor("#0b0b0e")); self.view.setFrameShape(QFrame.NoFrame)

        # toolbar = the 4-step workflow
        tb = self.addToolBar("Workflow"); tb.setMovable(False)
        self.b_imp = QPushButton("①  Import Video"); self.b_gen = QPushButton("②  Generate Subtitles")
        self.b_exp = QPushButton("④  Export MP4"); self.b_can = QPushButton("Cancel")
        self.b_imp.clicked.connect(self.pick_video); self.b_gen.clicked.connect(self.generate)
        self.b_exp.clicked.connect(self.export); self.b_can.clicked.connect(self.cancel)
        self.model = QComboBox(); self.model.setEditable(True); self.model.addItems(["small", "medium", "large-v3"])
        self.model.setCurrentText("small"); self.model.setToolTip("Whisper model, or a path to a converted (CTranslate2) custom model, e.g. a Sinhala fine-tune")
        self.music = QCheckBox("Music / singing"); self.music.setChecked(True)
        self.music.setToolTip("Turns off the voice filter so vocals over music are not skipped")
        for wd in (self.b_imp, QLabel("  Model: "), self.model, self.music, self.b_gen, QLabel("   ③ Edit & style →  "), self.b_exp, self.b_can):
            tb.addWidget(wd)
        self.b_can.setEnabled(False)

        # left: preview + controls
        self.play = QPushButton("▶"); self.play.setFixedWidth(44); self.play.clicked.connect(self.toggle)
        self.tl = Timeline(); self.tl.seek.connect(self.player.setPosition); self.clock = QLabel("0:00:00.000")
        ctl = QHBoxLayout(); ctl.addWidget(self.play); ctl.addWidget(self.tl, 1); ctl.addWidget(self.clock)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.addWidget(self.view, 1); lv.addLayout(ctl)

        tabs = QTabWidget(); tabs.addTab(self.subs_tab(), "Subtitles"); tabs.addTab(self.style_tab(), "Style"); tabs.addTab(self.export_tab(), "Export")
        sp = QSplitter(); sp.addWidget(left); sp.addWidget(tabs); sp.setSizes([900, 520]); self.setCentralWidget(sp)

        self.bar = QProgressBar(); self.bar.setFixedWidth(280); self.status = QLabel("Drop a video here or click Import.")
        self.statusBar().addWidget(self.status, 1); self.statusBar().addPermanentWidget(self.bar)
        self.player.positionChanged.connect(self.on_pos); self.player.durationChanged.connect(lambda d: setattr(self.tl, "dur", max(d, 1)))
        self.player.playbackStateChanged.connect(lambda s: self.play.setText("⏸" if s == QMediaPlayer.PlayingState else "▶"))
        self.player.errorOccurred.connect(lambda e, s: self.status.setText("Preview error: " + s))
        self.refresh()

    # ---- tabs
    def subs_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        h = self.table.horizontalHeader(); h.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 36); self.table.setColumnWidth(1, 100); self.table.setColumnWidth(2, 100)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setWordWrap(True)
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
        self.font = QFontComboBox(); self.font.setCurrentFont(QFont(self.st.font)); self.font.currentFontChanged.connect(lambda x: self.setst("font", x.family()))
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
        self.res = QComboBox(); self.res.addItems(["Original", "1080p", "720p", "480p"]); self.res.setCurrentText("720p"); f.addRow("Resolution", self.res)
        self.qual = QComboBox(); self.qual.addItems(["High (CRF 18)", "Balanced (CRF 23)", "Small file (CRF 28)"]); f.addRow("Quality", self.qual)
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
        self.b_can.setEnabled(b)

    def cancel(self):
        if self.worker: self.worker.cancel = True

    def fail(self, msg):
        self.status.setText("Failed."); QMessageBox.critical(self, "Something went wrong", msg)

    def open_video(self, path): self.start(lambda w: load_job(path, self.tmp, w), self.loaded, "Reading video…")

    def loaded(self, r):
        self.video, proxy, self.W, self.H, self.dur = r; self.subs = []
        self.scene.setSceneRect(0, 0, self.W, self.H); self.vitem.setSize(QSizeF(self.W, self.H))
        self.player.setSource(QUrl.fromLocalFile(proxy or self.video)); self.player.pause()
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio); self.refill(); self.bar.setValue(100)
        self.status.setText(f"Loaded {Path(self.video).name}  ({self.W}×{self.H}). Next: Generate Subtitles.")

    def generate(self):
        if not self.video: return QMessageBox.information(self, "No video", "Import a video first.")
        if self.subs and QMessageBox.question(self, "Replace subtitles?", "This replaces the current subtitles. Continue?") != QMessageBox.Yes: return
        self.start(lambda w: transcribe_job(self.video, self.model.currentText().strip(), self.tmp, w, self.music.isChecked()), self.generated, "Starting…")

    def generated(self, r):
        lang, self.subs = r; self.refill(); self.bar.setValue(100)
        self.status.setText(f"Done: {len(self.subs)} subtitles, detected {'Sinhala' if lang == 'si' else 'English'}. Review the text, then export.")

    def export(self):
        if not self.video: return QMessageBox.information(self, "No video", "Import a video first.")
        if not self.subs: return QMessageBox.information(self, "No subtitles", "Generate or add subtitles first.")
        out, _ = QFileDialog.getSaveFileName(self, "Export MP4", str(Path(self.video).with_name(Path(self.video).stem + "_subtitled.mp4")), "MP4 (*.mp4)")
        if not out: return
        if os.path.abspath(out) == os.path.abspath(self.video): return QMessageBox.warning(self, "Choose another name", "Output must differ from the original video.")
        tgt = {"Original": None, "1080p": 1080, "720p": 720, "480p": 480}[self.res.currentText()]   # target = shorter side
        sc = tgt / min(self.W, self.H) if tgt else 1.0   # upscaling allowed: text is drawn at the output size, so it stays sharp
        W = round(self.W * sc / 2) * 2; H = round(self.H * sc / 2) * 2; crf = (18, 23, 28)[self.qual.currentIndex()]
        subs = [list(s) for s in self.subs]; st = Style(**self.st.__dict__)
        self.start(lambda w: export_job(self.video, out, subs, st, W, H, self.dur, crf, self.tmp, w),
                   lambda o: (self.bar.setValue(100), self.status.setText("Export complete: " + o)), "Exporting…")

    def closeEvent(self, e):
        self.player.stop(); shutil.rmtree(self.tmp, ignore_errors=True); super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    def hook(t, v, tb):
        import traceback
        QMessageBox.critical(None, "Unexpected error", "".join(traceback.format_exception(t, v, tb))[-1500:])
    sys.excepthook = hook; app.setStyle("Fusion"); pal = QPalette()
    for role, col in ((QPalette.Window, "#16161b"), (QPalette.Base, "#1d1d24"), (QPalette.AlternateBase, "#22222a"), (QPalette.Button, "#2a2a33"),
                      (QPalette.WindowText, "#e8e8ee"), (QPalette.Text, "#e8e8ee"), (QPalette.ButtonText, "#e8e8ee"),
                      (QPalette.Highlight, "#4f8cff"), (QPalette.HighlightedText, "#ffffff"), (QPalette.ToolTipBase, "#2a2a33"), (QPalette.ToolTipText, "#e8e8ee")):
        pal.setColor(role, QColor(col))
    app.setPalette(pal); app.setStyleSheet("QPushButton{padding:6px 12px;border-radius:5px;} QToolBar{spacing:8px;padding:6px;border:0;}"
                                           "QProgressBar{border-radius:4px;text-align:center;} QProgressBar::chunk{background:#4f8cff;}")
    w = Main(); w.show(); sys.exit(app.exec())


if __name__ == "__main__":
    main()