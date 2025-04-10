# 专业视频处理工具 v4.1

一个基于Python和FFmpeg的图形界面视频处理工具，支持批量添加片头片尾、硬件加速转码等功能。

## 功能特性

- 🎬 批量添加片头、片尾或同时添加
- ⚡ 硬件加速编码（支持NVIDIA/AMD/Intel GPU）
- 📁 支持文件夹递归扫描添加视频文件
- 🖥️ 可调整分辨率、帧率和码率
- 📊 实时进度显示和日志输出
- 🚦 处理过程可随时停止
- 🗑️ 自动清理临时文件

## 系统要求

- Python 3.6+
- FFmpeg (需添加到系统PATH)
- 支持的硬件加速编码器（可选）

## 安装步骤

1. 克隆本仓库或下载源代码
   ```bash
[   git clone https://github.com/yourusername/video-processor.git
   cd video-processor](https://github.com/CommonerOfWestWall/Add-headers-or-trailers-to-videos-in-batches.git)
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 确保FFmpeg已安装并添加到系统PATH

## 使用方法

1. 运行程序
   ```bash
   python 加片头片尾4.1大改版.py
   ```

2. 界面操作：
   - 使用"添加文件"或"添加文件夹"按钮导入视频
   - 设置片头片尾文件路径
   - 选择输出目录
   - 配置编码参数（可选）
   - 点击"开始处理"按钮

## 参数说明

### 处理设置
- **处理类型**：选择添加片头、片尾或同时添加
- **片头/片尾文件**：选择要添加的视频文件
- **输出目录**：指定处理后的文件保存位置

### 编码设置
- **硬件加速**：选择编码器类型（NVIDIA/AMD/Intel GPU或CPU）
- **分辨率**：输出视频分辨率
- **帧率**：输出视频帧率
- **码率**：输出视频比特率（kbps）

## 注意事项

1. 处理大型视频文件可能需要较长时间
2. 使用硬件加速需要相应的显卡驱动支持
3. 输出目录需要有足够的磁盘空间
4. 程序运行时不要关闭主窗口

## 常见问题

**Q: 程序报错"ffmpeg not found"**  
A: 请确保FFmpeg已正确安装并添加到系统PATH环境变量

**Q: 硬件加速选项无效**  
A: 请检查显卡驱动是否安装正确，并确认FFmpeg支持所选编码器

**Q: 处理后的视频没有声音**  
A: 当前版本主要处理视频流，音频处理将在后续版本完善

## 贡献指南

欢迎提交Issue和Pull Request。对于重大更改，请先开Issue讨论。

## 许可证

MIT License
