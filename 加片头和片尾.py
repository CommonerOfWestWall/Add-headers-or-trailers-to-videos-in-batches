import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import subprocess
import tempfile
import logging

class UltimateVideoProcessor:
    def __init__(self, master):
        self.master = master
        self.master.title("专业视频处理工具 v4.1")
        self.master.geometry("1366x900")
        
        # 初始化变量
        self.file_list = []
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.status_update_queue = queue.Queue()
        
        # 创建界面
        self.create_widgets()
        self.setup_styles()
        
        # 启动队列处理
        self.master.after(100, self.process_queues)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TButton", padding=6, font=('微软雅黑', 10))
        style.configure("Title.TLabel", font=('微软雅黑', 12, 'bold'))
        style.configure("Success.TLabel", foreground='#28a745')
        style.configure("Error.TLabel", foreground='#dc3545')
        style.configure("Processing.TLabel", foreground='#17a2b8')
        style.map("Red.TButton", background=[('active', '#c82333')])

    def create_widgets(self):
        # 主布局容器
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧控制面板
        control_panel = ttk.Frame(main_frame, width=480)
        control_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)

        # 文件列表管理
        self.create_file_list_section(control_panel)
        
        # 处理参数设置
        self.create_processing_settings(control_panel)
        self.create_advanced_settings(control_panel)

        # 右侧日志面板
        log_panel = ttk.Frame(main_frame)
        log_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # 日志输出
        self.create_log_section(log_panel)

        # 控制按钮（位于左侧底部）
        self.create_control_buttons(control_panel)

    def create_file_list_section(self, parent):
        """创建文件列表管理区域"""
        frame = ttk.LabelFrame(parent, text="文件管理")
        frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 操作按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="添加文件夹", 
                  command=self.add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="添加文件", 
                  command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="清空列表", style='Red.TButton',
                  command=self.clear_list).pack(side=tk.RIGHT, padx=2)

        # 文件列表（含状态列）
        self.tree = ttk.Treeview(frame, columns=('status', 'file'), show='headings', 
                                selectmode='extended', height=15)
        self.tree.heading('status', text='状态', anchor=tk.CENTER)
        self.tree.heading('file', text='文件路径')
        self.tree.column('status', width=80, anchor=tk.CENTER)
        self.tree.column('file', width=400)
        
        # 滚动条
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 右键菜单
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="删除选中", command=self.delete_selected)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def create_processing_settings(self, parent):
        """创建处理参数设置区域"""
        frame = ttk.LabelFrame(parent, text="处理设置")
        frame.pack(fill=tk.X, pady=5)

        # 处理类型
        ttk.Label(frame, text="处理类型：").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.process_type = ttk.Combobox(frame, values=["加片头", "加片尾", "同时添加"], state="readonly")
        self.process_type.current(0)
        self.process_type.grid(row=0, column=1, sticky=tk.EW, padx=5)

        # 片头文件
        ttk.Label(frame, text="片头文件：").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.intro_entry = ttk.Entry(frame)
        self.intro_entry.grid(row=1, column=1, sticky=tk.EW, padx=5)
        ttk.Button(frame, text="浏览", command=lambda: self.browse_file(self.intro_entry)).grid(row=1, column=2)

        # 片尾文件
        ttk.Label(frame, text="片尾文件：").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.outro_entry = ttk.Entry(frame)
        self.outro_entry.grid(row=2, column=1, sticky=tk.EW, padx=5)
        ttk.Button(frame, text="浏览", command=lambda: self.browse_file(self.outro_entry)).grid(row=2, column=2)

        # 输出目录
        ttk.Label(frame, text="输出目录：").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.output_entry = ttk.Entry(frame)
        self.output_entry.grid(row=3, column=1, sticky=tk.EW, padx=5)
        ttk.Button(frame, text="浏览", command=self.browse_output_dir).grid(row=3, column=2)

        frame.columnconfigure(1, weight=1)

    def create_advanced_settings(self, parent):
        """创建高级编码设置区域"""
        frame = ttk.LabelFrame(parent, text="编码设置")
        frame.pack(fill=tk.X, pady=5)

        # 硬件加速
        ttk.Label(frame, text="硬件加速：").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.hardware_accel = ttk.Combobox(frame, 
                                         values=["NVIDIA GPU", "AMD GPU", "Intel GPU", "CPU"],
                                         state="readonly")
        self.hardware_accel.current(0)
        self.hardware_accel.grid(row=0, column=1, sticky=tk.EW, padx=5)

        # 分辨率
        ttk.Label(frame, text="分辨率：").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.resolution = ttk.Combobox(frame, values=["1920x1080", "1280x720", "3840x2160"])
        self.resolution.current(0)
        self.resolution.grid(row=1, column=1, sticky=tk.EW, padx=5)

        # 帧率
        ttk.Label(frame, text="帧率 (fps)：").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.framerate = ttk.Spinbox(frame, from_=1, to=60, increment=1)
        self.framerate.set("30")
        self.framerate.grid(row=2, column=1, sticky=tk.EW, padx=5)

        # 码率
        ttk.Label(frame, text="码率 (kbps)：").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.bitrate = ttk.Spinbox(frame, from_=1000, to=50000, increment=500)
        self.bitrate.set("5000")
        self.bitrate.grid(row=3, column=1, sticky=tk.EW, padx=5)

        frame.columnconfigure(1, weight=1)

    def create_log_section(self, parent):
        """创建日志区域"""
        # 日志输出
        self.log_text = tk.Text(parent, wrap=tk.WORD, state=tk.DISABLED,
                              font=('Consolas', 10), bg='#f8f9fa', height=20)
        scrollbar = ttk.Scrollbar(parent, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 进度条
        self.progress = ttk.Progressbar(parent, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

    def create_control_buttons(self, parent):
        """创建控制按钮（位于左侧底部）"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="开始处理", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止处理", style='Red.TButton',
                                  command=self.stop_processing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

    def browse_file(self, entry_widget):
        """选择文件"""
        path = filedialog.askopenfilename(filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov")])
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def browse_output_dir(self):
        """选择输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    def show_context_menu(self, event):
        """显示右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def add_folder(self):
        """添加文件夹及其子文件夹中的视频文件"""
        folder = filedialog.askdirectory()
        if folder:
            new_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                        full_path = os.path.join(root, file)
                        if full_path not in self.file_list:
                            new_files.append(full_path)
            self.update_file_list(new_files)

    def add_files(self):
        """添加单个或多个文件"""
        files = filedialog.askopenfilenames(
            filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov")]
        )
        self.update_file_list(files)

    def delete_selected(self):
        """删除选中的文件"""
        selected = self.tree.selection()
        for item in selected:
            file_path = self.tree.item(item)['values'][1]
            self.file_list.remove(file_path)
            self.tree.delete(item)
        self.log(f"已删除 {len(selected)} 个文件")

    def clear_list(self):
        """清空文件列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_list.clear()
        self.log("已清空文件列表")

    def update_file_list(self, new_files):
        """更新文件列表并去重"""
        existing = set(self.file_list)
        added = [f for f in new_files if f not in existing]
        
        for f in added:
            self.file_list.append(f)
            self.tree.insert('', tk.END, values=('等待处理', f))
        
        if added:
            self.log(f"成功添加 {len(added)} 个文件")
        else:
            self.log("没有新增文件")

    def start_processing(self):
        """开始处理"""
        if not self.validate_inputs():
            return
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress['value'] = 0
        self.stop_event.clear()
        
        self.processing_thread = threading.Thread(target=self.process_files, daemon=True)
        self.processing_thread.start()

    def validate_inputs(self):
        """验证输入有效性"""
        if not self.output_entry.get():
            messagebox.showerror("错误", "请选择输出目录")
            return False
        
        if not self.file_list:
            messagebox.showerror("错误", "请先添加要处理的文件")
            return False
        
        process_type = self.process_type.get()
        if process_type in ["加片头", "同时添加"] and not self.intro_entry.get():
            messagebox.showerror("错误", "请选择片头文件")
            return False
        
        if process_type in ["加片尾", "同时添加"] and not self.outro_entry.get():
            messagebox.showerror("错误", "请选择片尾文件")
            return False
        
        return True

    def process_files(self):
        """处理文件主逻辑"""
        try:
            total = len(self.file_list)
            output_dir = self.output_entry.get()
            
            for idx, file_path in enumerate(self.file_list):
                if self.stop_event.is_set():
                    break
                
                item_id = self.get_item_id(file_path)
                self.update_status(item_id, "处理中", "processing")
                
                try:
                    output_path = os.path.join(output_dir, f"processed_{os.path.basename(file_path)}")
                    self.process_single_file(file_path, output_path)
                    self.update_status(item_id, "成功", "success")
                except Exception as e:
                    self.log(f"文件处理失败：{file_path} - {str(e)}", "error")
                    self.update_status(item_id, "失败", "error")
                    continue
                
                # 更新进度
                progress = (idx + 1) / total * 100
                self.progress['value'] = progress
            
            if not self.stop_event.is_set():
                self.log("所有文件处理完成！", "success")
                
        except Exception as e:
            self.log(f"处理失败: {str(e)}", "error")
        finally:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def process_single_file(self, input_path, output_path):
        """单个文件处理"""
        temp_dir = tempfile.mkdtemp()
        try:
            encoder = self.get_encoder()
            resolution = self.resolution.get()
            framerate = self.framerate.get()
            bitrate = f"{self.bitrate.get()}k"
            
            segments = []
            if self.process_type.get() in ["加片头", "同时添加"]:
                intro_temp = os.path.join(temp_dir, "intro.mp4")
                self.preprocess_video(self.intro_entry.get(), intro_temp, encoder, resolution, framerate)
                segments.append(intro_temp)
            
            main_temp = os.path.join(temp_dir, "main.mp4")
            self.preprocess_video(input_path, main_temp, encoder, resolution, framerate)
            segments.append(main_temp)
            
            if self.process_type.get() in ["加片尾", "同时添加"]:
                outro_temp = os.path.join(temp_dir, "outro.mp4")
                self.preprocess_video(self.outro_entry.get(), outro_temp, encoder, resolution, framerate)
                segments.append(outro_temp)
            
            self.concat_videos(segments, output_path, encoder, bitrate, framerate)
            
        except Exception as e:
            raise e
        finally:
            # 清理临时文件
            for f in segments:
                try:
                    os.remove(f)
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass

    def preprocess_video(self, input_path, output_path, encoder, resolution, framerate):
        """预处理视频"""
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-i', input_path,
            '-vf', f'scale={resolution},fps={framerate}',
            '-c:v', encoder,
            '-y', output_path
        ]
        self.run_command(cmd)

    def concat_videos(self, input_files, output_path, encoder, bitrate, framerate):
        """拼接视频"""
        list_file = os.path.join(tempfile.gettempdir(), "filelist.txt")
        with open(list_file, 'w', encoding='utf-8') as f:
            for file in input_files:
                f.write(f"file '{file}'\n")
        
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c:v', encoder,
            '-b:v', bitrate,
            '-r', framerate,
            '-y', output_path
        ]
        self.run_command(cmd)
        os.remove(list_file)

    def get_encoder(self):
        """获取选择的编码器"""
        hardware = self.hardware_accel.get()
        return {
            "NVIDIA GPU": "h264_nvenc",
            "AMD GPU": "h264_amf",
            "Intel GPU": "h264_qsv",
            "CPU": "libx264"
        }[hardware]

    def run_command(self, cmd):
        """执行命令行并处理输出"""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            for line in process.stdout:
                self.log(line.strip(), "debug")
            
            if process.wait() != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
                
        except UnicodeDecodeError as ude:
            self.log(f"编码错误：{str(ude)}", "warning")
        except Exception as e:
            raise e

    def update_status(self, item_id, status, tag):
        """更新文件状态"""
        self.status_update_queue.put((item_id, status, tag))

    def get_item_id(self, file_path):
        """通过文件路径获取Treeview的item id"""
        for child in self.tree.get_children():
            if self.tree.item(child)['values'][1] == file_path:
                return child
        return None

    def process_queues(self):
        """处理所有队列"""
        # 处理日志队列
        while not self.log_queue.empty():
            msg, tag = self.log_queue.get()
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n", tag)
            self.log_text.tag_config(tag, foreground=self.get_log_color(tag))
            self.log_text.configure(state=tk.DISABLED)
            self.log_text.see(tk.END)
        
        # 处理状态更新队列
        while not self.status_update_queue.empty():
            item_id, status, tag = self.status_update_queue.get()
            self.tree.item(item_id, values=(status, self.tree.item(item_id)['values'][1]))
            self.tree.tag_configure(tag, foreground=self.get_log_color(tag))
        
        self.master.after(100, self.process_queues)

    def get_log_color(self, tag):
        """获取日志颜色"""
        colors = {
            "info": "#2c3e50",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545",
            "processing": "#17a2b8",
            "debug": "#6c757d"
        }
        return colors.get(tag, "#2c3e50")

    def stop_processing(self):
        """停止处理"""
        if messagebox.askyesno("确认", "确定要停止当前处理任务吗？"):
            self.stop_event.set()
            self.log("处理已中止", "warning")
            self.stop_btn.config(state=tk.DISABLED)

    def log(self, message, tag="info"):
        """记录日志"""
        self.log_queue.put((message, tag))

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateVideoProcessor(root)
    root.mainloop()
