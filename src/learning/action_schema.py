"""
操作数据结构定义 - Action Schema
定义游戏操作的数据结构
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ActionType(Enum):
    """操作类型"""
    USE_CARD = "use_card"  # 使用卡片
    ACTIVATE_EFFECT = "activate_effect"  # 发动效果
    NORMAL_SUMMON = "normal_summon"  # 通常召唤
    SPECIAL_SUMMON = "special_summon"  # 特殊召唤
    SET_CARD = "set_card"  # 盖放卡片
    CHAIN = "chain"  # 连锁
    DRAW = "draw"  # 抽卡
    SEARCH = "search"  # 检索
    DESTROY = "destroy"  # 破坏
    NEGATE = "negate"  # 无效
    ATTACK = "attack"  # 攻击
    CHANGE_POSITION = "change_position"  # 改变表示形式
    END_PHASE = "end_phase"  # 结束阶段


class Zone(Enum):
    """区域"""
    HAND = "hand"  # 手牌
    FIELD_MONSTER = "field_monster"  # 怪兽区
    FIELD_SPELL = "field_spell"  # 魔陷区
    GRAVEYARD = "graveyard"  # 墓地
    BANISHED = "banished"  # 除外区
    EXTRA_DECK = "extra_deck"  # 额外卡组
    DECK = "deck"  # 卡组
    UNKNOWN = "unknown"  # 未知


class GamePhase(Enum):
    """游戏阶段"""
    DRAW = "draw_phase"
    STANDBY = "standby_phase"
    MAIN1 = "main_phase_1"
    BATTLE = "battle_phase"
    MAIN2 = "main_phase_2"
    END = "end_phase"
    UNKNOWN = "unknown"


@dataclass
class GameAction:
    """游戏操作"""
    # 基本信息
    timestamp: float  # 时间戳
    action_type: ActionType  # 操作类型
    card_name: str  # 卡片名称
    
    # 区域信息
    source_zone: Zone = Zone.UNKNOWN  # 来源区域
    target_zone: Optional[Zone] = None  # 目标区域
    
    # 效果信息
    effect_description: str = ""  # 效果描述
    targets: List[str] = field(default_factory=list)  # 目标卡片列表
    
    # 游戏状态
    game_phase: GamePhase = GamePhase.UNKNOWN  # 游戏阶段
    turn_number: int = 1  # 回合数
    is_my_turn: bool = True  # 是否我的回合
    
    # OCR信息
    ocr_confidence: float = 0.0  # OCR置信度
    screenshot_path: Optional[str] = None  # 截图路径
    
    # 额外信息
    notes: str = ""  # 备注
    verified: bool = False  # 是否已验证
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换枚举为字符串
        data['action_type'] = self.action_type.value
        data['source_zone'] = self.source_zone.value
        if self.target_zone:
            data['target_zone'] = self.target_zone.value
        data['game_phase'] = self.game_phase.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameAction':
        """从字典创建"""
        # 转换字符串为枚举
        if 'action_type' in data and isinstance(data['action_type'], str):
            data['action_type'] = ActionType(data['action_type'])
        if 'source_zone' in data and isinstance(data['source_zone'], str):
            data['source_zone'] = Zone(data['source_zone'])
        if 'target_zone' in data and isinstance(data['target_zone'], str):
            data['target_zone'] = Zone(data['target_zone'])
        if 'game_phase' in data and isinstance(data['game_phase'], str):
            data['game_phase'] = GamePhase(data['game_phase'])
        return cls(**data)


@dataclass
class ActionSequence:
    """操作序列（一次完整的展开/combo）"""
    sequence_id: str  # 序列ID
    start_time: float  # 开始时间
    end_time: float  # 结束时间
    actions: List[GameAction] = field(default_factory=list)  # 操作列表
    
    # 分析结果
    combo_name: str = ""  # Combo名称
    combo_type: str = ""  # Combo类型
    success: bool = True  # 是否成功
    final_board: str = ""  # 最终场面描述
    
    # LLM分析
    llm_analysis: Dict[str, Any] = field(default_factory=dict)  # LLM分析结果
    learned_patterns: List[str] = field(default_factory=list)  # 学习到的模式
    
    def add_action(self, action: GameAction):
        """添加操作"""
        self.actions.append(action)
        self.end_time = action.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'sequence_id': self.sequence_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.end_time - self.start_time,
            'actions': [action.to_dict() for action in self.actions],
            'combo_name': self.combo_name,
            'combo_type': self.combo_type,
            'success': self.success,
            'final_board': self.final_board,
            'llm_analysis': self.llm_analysis,
            'learned_patterns': self.learned_patterns
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionSequence':
        """从字典创建"""
        actions = [GameAction.from_dict(a) for a in data.get('actions', [])]
        return cls(
            sequence_id=data['sequence_id'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            actions=actions,
            combo_name=data.get('combo_name', ''),
            combo_type=data.get('combo_type', ''),
            success=data.get('success', True),
            final_board=data.get('final_board', ''),
            llm_analysis=data.get('llm_analysis', {}),
            learned_patterns=data.get('learned_patterns', [])
        )


@dataclass
class GameReplay:
    """完整的游戏录像"""
    replay_id: str  # 录像ID
    created_at: str  # 创建时间
    deck_used: str  # 使用的卡组
    opponent_deck: str = "未知"  # 对手卡组
    
    # 对局信息
    result: str = "未知"  # 对局结果（胜利/失败/平局）
    total_turns: int = 0  # 总回合数
    
    # 操作序列
    sequences: List[ActionSequence] = field(default_factory=list)  # 所有操作序列
    
    # 统计
    total_actions: int = 0  # 总操作数
    
    # 元数据
    notes: str = ""  # 备注
    tags: List[str] = field(default_factory=list)  # 标签
    
    def add_sequence(self, sequence: ActionSequence):
        """添加操作序列"""
        self.sequences.append(sequence)
        self.total_actions += len(sequence.actions)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'replay_id': self.replay_id,
            'created_at': self.created_at,
            'deck_used': self.deck_used,
            'opponent_deck': self.opponent_deck,
            'result': self.result,
            'total_turns': self.total_turns,
            'total_actions': self.total_actions,
            'sequences': [seq.to_dict() for seq in self.sequences],
            'notes': self.notes,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameReplay':
        """从字典创建"""
        sequences = [ActionSequence.from_dict(s) for s in data.get('sequences', [])]
        return cls(
            replay_id=data['replay_id'],
            created_at=data['created_at'],
            deck_used=data['deck_used'],
            opponent_deck=data.get('opponent_deck', '未知'),
            result=data.get('result', '未知'),
            total_turns=data.get('total_turns', 0),
            sequences=sequences,
            total_actions=data.get('total_actions', 0),
            notes=data.get('notes', ''),
            tags=data.get('tags', [])
        )


# 测试代码
if __name__ == "__main__":
    import time
    
    # 创建示例操作
    action1 = GameAction(
        timestamp=time.time(),
        action_type=ActionType.NORMAL_SUMMON,
        card_name="骸骨恶魔",
        source_zone=Zone.HAND,
        target_zone=Zone.FIELD_MONSTER,
        game_phase=GamePhase.MAIN1,
        turn_number=1
    )
    
    action2 = GameAction(
        timestamp=time.time() + 1,
        action_type=ActionType.ACTIVATE_EFFECT,
        card_name="骸骨恶魔",
        source_zone=Zone.FIELD_MONSTER,
        effect_description="检索暗红恶魔卡",
        game_phase=GamePhase.MAIN1,
        turn_number=1
    )
    
    # 创建操作序列
    sequence = ActionSequence(
        sequence_id="seq_001",
        start_time=action1.timestamp,
        end_time=action2.timestamp
    )
    sequence.add_action(action1)
    sequence.add_action(action2)
    sequence.combo_name = "骸骨恶魔检索"
    
    # 转换为字典
    seq_dict = sequence.to_dict()
    print("操作序列:")
    print(f"  ID: {seq_dict['sequence_id']}")
    print(f"  持续时间: {seq_dict['duration']:.2f}秒")
    print(f"  操作数: {len(seq_dict['actions'])}")
    print(f"  Combo: {seq_dict['combo_name']}")
