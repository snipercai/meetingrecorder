# 会议转写系统
本项目全量代码均由Trae生成，编程模型采用GML-5

## 📋 项目概览

会议转写系统是一个实时语音识别与智能总结的工具，采用轻量化技术栈，可在个人笔记本终端上本地运行。该系统能够通过麦克风获取语音，使用Qwen3-ASR-0.6B模型进行实时语音识别，并将识别结果显示在Web前端页面上。系统会每隔1分钟将累积的转写文本和历史总结一起输入给LLM模型进行归纳总结，并自动保存为Markdown文件。

### ✨ 核心特性
- **实时语音识别**：基于 Qwen3-ASR-0.6B 模型，提供高精度语音转文字
- **智能会议总结**：支持 OpenAI 兼容 API 调用 LLM，生成专业会议总结
- **Web 实时显示**：极简深色主题界面，WebSocket 实时推送转写内容
- **Markdown 记录**：自动保存会议总结到文件，便于后续查阅和分享
- **Hugging Face 模型管理**：首次运行自动下载模型到本地，支持离线模式使用
- **灵活的测试模式**：支持在线和离线模式的测试，确保系统稳定性

## 🔗 仓库地址
https://github.com/snipercai/meeting-recorder

## 📁 项目结构

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

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动服务
```bash
# 首次运行（在线模式，自动下载模型到本地model目录）
python main.py

# 后续运行（离线模式，使用本地已下载的模型）
python main.py --offline

# 指定设备和离线模式
python main.py --device cpu --offline

# 指定端口和离线模式
python main.py --port 9000 --offline
```

### 访问 Web 界面
打开浏览器访问：`http://localhost:8080`

## 📚 核心功能

### 1. 模型管理
- **首次运行**：系统自动从Hugging Face下载Qwen3-ASR-0.6B模型到本地`model`目录
- **离线模式**：使用`--offline`参数启动时，系统使用本地已下载的模型，无需网络连接
- **模型存储**：模型默认存储在`model`目录中，采用Hugging Face缓存格式

### 2. 测试模式
系统支持在线和离线模式的测试，可通过`--mode`参数指定：

```bash
# 在线模式测试
python test/test_all.py --module asr --mode online

# 离线模式测试
python test/test_all.py --module asr --mode offline

# 离线模式冒烟测试
python test/test_all.py --smoke --mode offline
```

## ⚙️ 配置管理

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

## 🧩 系统架构

### 模块说明

| 模块 | 职责 | 文件 |
|------|------|------|
| 主入口 | 协调各模块的初始化、运行和停止 | main.py |
| 配置管理 | 管理系统配置，支持环境变量和命令行参数 | config.py |
| 日志模块 | 提供分级日志记录功能 | logger.py |
| 音频采集 | 从麦克风获取音频数据 | audio_capture.py |
| ASR引擎 | 加载模型并进行语音识别 | asr_engine.py |
| LLM总结 | 定时生成会议总结 | summarizer.py |
| 文件管理 | 创建和更新会议记录文件 | file_manager.py |
| Web服务 | 提供HTTP服务和WebSocket通信 | web_server.py |

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
1. **音频采集**：AudioCapture模块从麦克风采集音频数据
2. **语音识别**：ASREngine对音频数据进行语音识别
3. **转写处理**：MeetingRecorder处理识别结果并添加到转写缓冲区
4. **实时推送**：WebServer将转写结果实时推送到前端
5. **定时总结**：Summarizer定时生成会议总结
6. **文件更新**：FileManager将会议总结写入Markdown文件
7. **总结推送**：WebServer将会议总结推送到前端

## 🛠️ 技术栈

| 技术/库 | 用途 | 版本要求 |
|---------|------|---------|
| Python 3 | 基础编程语言 | 3.8+ |
| PyAudio | 音频采集 | 0.2.11+ |
| NumPy | 数据处理 | 1.20+ |
| qwen-asr | 语音识别 | 最新版 |
| aiohttp | Web服务器和WebSocket | 3.8+ |
| requests | HTTP请求（API模式） | 2.28+ |

## 📱 前端界面

前端界面采用极简设计，主要功能是实时显示转写和总结内容。

### 核心功能
- **实时转写**：显示实时语音识别结果
- **会议总结**：显示最新的会议总结内容
- **深色主题**：适合长时间观看，减少视觉疲劳
- **响应式设计**：适配不同屏幕尺寸

### 技术实现
- **HTML5**：基础页面结构
- **CSS3**：样式设计，包括深色主题
- **JavaScript**：WebSocket客户端，实时接收和显示数据

## 🧪 测试与部署

### 测试方法

系统提供了完整的测试脚本，支持模块级测试和端到端测试。

#### 测试命令
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

#### 测试报告
- 每次运行测试都会自动生成Markdown格式的测试报告
- 报告保存在 `test/` 目录下，命名格式为 `test_report_<测试类型>_<时间戳>.md`
- 报告包含测试概览、结果摘要和详细日志

### 部署步骤
1. **安装依赖**：`pip install -r requirements.txt`
2. **配置环境变量**：复制`.env.example`为`.env`并填写必要信息
3. **启动服务**：`python main.py`
4. **访问Web界面**：打开浏览器访问 `http://localhost:8080`

## 🌟 技术亮点

1. **多模态处理**：整合音频采集、语音识别和自然语言处理
2. **实时性**：通过WebSocket实现实时数据推送
3. **智能总结**：利用OpenAI兼容API生成高质量会议总结
4. **灵活性**：支持Hugging Face离线模式，使用本地缓存的模型
5. **可扩展性**：模块化设计便于功能扩展和集成
6. **稳定性**：完善的异常处理和日志记录机制

## 🎯 应用场景

- **会议记录**：自动记录会议内容，生成会议总结
- **讲座记录**：记录讲座内容，生成学习笔记
- **访谈记录**：记录访谈内容，生成访谈摘要
- **个人笔记**：通过语音输入快速记录个人想法

## 📈 未来发展方向

1. **多语言支持**：增加对多种语言的识别和总结能力
2. **智能分析**：增加会议内容的智能分析，如情感分析、关键词提取等
3. **集成能力**：与更多第三方工具集成，如日历、任务管理等
4. **移动化**：开发移动应用，支持移动端使用
5. **云服务**：提供云服务版本，支持远程访问和多设备同步

## 🤝 贡献

欢迎提交Issue和Pull Request，共同改进项目。

## 📄 许可证

本项目采用MIT许可证。