# 🚀 快速开始指南 - 雷电模拟器版

## 📋 准备工作清单

- [ ] 安装雷电模拟器
- [ ] 在模拟器中安装 Master Duel
- [ ] 安装 Python 3.10+
- [ ] 安装项目依赖

## 第一步：环境配置（5 分钟）

### 1.1 安装雷电模拟器

1. 下载雷电模拟器：https://www.ldplayer.net/
2. 安装并启动
3. 在模拟器中安装 Master Duel

### 1.2 开启 ADB 调试

1. 点击雷电模拟器右侧的"设置"按钮（齿轮图标）
2. 进入"其他设置"
3. 找到"ADB 调试"，**开启它**
4. 记下端口号（通常是 5555）

### 1.3 安装 Python 依赖

```bash
# 克隆项目（如果还没有）
git clone <your-repo-url>
cd YGO

# 安装依赖
pip install -r requirements.txt

# 确保安装了关键库
pip install PyQt5 pure-python-adb opencv-python numpy loguru
```

## 第二步：测试连接（2 分钟）

### 2.1 运行连接测试

```bash
python test_ldplayer_connection.py
```

### 2.2 预期结果

你应该看到：
```
✅ 连接成功！
✅ 屏幕尺寸: 1920x1080
✅ 截图成功！
✅ 点击命令已发送
✅ 滑动命令已发送
✅ 性能测试完成
```

### 2.3 如果连接失败

```bash
# 手动连接
adb connect 127.0.0.1:5555

# 查看设备
adb devices

# 应该看到:
# 127.0.0.1:5555    device
```

## 第三步：启动调试 UI（1 分钟）

### 3.1 启动界面

```bash
# 方法 1: 直接运行
python debug_ui.py

# 方法 2: 使用启动脚本（Windows）
start_debug_ui.bat
```

### 3.2 界面说明

- **左侧**: 实时截图显示
- **右侧**: 识别结果、调试信息、设置

### 3.3 测试功能

1. 点击"📷 截图"按钮
2. 查看是否显示游戏画面
3. 勾选"自动截图"
4. 观察画面是否实时更新

## 第四步：制作模板（10 分钟）

### 4.1 启动模板制作工具

```bash
python tools/create_templates.py
```

### 4.2 制作步骤

1. **截图**: 点击"📷 截图"获取游戏画面
2. **选择**: 用鼠标拖动选择要识别的元素（如按钮）
3. **命名**: 输入模板名称（如 `end_turn_button`）
4. **分类**: 输入分类（如 `battle`）
5. **保存**: 点击"💾 保存模板"

### 4.3 推荐制作的模板

#### 战斗场景 (battle)
- `end_turn_button` - 结束回合按钮
- `summon_button` - 召唤按钮
- `activate_button` - 发动按钮
- `main_phase` - 主要阶段指示器
- `battle_phase` - 战斗阶段指示器

#### 菜单场景 (menu)
- `duel_button` - 决斗按钮
- `solo_mode` - 单人模式按钮
- `deck_button` - 卡组按钮

#### 卡组编辑 (deck_editor)
- `save_button` - 保存按钮
- `card_slot` - 卡槽

### 4.4 模板制作技巧

✅ **好的模板**:
- 清晰、无模糊
- 包含独特的特征
- 大小适中（不要太大或太小）
- 避免包含动态内容

❌ **不好的模板**:
- 模糊不清
- 包含文字（文字可能变化）
- 太小（难以匹配）
- 太大（匹配慢）

## 第五步：测试识别（5 分钟）

### 5.1 在调试 UI 中测试

1. 启动调试 UI
2. 开启自动截图
3. 在游戏中进入不同场景
4. 查看"🔍 识别结果"标签页
5. 观察识别是否准确

### 5.2 调整识别参数

如果识别不准确，编辑 `src/vision/game_recognizer.py`:

```python
# 调整匹配阈值
match = self.match_template(screenshot, "button", threshold=0.8)
# 降低阈值 (0.7) = 更宽松
# 提高阈值 (0.9) = 更严格
```

## 第六步：自动操作（10 分钟）

### 6.1 简单模式测试

```bash
python auto_play_example.py
# 选择 1 - 简单模式
```

这会执行预定义的操作序列：
- 点击屏幕中心
- 滑动

### 6.2 高级模式测试

```bash
python auto_play_example.py
# 选择 2 - 高级模式
```

这会使用识别系统自动操作（需要模板）

### 6.3 编写自己的自动化脚本

创建 `my_auto_script.py`:

```python
from src.control.adb_controller import ADBController, AndroidGestureController
from src.vision.game_recognizer import SceneDetector
import time

# 连接设备
adb = ADBController(emulator_type="LDPlayer")
gesture = AndroidGestureController(adb)
detector = SceneDetector()

# 主循环
while True:
    # 截图
    screenshot = adb.screenshot()
    
    # 识别
    results = detector.recognize(screenshot)
    scene = results['scene']
    
    # 根据场景执行操作
    if scene == 'battle':
        # 战斗逻辑
        print("战斗中...")
        # TODO: 你的逻辑
        
    elif scene == 'menu':
        # 菜单逻辑
        print("在菜单中...")
        # TODO: 你的逻辑
    
    time.sleep(1)
```

## 🎯 完整工作流程

```
1. 启动雷电模拟器
   ↓
2. 打开 Master Duel
   ↓
3. 运行调试 UI (python debug_ui.py)
   ↓
4. 制作模板 (python tools/create_templates.py)
   ↓
5. 测试识别（在调试 UI 中）
   ↓
6. 编写自动化脚本
   ↓
7. 运行自动化 (python my_auto_script.py)
```

## 📊 性能优化建议

### 截图性能
```bash
# 安装 pure-python-adb（快 3-5 倍）
pip install pure-python-adb
```

### 识别性能
- 只识别需要的区域
- 缓存识别结果
- 降低识别频率

### 操作性能
- 添加合理的延迟
- 避免过于频繁的操作
- 使用随机延迟模拟真实用户

## 🐛 常见问题速查

| 问题 | 解决方法 |
|------|---------|
| 连接失败 | 1. 检查模拟器是否启动<br>2. 检查 ADB 调试是否开启<br>3. 运行 `adb connect 127.0.0.1:5555` |
| 截图黑屏 | 1. 重启模拟器<br>2. 重启 ADB: `adb kill-server && adb start-server` |
| 识别不准 | 1. 重新制作模板<br>2. 调整阈值<br>3. 检查分辨率 |
| 操作无反应 | 1. 检查坐标是否正确<br>2. 增加延迟<br>3. 查看日志 |
| UI 无法启动 | 1. 安装 PyQt5: `pip install PyQt5`<br>2. 检查 Python 版本 |

## 📚 下一步学习

- [ ] 阅读 [调试 UI 使用指南](DEBUG_UI_GUIDE.md)
- [ ] 阅读 [雷电模拟器设置指南](LDPLAYER_SETUP.md)
- [ ] 学习 [识别系统架构](DEBUG_UI_FEATURES.md)
- [ ] 查看 [自动化示例](auto_play_example.py)

## 💡 最佳实践

### 开发阶段
1. 使用调试 UI 实时查看
2. 保存关键截图
3. 制作高质量模板
4. 测试不同场景

### 测试阶段
1. 小范围测试
2. 观察识别准确性
3. 调整参数
4. 记录问题

### 生产阶段
1. 关闭调试 UI
2. 使用命令行模式
3. 添加错误处理
4. 监控日志

## 🎉 完成！

恭喜！你已经完成了基础设置。现在你可以：

✅ 连接雷电模拟器
✅ 实时查看游戏画面
✅ 识别游戏场景
✅ 执行自动操作

开始构建你的自动化脚本吧！🚀

---

**需要帮助？** 查看详细文档或提交 Issue。
