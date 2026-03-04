# 会议转写系统
本项目全量代码均由Trae生成，编程模型采用GML-5

## 项目概述

会议转写系统是一个实时语音识别与智能总结的工具，采用轻量化技术栈，可在个人笔记本终端上本地运行。该系统能够通过麦克风获取语音，使用Qwen3-ASR-0.6B模型进行实时语音识别，并将识别结果显示在Web前端页面上。系统会每隔1分钟将累积的转写文本和历史总结一起输入给LLM模型进行归纳总结，并自动保存为Markdown文件。

### 功能特性
- **实时语音识别**：基于 Qwen3-ASR-0.6B 模型
- **智能会议总结**：支持 OpenAI 兼容 API 调用 LLM
- **Web 实时显示**：极简深色主题界面，WebSocket 实时推送
- **Markdown 记录**：自动保存会议总结到文件
- **Hugging Face 模型管理**：首次运行自动下载模型到本地，支持离线模式使用本地模型
- **灵活的测试模式**：支持在线和离线模式的测试

## 仓库地址
https://github.com/snipercai/meeting-recorder

## 项目结构

```
meeting-recorder/
├── main.py            # 主入口文件，协调各模块
├── config.py          # 配置管理
├── logger.py          # 日志模块
├── audio_capture.py   # 音频采集模块
├── asr_engine.py      # ASR语音识别模块
├── summarizer.py      # LLM总结模块
├── file_manager.py    # Markdown文件管理
├── web_server.py      # Web服务模块
├── requirements.txt   # 依赖文件
├── .env               # 环境变量配置
├── .gitignore         # Git忽略配置
├── test/              # 测试目录
│   └── test_all.py    # 测试脚本
└── static/
    └── index.html     # Web前端页面
```

## 使用方法

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（默认在线模式，第一次运行会下载模型到本地model目录）
python main.py

# 启动服务（离线模式，使用本地已下载的模型）
python main.py --offline

# 启动服务（指定设备和离线模式）
python main.py --device cpu --offline

# 启动服务（指定端口和离线模式）
python main.py --port 9000 --offline

# 访问 Web 界面
# http://localhost:8080
```

### 模型管理
- **首次运行**：系统会自动从Hugging Face下载Qwen3-ASR-0.6B模型到本地`model`目录
- **离线模式**：使用`--offline`参数启动时，系统会使用本地已下载的模型，无需网络连接
- **模型路径**：模型默认存储在`model`目录中，采用Hugging Face缓存格式

### 测试模式
系统支持在线和离线模式的测试，可通过`--mode`参数指定：

```bash
# 在线模式测试
python test/test_all.py --module asr --mode online

# 离线模式测试
python test/test_all.py --module asr --mode offline

# 离线模式冒烟测试
python test/test_all.py --smoke --mode offline
```

## 配置管理

系统使用`.env`文件和环境变量进行配置管理，支持命令行参数覆盖默认配置。

### 核心配置项

| 配置项 | 描述 | 默认值 | 环境变量 |
|--------|------|--------|----------|
| LLM_API_BASE_URL | LLM API地址 | - | LLM_API_BASE_URL |
| LLM_API_KEY | LLM API密钥 | - | LLM_API_KEY |
| LLM_API_MODEL | LLM API模型名称 | - | LLM_API_MODEL |
| ASR_MODEL_PATH | ASR模型路径 | Qwen/Qwen3-ASR-0.6B | ASR_MODEL_PATH |
| ASR_DEVICE | ASR设备（auto/cpu/cuda） | auto | ASR_DEVICE |
| ASR_OFFLINE | ASR离线模式 | false | ASR_OFFLINE |
| WEB_HOST | Web服务主机 | 0.0.0.0 | WEB_HOST |
| WEB_PORT | Web服务端口 | 8080 | WEB_PORT |
| SUMMARY_INTERVAL | 总结间隔（秒） | 60 | SUMMARY_INTERVAL |
| MODEL_DIR | 模型存储目录 | ./model | - |

## 核心功能模块分析

### 1. 主入口模块 (main.py)

主入口模块是系统的控制中心，负责协调各模块的初始化、运行和停止。

**核心功能**：
- 解析命令行参数，支持多种配置选项
- 初始化各功能模块
- 启动Web服务器
- 运行音频采集和处理
- 处理系统信号，支持优雅退出

**设计亮点**：
- 使用异步编程模式，提高系统响应速度
- 模块化设计，各组件职责清晰
- 完善的错误处理和日志记录
- 支持优雅退出，确保资源正确释放

### 2. 音频采集模块 (audio_capture.py)

音频采集模块负责从麦克风获取音频数据，并通过回调函数传递给ASR引擎进行处理。

**核心功能**：
- 初始化PyAudio设备
- 配置音频参数（采样率、声道数、帧大小）
- 启动音频流采集
- 处理音频数据回调

**设计亮点**：
- 使用PyAudio库进行音频采集，兼容性好
- 支持多种音频参数配置
- 异常处理机制完善
- 提供上下文管理器接口，方便资源管理

### 3. ASR引擎模块 (asr_engine.py)

ASR引擎模块负责加载Qwen3-ASR-0.6B模型，并对音频数据进行语音识别。

**核心功能**：
- 加载和管理ASR模型
- 处理不同格式的音频输入
- 执行语音识别推理
- 处理识别结果

**设计亮点**：
- 支持自动设备选择（CUDA/CPU）
- 处理多种音频输入格式
- 完善的错误处理和日志记录
- 支持流式识别和批处理

### 4. LLM总结模块 (summarizer.py)

LLM总结模块负责对会议转写内容进行定时总结，支持OpenAI兼容API模式。

**核心功能**：
- 验证API配置
- 构建总结提示词
- 调用LLM生成会议总结
- 定时执行总结任务

**设计亮点**：
- 支持OpenAI兼容API调用
- 构建专业的会议总结提示词
- 定时自动执行总结任务
- 完善的错误处理和日志记录

### 5. Web服务模块 (web_server.py)

Web服务模块负责提供HTTP静态文件服务和WebSocket实时通信功能，用于展示转写和总结内容。

**核心功能**：
- 提供HTTP静态文件服务
- 处理WebSocket连接
- 广播转写和总结内容到客户端
- 管理WebSocket客户端连接

**设计亮点**：
- 使用aiohttp库实现异步Web服务
- 支持WebSocket实时通信
- 高效的消息广播机制
- 完善的错误处理和日志记录

### 6. 文件管理模块 (file_manager.py)

文件管理模块负责创建和更新会议记录Markdown文件。

**核心功能**：
- 创建带时间戳的会议记录文件
- 更新会议总结（替换原有内容）
- 管理文件路径和状态

**设计亮点**：
- 自动创建带时间戳的文件
- 支持会议总结的更新和替换
- 完善的错误处理和日志记录

## 系统架构与数据流

系统采用模块化架构，各组件之间通过明确的接口进行通信，形成完整的数据流。

### 数据流图

```
[麦克风] → [AudioCapture] → [ASREngine] → [MeetingRecorder] → [Summarizer]
     ↓                    ↓              ↓                     ↓
     ↓                    ↓              ↓                     ↓
[音频数据] → [音频处理] → [语音识别] → [转写文本] → [会议总结]
                                                            ↓
                                                            ↓
                                               [FileManager] → [Markdown文件]
                                                            ↓
                                                            ↓
                                               [WebServer] → [Web前端]
```

### 核心流程

1. **音频采集**：AudioCapture模块从麦克风采集音频数据，通过回调函数传递给MeetingRecorder
2. **语音识别**：MeetingRecorder将音频数据传递给ASREngine进行语音识别
3. **转写处理**：ASREngine返回识别结果，MeetingRecorder将其添加到转写缓冲区
4. **实时推送**：MeetingRecorder将转写结果通过WebServer实时推送到前端
5. **定时总结**：Summarizer定时从MeetingRecorder获取转写文本，生成会议总结
6. **文件更新**：FileManager将最新的会议总结写入Markdown文件
7. **总结推送**：WebServer将会议总结实时推送到前端

## 技术栈

| 技术/库 | 用途 | 版本要求 |
|---------|------|---------|
| Python 3 | 基础编程语言 | 3.8+ |
| PyAudio | 音频采集 | 0.2.11+ |
| NumPy | 数据处理 | 1.20+ |
| qwen-asr | 语音识别 | 最新版 |
| aiohttp | Web服务器和WebSocket | 3.8+ |
| requests | HTTP请求（API模式） | 2.28+ |

## 异常处理与日志

系统采用多层次的异常处理机制，确保系统稳定性和可维护性。

### 异常处理
- **模块级异常**：每个模块定义了特定的异常类，如`ASRError`、`AudioCaptureError`等
- **全局异常捕获**：主入口模块捕获全局异常，确保系统不会崩溃
- **错误恢复**：部分模块支持错误恢复，如ASR引擎在CUDA不可用时自动切换到CPU模式

### 日志系统
- **分级日志**：支持DEBUG、INFO、WARNING、ERROR、CRITICAL五个级别
- **模块日志**：每个模块有独立的日志记录器
- **详细输出**：开发调试阶段可设置为DEBUG级别，生产环境可设置为INFO或更高级别
- **文件日志**：支持将日志写入文件，便于问题排查

## 前端界面

前端界面采用极简设计，主要功能是实时显示转写和总结内容。

### 核心功能
- **实时转写**：显示实时语音识别结果，同一个总结周期内的所有文字显示在一个段落里
- **会议总结**：显示最新的会议总结内容
- **深色主题**：适合长时间观看，减少视觉疲劳
- **响应式设计**：适配不同屏幕尺寸

### 技术实现
- **HTML5**：基础页面结构
- **CSS3**：样式设计，包括深色主题
- **JavaScript**：WebSocket客户端，实时接收和显示数据

## 测试与部署

### 测试方法

系统提供了完整的测试脚本，支持模块级测试和端到端测试。

1. **测试目录结构**：
   ```
   meeting-recorder/
   └── test/
       └── test_all.py    # 测试脚本
   ```

2. **测试脚本使用**：
   ```bash
   # 运行所有测试
   python test/test_all.py

   # 运行指定模块测试
   python test/test_all.py --module config    # 测试配置模块
   python test/test_all.py --module logger    # 测试日志模块
   python test/test_all.py --module audio     # 测试音频采集模块
   python test/test_all.py --module asr       # 测试ASR引擎模块
   python test/test_all.py --module summarizer # 测试总结模块
   python test/test_all.py --module file      # 测试文件管理模块
   python test/test_all.py --module web       # 测试Web服务器模块

   # 运行端到端冒烟测试
   python test/test_all.py --smoke

   # 列出所有可用测试
   python test/test_all.py --list

   # 不生成测试报告
   python test/test_all.py --no-report
   ```

3. **测试报告**：
   - 每次运行测试都会自动生成Markdown格式的测试报告
   - 报告保存在 `test/` 目录下，命名格式为 `test_report_<测试类型>_<时间戳>.md`
   - 报告包含测试概览、结果摘要和详细日志

4. **模块测试**：
   - 运行各模块的独立测试代码
   - 验证模块功能是否正常

5. **集成测试**：
   - 运行完整系统，测试各模块协同工作
   - 验证端到端流程是否正常

6. **性能测试**：
   - 测试系统在不同硬件环境下的性能
   - 验证实时性和稳定性

### 部署步骤
1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**：
   - 复制`.env.example`为`.env`
   - 填写LLM API配置等必要信息

3. **启动服务**：
   ```bash
   python main.py
   ```

4. **访问Web界面**：
   - 打开浏览器访问 `http://localhost:8080`

## 总结与展望

会议转写系统是一个功能完整、架构清晰的实时语音识别与智能总结工具。系统采用模块化设计，各组件职责明确，通过异步编程提高系统响应速度，支持实时语音识别、智能会议总结、Web实时显示和Markdown文件保存等核心功能。

### 技术亮点
1. **多模态处理**：整合音频采集、语音识别和自然语言处理
2. **实时性**：通过WebSocket实现实时数据推送
3. **智能总结**：利用OpenAI兼容API生成高质量会议总结
4. **灵活性**：支持Hugging Face离线模式，使用本地缓存的模型
5. **可扩展性**：模块化设计便于功能扩展和集成

### 应用场景
- **会议记录**：自动记录会议内容，生成会议总结
- **讲座记录**：记录讲座内容，生成学习笔记
- **访谈记录**：记录访谈内容，生成访谈摘要
- **个人笔记**：通过语音输入快速记录个人想法

### 未来发展方向
1. **多语言支持**：增加对多种语言的识别和总结能力
2. **智能分析**：增加会议内容的智能分析，如情感分析、关键词提取等
3. **集成能力**：与更多第三方工具集成，如日历、任务管理等
4. **移动化**：开发移动应用，支持移动端使用
5. **云服务**：提供云服务版本，支持远程访问和多设备同步

会议转写系统通过结合现代语音识别和自然语言处理技术，为会议记录和知识管理提供了一种高效、智能的解决方案。系统的轻量化设计和模块化架构使其具有良好的可扩展性和可维护性，为未来的功能扩展和技术升级奠定了基础。