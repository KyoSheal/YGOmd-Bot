# 卡片模板库使用指南

## 概述

卡片模板库用于通过图像识别卡片。使用卡图特征匹配比OCR文字识别更准确、更快速。

## 目录结构

```
data/templates/
├── <card_id>.png        # 卡片艺术图
├── <card_id>.json       # 卡片元数据
└── collected_list.json  # 已采集卡片列表
```

## 使用流程

### 1. 采集卡片模板

使用模板采集工具：

```bash
python tools/collect_templates.py
```

**交互式采集**：
1. 提供游戏截图路径
2. 在图像中框选卡片区域
3. 输入卡片信息（ID和名称）
4. 按's'保存，'r'重置，'q'退出

**自动采集（从手牌）**：
```python
from tools.collect_templates import TemplateCollector

collector = TemplateCollector()
card_names = ["灰流丽", "增殖的G", "无限泡影"]
collector.auto_collect_from_hand(screenshot, card_names)
```

### 2. 识别卡片

```python
from src.vision.card_detector import CardImageRecognizer

recognizer = CardImageRecognizer()

# 识别单张卡片
result = recognizer.recognize_card(card_image)
# 返回: {'card_id': '...', 'name': '...', 'confidence': 0.95}

# 检测图像中的所有卡片
cards = recognizer.detect_cards_in_image(screenshot, zone='hand')
```

## 识别原理

### 双重匹配机制

1. **特征匹配（主要，权重70%）**
   - 使用ORB特征检测器
   - 提取卡片艺术图的关键点和描述符
   - 对光照、角度变化更鲁棒

2. **模板匹配（辅助，权重30%）**
   - 直接比较图像相似度
   - 补充特征匹配的不足

### 艺术图提取

只使用卡片上半部分（约60%区域）的艺术图，因为：
- 艺术图最具辨识度
- 避免文字、属性等干扰
- 提高识别速度

## 最佳实践

### 采集高质量模板

✅ **好的模板**：
- 卡片居中、完整
- 光照均匀
- 无遮挡、无模糊

❌ **避免**：
- 截取不完整
- 过度倾斜
- 反光严重

### 建立完整卡组模板

采集你常用卡组的所有卡片：
```python
# 示例：青眼卡组
blue_eyes_cards = [
    "青眼白龙",
    "青眼亚白龙", 
    "青眼究极龙",
    "贤者之石",
    "融合",
    # ... 更多卡片
]

for card_name in blue_eyes_cards:
    # 从截图采集或手动添加
    pass
```

## 性能优化

- **模板数量**: 100-200张常用卡片已足够
- **识别速度**: 单张卡片 < 100ms
- **准确率**: 特征匹配 > 95%（良好模板）

## 故障排除

### 问题：识别不准确

**解决方案**：
1. 检查模板质量
2. 重新采集清晰模板
3. 增加同一张卡的多个角度模板

### 问题：检测不到卡片

**解决方案**：
1. 调整`_detect_card_regions`的参数
2. 检查截图分辨率
3. 使用`calibrate_regions`校准区域

## 示例代码

### 完整识别流程

```python
from src.vision.screen_capture import ScreenCapture
from src.vision.card_detector import CardImageRecognizer
from src.core.game_state import GameState

# 捕获游戏画面
capture = ScreenCapture()
screenshot = capture.capture_window()

# 识别手牌
recognizer = CardImageRecognizer()
hand_cards = recognizer.detect_cards_in_image(screenshot, zone='hand')

# 更新游戏状态
state = GameState()
for card_data in hand_cards:
    from src.core.game_state import Card, Zone
    card = Card(
        card_id=card_data['card_id'],
        name=card_data['name'],
        zone=Zone.HAND,
        zone_index=card_data['zone_index']
    )
    state.hand.append(card)

print(f"检测到手牌: {[c.name for c in state.hand]}")
```

## 进阶：深度学习识别（可选）

未来可以集成YOLO或其他目标检测模型：
- 更准确的卡片定位
- 端到端识别
- 处理复杂场景

## 贡献模板

如果你采集了大量高质量模板，可以分享给社区！

---

**下一步**: 查看 `src/vision/card_detector.py` 了解详细实现
