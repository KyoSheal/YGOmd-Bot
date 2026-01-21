"""
游戏状态表示模块
定义游戏的各种状态信息
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class Phase(Enum):
    """游戏阶段"""
    DRAW = "抽卡阶段"
    STANDBY = "准备阶段"
    MAIN1 = "主要阶段1"
    BATTLE = "战斗阶段"
    MAIN2 = "主要阶段2"
    END = "结束阶段"
    OPPONENT = "对手回合"
    UNKNOWN = "未知"


class Zone(Enum):
    """卡片区域"""
    HAND = "手牌"
    MONSTER = "怪兽区"
    SPELL_TRAP = "魔法陷阱区"
    EXTRA = "额外卡组"
    GRAVE = "墓地"
    BANISH = "除外区"
    FIELD = "场地魔法"
    DECK = "卡组"


@dataclass
class Card:
    """卡片信息"""
    card_id: Optional[str] = None  # 卡片ID
    name: Optional[str] = None  # 卡片名称
    card_type: Optional[str] = None  # 卡片类型
    position: Optional[tuple] = None  # 屏幕位置
    zone: Optional[Zone] = None  # 所在区域
    zone_index: int = 0  # 区域内索引
    face_up: bool = True  # 是否表侧
    attack_position: bool = True  # 是否攻击表示
    can_activate: bool = False  # 是否可以发动
    effect_description: Optional[str] = None  # 效果描述
    extra_data: Dict = field(default_factory=dict)  # 额外数据


@dataclass
class GameState:
    """完整游戏状态"""
    # 基础信息
    turn_count: int = 0  # 回合数
    current_phase: Phase = Phase.UNKNOWN  # 当前阶段
    is_my_turn: bool = False  # 是否我的回合
    
    # 玩家状态
    my_lp: int = 8000  # 我的LP
    opponent_lp: int = 8000  # 对手LP
    
    # 卡片状态
    hand: List[Card] = field(default_factory=list)  # 手牌
    my_monsters: List[Card] = field(default_factory=list)  # 我的怪兽区
    my_spells: List[Card] = field(default_factory=list)  # 我的魔法陷阱区
    opponent_monsters: List[Card] = field(default_factory=list)  # 对手怪兽区
    opponent_spells: List[Card] = field(default_factory=list)  # 对手魔法陷阱区
    
    # 其他区域
    my_grave: List[Card] = field(default_factory=list)  # 我的墓地
    opponent_grave: List[Card] = field(default_factory=list)  # 对手墓地
    my_banish: List[Card] = field(default_factory=list)  # 我的除外区
    opponent_banish: List[Card] = field(default_factory=list)  # 对手除外区
    
    # 链处理
    chain_active: bool = False  # 是否正在处理连锁
    chain_links: List[Card] = field(default_factory=list)  # 连锁中的卡片
    
    # UI状态
    buttons_visible: Dict[str, bool] = field(default_factory=dict)  # 可见按钮
    dialog_open: bool = False  # 是否有对话框
    
    # 元信息
    timestamp: float = 0.0  # 时间戳
    screenshot_path: Optional[str] = None  # 截图路径
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "turn_count": self.turn_count,
            "current_phase": self.current_phase.value,
            "is_my_turn": self.is_my_turn,
            "my_lp": self.my_lp,
            "opponent_lp": self.opponent_lp,
            "hand_count": len(self.hand),
            "my_monster_count": len(self.my_monsters),
            "opponent_monster_count": len(self.opponent_monsters),
            "chain_active": self.chain_active,
            "timestamp": self.timestamp
        }
    
    def get_zone_cards(self, zone: Zone, is_my_side: bool = True) -> List[Card]:
        """获取指定区域的卡片"""
        if zone == Zone.HAND:
            return self.hand
        elif zone == Zone.MONSTER:
            return self.my_monsters if is_my_side else self.opponent_monsters
        elif zone == Zone.SPELL_TRAP:
            return self.my_spells if is_my_side else self.opponent_spells
        elif zone == Zone.GRAVE:
            return self.my_grave if is_my_side else self.opponent_grave
        elif zone == Zone.BANISH:
            return self.my_banish if is_my_side else self.opponent_banish
        return []
