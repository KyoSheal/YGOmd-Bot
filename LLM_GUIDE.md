# LLM模型选择和配置指南

## 你的本地模型

✅ **qwen2.5:7b** - 推荐用于游戏决策
✅ **deepseek-r1:8b** - 推荐用于复杂推理

## 模型能力评估

### qwen2.5:7b (推荐主力模型)
- **用途**: 游戏状态分析、Combo建议、卡片效果理解
- **优势**: 中文支持优秀、推理速度快、上下文理解好
- **适合场景**:
  - ✅ 分析手牌组合
  - ✅ 建议下一步操作  
  - ✅ 识别combo模式
  - ✅ 基础卡片效果解析

### deepseek-r1:8b (复杂推理)
- **用途**: 复杂决策链、连锁时点判断
- **优势**: 推理能力强、逻辑严密
- **适合场景**:
  - ✅ 多步展开规划
  - ✅ 对手意图预测
  - ✅ 最优解计算
  - ✅ 复杂连锁处理

## 使用建议

### 场景1：Solo模式自动化（简单）
**推荐**: qwen2.5:7b 足够

Solo模式对手AI简单，主要是：
- 识别手牌中可以打出的combo
- 按固定套路展开
- 简单的战斗决策

**7B模型完全足够！**

### 场景2：复杂Combo展开（中等）
**推荐**: qwen2.5:7b

对于大部分展开：
- 电子龙、青眼、剑斗兽等常规卡组
- 2-3步的连续操作
- 检索+召唤的基本combo

**7B模型完全足够！**

### 场景3：高级决策（复杂）
**推荐**: deepseek-r1:8b 或两者结合

需要用到推理模型的场景：
- 🎯 对手盖卡判断（是坑还是资源）
- 🎯 多种展开路线的选择（需要计算最优解）
- 🎯 复杂连锁时点（CL1/CL2/CL3）
- 🎯 资源管理（什么时候用手坑）

**策略**：
```python
# 简单决策用qwen2.5
if scenario == "simple_combo":
    model = "qwen2.5:7b"

# 复杂推理用deepseek-r1  
elif scenario == "complex_decision":
    model = "deepseek-r1:8b"
```

## 配置方法

### 方法1：在配置文件中设置

编辑 `config/settings.yaml`:

```yaml
decision:
  strategy: "hybrid"  # learned, rule_based, hybrid
  use_llm: true
  llm_model: "qwen2.5:7b"  # 主模型
  llm_fallback: "deepseek-r1:8b"  # 复杂场景备用
  confidence_threshold: 0.6
```

### 方法2：在代码中切换

```python
from src.learning.llm_engine import LLMDecisionEngine

# 快速决策
quick_engine = LLMDecisionEngine(model_name="qwen2.5:7b")

# 深度推理
reasoning_engine = LLMDecisionEngine(model_name="deepseek-r1:8b")
```

## 性能对比

| 模型 | 推理速度 | 准确性 | 资源占用 | 适用场景 |
|------|---------|--------|----------|---------|
| qwen2.5:7b | ⚡⚡⚡ 快 | ✅ 高 | 💾 中等 | 日常使用 |
| deepseek-r1:8b | ⚡⚡ 中 | ✅✅ 很高 | 💾💾 较高 | 复杂决策 |

## 实战建议

### 初期（学习阶段）
使用 **qwen2.5:7b** 即可：
1. 录制你的操作
2. 让LLM分析combo模式
3. 提取策略到JSON

### 中期（自动化Solo）
继续使用 **qwen2.5:7b**：
- Solo模式对手弱
- 主要是按套路展开
- 速度比准确性更重要

### 后期（PVP/高难度）
结合使用两个模型：
- 常规操作：qwen2.5:7b（快）
- 关键决策：deepseek-r1:8b（准）

## 更强模型必要性？

**不需要！** 除非：
- ❌ 你要打世界冠军级别的PVP
- ❌ 需要完美的连锁时点判断
- ❌ 需要实时计算所有可能性

对于：
- ✅ Solo模式挂机
- ✅ 日常Rank对战
- ✅ 学习combo操作

**你的7-8B模型已经绰绰有余！**

## 测试LLM

运行以下命令测试：

```bash
# 测试qwen2.5
ollama run qwen2.5:7b "分析以下游戏王手牌组合：灰流丽、增殖的G、无限泡影。应该如何使用？"

# 测试deepseek-r1  
ollama run deepseek-r1:8b "在游戏王对局中，对手盖了3张后场。我手里有闪电风暴。应该什么时候发动？请详细推理。"
```

## 最终推荐

**默认配置**：
```yaml
llm_model: "qwen2.5:7b"
```

**原因**：
1. 速度快（实时决策重要）
2. 中文理解好（卡片效果是中文）
3. 资源占用低（可以持续运行）
4. 准确性足够（Solo模式完全够用）

需要时手动切换到deepseek-r1即可！

---

**总结：你的配置完美！直接用qwen2.5:7b开始就行🎉**
