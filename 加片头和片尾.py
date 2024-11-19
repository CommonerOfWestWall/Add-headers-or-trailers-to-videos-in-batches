import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import tempfile


def get_ffmpeg_path():
    """获取封装在程序中的 ffmpeg 路径"""
    if getattr(sys, 'frozen', False):  # 如果是打包后的程序
        base_path = sys._MEIPASS
    else:  # 如果是脚本运行
        base_path = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_path = os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe")
    if not os.path.exists(ffmpeg_path):
        raise FileNotFoundError(f"未找到 ffmpeg: {ffmpeg_path}")
    return ffmpeg_path


def get_ffprobe_path():
    """获取封装在程序中的 ffprobe 路径"""
    if getattr(sys, 'frozen', False):  # 如果是打包后的程序
        base_path = sys._MEIPASS
    else:  # 如果是脚本运行
        base_path = os.path.dirname(os.path.abspath(__file__))
    ffprobe_path = os.path.join(base_path, "ffmpeg", "bin", "ffprobe.exe")
    if not os.path.exists(ffprobe_path):
        raise FileNotFoundError(f"未找到 ffprobe: {ffprobe_path}")
    return ffprobe_path


def check_video_properties(video_path, target_width, target_height, target_sar):
    """检查视频分辨率和SAR是否匹配"""
    ffprobe_path = get_ffprobe_path()
    ffprobe_cmd = [
        ffprobe_path, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,sample_aspect_ratio",
        "-of", "default=noprint_wrappers=1", video_path
    ]
    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
    props = dict(line.split('=') for line in result.stdout.strip().splitlines())
    width, height = int(props.get("width", 0)), int(props.get("height", 0))
    sar = props.get("sample_aspect_ratio", "1")
    return width == target_width and height == target_height and sar == target_sar


def get_encoder(gpu_type):
    """根据选择的GPU类型返回适合的编码器"""
    if gpu_type == "N卡":
        return "h264_nvenc"
    elif gpu_type == "A卡":
        return "h264_amf"
    elif gpu_type == "I卡":
        return "h264_qsv"
    else:
        return "libx264"


def preprocess_video(input_video, output_video, width, height, gpu_type=None):
    """预处理视频：调整分辨率和宽高比"""
    ffmpeg_path = get_ffmpeg_path()
    codec = get_encoder(gpu_type) if gpu_type else "libx264"

    ffmpeg_cmd = [
        ffmpeg_path, "-i", input_video,
        "-vf", f"scale={width}:{height},setsar=1",
        "-c:v", codec, "-c:a", "aac", "-y", output_video
    ]
    print(f"预处理命令: {ffmpeg_cmd}")
    subprocess.run(ffmpeg_cmd, check=True)


def process_single_video(main_video, intro_video, outro_video, output_video, video_type, width, height, codec, bitrate, frame_rate, gpu_type):
    """为单个视频添加片头或片尾并输出"""
    ffmpeg_path = get_ffmpeg_path()
    temp_dir = tempfile.gettempdir()
    temp_videos = []

    if video_type in ["片头", "同时添加片头片尾"] and intro_video:
        preprocessed_intro = os.path.join(temp_dir, f"preprocessed_intro.mp4")
        if not check_video_properties(intro_video, width, height, "1"):
            preprocess_video(intro_video, preprocessed_intro, width, height, gpu_type)
        else:
            preprocessed_intro = intro_video
        temp_videos.append(preprocessed_intro)

    preprocessed_main = os.path.join(temp_dir, f"preprocessed_main.mp4")
    if not check_video_properties(main_video, width, height, "1"):
        preprocess_video(main_video, preprocessed_main, width, height, gpu_type)
    else:
        preprocessed_main = main_video
    temp_videos.append(preprocessed_main)

    if video_type in ["片尾", "同时添加片头片尾"] and outro_video:
        preprocessed_outro = os.path.join(temp_dir, f"preprocessed_outro.mp4")
        if not check_video_properties(outro_video, width, height, "1"):
            preprocess_video(outro_video, preprocessed_outro, width, height, gpu_type)
        else:
            preprocessed_outro = outro_video
        temp_videos.append(preprocessed_outro)

    ffmpeg_cmd = [ffmpeg_path]
    for video in temp_videos:
        ffmpeg_cmd.extend(["-i", video])

    filter_complex = ''.join([f"[{i}:v][{i}:a]" for i in range(len(temp_videos))])
    filter_complex += f"concat=n={len(temp_videos)}:v=1:a=1[outv][outa]"

    ffmpeg_cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", codec, "-b:v", f"{bitrate}k", "-r", str(frame_rate), "-c:a", "aac", "-strict", "-2",
        "-y", output_video
    ])

    print(f"执行 ffmpeg 命令: {' '.join(ffmpeg_cmd)}")
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"已生成最终视频: {output_video}")

    for video in temp_videos:
        if video.startswith(temp_dir) and os.path.exists(video):
            os.remove(video)
            print(f"已删除临时文件: {video}")


def batch_process(folder_path, video_type, intro_video, outro_video, output_folder, gpu_type, bitrate, resolution, frame_rate, orientation):
    codec = get_encoder(gpu_type)

    if resolution == "1080p":
        width, height = 1920, 1080
    elif resolution == "720p":
        width, height = 1280, 720
    elif resolution == "4k":
        width, height = 3840, 2160
    else:
        width, height = 1920, 1080

    if orientation == "竖屏":
        width, height = height, width

    for filename in os.listdir(folder_path):
        if filename.endswith(('.mp4', '.mkv', '.avi')):
            main_video = os.path.join(folder_path, filename)
            output_video = os.path.join(output_folder, f"output_{filename}")
            process_single_video(
                main_video, intro_video, outro_video, output_video,
                video_type, width, height, codec, bitrate, frame_rate, gpu_type
            )


def update_status(message):
    status_label.config(text=message)
    app.update_idletasks()


def start_processing():
    folder_path = folder_path_var.get()
    video_type = video_type_var.get()
    intro_video = intro_video_var.get()
    outro_video = outro_video_var.get()
    gpu_type = gpu_type_var.get()
    bitrate = bitrate_var.get()
    resolution = resolution_var.get()
    frame_rate = frame_rate_var.get()
    orientation = orientation_var.get()
    output_folder = output_folder_var.get()

    if not all([folder_path, output_folder, bitrate, resolution, frame_rate]):
        messagebox.showerror("错误", "请确保所有必要选项都已填写")
        return

    start_button.config(state="disabled")

    def processing_thread():
        try:
            batch_process(folder_path, video_type, intro_video, outro_video, output_folder, gpu_type, bitrate, resolution, frame_rate, orientation)
            update_status("所有视频处理完成")
        except Exception as e:
            messagebox.showerror("错误", str(e))
        finally:
            start_button.config(state="normal")

    thread = threading.Thread(target=processing_thread, daemon=True)
    thread.start()


def browse_folder(var):
    folder = filedialog.askdirectory()
    if folder:
        var.set(folder)


def browse_file(var):
    filetypes = [('视频文件', '*.mp4 *.mkv *.avi'), ('所有文件', '*.*')]
    filename = filedialog.askopenfilename(filetypes=filetypes)
    if filename:
        var.set(filename)


# 创建图形界面
app = tk.Tk()
app.title("视频批量处理器")

# 定义变量
folder_path_var = tk.StringVar()
video_type_var = tk.StringVar(value="片尾")
intro_video_var = tk.StringVar()
outro_video_var = tk.StringVar()
gpu_type_var = tk.StringVar(value="N卡")
bitrate_var = tk.StringVar()
resolution_var = tk.StringVar(value="1080p")
frame_rate_var = tk.StringVar()
output_folder_var = tk.StringVar()
orientation_var = tk.StringVar(value="横屏")

# 文件夹选择框架
folder_frame = tk.Frame(app)
folder_frame.pack(padx=10, pady=5)
tk.Label(folder_frame, text="选择视频文件夹：").pack(side=tk.LEFT)
tk.Entry(folder_frame, textvariable=folder_path_var, width=50).pack(side=tk.LEFT)
tk.Button(folder_frame, text="浏览", command=lambda: browse_folder(folder_path_var)).pack(side=tk.LEFT)

# 视频类型选择框架
video_type_frame = tk.Frame(app)
video_type_frame.pack(padx=10, pady=5)
tk.Label(video_type_frame, text="选择类型：").pack(side=tk.LEFT)
tk.Radiobutton(video_type_frame, text="片头", variable=video_type_var, value="片头").pack(side=tk.LEFT)
tk.Radiobutton(video_type_frame, text="片尾", variable=video_type_var, value="片尾").pack(side=tk.LEFT)
tk.Radiobutton(video_type_frame, text="同时添加片头片尾", variable=video_type_var, value="同时添加片头片尾").pack(side=tk.LEFT)

# 屏幕方向选择框架
orientation_frame = tk.Frame(app)
orientation_frame.pack(padx=10, pady=5)
tk.Label(orientation_frame, text="选择屏幕方向：").pack(side=tk.LEFT)
tk.Radiobutton(orientation_frame, text="横屏", variable=orientation_var, value="横屏").pack(side=tk.LEFT)
tk.Radiobutton(orientation_frame, text="竖屏", variable=orientation_var, value="竖屏").pack(side=tk.LEFT)

# 片头视频文件选择框架
intro_video_frame = tk.Frame(app)
intro_video_frame.pack(padx=10, pady=5)
tk.Label(intro_video_frame, text="选择片头视频文件：").pack(side=tk.LEFT)
tk.Entry(intro_video_frame, textvariable=intro_video_var, width=50).pack(side=tk.LEFT)
tk.Button(intro_video_frame, text="浏览", command=lambda: browse_file(intro_video_var)).pack(side=tk.LEFT)

# 片尾视频文件选择框架
outro_video_frame = tk.Frame(app)
outro_video_frame.pack(padx=10, pady=5)
tk.Label(outro_video_frame, text="选择片尾视频文件：").pack(side=tk.LEFT)
tk.Entry(outro_video_frame, textvariable=outro_video_var, width=50).pack(side=tk.LEFT)
tk.Button(outro_video_frame, text="浏览", command=lambda: browse_file(outro_video_var)).pack(side=tk.LEFT)

# 显卡类型选择框架
gpu_type_frame = tk.Frame(app)
gpu_type_frame.pack(padx=10, pady=5)
tk.Label(gpu_type_frame, text="选择显卡类型：").pack(side=tk.LEFT)
gpu_options = ["N卡", "A卡", "I卡", "集成核显"]
gpu_menu = ttk.Combobox(gpu_type_frame, textvariable=gpu_type_var, values=gpu_options, state="readonly")
gpu_menu.pack(side=tk.LEFT)
gpu_menu.set(gpu_options[0])  # 设置默认选项

# 码率设置框架
bitrate_frame = tk.Frame(app)
bitrate_frame.pack(padx=10, pady=5)
tk.Label(bitrate_frame, text="设置码率 (kbps)：").pack(side=tk.LEFT)
tk.Entry(bitrate_frame, textvariable=bitrate_var, width=10).pack(side=tk.LEFT)
bitrate_var.set("1100")

# 分辨率和帧率选择框架
resolution_frame = tk.Frame(app)
resolution_frame.pack(padx=10, pady=5)
tk.Label(resolution_frame, text="选择分辨率：").pack(side=tk.LEFT)
resolution_options = ["1080p", "720p", "4k"]
resolution_menu = ttk.Combobox(resolution_frame, textvariable=resolution_var, values=resolution_options, state="readonly")
resolution_menu.pack(side=tk.LEFT)
resolution_menu.set(resolution_options[0])  # 设置默认选项

frame_rate_frame = tk.Frame(app)
frame_rate_frame.pack(padx=10, pady=5)
tk.Label(frame_rate_frame, text="设置帧率：").pack(side=tk.LEFT)
tk.Entry(frame_rate_frame, textvariable=frame_rate_var, width=10).pack(side=tk.LEFT)
frame_rate_var.set("25")

# 选择输出文件夹
output_folder_frame = tk.Frame(app)
output_folder_frame.pack(padx=10, pady=5)
tk.Label(output_folder_frame, text="选择输出文件夹：").pack(side=tk.LEFT)
tk.Entry(output_folder_frame, textvariable=output_folder_var, width=50).pack(side=tk.LEFT)
tk.Button(output_folder_frame, text="浏览", command=lambda: browse_folder(output_folder_var)).pack(side=tk.LEFT)

# 开始按钮
start_button = tk.Button(app, text="开始处理", bg="red", fg="white", font=("Arial", 12, "bold"), command=start_processing)
start_button.pack(pady=20)

# 状态标签
status_label = tk.Label(app, text="等待开始...")
status_label.pack(pady=5)

app.mainloop()
