import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading

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

def concatenate_videos(folder_path, video_type, intro_video, outro_video, output_folder, gpu_type, bitrate, resolution, frame_rate):
    codec = get_encoder(gpu_type)
    scale = "1920:-2" if resolution == "1080p" else "1280:-2"

    for filename in os.listdir(folder_path):
        if filename.endswith(('.mp4', '.mkv', '.avi')):
            main_video = os.path.join(folder_path, filename)
            output_video = os.path.join(output_folder, f"processed_{filename}")

            ffmpeg_cmd = ["ffmpeg"]
            input_streams = []

            # 添加片头视频（如果需要）
            if video_type in ["片头", "同时添加片头片尾"]:
                ffmpeg_cmd.extend(["-i", intro_video])
                input_streams.append(len(input_streams))

            # 添加主视频
            ffmpeg_cmd.extend(["-i", main_video])
            input_streams.append(len(input_streams))

            # 添加片尾视频（如果需要）
            if video_type in ["片尾", "同时添加片头片尾"]:
                ffmpeg_cmd.extend(["-i", outro_video])
                input_streams.append(len(input_streams))

            # 构建 filter_complex 字符串
            video_filters = ';'.join([f"[{i}:v]scale={scale},setdar=16/9[v{i}]" for i in input_streams])
            audio_filters = ';'.join([f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]" for i in input_streams])
            concat_filter = f"{video_filters};{audio_filters};{''.join([f'[v{i}][a{i}]' for i in input_streams])}concat=n={len(input_streams)}:v=1:a=1[outv][outa]"

            # 添加 filter_complex 到 ffmpeg 命令
            ffmpeg_cmd.extend(["-filter_complex", concat_filter])

            # 设置映射和编码选项
            ffmpeg_cmd.extend(["-map", "[outv]", "-map", "[outa]", "-c:v", codec, "-b:v", bitrate + "k", "-c:a", "aac", "-strict", "-2", output_video])

            # 运行 FFmpeg 命令
            try:
                subprocess.run(ffmpeg_cmd, check=True)
                print(f"已处理: {filename}")  # 或者使用其他方式更新状态
            except subprocess.CalledProcessError as e:
                print(f"处理失败: {filename}")  # 错误处理

def update_status(message):
    # 调用此函数来更新状态标签
    status_label.config(text=message)
    app.update_idletasks()  # 确保UI更新

def start_processing():
    folder_path = folder_path_var.get()
    video_type = video_type_var.get()
    intro_video = intro_video_var.get()
    outro_video = outro_video_var.get()
    gpu_type = gpu_type_var.get()
    bitrate = bitrate_var.get()
    resolution = resolution_var.get()
    frame_rate = frame_rate_var.get()
    output_folder = output_folder_var.get()
    start_button.config(state="disabled")

    if not all([folder_path, output_folder, bitrate, resolution, frame_rate]):
        messagebox.showerror("错误", "请确保所有必要选项都已填写")
        return

    start_button.config(state="disabled")

    def processing_thread():
        for filename in os.listdir(folder_path):
             update_status(f"正在处理: {filename}")
        concatenate_videos(folder_path, video_type, intro_video, outro_video, output_folder, gpu_type, bitrate, resolution, frame_rate)
        
        app.after(0, lambda: update_status("处理完成"))
        update_status("所有视频处理完成")
        start_button.config(state="normal")  # 重新激活开始按钮
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
app.title("视频处理器")

# 定义变量
folder_path_var = tk.StringVar()
video_type_var = tk.StringVar(value="片尾")
intro_video_var = tk.StringVar()
outro_video_var = tk.StringVar()
gpu_type_var = tk.StringVar(value="N卡")
bitrate_var = tk.StringVar()
resolution_var = tk.StringVar(value="1080p")
frame_rate_var = tk.StringVar(value="25")
output_folder_var = tk.StringVar()

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
resolution_options = ["1080p", "720p"]
resolution_menu = ttk.Combobox(resolution_frame, textvariable=resolution_var, values=resolution_options, state="readonly")
resolution_menu.pack(side=tk.LEFT)
resolution_menu.set(resolution_options[0])  # 设置默认选项

frame_rate_frame = tk.Frame(app)
frame_rate_frame.pack(padx=10, pady=5)
tk.Label(frame_rate_frame, text="选择帧率：").pack(side=tk.LEFT)
frame_rate_options = ["25", "30"]
frame_rate_menu = ttk.Combobox(frame_rate_frame, textvariable=frame_rate_var, values=frame_rate_options, state="readonly")
frame_rate_menu.pack(side=tk.LEFT)
frame_rate_menu.set(frame_rate_options[0])  

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
