# 项目状态

## 当前进度

### ✅ 已完成
1. **ADB 控制系统** - 连接 LDPlayer 模拟器，支持截图、点击、滑动
2. **Pipeline 任务引擎** - 参考 MAA 设计，支持 JSON 配置任务流程
3. **模板匹配系统** - 基于 OpenCV 的图像识别
4. **观看对战录像任务** - 完整的任务流程配置

### ⚠️ 进行中
- 调试模板识别问题
- 优化 ROI 配置
- 完善任务流程

## 核心文件

### 系统核心
- `src/core/pipeline.py` - Pipeline 执行引擎
- `src/control/adb_controller.py` - ADB 控制器
- `data/tasks/watch_replay.json` - 任务配置
- `data/templates/daily/` - 模板图片

### 运行脚本
- `run_watch_replay_v2.py` - 观看对战录像

### 工具
- `tools/manual_template_extractor.py` - 手动提取模板

## 下一步

1. 修复 DUEL LIVE 识别问题
2. 完成完整任务流程测试
3. 添加更多日常任务
4. 优化性能和稳定性

## 使用方法

```bash
# 运行观看对战录像任务
python run_watch_replay_v2.py

# 提取模板
python tools/manual_template_extractor.py
```

## 技术栈

- Python 3.x
- OpenCV - 图像识别
- pure-python-adb - Android 控制
- loguru - 日志系统
