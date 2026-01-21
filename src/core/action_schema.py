"""
操作模式定义
参考MAA的JSON结构设计YGO的操作描述格式
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class ActionType(Enum):
    """操作类型"""
    SUMMON = "召唤"  # 通常召唤
    SPECIAL_SUMMON = "特殊召唤"  # 特召
    ACTIVATE = "发动"  # 发动效果
    SET = "盖放"  # 盖放卡片
    ATTACK = "攻击"  # 攻击
    CHANGE_POSITION = "改变表示形式"  # 攻守切换
    END_PHASE = "结束阶段"  # 进入下一阶段
    ACTIVATE_SKILL = "发动技能"  # 发动特定技能
    CHAIN = "连锁"  # 连锁发动


class CardPosition(Enum):
    """卡片位置"""
    HAND = "手牌"
    FIELD_MONSTER = "怪兽区"
    FIELD_SPELL = "魔法陷阱区"
    GRAVEYARD = "墓地"
    BANISHED = "除外区"
    EXTRA_DECK = "额外卡组"
    DECK = "卡组"


@dataclass
class ActionStep:
    """单个操作步骤"""
    type: str  # 操作类型
    card_name: Optional[str] = None  # 卡片名称
    card_id: Optional[str] = None  # 卡片ID
    position: Optional[str] = None  # 位置 (attack/defense/face_down)
    targets: List[str] = field(default_factory=list)  # 目标卡片
    zone_index: Optional[int] = None  # 区域索引 (0-4)
    from_zone: Optional[str] = None  # 来源区域
    to_zone: Optional[str] = None  # 目标区域
    wait_time: float = 0.5  # 等待时间
    optional: bool = False  # 是否可选
    retry_times: int = 3  # 重试次数
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type,
            "card_name": self.card_name,
            "card_id": self.card_id,
            "position": self.position,
            "targets": self.targets,
            "zone_index": self.zone_index,
            "from_zone": self.from_zone,
            "to_zone": self.to_zone,
            "wait_time": self.wait_time,
            "optional": self.optional,
            "retry_times": self.retry_times
        }


@dataclass
class ComboStage:
    """Combo阶段"""
    stage_name: str  # 阶段名称
    description: str = ""  # 描述
    
    # 条件
    conditions: Dict[str, Any] = field(default_factory=dict)  # 触发条件
    min_hand_count: int = 0  # 最小手牌数
    required_cards: List[str] = field(default_factory=list)  # 需要的卡片
    forbidden_cards: List[str] = field(default_factory=list)  # 禁止的卡片
    
    # 操作序列
    actions: List[ActionStep] = field(default_factory=list)  # 操作列表
    
    # 控制
    retry_times: int = 3  # 重试次数
    timeout: float = 30.0  # 超时时间
    skip_on_failure: bool = False  # 失败时是否跳过
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "stage_name": self.stage_name,
            "description": self.description,
            "conditions": self.conditions,
            "min_hand_count": self.min_hand_count,
            "required_cards": self.required_cards,
            "forbidden_cards": self.forbidden_cards,
            "actions": [action.to_dict() for action in self.actions],
            "retry_times": self.retry_times,
            "timeout": self.timeout,
            "skip_on_failure": self.skip_on_failure
        }


@dataclass
class ComboStrategy:
    """完整Combo策略（类似MAA的作业文件）"""
    combo_name: str  # Combo名称
    deck_type: str  # 卡组类型
    author: str = ""  # 作者
    version: str = "1.0.0"  # 版本
    minimum_required: str = "v0.1.0"  # 最低bot版本要求
    
    # 文档信息
    doc: Dict[str, str] = field(default_factory=dict)  # 文档
    
    # 核心卡片
    core_cards: List[Dict[str, Any]] = field(default_factory=list)  # 核心卡片列表
    blacklist: List[str] = field(default_factory=list)  # 黑名单卡片
    
    # 阶段
    stages: List[ComboStage] = field(default_factory=list)  # Combo阶段列表
    
    # 元数据
    win_rate: float = 0.0  # 胜率
    avg_turns: int = 0  # 平均回合数
    difficulty: str = "medium"  # 难度 (easy/medium/hard)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "combo_name": self.combo_name,
            "deck_type": self.deck_type,
            "author": self.author,
            "version": self.version,
            "minimum_required": self.minimum_required,
            "doc": self.doc,
            "core_cards": self.core_cards,
            "blacklist": self.blacklist,
            "stages": [stage.to_dict() for stage in self.stages],
            "win_rate": self.win_rate,
            "avg_turns": self.avg_turns,
            "difficulty": self.difficulty
        }
    
    def save_to_file(self, filepath: str):
        """保存到JSON文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_from_file(filepath: str) -> 'ComboStrategy':
        """从JSON文件加载"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        strategy = ComboStrategy(
            combo_name=data["combo_name"],
            deck_type=data["deck_type"],
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            minimum_required=data.get("minimum_required", "v0.1.0"),
            doc=data.get("doc", {}),
            core_cards=data.get("core_cards", []),
            blacklist=data.get("blacklist", []),
            win_rate=data.get("win_rate", 0.0),
            avg_turns=data.get("avg_turns", 0),
            difficulty=data.get("difficulty", "medium")
        )
        
        # 加载阶段
        for stage_data in data.get("stages", []):
            stage = ComboStage(
                stage_name=stage_data["stage_name"],
                description=stage_data.get("description", ""),
                conditions=stage_data.get("conditions", {}),
                min_hand_count=stage_data.get("min_hand_count", 0),
                required_cards=stage_data.get("required_cards", []),
                forbidden_cards=stage_data.get("forbidden_cards", []),
                retry_times=stage_data.get("retry_times", 3),
                timeout=stage_data.get("timeout", 30.0),
                skip_on_failure=stage_data.get("skip_on_failure", False)
            )
            
            # 加载操作
            for action_data in stage_data.get("actions", []):
                action = ActionStep(
                    type=action_data["type"],
                    card_name=action_data.get("card_name"),
                    card_id=action_data.get("card_id"),
                    position=action_data.get("position"),
                    targets=action_data.get("targets", []),
                    zone_index=action_data.get("zone_index"),
                    from_zone=action_data.get("from_zone"),
                    to_zone=action_data.get("to_zone"),
                    wait_time=action_data.get("wait_time", 0.5),
                    optional=action_data.get("optional", False),
                    retry_times=action_data.get("retry_times", 3)
                )
                stage.actions.append(action)
            
            strategy.stages.append(stage)
        
        return strategy


# 示例：创建一个简单的combo策略
def create_example_strategy() -> ComboStrategy:
    """创建示例策略"""
    strategy = ComboStrategy(
        combo_name="青眼白龙基础展开",
        deck_type="青眼",
        author="YGO Bot",
        version="1.0.0",
        doc={
            "title": "青眼白龙基础展开combo",
            "description": "使用贤者之石和旋律快速召唤青眼白龙"
        },
        core_cards=[
            {"name": "青眼白龙", "copies": 3},
            {"name": "贤者之石", "copies": 3},
            {"name": "青眼的白石", "copies": 3}
        ]
    )
    
    # 第一阶段：召唤准备
    stage1 = ComboStage(
        stage_name="召唤准备",
        description="使用贤者之石检索青眼白龙",
        required_cards=["贤者之石"],
        actions=[
            ActionStep(
                type=ActionType.ACTIVATE.value,
                card_name="贤者之石",
                from_zone=CardPosition.HAND.value
            ),
            ActionStep(
                type=ActionType.ACTIVATE.value,
                card_name="贤者之石",
                targets=["青眼白龙"]
            )
        ]
    )
    
    # 第二阶段：召唤青眼
    stage2 = ComboStage(
        stage_name="召唤青眼白龙",
        description="通常召唤青眼白龙",
        required_cards=["青眼白龙"],
        actions=[
            ActionStep(
                type=ActionType.SUMMON.value,
                card_name="青眼白龙",
                position="attack",
                zone_index=2  # 中间位置
            )
        ]
    )
    
    strategy.stages.extend([stage1, stage2])
    
    return strategy


if __name__ == "__main__":
    # 创建并保存示例策略
    strategy = create_example_strategy()
    strategy.save_to_file("data/combos/example_blueyes.json")
    print("示例策略已创建并保存")
    
    # 加载并验证
    loaded = ComboStrategy.load_from_file("data/combos/example_blueyes.json")
    print(f"加载的策略: {loaded.combo_name}")
    print(f"包含 {len(loaded.stages)} 个阶段")
