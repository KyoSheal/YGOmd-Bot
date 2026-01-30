# 🎮 Yu-Gi-Oh! Master Duel AI Bot

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent AI bot for Yu-Gi-Oh! Master Duel that learns from human gameplay through deep learning and LLM-powered analysis.

## ✨ Features

### 🎮 多平台支持
- **PC 版支持**: 通过 PyAutoGUI 控制 Steam 版 Master Duel
- **Android 版支持**: 通过 ADB 控制模拟器中的 Master Duel（推荐）
  - 更快的响应速度
  - 更精确的触摸控制
  - 更难被检测
  - 参考 MaaAssistantArknights 架构设计

### 🧠 Deep Learning Recording System
- **Manual Gameplay Recording**: Record your gameplay sessions and let the AI learn from your strategies
- **LLM-Powered Analysis**: Uses local LLM (Ollama) to understand tactical intent, combo patterns, and card synergies
- **Multi-Path Learning**: Discovers multiple possible combo routes from the same hand
- **Knowledge Base**: Builds a library of learned combos and patterns

### 📋 Deck Management
- **Automatic Deck Parsing**: Converts deck lists to structured JSON format
- **Card Categorization**: Auto-categorizes cards (monster/spell/trap) and extra deck summon types
- **Deck Type Recognition**: Automatically identifies deck archetypes

### 👁️ Game State Detection
- **Screen Capture**: Real-time game window capture
- **UI Detection**: Detects game phases, LP, buttons, and card information panels
- **OCR Integration**: Tesseract OCR for card name recognition
- **Debug UI**: Real-time monitoring interface with screenshot display and recognition results (参考 MAA 设计)

### 🎯 Action Recording
- **Operation Tracking**: Records card usage, effect activation, summons, and more
- **Sequence Analysis**: Groups operations into meaningful combo sequences
- **Replay System**: Saves recordings as JSON for later analysis

## 📁 Project Structure

```
YGO/
├── config/
│   └── settings.yaml          # Configuration settings
├── data/
│   ├── combos/                # Learned combo patterns
│   ├── replays/               # Recorded gameplay sessions
│   ├── schemas/               # JSON schemas
│   ├── templates/             # Card image templates
│   └── standard_deck.json     # Converted deck file
├── src/
│   ├── automation/            # Auto-play execution
│   ├── control/               # Mouse/keyboard control
│   ├── core/                  # Core game state logic
│   ├── data/                  # Data processing
│   │   └── deck_converter.py  # Deck format converter
│   ├── learning/              # AI learning modules
│   │   ├── action_recorder.py # Gameplay recorder
│   │   ├── action_schema.py   # Action data structures
│   │   └── llm_engine.py      # LLM decision engine
│   └── vision/                # Computer vision
│       ├── master_duel_detector.py  # Game UI detector
│       └── card_detector.py   # Card recognition
├── tools/
│   ├── manual_recorder_ui.py  # Recording GUI
│   └── smart_deck_scanner.py  # Deck scanning tool
├── main.py                    # Main entry point
└── requirements.txt           # Dependencies
```

## 🚀 Quick Start

### 新手推荐路径 🌟

**使用雷电模拟器？直接看这里！**

📖 **[快速开始指南 - 雷电模拟器版](QUICK_START.md)** ⭐

这个指南会带你：
1. ✅ 5 分钟完成环境配置
2. ✅ 2 分钟测试连接
3. ✅ 1 分钟启动调试 UI
4. ✅ 10 分钟制作识别模板
5. ✅ 开始自动操作

### Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for card name recognition)
- [Ollama](https://ollama.ai/) (for LLM-powered analysis)
- **选择一个平台**:
  - **PC 版**: Yu-Gi-Oh! Master Duel (Steam version)
  - **Android 版** (推荐): Android 模拟器 (BlueStacks 5 / MuMu 12 / 雷电模拟器)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/YGO.git
cd YGO

# Install dependencies
pip install -r requirements.txt

# (推荐) 安装 pure-python-adb 以获得更好的 Android 控制性能
pip install pure-python-adb

# Install Tesseract OCR (Windows)
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH and install Chinese language pack

# Install Ollama and download a model
# https://ollama.ai/
ollama pull qwen2.5:7b
```

### Android 模拟器设置 (推荐)

如果你想使用 Android 版（更快、更稳定、更难被检测），请查看详细指南：

📖 **[Android 模拟器设置指南](ANDROID_SETUP_GUIDE.md)**

快速开始：
```bash
# 1. 安装并启动模拟器（BlueStacks 5 / MuMu 12）
# 2. 在模拟器中安装 Master Duel
# 3. 开启 ADB 调试
# 4. 运行测试
python src/control/adb_controller.py
```

### Usage

#### 1. Convert Your Deck
Create a `Deck.json` file with your deck list, then convert it:

```bash
python src/data/deck_converter.py
```

#### 2. Start the Debug UI (推荐)
实时查看截图和识别结果：

```bash
python debug_ui.py
```

功能特性：
- 📷 实时截图显示
- 🔍 识别结果展示（场景、卡片、OCR）
- 🐛 调试信息和日志输出
- ⚙️ 设备和识别设置

详细说明请查看 [调试 UI 使用指南](DEBUG_UI_GUIDE.md)

#### 3. Start the Recording UI
```bash
python tools/manual_recorder_ui.py
```

#### 4. Record Your Gameplay
1. Open Yu-Gi-Oh! Master Duel
2. Click "▶ 开始录制" to start recording
3. Play the game normally
4. Click "⏸ 停止录制" when done
5. Use "分析当前序列" for LLM analysis

## 📖 Documentation

- [调试 UI 使用指南](DEBUG_UI_GUIDE.md) - **新功能！实时监控和调试**
- [Android 模拟器设置指南](ANDROID_SETUP_GUIDE.md) - **推荐！使用 Android 版获得更好的体验**
- [Android 迁移计划](ANDROID_MIGRATION_PLAN.md) - 从 PC 版迁移到 Android 版
- [Deep Learning System Guide](DEEP_LEARNING_SYSTEM.md) - Detailed usage instructions
- [LLM Integration Guide](LLM_GUIDE.md) - How to configure and use the LLM engine
- [Tesseract Installation](TESSERACT_INSTALL.md) - OCR setup guide

## 🔧 Configuration

Edit `config/settings.yaml` to customize:

```yaml
game:
  window_title: "Yu-Gi-Oh! MASTER DUEL"
  resolution: [1920, 1080]

llm:
  model: "qwen2.5:7b"
  api_url: "http://localhost:11434"

recording:
  detection_interval: 0.5
  action_cooldown: 1.0
```

## 🎲 Supported Features

| Feature | PC Version | Android Version |
|---------|------------|-----------------|
| Deck Conversion | ✅ Complete | ✅ Complete |
| Manual Recording | ✅ Complete | ✅ Complete |
| LLM Analysis | ✅ Complete | ✅ Complete |
| UI Detection | ✅ Complete | 🔧 In Progress |
| OCR Recognition | 🔧 In Progress | 🔧 In Progress |
| Input Control | ⚠️ PyAutoGUI | ✅ ADB + Touch |
| Auto-Play | 🚧 Planned | 🚧 Planned |
| Detection Avoidance | ⚠️ Medium | ✅ High |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This project is for educational purposes only. Use at your own risk. The developers are not responsible for any consequences of using this software, including but not limited to account bans.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights) - Android control architecture inspiration
- [MaaFramework](https://github.com/MaaXYZ/MaaFramework) - Automation framework reference
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Chinese OCR
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [pure-python-adb](https://github.com/Swind/pure-python-adb) - Python ADB implementation
- Konami - Yu-Gi-Oh! Master Duel

---

**Note**: This is an ongoing project. Features are continuously being improved and added.
