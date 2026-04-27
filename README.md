# 视频片头片尾批处理工具 v4.4

<p align="center">
  <a href="https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches/releases">
    <img src="https://img.shields.io/github/downloads/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches/total?style=flat-square" alt="Downloads">
  </a>
  <a href="https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches?style=flat-square" alt="License">
  </a>
</p>

> A batch video intro/outro tool with an elegant Tkinter GUI. Add intro clips, outro clips, or both to any number of videos at once — with GPU-accelerated encoding support.

[English](#english) | [中文说明](#中文)

---

## English

### Features

- 🎬 **Batch add intro/outro** — intro only, outro only, or both simultaneously
- ⚡ **GPU acceleration** — NVIDIA NVENC, AMD AMF, Intel QSV, or pure CPU
- 📐 **Flexible output** — 9:16 vertical / 16:9 horizontal / custom resolution
- 🎯 **Smart crop** — center crop, letterbox, or stretch to fit
- 📊 **Real-time progress** — live ffmpeg log output, instant abort
- 🖥️ **Beginner-friendly** — default settings Just Work; pro mode for fine-tuning

### Quick Start (Executable)

No Python needed. Download the latest `.exe` from [Releases](https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches/releases) and place it anywhere.

**FFmpeg setup (one-time, ~2 minutes):**

1. Download FFmpeg from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) (or [ffmpeg.org](https://ffmpeg.org/download.html))
2. Extract, then copy `ffmpeg.exe` and `ffprobe.exe` into the **same folder as the `.exe`**
3. Double-click the `.exe` — done!

```
your-folder/
├── 视频片头片尾批处理工具.exe   ← the tool
├── ffmpeg.exe                   ← from FFmpeg zip
└── ffprobe.exe                  ← from FFmpeg zip
```

**Upgrading FFmpeg:** just replace the old `ffmpeg.exe` / `ffprobe.exe` with the new ones. No need to re-download the tool.

### Quick Start (From Source)

Requires Python 3.8+, FFmpeg in PATH.

```bash
git clone https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches.git
cd Add-headers-or-trailers-to-videos-in-batches
pip install pyinstaller
pyinstaller src/视频片头片尾工具.spec
# find the exe in src/dist/
```

Or run directly:

```bash
cd src
pip install tkinter-tte   # usually bundled with Python
python 加片头片尾4.4_简洁高级分层_UI优化版.py
```

### Supported Formats

`.mp4` `.mkv` `.avi` `.mov` `.flv` `.wmv` `.webm` `.m4v`

### UI Modes

| Mode | Description |
|------|-------------|
| **Beginner** (default) | Shows only essential options. Defaults are optimized for short vertical videos (9:16, 1080×1920). Just add files and click Start. |
| **Pro** | Exposes codec, bitrate, audio, and custom FFmpeg parameters. |

### GPU Encoding Guide

| GPU Brand | Choose in UI | Notes |
|-----------|-------------|-------|
| NVIDIA | `NVIDIA GPU` | Requires NVIDIA drivers + ffmpeg built with NVENC |
| AMD | `AMD GPU` | Requires AMD drivers + ffmpeg built with AMF |
| Intel | `Intel GPU` | Integrated/dedicated Intel GPU |
| No GPU / unsure | `Auto` or `CPU` | Auto detects best available encoder |

### Build from Source

See `build/视频片头片尾工具.spec` — PyInstaller onefile build. Run:

```bash
cd build
pyinstaller 视频片头片尾工具.spec
```

The executable will be at `releases/视频片头片尾批处理工具.exe`.

### License

MIT — free to use, modify, and distribute, even in commercial projects.

---

## 中文

### 功能特点

- 🎬 **批量添加片头/片尾** — 可只加片头、只加片尾，或同时添加
- ⚡ **硬件加速编码** — 支持 NVIDIA NVENC / AMD AMF / Intel QSV / 纯 CPU
- 📐 **灵活分辨率** — 9:16 竖屏 / 16:9 横屏 / 自定义分辨率
- 🎯 **智能画面适配** — 居中裁剪（短视频推荐）、补黑边、拉伸填满
- 📊 **实时进度** — 实时显示 ffmpeg 执行日志，随时终止任务
- 🖥️ **小白友好** — 默认参数即最优，无需任何专业知识

### 使用方法（推荐：直接下载 exe）

无需安装 Python，直接下载 [Releases](https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches/releases) 中的 exe 文件，放到任意文件夹即可。

**首次使用只需做一次这件事（2分钟）：**

1. 下载 FFmpeg（推荐 gyan.dev 的 [Essentials 构建](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip)，或 [ffmpeg.org](https://ffmpeg.org/download.html)）
2. 解压后，将 `ffmpeg.exe` 和 `ffprobe.exe` **复制到 exe 所在文件夹**
3. 双击 exe 运行，搞定！

```
你的文件夹\
├── 视频片头片尾批处理工具.exe   ← 主程序
├── ffmpeg.exe                  ← 从 FFmpeg 包里复制
└── ffprobe.exe                 ← 从 FFmpeg 包里复制
```

**升级 FFmpeg：** 直接用新版的 `ffmpeg.exe` / `ffprobe.exe` 覆盖原文件即可，无需重新下载本工具。

### 使用方法（从源码运行）

需要 Python 3.8+ 和系统 PATH 中的 FFmpeg。

```bash
git clone https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches.git
cd Add-headers-or-trailers-to-videos-in-batches
pip install pyinstaller
pyinstaller build/视频片头片尾工具.spec
# 打包好的 exe 在 releases/ 目录
```

### 界面模式说明

| 模式 | 特点 |
|------|------|
| **小白推荐**（默认） | 只显示必要选项，默认参数针对竖屏短视频优化（9:16 / 1080×1920 / 高清）。只需添加视频文件，点击开始。 |
| **半专业调节** | 展开编码器、码率模式、音频参数、自定义 FFmpeg 参数。 |

### 硬件加速对照表

| 显卡品牌 | 界面上选择 | 前提条件 |
|---------|-----------|---------|
| NVIDIA | `NVIDIA GPU` | 已装 NVIDIA 驱动 + FFmpeg 含 NVENC |
| AMD | `AMD GPU` | 已装 AMD 驱动 + FFmpeg 含 AMF |
| Intel | `Intel GPU` | Intel 核显或独显 |
| 无独显 / 不确定 | `自动选择` 或 `CPU` | 自动检测最佳编码器 |

### 重新打包

配置文件在 `build/视频片头片尾工具.spec`，执行：

```bash
cd build
pyinstaller 视频片头片尾工具.spec
```

打包后的 exe 输出到 `releases/视频片头片尾批处理工具.exe`。

### 支持的视频格式

`.mp4` `.mkv` `.avi` `.mov` `.flv` `.wmv` `.webm` `.m4v`

### 许可证

MIT License — 可自由使用、修改和分发，包括商业项目。
