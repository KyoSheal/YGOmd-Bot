# 深度学习录制系统使用指南

## 📋 概述

这个系统可以**记录并深度学习**您的游戏王Master Duel操作，通过LLM理解您的战术意图、combo模式和卡片协同。

## 🎯 核心特性

1. **智能卡片识别**：使用OCR识别卡片，并通过卡组约束确保准确性
2. **深度学习分析**：LLM理解操作意图，而不仅仅是简单记录
3. **多路径发现**：系统会学习一手牌的多种展开可能
4. **实时反馈**：录制界面实时显示检测到的操作和LLM分析

## 🚀 快速开始

### 1. 准备卡组文件

首先转换您的`Deck.json`为标准格式：

```bash
python src\data\deck_converter.py
```

这会生成`data/standard_deck.json`，包含您的40张主卡组和15张额外卡组。

### 2. 启动录制界面

```bash
python tools\manual_recorder_ui.py
```

### 3. 开始录制

1. 点击"▶ 开始录制"按钮
2. 进入游戏王Master Duel
3. 正常进行游戏，系统会自动检测您的操作
4. 界面会实时显示：
   - 检测到的卡片和操作
   - OCR置信度
   - 时间戳

### 4. 获取分析

在每个操作序列后，点击"分析当前序列"按钮，LLM会进行深度分析：

- **Combo名称**：识别您使用的combo
- **战术意图**：理解您的战术目标
- **核心卡片**：识别关键卡片
- **关键协同**：分析卡片之间的配合
- **替代路线**：发现其他可能的展开方式
- **深度洞察**：LLM的战术理解

## 📁 文件结构

```
Project/YGO/
├── Deck.json                        # 原始卡组文件
├── data/
│   ├── standard_deck.json           # 标准化卡组
│   ├── replays/                     # 录像存储
│   │   ├── replay_20260121_01/.json # 单场录像
│   │   └── screenshots/             # 操作截图
│   └── learned_patterns/            # 学习到的模式
├── src/
│   ├── data/
│   │   └── deck_converter.py        # 卡组转换器
│   └── learning/
│       ├── action_schema.py         # 操作数据结构
│       ├── action_recorder.py       # 录制器
│       └── llm_engine.py            # LLM引擎（增强版）
└── tools/
    └── manual_recorder_ui.py        # 录制界面
```

## 🧠 深度学习功能

### 1. 从操作序列学习
`llm_engine.learn_from_action_sequence()`

分析整个操作序列，理解：
- Combo的战术意图
- 核心模式和关键转折点
- 卡片协同关系
- 关键决策点
- 可复用的通用模式

### 2. 发现多种展开路线
`llm_engine.discover_alternative_combos()`

同一手牌可能有**多种展开方式**，系统会发现所有可能性：
- 每种路线的步骤
- 最终场面
- 优势和劣势
- 适用场景（先攻/后攻）
- 成功率

### 3. 理解战术决策
`llm_engine.understand_strategic_decision()`

分析单个操作的战术价值：
- 决策原因
- 战术价值
- 风险评估
- 可能的替代操作

### 4. 提取卡片协同
`llm_engine.extract_card_synergy()`

分析卡片之间的协同关系：
- 直接协同（效果直接配合）
- 间接协同（资源/场面配合）
- 时机协同（发动时机配合）
- Combo协同（combo链的一部分）

## 📊 数据格式

### Replay结构
```json
{
  "replay_id": "replay_20260121_012530",
  "deck_used": "暗红恶魔",
  "sequences": [
    {
      "sequence_id": "seq_001",
      "actions": [
        {
          "timestamp": 1737452730.123,
          "action_type": "normal_summon",
          "card_name": "骸骨恶魔",
          "source_zone": "hand",
          "ocr_confidence": 0.95
        }
      ],
      "llm_analysis": {
        "combo_name": "骸骨恶魔检索展开",
        "tactical_intent": "检索暗红恶魔龙调整...",
        "core_cards": ["骸骨恶魔", "暗红地狱盖亚"],
        "alternative_paths": [...]
      }
    }
  ]
}
```

## 🔧 配置

### OCR设置
在`action_recorder.py`中：
```python
self.detection_interval = 0.5  # 检测间隔（秒）
self.action_cooldown = 1.0     # 操作冷却时间
```

### LLM设置
在`llm_engine.py`中：
```python
model_name = "qwen2.5:7b"      # Ollama模型
api_url = "http://localhost:11434"
```

## ⚠️ 注意事项

1. **OCR准确性**：系统通过卡组约束大幅提高准确性，但仍可能出错
2. **手动验证**：如果OCR置信度低，建议手动验证
3. **LLM依赖**：需要运行Ollama本地服务
4. **性能**：LLM分析可能需要几秒钟，请耐心等待

## 🎓 使用建议

1. **先演示基础Combo**：从简单的展开开始，让系统学习基础模式
2. **多次演示同一Combo**：重复演示可以让系统更好地理解
3. **演示多种路线**：同一手牌尝试不同的展开方式
4. **记录笔记**：在分析结果中添加您的注释

## 🔜 下一步

1. 实际录制几场对局
2. 检查LLM分析质量
3. 构建Combo知识库
4. 实现模式复用到AI决策

---

**问题？** 查看日志文件或联系开发团队
