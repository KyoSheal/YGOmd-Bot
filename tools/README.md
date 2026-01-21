# 工具脚本目录

这个目录包含各种辅助工具脚本。

## 可用工具

### collect_templates.py
卡片模板采集工具

**功能**：
- 从游戏截图中提取卡片图像
- 建立卡片模板库用于识别
- 支持交互式和自动采集

**使用方法**：
```bash
python tools/collect_templates.py
```

或从主程序菜单选择"采集卡片模板"

**详细说明**：
查看 `data/templates/README.md`

## 创建新工具

在此目录下创建新的Python脚本即可。

建议命名规范：
- `<功能>_<对象>.py`
- 例如：`analyze_recording.py`, `export_combos.py`
