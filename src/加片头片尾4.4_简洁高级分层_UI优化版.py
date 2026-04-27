# -*- coding: utf-8 -*-
"""
专业视频片头片尾批处理工具 v4.4

设计目标：
1. 小白模式：只保留必要选项，默认参数就能稳定处理。
2. 半专业模式：展开编码、码率、画面适配、音频、高级 FFmpeg 参数。
3. UI 更省空间：文件区 + 设置区为主体，日志缩到底部并支持展开/收起。
4. 防呆设计：自动检测 ffmpeg、路径校验、参数校验、停止时终止 ffmpeg 子进程。

运行：
    python 加片头片尾4.4_简洁高级分层_UI优化版.py

依赖：
    需要安装 ffmpeg，并把 ffmpeg 加入系统 PATH。
"""

import os
import re
import sys
import shlex
import shutil
import signal
import queue
import tempfile
import threading
import subprocess
from dataclasses import dataclass
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v")


def _find_ffmpeg_binary(name: str) -> str | None:
    """
    查找 ffmpeg / ffprobe 可执行文件。
    优先级：
      1. exe 同级目录下的 {name}.exe   ← 用户直接把 ffmpeg.exe/ffprobe.exe 丢进来
      2. 系统 PATH（shutil.which）      ← 兜底，方便开发者本机调试
    """
    # frozen=True 说明已打包为 exe；此时 sys.executable 就是 exe 本体路径。
    # 脚本直接运行时用 __file__ 所在目录（方便调试）。
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent

    local = base_dir / f"{name}.exe"
    if local.is_file():
        return str(local)

    return shutil.which(name)


@dataclass
class EncodePlan:
    codec: str
    encoder: str
    preset: str
    rate_mode: str
    bitrate: str
    maxrate: str
    crf_cq: str
    audio_bitrate: str
    extra_args: str


class ScrollableFrame(ttk.Frame):
    """一个可滚动的 ttk.Frame，用于小屏幕下防止按钮被挤出窗口。"""

    def __init__(self, parent, height=None):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        if height:
            self.canvas.configure(height=height)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_windows)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel_windows(self, event):
        # 只在鼠标位于该控件内时滚动，避免影响 Treeview / Text。
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget and str(widget).startswith(str(self)):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        if not (widget and str(widget).startswith(str(self))):
            return
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


class VideoProcessorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("专业视频片头片尾批处理工具 v4.4")
        self.master.geometry("1180x760")
        self.master.minsize(980, 640)

        self.file_list = []
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self.current_process = None

        self.ffmpeg_path = _find_ffmpeg_binary("ffmpeg")
        self.ffprobe_path = _find_ffmpeg_binary("ffprobe")

        self._build_variables()
        self._setup_styles()
        self._build_ui()
        self._bind_events()
        self._refresh_mode_ui()
        self._refresh_resolution_presets()
        self.master.after(100, self._process_queues)

        if not self.ffmpeg_path:
            self._show_ffmpeg_warning()
        else:
            self.log(f"检测到 FFmpeg：{self.ffmpeg_path}", "success")

    # ------------------------------------------------------------------
    # UI 初始化
    # ------------------------------------------------------------------
    def _build_variables(self):
        self.mode_var = tk.StringVar(value="小白推荐")
        self.process_type_var = tk.StringVar(value="同时添加")
        self.aspect_var = tk.StringVar(value="9:16 竖屏")
        self.resolution_var = tk.StringVar(value="1080x1920")
        self.fit_mode_var = tk.StringVar(value="居中裁剪")
        self.framerate_var = tk.StringVar(value="30")
        self.quality_preset_var = tk.StringVar(value="高清推荐")

        self.accel_var = tk.StringVar(value="自动选择")
        self.codec_var = tk.StringVar(value="H.264 兼容优先")
        self.rate_mode_var = tk.StringVar(value="智能动态码率")
        self.bitrate_var = tk.StringVar(value="6000")
        self.maxrate_var = tk.StringVar(value="9000")
        self.crf_cq_var = tk.StringVar(value="22")
        self.encoder_preset_var = tk.StringVar(value="均衡")
        self.audio_bitrate_var = tk.StringVar(value="192")
        self.audio_mode_var = tk.StringVar(value="AAC 立体声")
        self.extra_args_var = tk.StringVar(value="")
        self.log_expanded_var = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=True)
        self.keep_temp_var = tk.BooleanVar(value=False)

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background="#f4f6f8")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#f4f6f8", font=("微软雅黑", 9))
        style.configure("Card.TLabel", background="#ffffff", font=("微软雅黑", 9))
        style.configure("Hint.TLabel", background="#ffffff", foreground="#64748b", font=("微软雅黑", 8))
        style.configure("Title.TLabel", background="#f4f6f8", font=("微软雅黑", 15, "bold"), foreground="#0f172a")
        style.configure("Section.TLabel", background="#ffffff", font=("微软雅黑", 10, "bold"), foreground="#1e293b")
        style.configure("TButton", font=("微软雅黑", 9), padding=(8, 4))
        style.configure("Primary.TButton", font=("微软雅黑", 10, "bold"), padding=(12, 7))
        style.configure("Danger.TButton", foreground="#b91c1c", font=("微软雅黑", 10, "bold"), padding=(12, 7))
        style.configure("Small.TButton", font=("微软雅黑", 8), padding=(6, 2))
        style.configure("TCheckbutton", background="#ffffff", font=("微软雅黑", 9))
        style.configure("TRadiobutton", background="#ffffff", font=("微软雅黑", 9))
        style.configure("TLabelframe", background="#ffffff")
        style.configure("TLabelframe.Label", font=("微软雅黑", 10, "bold"), foreground="#334155")

    def _build_ui(self):
        root = ttk.Frame(self.master, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        self._build_header(root)

        body = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, pady=(8, 6))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        self._build_file_panel(left)
        self._build_settings_panel(right)
        self._build_bottom_bar(root)
        self._build_log_panel(root)

    def _build_header(self, parent):
        header = ttk.Frame(parent)
        header.pack(fill=tk.X)

        ttk.Label(header, text="视频片头片尾批处理", style="Title.TLabel").pack(side=tk.LEFT)

        mode_box = ttk.Frame(header)
        mode_box.pack(side=tk.RIGHT)
        ttk.Label(mode_box, text="操作模式：").pack(side=tk.LEFT, padx=(0, 4))
        self.mode_combo = ttk.Combobox(
            mode_box,
            textvariable=self.mode_var,
            values=["小白推荐", "半专业调节"],
            state="readonly",
            width=14,
        )
        self.mode_combo.pack(side=tk.LEFT)

    def _build_file_panel(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        card.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill=tk.X)
        ttk.Label(top, text="文件列表", style="Section.TLabel").pack(side=tk.LEFT)

        btns = ttk.Frame(top, style="Card.TFrame")
        btns.pack(side=tk.RIGHT)
        ttk.Button(btns, text="添加文件夹", style="Small.TButton", command=self.add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="添加文件", style="Small.TButton", command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="删除选中", style="Small.TButton", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="清空", style="Small.TButton", command=self.clear_list).pack(side=tk.LEFT, padx=2)

        hint = ttk.Label(
            card,
            text="支持 mp4 / mov / mkv / avi / webm 等常见格式，可批量添加文件夹。",
            style="Hint.TLabel",
        )
        hint.pack(fill=tk.X, pady=(4, 6))

        table_frame = ttk.Frame(card, style="Card.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("status", "name", "path"),
            show="headings",
            selectmode="extended",
        )
        self.tree.heading("status", text="状态")
        self.tree.heading("name", text="文件名")
        self.tree.heading("path", text="路径")
        self.tree.column("status", width=76, anchor=tk.CENTER, stretch=False)
        self.tree.column("name", width=180, anchor=tk.W, stretch=False)
        self.tree.column("path", width=420, anchor=tk.W)

        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="删除选中", command=self.delete_selected)
        self.context_menu.add_command(label="打开所在文件夹", command=self.open_selected_folder)
        self.tree.bind("<Button-3>", self._show_context_menu)

    def _build_settings_panel(self, parent):
        outer = ttk.Frame(parent, style="Card.TFrame", padding=10)
        outer.pack(fill=tk.BOTH, expand=True, padx=(8, 0))

        ttk.Label(outer, text="处理与编码设置", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="小白模式只显示必要选项；半专业模式会展开码率、编码器、音频和高级参数。",
            style="Hint.TLabel",
        ).pack(fill=tk.X, pady=(4, 6))

        self.settings_scroll = ScrollableFrame(outer)
        self.settings_scroll.pack(fill=tk.BOTH, expand=True)
        form = self.settings_scroll.inner

        self._build_basic_settings(form)
        self._build_simple_settings(form)
        self._build_advanced_settings(form)

    def _build_basic_settings(self, parent):
        frame = ttk.LabelFrame(parent, text="基础处理", padding=10)
        frame.pack(fill=tk.X, pady=(0, 8), padx=(0, 2))
        frame.columnconfigure(1, weight=1)

        self._add_label(frame, "处理类型", 0)
        ttk.Combobox(
            frame,
            textvariable=self.process_type_var,
            values=["加片头", "加片尾", "同时添加"],
            state="readonly",
            width=14,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        self._add_label(frame, "片头文件", 1)
        self.intro_entry = ttk.Entry(frame)
        self.intro_entry.grid(row=1, column=1, sticky="ew", padx=(8, 4), pady=3)
        ttk.Button(frame, text="浏览", style="Small.TButton", command=lambda: self.browse_file(self.intro_entry)).grid(row=1, column=2, pady=3)

        self._add_label(frame, "片尾文件", 2)
        self.outro_entry = ttk.Entry(frame)
        self.outro_entry.grid(row=2, column=1, sticky="ew", padx=(8, 4), pady=3)
        ttk.Button(frame, text="浏览", style="Small.TButton", command=lambda: self.browse_file(self.outro_entry)).grid(row=2, column=2, pady=3)

        self._add_label(frame, "输出目录", 3)
        self.output_entry = ttk.Entry(frame)
        self.output_entry.grid(row=3, column=1, sticky="ew", padx=(8, 4), pady=3)
        ttk.Button(frame, text="浏览", style="Small.TButton", command=self.browse_output_dir).grid(row=3, column=2, pady=3)

    def _build_simple_settings(self, parent):
        self.simple_frame = ttk.LabelFrame(parent, text="小白推荐", padding=10)
        self.simple_frame.pack(fill=tk.X, pady=(0, 8), padx=(0, 2))
        self.simple_frame.columnconfigure(1, weight=1)

        self._add_label(self.simple_frame, "画面比例", 0)
        ttk.Combobox(
            self.simple_frame,
            textvariable=self.aspect_var,
            values=["9:16 竖屏", "16:9 横屏", "跟随原视频", "自定义"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        self._add_label(self.simple_frame, "分辨率", 1)
        self.simple_resolution_combo = ttk.Combobox(self.simple_frame, textvariable=self.resolution_var)
        self.simple_resolution_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=3)

        self._add_label(self.simple_frame, "帧率", 2)
        self.simple_fps_combo = ttk.Combobox(
            self.simple_frame,
            textvariable=self.framerate_var,
            values=["跟随原视频", "24", "25", "30", "50", "60"],
        )
        self.simple_fps_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=3)

        self._add_label(self.simple_frame, "画质", 3)
        ttk.Combobox(
            self.simple_frame,
            textvariable=self.quality_preset_var,
            values=["体积优先", "高清推荐", "高质量", "极致质量"],
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(
            self.simple_frame,
            text="推荐：竖屏短视频用 9:16 + 1080x1920 + 高清推荐；普通电脑也能直接跑。",
            style="Hint.TLabel",
            wraplength=340,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    def _build_advanced_settings(self, parent):
        self.advanced_frame = ttk.Frame(parent, style="Card.TFrame")
        self.advanced_frame.pack(fill=tk.X, pady=(0, 8), padx=(0, 2))

        video = ttk.LabelFrame(self.advanced_frame, text="半专业画面设置", padding=10)
        video.pack(fill=tk.X, pady=(0, 8))
        video.columnconfigure(1, weight=1)
        video.columnconfigure(3, weight=1)

        self._add_label(video, "画面比例", 0, 0)
        ttk.Combobox(
            video,
            textvariable=self.aspect_var,
            values=["9:16 竖屏", "16:9 横屏", "跟随原视频", "自定义"],
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=3)

        self._add_label(video, "分辨率", 0, 2)
        self.advanced_resolution_combo = ttk.Combobox(video, textvariable=self.resolution_var, width=14)
        self.advanced_resolution_combo.grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=3)

        self._add_label(video, "适配方式", 1, 0)
        ttk.Combobox(
            video,
            textvariable=self.fit_mode_var,
            values=["居中裁剪", "完整保留补黑边", "拉伸填满"],
            state="readonly",
            width=12,
        ).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=3)

        self._add_label(video, "帧率", 1, 2)
        self.advanced_fps_combo = ttk.Combobox(
            video,
            textvariable=self.framerate_var,
            values=["跟随原视频", "24", "25", "30", "50", "60"],
            width=14,
        )
        self.advanced_fps_combo.grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=3)

        codec = ttk.LabelFrame(self.advanced_frame, text="编码与码率", padding=10)
        codec.pack(fill=tk.X, pady=(0, 8))
        codec.columnconfigure(1, weight=1)
        codec.columnconfigure(3, weight=1)

        self._add_label(codec, "编码格式", 0, 0)
        ttk.Combobox(
            codec,
            textvariable=self.codec_var,
            values=["H.264 兼容优先", "H.265 体积更小"],
            state="readonly",
            width=14,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=3)

        self._add_label(codec, "硬件加速", 0, 2)
        ttk.Combobox(
            codec,
            textvariable=self.accel_var,
            values=["自动选择", "NVIDIA GPU", "AMD GPU", "Intel GPU", "CPU"],
            state="readonly",
            width=14,
        ).grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=3)

        self._add_label(codec, "码率模式", 1, 0)
        ttk.Combobox(
            codec,
            textvariable=self.rate_mode_var,
            values=["智能动态码率", "固定码率 CBR", "平均码率 VBR", "恒定质量 CRF/CQ"],
            state="readonly",
            width=14,
        ).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=3)

        self.bitrate_label = self._add_label(codec, "目标码率", 2, 0)
        self.bitrate_entry = ttk.Combobox(codec, textvariable=self.bitrate_var, values=["3000", "5000", "6000", "8000", "12000", "20000"], width=12)
        self.bitrate_entry.grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=3)

        self.maxrate_label = self._add_label(codec, "最高码率", 2, 2)
        self.maxrate_entry = ttk.Combobox(codec, textvariable=self.maxrate_var, values=["5000", "9000", "12000", "18000", "30000"], width=12)
        self.maxrate_entry.grid(row=2, column=3, sticky="ew", padx=(8, 0), pady=3)

        self.crf_label = self._add_label(codec, "CRF/CQ", 3, 0)
        self.crf_entry = ttk.Combobox(codec, textvariable=self.crf_cq_var, values=["18", "20", "22", "24", "26", "28"], width=12)
        self.crf_entry.grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=3)

        self._add_label(codec, "编码预设", 3, 2)
        ttk.Combobox(
            codec,
            textvariable=self.encoder_preset_var,
            values=["速度优先", "均衡", "质量优先"],
            state="readonly",
            width=12,
        ).grid(row=3, column=3, sticky="ew", padx=(8, 0), pady=3)

        audio = ttk.LabelFrame(self.advanced_frame, text="音频与高级", padding=10)
        audio.pack(fill=tk.X, pady=(0, 8))
        audio.columnconfigure(1, weight=1)
        audio.columnconfigure(3, weight=1)

        self._add_label(audio, "音频模式", 0, 0)
        ttk.Combobox(
            audio,
            textvariable=self.audio_mode_var,
            values=["AAC 立体声", "复制音频", "静音输出"],
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=3)

        self._add_label(audio, "音频码率", 0, 2)
        ttk.Combobox(audio, textvariable=self.audio_bitrate_var, values=["128", "160", "192", "256", "320"], width=12).grid(
            row=0, column=3, sticky="ew", padx=(8, 0), pady=3
        )

        self._add_label(audio, "高级参数", 1, 0)
        ttk.Entry(audio, textvariable=self.extra_args_var).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=3)

        options = ttk.Frame(audio, style="Card.TFrame")
        options.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Checkbutton(options, text="覆盖同名输出", variable=self.overwrite_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(options, text="保留临时文件", variable=self.keep_temp_var).pack(side=tk.LEFT)

        ttk.Label(
            audio,
            text="提示：高级参数可填写如 -movflags +faststart；不会写就留空。",
            style="Hint.TLabel",
        ).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(4, 0))

    def _build_bottom_bar(self, parent):
        bottom = ttk.Frame(parent)
        bottom.pack(fill=tk.X, pady=(0, 6))

        self.status_label = ttk.Label(bottom, text="准备就绪", foreground="#334155")
        self.status_label.pack(side=tk.LEFT)

        right = ttk.Frame(bottom)
        right.pack(side=tk.RIGHT)
        self.progress = ttk.Progressbar(right, orient=tk.HORIZONTAL, mode="determinate", length=220)
        self.progress.pack(side=tk.LEFT, padx=(0, 8))
        self.start_btn = ttk.Button(right, text="开始处理", style="Primary.TButton", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = ttk.Button(right, text="停止", style="Danger.TButton", command=self.stop_processing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)

    def _build_log_panel(self, parent):
        shell = ttk.Frame(parent)
        shell.pack(fill=tk.X)

        top = ttk.Frame(shell)
        top.pack(fill=tk.X)
        ttk.Checkbutton(
            top,
            text="展开详细日志",
            variable=self.log_expanded_var,
            command=self._toggle_log_height,
        ).pack(side=tk.LEFT)
        ttk.Button(top, text="清空日志", style="Small.TButton", command=self.clear_log).pack(side=tk.RIGHT)

        self.log_frame = ttk.Frame(shell)
        self.log_frame.pack(fill=tk.X)
        self.log_text = tk.Text(
            self.log_frame,
            wrap=tk.WORD,
            height=4,
            state=tk.DISABLED,
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
        )
        log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _add_label(self, parent, text, row, column=0):
        label = ttk.Label(parent, text=f"{text}：", style="Card.TLabel")
        label.grid(row=row, column=column, sticky=tk.W, pady=3)
        return label

    def _bind_events(self):
        self.mode_var.trace_add("write", lambda *_: self._refresh_mode_ui())
        self.aspect_var.trace_add("write", lambda *_: self._refresh_resolution_presets())
        self.rate_mode_var.trace_add("write", lambda *_: self._refresh_rate_mode_ui())
        self.process_type_var.trace_add("write", lambda *_: self._refresh_process_type_ui())

    # ------------------------------------------------------------------
    # UI 动态刷新
    # ------------------------------------------------------------------
    def _refresh_mode_ui(self):
        is_simple = self.mode_var.get() == "小白推荐"
        if is_simple:
            self.advanced_frame.pack_forget()
            if not self.simple_frame.winfo_ismapped():
                self.simple_frame.pack(fill=tk.X, pady=(0, 8), padx=(0, 2), after=self.simple_frame.master.winfo_children()[0])
            self.status_label.configure(text="小白推荐模式：保留必要参数，默认即可使用")
        else:
            self.simple_frame.pack_forget()
            if not self.advanced_frame.winfo_ismapped():
                self.advanced_frame.pack(fill=tk.X, pady=(0, 8), padx=(0, 2))
            self.status_label.configure(text="半专业调节模式：可调整编码、码率、音频和高级参数")
        self._refresh_rate_mode_ui()
        self._refresh_process_type_ui()

    def _refresh_process_type_ui(self):
        pt = self.process_type_var.get()
        intro_needed = pt in ("加片头", "同时添加")
        outro_needed = pt in ("加片尾", "同时添加")
        self._set_entry_state(self.intro_entry, intro_needed)
        self._set_entry_state(self.outro_entry, outro_needed)

    def _set_entry_state(self, entry, enabled):
        entry.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _refresh_resolution_presets(self):
        aspect = self.aspect_var.get()
        if aspect == "9:16 竖屏":
            values = ["1080x1920", "720x1280", "1440x2560", "2160x3840", "自定义输入"]
            if self.resolution_var.get() not in values or self.resolution_var.get() == "1920x1080":
                self.resolution_var.set("1080x1920")
        elif aspect == "16:9 横屏":
            values = ["1920x1080", "1280x720", "2560x1440", "3840x2160", "自定义输入"]
            if self.resolution_var.get() not in values or self.resolution_var.get() == "1080x1920":
                self.resolution_var.set("1920x1080")
        elif aspect == "跟随原视频":
            values = ["跟随原视频"]
            self.resolution_var.set("跟随原视频")
        else:
            values = ["1080x1920", "1920x1080", "720x1280", "1280x720", "自定义输入"]
            if self.resolution_var.get() == "跟随原视频":
                self.resolution_var.set("1080x1920")

        for combo_name in ("simple_resolution_combo", "advanced_resolution_combo"):
            combo = getattr(self, combo_name, None)
            if combo:
                combo.configure(values=values)

    def _refresh_rate_mode_ui(self):
        mode = self.rate_mode_var.get()
        show_bitrate = mode in ("智能动态码率", "固定码率 CBR", "平均码率 VBR")
        show_maxrate = mode in ("智能动态码率", "平均码率 VBR")
        show_crf = mode in ("恒定质量 CRF/CQ", "智能动态码率")
        self._grid_visible(self.bitrate_label, show_bitrate)
        self._grid_visible(self.bitrate_entry, show_bitrate)
        self._grid_visible(self.maxrate_label, show_maxrate)
        self._grid_visible(self.maxrate_entry, show_maxrate)
        self._grid_visible(self.crf_label, show_crf)
        self._grid_visible(self.crf_entry, show_crf)

    def _grid_visible(self, widget, visible):
        if visible:
            widget.grid()
        else:
            widget.grid_remove()

    def _toggle_log_height(self):
        self.log_text.configure(height=10 if self.log_expanded_var.get() else 4)

    # ------------------------------------------------------------------
    # 文件管理
    # ------------------------------------------------------------------
    def browse_file(self, entry_widget):
        path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v"), ("所有文件", "*.*")])
        if path:
            entry_widget.configure(state=tk.NORMAL)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)
            self._refresh_process_type_ui()

    def browse_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    def add_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        new_files = []
        for root, _, files in os.walk(folder):
            for filename in files:
                if filename.lower().endswith(VIDEO_EXTENSIONS):
                    new_files.append(os.path.normpath(os.path.join(root, filename)))
        self.update_file_list(new_files)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v"), ("所有文件", "*.*")])
        self.update_file_list([os.path.normpath(f) for f in files])

    def update_file_list(self, new_files):
        existing = set(self.file_list)
        added = []
        skipped = 0
        for f in new_files:
            if not f:
                continue
            if not os.path.isfile(f):
                skipped += 1
                continue
            if not f.lower().endswith(VIDEO_EXTENSIONS):
                skipped += 1
                continue
            if f not in existing:
                self.file_list.append(f)
                existing.add(f)
                added.append(f)
                self.tree.insert("", tk.END, values=("等待", os.path.basename(f), f), tags=("waiting",))

        if added:
            self.log(f"成功添加 {len(added)} 个视频文件", "success")
        if skipped:
            self.log(f"已跳过 {skipped} 个非视频或无效文件", "warning")
        if not added and not skipped:
            self.log("没有新增文件", "info")
        self._set_status(f"当前共有 {len(self.file_list)} 个待处理文件")

    def delete_selected(self):
        selected = list(self.tree.selection())
        if not selected:
            return
        for item in selected:
            values = self.tree.item(item, "values")
            path = values[2]
            if path in self.file_list:
                self.file_list.remove(path)
            self.tree.delete(item)
        self.log(f"已删除 {len(selected)} 个选中文件", "info")
        self._set_status(f"当前共有 {len(self.file_list)} 个待处理文件")

    def clear_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_list.clear()
        self.log("已清空文件列表", "info")
        self._set_status("当前没有待处理文件")

    def open_selected_folder(self):
        selected = self.tree.selection()
        if not selected:
            return
        path = self.tree.item(selected[0], "values")[2]
        folder = os.path.dirname(path)
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif os.name == "posix":
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", folder])
        except Exception as exc:
            self.log(f"打开文件夹失败：{exc}", "error")

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    # ------------------------------------------------------------------
    # 参数校验与处理入口
    # ------------------------------------------------------------------
    def start_processing(self):
        ok, message = self.validate_inputs()
        if not ok:
            messagebox.showerror("无法开始", message)
            return

        self.stop_event.clear()
        self.progress.configure(value=0, maximum=max(1, len(self.file_list)))
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self._set_status("开始处理...")

        self.processing_thread = threading.Thread(target=self.process_files, daemon=True)
        self.processing_thread.start()

    def validate_inputs(self):
        if not self.ffmpeg_path:
            return False, "没有检测到 ffmpeg。请先安装 ffmpeg，并加入系统 PATH。"
        if not self.file_list:
            return False, "请先添加要处理的视频文件。"
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            return False, "请选择输出目录。"
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return False, f"输出目录不可用：{exc}"

        process_type = self.process_type_var.get()
        if process_type in ("加片头", "同时添加"):
            intro = self.intro_entry.get().strip()
            if not intro or not os.path.isfile(intro):
                return False, "请选择有效的片头视频文件。"
        if process_type in ("加片尾", "同时添加"):
            outro = self.outro_entry.get().strip()
            if not outro or not os.path.isfile(outro):
                return False, "请选择有效的片尾视频文件。"

        ok, msg = self._validate_resolution_and_fps()
        if not ok:
            return False, msg

        if self.mode_var.get() == "半专业调节":
            ok, msg = self._validate_advanced_values()
            if not ok:
                return False, msg
        return True, "ok"

    def _validate_resolution_and_fps(self):
        res = self.resolution_var.get().strip()
        if res in ("跟随原视频", "自定义输入"):
            if res == "自定义输入":
                return False, "分辨率不能保留为“自定义输入”，请直接输入例如 1080x1920。"
        else:
            if not re.fullmatch(r"\d{2,5}\s*[xX*]\s*\d{2,5}", res):
                return False, "分辨率格式不正确，请输入例如 1080x1920 或 1920x1080。"
            w, h = self._parse_resolution(res)
            if w < 64 or h < 64:
                return False, "分辨率太小，宽高都建议不低于 64。"
            if w % 2 != 0 or h % 2 != 0:
                return False, "分辨率的宽和高必须是偶数，避免编码器报错。"

        fps = self.framerate_var.get().strip()
        if fps != "跟随原视频":
            try:
                val = float(fps)
            except ValueError:
                return False, "帧率必须是数字，例如 30，也可以选择“跟随原视频”。"
            if val <= 0 or val > 240:
                return False, "帧率范围建议在 1 到 240 之间。"
        return True, "ok"

    def _validate_advanced_values(self):
        for label, value, min_val, max_val in [
            ("目标码率", self.bitrate_var.get(), 300, 200000),
            ("最高码率", self.maxrate_var.get(), 300, 300000),
            ("音频码率", self.audio_bitrate_var.get(), 32, 1024),
        ]:
            if self.rate_mode_var.get() == "恒定质量 CRF/CQ" and label in ("目标码率", "最高码率"):
                continue
            try:
                intval = int(str(value).strip())
            except ValueError:
                return False, f"{label}必须是数字。"
            if not (min_val <= intval <= max_val):
                return False, f"{label}建议在 {min_val} 到 {max_val} 之间。"

        try:
            q = int(str(self.crf_cq_var.get()).strip())
        except ValueError:
            return False, "CRF/CQ 必须是数字。"
        if not (0 <= q <= 51):
            return False, "CRF/CQ 建议在 0 到 51 之间，数字越小质量越高、文件越大。"
        return True, "ok"

    # ------------------------------------------------------------------
    # 处理逻辑
    # ------------------------------------------------------------------
    def process_files(self):
        total = len(self.file_list)
        processed_count = 0
        try:
            output_dir = self.output_entry.get().strip()
            self.log("========== 开始批处理 ==========")
            self.log(f"模式：{self.mode_var.get()} | 比例：{self.aspect_var.get()} | 分辨率：{self.resolution_var.get()} | 帧率：{self.framerate_var.get()}")

            for index, input_path in enumerate(list(self.file_list), start=1):
                if self.stop_event.is_set():
                    break
                self._queue_tree_status(input_path, "处理中")
                self._queue_status(f"正在处理 {index}/{total}：{os.path.basename(input_path)}")

                try:
                    output_path = self._make_output_path(input_path, output_dir)
                    self.process_single_file(input_path, output_path)
                    processed_count += 1
                    self._queue_tree_status(input_path, "成功")
                    self.log(f"处理完成：{output_path}", "success")
                except Exception as exc:
                    self._queue_tree_status(input_path, "失败")
                    self.log(f"处理失败：{input_path}\n原因：{exc}", "error")

                self.ui_queue.put(("progress", index))

            if self.stop_event.is_set():
                self.log("任务已停止。", "warning")
                self._queue_status(f"已停止，成功处理 {processed_count}/{total} 个文件")
            else:
                self.log("========== 全部处理完成 ==========" , "success")
                self._queue_status(f"全部完成，成功处理 {processed_count}/{total} 个文件")
        finally:
            self.ui_queue.put(("buttons", False))
            self.current_process = None

    def process_single_file(self, input_path, output_path):
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="video_processor_")
        temp_dir = temp_dir_obj.name
        segments = []
        try:
            plan = self._build_encode_plan()
            process_type = self.process_type_var.get()

            if process_type in ("加片头", "同时添加"):
                intro_temp = os.path.join(temp_dir, "001_intro.mp4")
                self._preprocess_video(self.intro_entry.get().strip(), intro_temp, plan)
                segments.append(intro_temp)

            main_temp = os.path.join(temp_dir, "002_main.mp4")
            self._preprocess_video(input_path, main_temp, plan)
            segments.append(main_temp)

            if process_type in ("加片尾", "同时添加"):
                outro_temp = os.path.join(temp_dir, "003_outro.mp4")
                self._preprocess_video(self.outro_entry.get().strip(), outro_temp, plan)
                segments.append(outro_temp)

            self._concat_videos(segments, output_path, plan)
        finally:
            if self.keep_temp_var.get():
                self.log(f"已保留临时目录：{temp_dir}", "warning")
            else:
                temp_dir_obj.cleanup()

    def _preprocess_video(self, input_path, output_path, plan: EncodePlan):
        vf = self._build_video_filter(input_path)
        cmd = [self.ffmpeg_path, "-hide_banner", "-y", "-i", input_path]

        if vf:
            cmd += ["-vf", vf]

        fps = self.framerate_var.get().strip()
        if fps and fps != "跟随原视频":
            # fps 也可以在 filter 中做，但单独放 -r 更直观。
            cmd += ["-r", fps]

        cmd += ["-c:v", plan.encoder]
        cmd += self._video_rate_args(plan, stage="preprocess")
        cmd += self._preset_args(plan.encoder, plan.preset)
        cmd += ["-pix_fmt", "yuv420p"]
        cmd += self._audio_args(for_concat=True)
        cmd += ["-movflags", "+faststart", output_path]
        self._run_command(cmd)

    def _concat_videos(self, segments, output_path, plan: EncodePlan):
        list_file = os.path.join(tempfile.mkdtemp(prefix="concat_list_"), "filelist.txt")
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for file_path in segments:
                    safe_path = file_path.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                self.ffmpeg_path,
                "-hide_banner",
                "-y" if self.overwrite_var.get() else "-n",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-c:v",
                plan.encoder,
            ]
            cmd += self._video_rate_args(plan, stage="final")
            cmd += self._preset_args(plan.encoder, plan.preset)
            cmd += ["-pix_fmt", "yuv420p"]
            cmd += self._audio_args(for_concat=False)
            cmd += self._extra_args()
            cmd += ["-movflags", "+faststart", output_path]
            self._run_command(cmd)
        finally:
            try:
                folder = os.path.dirname(list_file)
                os.remove(list_file)
                os.rmdir(folder)
            except Exception:
                pass

    def _build_video_filter(self, input_path):
        res = self.resolution_var.get().strip()
        if res == "跟随原视频":
            filters = []
            fps = self.framerate_var.get().strip()
            if fps and fps != "跟随原视频":
                filters.append(f"fps={fps}")
            filters.append("format=yuv420p")
            return ",".join(filters)

        w, h = self._parse_resolution(res)
        fit = self.fit_mode_var.get()
        if self.mode_var.get() == "小白推荐":
            # 小白默认居中裁剪，更适合短视频发布，不留黑边。
            fit = "居中裁剪"

        if fit == "完整保留补黑边":
            vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
        elif fit == "拉伸填满":
            vf = f"scale={w}:{h},setsar=1,format=yuv420p"
        else:
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,format=yuv420p"

        fps = self.framerate_var.get().strip()
        if fps and fps != "跟随原视频":
            vf = f"{vf},fps={fps}"
        return vf

    def _build_encode_plan(self):
        if self.mode_var.get() == "小白推荐":
            quality = self.quality_preset_var.get()
            if quality == "体积优先":
                bitrate, maxrate, crf = "3500", "5000", "25"
            elif quality == "高质量":
                bitrate, maxrate, crf = "9000", "13000", "20"
            elif quality == "极致质量":
                bitrate, maxrate, crf = "14000", "20000", "18"
            else:
                bitrate, maxrate, crf = "6000", "9000", "22"
            codec = "H.264 兼容优先"
            accel = "自动选择"
            rate_mode = "智能动态码率"
            preset = "均衡"
            audio_bitrate = "192"
            extra_args = ""
        else:
            codec = self.codec_var.get()
            accel = self.accel_var.get()
            rate_mode = self.rate_mode_var.get()
            bitrate = self.bitrate_var.get().strip()
            maxrate = self.maxrate_var.get().strip()
            crf = self.crf_cq_var.get().strip()
            preset = self.encoder_preset_var.get()
            audio_bitrate = self.audio_bitrate_var.get().strip()
            extra_args = self.extra_args_var.get().strip()

        encoder = self._select_encoder(codec, accel)
        return EncodePlan(
            codec=codec,
            encoder=encoder,
            preset=preset,
            rate_mode=rate_mode,
            bitrate=bitrate,
            maxrate=maxrate,
            crf_cq=crf,
            audio_bitrate=audio_bitrate,
            extra_args=extra_args,
        )

    def _select_encoder(self, codec, accel):
        is_h265 = codec.startswith("H.265")
        cpu_encoder = "libx265" if is_h265 else "libx264"

        preferred = []
        if accel == "NVIDIA GPU":
            preferred = ["hevc_nvenc" if is_h265 else "h264_nvenc"]
        elif accel == "AMD GPU":
            preferred = ["hevc_amf" if is_h265 else "h264_amf"]
        elif accel == "Intel GPU":
            preferred = ["hevc_qsv" if is_h265 else "h264_qsv"]
        elif accel == "CPU":
            return cpu_encoder
        else:
            preferred = [
                "hevc_nvenc" if is_h265 else "h264_nvenc",
                "hevc_qsv" if is_h265 else "h264_qsv",
                "hevc_amf" if is_h265 else "h264_amf",
                cpu_encoder,
            ]

        available = self._get_available_encoders()
        for enc in preferred:
            if enc in available:
                return enc
        self.log("没有检测到可用硬件编码器，已自动回退 CPU 编码。", "warning")
        return cpu_encoder

    def _get_available_encoders(self):
        if hasattr(self, "_available_encoders_cache"):
            return self._available_encoders_cache
        if not self.ffmpeg_path:
            self._available_encoders_cache = set()
            return self._available_encoders_cache
        try:
            result = subprocess.run([self.ffmpeg_path, "-hide_banner", "-encoders"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=12)
            encoders = set(re.findall(r"\s([a-zA-Z0-9_]+)\s+", result.stdout))
            # 正则抓不全时，直接用包含判断也够用。
            for name in ["h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf", "libx264", "libx265"]:
                if name in result.stdout:
                    encoders.add(name)
            self._available_encoders_cache = encoders
        except Exception:
            self._available_encoders_cache = {"libx264", "libx265"}
        return self._available_encoders_cache

    def _video_rate_args(self, plan: EncodePlan, stage="final"):
        enc = plan.encoder
        mode = plan.rate_mode
        bitrate = f"{plan.bitrate}k"
        maxrate = f"{plan.maxrate}k"
        bufsize = f"{max(int(plan.maxrate or plan.bitrate) * 2, int(plan.bitrate or 1000))}k"
        q = plan.crf_cq

        is_x264_or_x265 = enc in ("libx264", "libx265")
        is_nvenc = enc.endswith("_nvenc")
        is_qsv = enc.endswith("_qsv")
        is_amf = enc.endswith("_amf")

        args = []
        if mode == "固定码率 CBR":
            args += ["-b:v", bitrate, "-minrate", bitrate, "-maxrate", bitrate, "-bufsize", bufsize]
            if is_nvenc:
                args += ["-rc", "cbr"]
        elif mode == "平均码率 VBR":
            args += ["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize]
            if is_nvenc:
                args += ["-rc", "vbr"]
        elif mode == "恒定质量 CRF/CQ":
            if is_x264_or_x265:
                args += ["-crf", q]
            elif is_nvenc:
                args += ["-rc", "vbr", "-cq", q, "-b:v", "0"]
            elif is_qsv:
                args += ["-global_quality", q]
            elif is_amf:
                args += ["-quality", "quality", "-qp_i", q, "-qp_p", q, "-qp_b", q]
            else:
                args += ["-b:v", bitrate]
        else:  # 智能动态码率
            if is_x264_or_x265:
                args += ["-crf", q, "-maxrate", maxrate, "-bufsize", bufsize]
            elif is_nvenc:
                args += ["-rc", "vbr", "-cq", q, "-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize]
            else:
                args += ["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize]
        return args

    def _preset_args(self, encoder, preset_name):
        if encoder in ("libx264", "libx265"):
            mapping = {"速度优先": "veryfast", "均衡": "medium", "质量优先": "slow"}
            return ["-preset", mapping.get(preset_name, "medium")]
        if encoder.endswith("_nvenc"):
            mapping = {"速度优先": "p3", "均衡": "p5", "质量优先": "p7"}
            return ["-preset", mapping.get(preset_name, "p5")]
        if encoder.endswith("_qsv"):
            mapping = {"速度优先": "veryfast", "均衡": "medium", "质量优先": "slower"}
            return ["-preset", mapping.get(preset_name, "medium")]
        if encoder.endswith("_amf"):
            mapping = {"速度优先": "speed", "均衡": "balanced", "质量优先": "quality"}
            return ["-quality", mapping.get(preset_name, "balanced")]
        return []

    def _audio_args(self, for_concat=False):
        mode = self.audio_mode_var.get() if self.mode_var.get() == "半专业调节" else "AAC 立体声"
        if mode == "静音输出":
            return ["-an"]
        if mode == "复制音频" and not for_concat:
            # 预处理阶段不能复制，否则拼接时音频参数可能不一致；最终阶段可以尽量复制。
            return ["-c:a", "copy"]
        bitrate = self.audio_bitrate_var.get().strip() if self.mode_var.get() == "半专业调节" else "192"
        return ["-c:a", "aac", "-b:a", f"{bitrate}k", "-ar", "48000", "-ac", "2"]

    def _extra_args(self):
        if self.mode_var.get() != "半专业调节":
            return []
        text = self.extra_args_var.get().strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except ValueError:
            self.log("高级参数解析失败，已忽略。", "warning")
            return []

    def _run_command(self, cmd):
        if self.stop_event.is_set():
            raise RuntimeError("用户已停止任务")
        self.log("执行命令：" + " ".join(self._quote_cmd(c) for c in cmd), "debug")
        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            for line in self.current_process.stdout:
                if self.stop_event.is_set():
                    self._terminate_current_process()
                    raise RuntimeError("用户已停止任务")
                line = line.strip()
                if line:
                    self.log(line, "debug")
            ret = self.current_process.wait()
            self.current_process = None
            if ret != 0:
                raise subprocess.CalledProcessError(ret, cmd)
        except Exception:
            self._terminate_current_process()
            raise

    def _terminate_current_process(self):
        process = self.current_process
        if not process or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 工具函数
    # ------------------------------------------------------------------
    def _make_output_path(self, input_path, output_dir):
        stem = Path(input_path).stem
        output_path = os.path.join(output_dir, f"processed_{stem}.mp4")
        if self.overwrite_var.get() or not os.path.exists(output_path):
            return output_path
        counter = 1
        while True:
            candidate = os.path.join(output_dir, f"processed_{stem}_{counter}.mp4")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def _parse_resolution(self, text):
        parts = re.split(r"[xX*]", text.replace(" ", ""))
        return int(parts[0]), int(parts[1])

    def _quote_cmd(self, s):
        if not isinstance(s, str):
            s = str(s)
        return f'"{s}"' if " " in s else s

    def _show_ffmpeg_warning(self):
        self.log("未检测到 ffmpeg.exe。请将 ffmpeg.exe 和 ffprobe.exe 放到本软件 exe 所在目录。", "error")
        messagebox.showwarning(
            "缺少 FFmpeg",
            "没有检测到 FFmpeg。\n\n"
            "操作步骤：\n"
            "  1. 前往 https://ffmpeg.org/download.html 下载 FFmpeg Windows 版\n"
            "  2. 解压后，将 ffmpeg.exe 和 ffprobe.exe\n"
            "     复制到本软件 exe 所在目录\n\n"
            "  目录示例：\n"
            "    视频片头片尾批处理工具.exe\n"
            "    ffmpeg.exe       ← 放这里\n"
            "    ffprobe.exe      ← 放这里\n\n"
            "放好后重新打开软件即可。\n\n"
            "（也支持将 ffmpeg 加入系统 PATH，效果相同）",
        )

    # ------------------------------------------------------------------
    # 队列与日志
    # ------------------------------------------------------------------
    def log(self, message, tag="info"):
        self.log_queue.put((str(message), tag))

    def clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _queue_tree_status(self, file_path, status):
        self.ui_queue.put(("tree_status", file_path, status))

    def _queue_status(self, text):
        self.ui_queue.put(("status", text))

    def _set_status(self, text):
        self.status_label.configure(text=text)

    def _process_queues(self):
        while not self.log_queue.empty():
            msg, tag = self.log_queue.get()
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n", tag)
            self.log_text.tag_config(tag, foreground=self._log_color(tag))
            self.log_text.configure(state=tk.DISABLED)
            self.log_text.see(tk.END)

        while not self.ui_queue.empty():
            item = self.ui_queue.get()
            action = item[0]
            if action == "tree_status":
                _, path, status = item
                self._update_tree_status(path, status)
            elif action == "status":
                _, text = item
                self._set_status(text)
            elif action == "progress":
                _, value = item
                self.progress.configure(value=value)
            elif action == "buttons":
                self.start_btn.configure(state=tk.NORMAL)
                self.stop_btn.configure(state=tk.DISABLED)

        self.master.after(100, self._process_queues)

    def _update_tree_status(self, file_path, status):
        for child in self.tree.get_children():
            values = self.tree.item(child, "values")
            if values and len(values) >= 3 and values[2] == file_path:
                self.tree.item(child, values=(status, values[1], values[2]))
                return

    def _log_color(self, tag):
        return {
            "info": "#e2e8f0",
            "success": "#86efac",
            "warning": "#fde68a",
            "error": "#fca5a5",
            "debug": "#94a3b8",
        }.get(tag, "#e2e8f0")

    def stop_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askyesno("确认停止", "确定要停止当前处理任务吗？\n正在运行的 FFmpeg 进程也会被终止。"):
                self.stop_event.set()
                self._terminate_current_process()
                self.stop_btn.configure(state=tk.DISABLED)
                self.log("正在停止任务...", "warning")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorApp(root)
    root.mainloop()
