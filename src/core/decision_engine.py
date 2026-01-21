"""
决策引擎主控
整合规则引擎和LLM引擎，做出智能决策
"""
from typing import Optional, Dict, List, Any
from loguru import logger
from ..core.game_state import GameState
from ..core.action_schema import ComboStrategy, ActionStep
from ..learning.llm_engine import LLMDecisionEngine
from pathlib import Path
import json


class DecisionEngine:
    """决策引擎 - 双引擎架构"""
    
    def __init__(self, combo_dir: str = "data/combos", 
                 use_llm: bool = True,
                 llm_model: str = "qwen2.5:latest"):
        """
        初始化决策引擎
        
        Args:
            combo_dir: combo策略文件目录
            use_llm: 是否启用LLM引擎
            llm_model: LLM模型名称
        """
        self.combo_dir = Path(combo_dir)
        self.combo_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载所有combo策略
        self.combo_strategies = self._load_all_combos()
        
        # LLM引擎
        self.llm_engine = None
        if use_llm:
            try:
                self.llm_engine = LLMDecisionEngine(model_name=llm_model)
                logger.info("LLM决策引擎已启用")
            except Exception as e:
                logger.warning(f"LLM引擎初始化失败: {e}，将只使用规则引擎")
        
        logger.info(f"决策引擎初始化完成，已加载 {len(self.combo_strategies)} 个combo策略")
    
    def decide_next_action(self, game_state: GameState, 
                          deck_type: Optional[str] = None) -> Optional[ActionStep]:
        """
        决定下一步操作
        
        Args:
            game_state: 当前游戏状态
            deck_type: 卡组类型（可选）
            
        Returns:
            推荐的操作，如果没有则返回None
        """
        logger.info("开始决策...")
        
        # 第一步：尝试规则引擎（已知场景）
        rule_action = self._rule_based_decision(game_state, deck_type)
        
        if rule_action and rule_action.get('confidence', 0) > 0.8:
            # 高置信度的规则匹配，直接使用
            logger.info(f"规则引擎决策: {rule_action['action'].type} "
                       f"(置信度: {rule_action['confidence']:.2f})")
            return rule_action['action']
        
        # 第二步：尝试LLM引擎（未知场景或低置信度）
        if self.llm_engine:
            llm_action = self._llm_based_decision(game_state, deck_type)
            
            if llm_action:
                logger.info(f"LLM引擎决策: {llm_action['action'].type}")
                
                # 比较两种结果，选择更好的
                if rule_action:
                    return self._choose_better_action(rule_action, llm_action)
                else:
                    return llm_action['action']
        
        # 如果都没有，返回规则引擎的结果（即使置信度低）
        if rule_action:
            return rule_action['action']
        
        logger.warning("无法做出决策")
        return None
    
    def _rule_based_decision(self, game_state: GameState, 
                            deck_type: Optional[str]) -> Optional[Dict]:
        """规则引擎决策"""
        # 筛选适用的combo策略
        applicable_combos = []
        
        for combo in self.combo_strategies:
            # 检查卡组类型匹配
            if deck_type and combo.deck_type != deck_type:
                continue
            
            # 检查是否有匹配的阶段
            for stage in combo.stages:
                # 检查条件是否满足
                if self._check_stage_conditions(stage, game_state):
                    applicable_combos.append({
                        'combo': combo,
                        'stage': stage,
                        'confidence': self._calculate_confidence(stage, game_state)
                    })
        
        if not applicable_combos:
            return None
        
        # 选择置信度最高的
        best_combo = max(applicable_combos, key=lambda x: x['confidence'])
        
        # 返回该阶段的第一个操作
        if best_combo['stage'].actions:
            return {
                'action': best_combo['stage'].actions[0],
                'confidence': best_combo['confidence'],
                'source': 'rule_engine',
                'combo_name': best_combo['combo'].combo_name,
                'stage_name': best_combo['stage'].stage_name
            }
        
        return None
    
    def _llm_based_decision(self, game_state: GameState, 
                           deck_type: Optional[str]) -> Optional[Dict]:
        """LLM引擎决策"""
        try:
            # 获取手牌名称
            hand_cards = [c.name for c in game_state.hand if c.name]
            
            if not hand_cards:
                return None
            
            # 让LLM建议combo
            suggestion = self.llm_engine.suggest_combo(
                hand_cards=hand_cards,
                extra_deck=[],  # TODO: 添加额外卡组信息
                deck_type=deck_type or "未知"
            )
            
            if not suggestion or 'steps' not in suggestion:
                return None
            
            # 解析第一步操作
            first_step = suggestion['steps'][0] if suggestion['steps'] else None
            
            if not first_step:
                return None
            
            # 将LLM建议转换为ActionStep
            action = self._parse_llm_suggestion(first_step)
            
            return {
                'action': action,
                'confidence': suggestion.get('success_rate', 0.5),
                'source': 'llm_engine',
                'explanation': suggestion.get('explanation', '')
            }
            
        except Exception as e:
            logger.error(f"LLM决策失败: {e}")
            return None
    
    def _check_stage_conditions(self, stage, game_state: GameState) -> bool:
        """检查阶段条件是否满足"""
        # 检查手牌数量
        if len(game_state.hand) < stage.min_hand_count:
            return False
        
        # 检查必需卡片
        hand_names = [c.name for c in game_state.hand if c.name]
        for required_card in stage.required_cards:
            if required_card not in hand_names:
                return False
        
        # 检查禁止卡片
        for forbidden_card in stage.forbidden_cards:
            if forbidden_card in hand_names:
                return False
        
        # 检查其他条件
        conditions = stage.conditions
        if conditions:
            # TODO: 实现更多条件检查
            pass
        
        return True
    
    def _calculate_confidence(self, stage, game_state: GameState) -> float:
        """计算匹配置信度"""
        confidence = 0.5  # 基础置信度
        
        # 手牌匹配度
        hand_names = set(c.name for c in game_state.hand if c.name)
        required_cards = set(stage.required_cards)
        
        if required_cards:
            match_ratio = len(hand_names & required_cards) / len(required_cards)
            confidence += match_ratio * 0.3
        
        # 阶段匹配度
        if game_state.is_my_turn:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _choose_better_action(self, rule_result: Dict, 
                             llm_result: Dict) -> ActionStep:
        """比较并选择更好的操作"""
        # 简单比较置信度
        if rule_result['confidence'] > llm_result['confidence']:
            logger.info(f"选择规则引擎决策 (置信度: {rule_result['confidence']:.2f})")
            return rule_result['action']
        else:
            logger.info(f"选择LLM引擎决策 (置信度: {llm_result['confidence']:.2f})")
            return llm_result['action']
    
    def _parse_llm_suggestion(self, step_text: str) -> ActionStep:
        """解析LLM建议为ActionStep"""
        # 简单解析（需要根据实际LLM输出调整）
        action = ActionStep(
            type="ACTIVATE",  # 默认类型
            card_name=step_text,  # 简化处理
        )
        return action
    
    def _load_all_combos(self) -> List[ComboStrategy]:
        """加载所有combo策略"""
        combos = []
        
        if not self.combo_dir.exists():
            return combos
        
        for combo_file in self.combo_dir.glob("*.json"):
            try:
                strategy = ComboStrategy.load_from_file(str(combo_file))
                combos.append(strategy)
                logger.debug(f"加载combo: {strategy.combo_name}")
            except Exception as e:
                logger.error(f"加载combo失败 {combo_file}: {e}")
        
        return combos
    
    def add_combo_strategy(self, strategy: ComboStrategy):
        """添加新的combo策略"""
        # 保存到文件
        filename = f"{strategy.deck_type}_{strategy.combo_name}.json"
        filepath = self.combo_dir / filename
        strategy.save_to_file(str(filepath))
        
        # 添加到内存
        self.combo_strategies.append(strategy)
        
        logger.info(f"添加combo策略: {strategy.combo_name}")
    
    def explain_decision(self, action: ActionStep, game_state: GameState) -> str:
        """解释决策原因"""
        if not self.llm_engine:
            return "无法解释（LLM未启用）"
        
        # 格式化游戏状态
        situation = f"回合{game_state.turn_count}，{game_state.current_phase.value}"
        if game_state.hand:
            situation += f"，手牌：{[c.name for c in game_state.hand if c.name]}"
        
        # 让LLM解释
        explanation = self.llm_engine.explain_decision(
            action=f"{action.type}: {action.card_name}",
            game_situation=situation
        )
        
        return explanation


# 测试代码
if __name__ == "__main__":
    logger.info("测试决策引擎...")
    
    engine = DecisionEngine(use_llm=False)  # 先不使用LLM测试
    
    # 创建测试状态
    from ..core.game_state import Card, Zone
    state = GameState()
    state.turn_count = 1
    state.is_my_turn = True
    
    # 添加手牌
    state.hand = [
        Card(name="灰流丽", zone=Zone.HAND),
        Card(name="增殖的G", zone=Zone.HAND),
    ]
    
    # 决策
    action = engine.decide_next_action(state)
    if action:
        logger.info(f"决策结果: {action.type} - {action.card_name}")
    else:
        logger.info("无决策")
