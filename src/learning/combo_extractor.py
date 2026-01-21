"""
Combo模式提取器
从录制的操作中提取combo模式
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from loguru import logger
from ..core.action_schema import ComboStrategy, ComboStage, ActionStep


class ComboExtractor:
    """Combo模式提取器"""
    
    def __init__(self, llm_engine=None):
        """
        初始化提取器
        
        Args:
            llm_engine: LLM引擎（可选，用于智能分析）
        """
        self.llm_engine = llm_engine
    
    def extract_from_recording(self, recording_file: str, 
                              combo_name: Optional[str] = None,
                              deck_type: Optional[str] = None) -> Optional[ComboStrategy]:
        """
        从录制文件提取combo策略
        
        Args:
            recording_file: 录制文件路径
            combo_name: combo名称（如果不提供，会自动生成）
            deck_type: 卡组类型
            
        Returns:
            提取的combo策略
        """
        logger.info(f"从录制文件提取combo: {recording_file}")
        
        # 加载录制数据
        with open(recording_file, 'r', encoding='utf-8') as f:
            recording = json.load(f)
        
        # 分析操作序列
        actions = recording.get('actions', [])
        game_states = recording.get('game_states', [])
        
        if not actions:
            logger.warning("录制中没有操作")
            return None
        
        # 使用LLM识别模式（如果可用）
        if self.llm_engine:
            pattern = self._llm_pattern_detection(actions, game_states)
            if pattern:
                combo_name = combo_name or pattern.get('combo_name', 'Unknown Combo')
                deck_type = deck_type or pattern.get('combo_type', 'Unknown')
        
        # 如果没有提供名称，使用默认
        combo_name = combo_name or f"录制_{recording.get('session_name', 'unknown')}"
        deck_type = deck_type or "未分类"
        
        # 创建combo策略
        strategy = ComboStrategy(
            combo_name=combo_name,
            deck_type=deck_type,
            author="Auto-Extracted"
        )
        
        # 提取阶段
        stages = self._extract_stages(actions, game_states)
        strategy.stages = stages
        
        # 提取核心卡片
        core_cards = self._extract_core_cards(actions, game_states)
        strategy.core_cards = core_cards
        
        logger.info(f"提取完成: {combo_name}, {len(stages)} 个阶段, {len(core_cards)} 张核心卡片")
        
        return strategy
    
    def _llm_pattern_detection(self, actions: List[Dict], 
                               game_states: List[Dict]) -> Optional[Dict]:
        """使用LLM检测combo模式"""
        try:
            # 格式化操作序列
            action_seq = []
            for action in actions[:50]:  # 限制长度
                if action['type'] in ['mouse_click', 'key_press']:
                    action_seq.append(action)
            
            # 调用LLM分析
            pattern = self.llm_engine.detect_combo_pattern(action_seq)
            return pattern
            
        except Exception as e:
            logger.error(f"LLM模式检测失败: {e}")
            return None
    
    def _extract_stages(self, actions: List[Dict], 
                       game_states: List[Dict]) -> List[ComboStage]:
        """提取操作阶段"""
        stages = []
        
        # 简单的阶段划分：按时间间隔
        current_stage_actions = []
        last_timestamp = 0
        stage_count = 1
        
        for action in actions:
            timestamp = action.get('timestamp', 0)
            
            # 如果时间间隔超过2秒，认为是新阶段
            if timestamp - last_timestamp > 2.0 and current_stage_actions:
                # 创建阶段
                stage = ComboStage(
                    stage_name=f"阶段{stage_count}",
                    description=f"自动提取的阶段{stage_count}",
                    actions=self._convert_to_action_steps(current_stage_actions)
                )
                stages.append(stage)
                
                # 重置
                current_stage_actions = []
                stage_count += 1
            
            current_stage_actions.append(action)
            last_timestamp = timestamp
        
        # 添加最后一个阶段
        if current_stage_actions:
            stage = ComboStage(
                stage_name=f"阶段{stage_count}",
                description=f"自动提取的阶段{stage_count}",
                actions=self._convert_to_action_steps(current_stage_actions)
            )
            stages.append(stage)
        
        return stages
    
    def _convert_to_action_steps(self, raw_actions: List[Dict]) -> List[ActionStep]:
        """将原始操作转换为ActionStep"""
        action_steps = []
        
        for action in raw_actions:
            action_type = action.get('type')
            
            # 根据操作类型转换
            if action_type == 'mouse_click':
                data = action.get('data', {})
                step = ActionStep(
                    type="CLICK",
                    position=f"({data.get('x')}, {data.get('y')})",
                    wait_time=0.5
                )
                action_steps.append(step)
            
            elif action_type == 'key_press':
                data = action.get('data', {})
                step = ActionStep(
                    type="KEY_PRESS",
                    card_name=data.get('key', ''),
                    wait_time=0.2
                )
                action_steps.append(step)
        
        return action_steps
    
    def _extract_core_cards(self, actions: List[Dict], 
                           game_states: List[Dict]) -> List[Dict]:
        """提取核心卡片"""
        # 统计游戏状态中出现的卡片
        card_counter = Counter()
        
        for state in game_states:
            state_data = state.get('state', {})
            # TODO: 从游戏状态中提取卡片名称
            # 这需要实际的游戏状态记录
        
        # 返回最常见的卡片
        core_cards = []
        for card_name, count in card_counter.most_common(10):
            core_cards.append({
                'name': card_name,
                'copies': min(count, 3)  # 最多3张
            })
        
        return core_cards
    
    def analyze_multiple_recordings(self, recording_files: List[str]) -> Dict:
        """
        分析多个录制文件，找出共同模式
        
        Args:
            recording_files: 录制文件列表
            
        Returns:
            分析结果
        """
        logger.info(f"分析 {len(recording_files)} 个录制文件...")
        
        all_combos = []
        for file_path in recording_files:
            try:
                combo = self.extract_from_recording(file_path)
                if combo:
                    all_combos.append(combo)
            except Exception as e:
                logger.error(f"处理 {file_path} 失败: {e}")
        
        if not all_combos:
            return {'error': '没有成功提取任何combo'}
        
        # 找出共同模式
        common_cards = self._find_common_cards(all_combos)
        common_sequences = self._find_common_sequences(all_combos)
        
        return {
            'combo_count': len(all_combos),
            'common_cards': common_cards,
            'common_sequences': common_sequences,
            'deck_types': [c.deck_type for c in all_combos]
        }
    
    def _find_common_cards(self, combos: List[ComboStrategy]) -> List[str]:
        """找出所有combo中的共同卡片"""
        if not combos:
            return []
        
        # 获取所有combo的核心卡片
        card_sets = []
        for combo in combos:
            cards = set(c['name'] for c in combo.core_cards)
            card_sets.append(cards)
        
        # 找交集
        common = card_sets[0]
        for card_set in card_sets[1:]:
            common &= card_set
        
        return list(common)
    
    def _find_common_sequences(self, combos: List[ComboStrategy]) -> List[List[str]]:
        """找出共同的操作序列"""
        # TODO: 实现序列模式匹配算法
        return []
    
    def suggest_improvements(self, strategy: ComboStrategy) -> List[str]:
        """
        建议combo改进
        
        Args:
            strategy: combo策略
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 检查阶段数量
        if len(strategy.stages) > 5:
            suggestions.append("阶段过多，考虑合并相关阶段")
        
        # 检查核心卡片
        if len(strategy.core_cards) < 3:
            suggestions.append("核心卡片较少，可能需要添加更多关键卡片")
        
        # 检查每个阶段的操作数
        for stage in strategy.stages:
            if len(stage.actions) > 10:
                suggestions.append(f"{stage.stage_name} 操作过多，考虑简化")
        
        return suggestions


# 测试代码
if __name__ == "__main__":
    logger.info("测试Combo提取器...")
    
    extractor = ComboExtractor()
    
    # 测试（需要实际的录制文件）
    # combo = extractor.extract_from_recording("data/recordings/test.json")
    # if combo:
    #     combo.save_to_file("data/combos/extracted_combo.json")
    #     logger.info("Combo已保存")
