# YGO Master Duel 智能Bot

一个能够学习和理解游戏王Master Duel的智能自动化bot，通过观察用户操作来学习展开combo，并理解卡片效果和连锁关系。

## 🎯 项目特点

- **智能学习**: 通过录制用户操作来学习游戏策略
- **视觉识别**: 使用OpenCV和OCR识别游戏状态和卡片
- **人性化操作**: 模拟真实玩家的鼠标键盘操作
- **知识库系统**: 理解卡片效果和combo关系
- **Solo模式自动化**: 从简单的Solo模式开始

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**: 
- 需要安装Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- 确保Python版本 >= 3.8

### 2. 配置设置

编辑 `config/settings.yaml` 根据你的需求调整配置。

### 3. 运行Bot

```bash
python main.py
```

## 📖 使用指南

### 录制模式

1. 启动游戏王Master Duel
2. 运行Bot并选择"录制模式"
3. 进入游戏并进行你的展开操作
4. Bot会记录你的所有操作和游戏状态
5. 按 Ctrl+C 停止录制并保存

### 测试视觉系统

选择"测试视觉系统"来验证Bot能否正确捕获游戏画面。

## 🏗️ 项目结构

```
YGO/
├── src/
│   ├── core/           # 核心引擎（游戏状态、决策引擎）
│   ├── vision/         # 视觉识别（屏幕捕获、卡片识别、OCR）
│   ├── control/        # 操作控制（鼠标、键盘）
│   ├── knowledge/      # 知识库（卡片数据、效果、combo）
│   ├── learning/       # 学习系统（录制、分析、模型）
│   └── automation/     # 自动化流程（Solo模式、对战）
├── data/
│   ├── cards/          # 卡片数据
│   ├── templates/      # 图像模板
│   ├── models/         # 训练模型
│   └── recordings/     # 操作录制
├── config/             # 配置文件
├── logs/               # 日志文件
├── main.py             # 主入口
└── requirements.txt    # 依赖列表
```

## ⚙️ 核心模块

### 视觉识别系统
- **屏幕捕获**: 使用Win32 API捕获游戏窗口
- **卡片识别**: OpenCV模板匹配 + OCR
- **状态检测**: 识别回合、阶段、按钮等UI元素

### 操作控制系统
- **人性化移动**: 贝塞尔曲线模拟真实鼠标轨迹
- **随机延迟**: 模拟人类反应时间
- **智能点击**: 带有随机偏移的点击

### 学习系统
- **操作录制**: 记录鼠标、键盘和游戏状态
- **模式识别**: 分析操作序列找出combo模式
- **策略学习**: 从演示中学习决策

## 🔧 配置说明

主要配置项（在 `config/settings.yaml` 中）：

```yaml
game:
  window_title: "Yu-Gi-Oh! Master Duel"  # 游戏窗口标题

vision:
  ocr_language: "chi_sim+eng"  # OCR语言
  confidence_threshold: 0.75   # 识别置信度

control:
  click_delay: [0.15, 0.35]   # 点击延迟范围
  humanize: true               # 启用人性化操作

learning:
  recording_enabled: true      # 启用录制
  recording_path: "data/recordings"
```

## 🎮 开发路线

- [x] 项目基础架构
- [x] 屏幕捕获模块
- [x] 鼠标控制模块
- [x] 操作录制系统
- [ ] 卡片识别模块
- [ ] OCR文字识别
- [ ] 游戏状态分析
- [ ] 决策引擎
- [ ] Solo模式自动化
- [ ] 卡片知识库
- [ ] 学习系统优化

## ⚠️ 免责声明

本项目仅供学习研究使用。使用自动化工具可能违反游戏服务条款，可能导致账号被封禁。请谨慎使用，风险自负。

## 📝 许可证

本项目采用MIT许可证。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题或建议，请提交Issue。
