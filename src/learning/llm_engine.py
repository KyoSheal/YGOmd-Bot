"""
LLM决策引擎
使用本地LLM进行智能决策和卡片效果理解
"""
import json
import requests
from typing import List, Dict, Optional, Any, Tuple
from loguru import logger
from ..core.game_state import GameState, Card


class LLMDecisionEngine:
    """LLM决策引擎"""
    
    def __init__(self, model_name: str = "qwen2.5:7b", api_url: str = "http://localhost:11434"):
        """
        初始化LLM引擎
        
        Args:
            model_name: 使用的模型名称（支持Ollama本地模型）
            api_url: Ollama API地址
        """
        self.model_name = model_name
        self.api_url = api_url
        self.conversation_history = []
        
        logger.info(f"初始化LLM引擎: {model_name} @ {api_url}")
        
    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        调用本地LLM
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            
        Returns:
            LLM回复
        """
        try:
            url = f"{self.api_url}/api/generate"
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": False
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ""
    
    def analyze_game_state(self, state: GameState) -> Dict[str, Any]:
        """
        分析游戏状态
        
        Args:
            state: 游戏状态对象
            
        Returns:
            分析结果
        """
        # 构建游戏状态描述
        state_desc = self._format_game_state(state)
        
        system_prompt = """你是一个游戏王Master Duel的专家AI助手。
你的任务是分析当前游戏状态，识别展开机会和最优操作。
请用简洁的JSON格式回复，包含以下字段：
- situation: 当前局势分析
- opportunities: 可能的展开机会列表
- threats: 对手的威胁
- recommended_action: 推荐的下一步操作
"""
        
        prompt = f"""请分析以下游戏王对局状态：

{state_desc}

请提供你的分析和建议。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            # 尝试解析JSON
            analysis = json.loads(response)
        except:
            # 如果不是JSON，返回纯文本
            analysis = {"raw_response": response}
        
        return analysis
    
    def understand_card_effect(self, card_text: str, card_name: str = "") -> Dict[str, Any]:
        """
        理解卡片效果
        
        Args:
            card_text: 卡片效果文本
            card_name: 卡片名称
            
        Returns:
            效果分析
        """
        system_prompt = """你是游戏王卡片效果专家。
分析卡片效果，提取关键信息：
- effect_type: 效果类型（发动效果/触发效果/永续效果等）
- activation_condition: 发动条件
- cost: 代价
- effect: 效果内容
- targets: 目标要求
- timing: 时点要求
- can_chain: 是否可以连锁
"""
        
        prompt = f"""卡片名称：{card_name}
卡片效果文本：
{card_text}

请解析这张卡片的效果。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            effect_analysis = json.loads(response)
        except:
            effect_analysis = {"raw_response": response}
        
        return effect_analysis
    
    def suggest_combo(self, hand_cards: List[str], extra_deck: List[str], 
                     deck_type: str = "未知") -> Dict[str, Any]:
        """
        建议combo路线
        
        Args:
            hand_cards: 手牌列表
            extra_deck: 额外卡组列表
            deck_type: 卡组类型
            
        Returns:
            combo建议
        """
        system_prompt = f"""你是游戏王{deck_type}卡组的专家。
根据手牌和额外卡组，建议最优的combo路线。
返回JSON格式：
- combo_name: combo名称
- steps: 操作步骤列表
- expected_result: 预期结果
- success_rate: 估计成功率
- explanation: 解释为什么这样操作
"""
        
        prompt = f"""当前手牌：{', '.join(hand_cards)}
额外卡组可用：{', '.join(extra_deck[:5])}

请建议一个combo路线。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            combo_suggestion = json.loads(response)
        except:
            combo_suggestion = {"raw_response": response}
        
        return combo_suggestion
    
    def explain_decision(self, action: str, game_situation: str) -> str:
        """
        解释决策原因
        
        Args:
            action: 采取的操作
            game_situation: 游戏局势
            
        Returns:
            解释文本
        """
        prompt = f"""游戏局势：{game_situation}

我采取的操作：{action}

请解释为什么这是个好的选择。"""
        
        system_prompt = "你是游戏王策略分析专家，简洁地解释游戏决策的原因。"
        
        return self._call_llm(prompt, system_prompt)
    
    def detect_combo_pattern(self, action_sequence: List[Dict]) -> Dict[str, Any]:
        """
        从操作序列中检测combo模式
        
        Args:
            action_sequence: 操作序列
            
        Returns:
            检测到的模式
        """
        # 格式化操作序列
        seq_str = "\n".join([
            f"{i+1}. {action.get('type')}: {action.get('card_name', 'N/A')}"
            for i, action in enumerate(action_sequence)
        ])
        
        system_prompt = """你是游戏王combo分析专家。
从操作序列中识别combo模式，提取关键信息：
- combo_name: combo名称
- core_cards: 核心卡片列表
- combo_type: combo类型（展开/检索/破坏/抽卡等）
- key_points: 关键点说明
"""
        
        prompt = f"""以下是一个操作序列：

{seq_str}

请识别这是什么combo，并分析其模式。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            pattern = json.loads(response)
        except:
            pattern = {"raw_response": response}
        
        return pattern
    
    def learn_from_action_sequence(self, actions: List[Dict], deck_type: str = "") -> Dict[str, Any]:
        """
        从操作序列中深度学习
        
        Args:
            actions: 操作序列列表
            deck_type: 卡组类型
            
        Returns:
            学习结果
        """
        # 格式化操作序列
        seq_str = self._format_action_sequence(actions)
        
        system_prompt = f"""你是游戏王{deck_type}卡组的专家分析师。
你的任务是从玩家的操作序列中进行**深度学习**，而不仅仅是简单记录。

分析要点：
1. **战术意图**：理解玩家为什么这样操作，战术目标是什么
2. **Combo模式**：识别combo的核心模式和关键转折点
3. **卡片协同**：分析卡片之间的协同关系和配合逻辑
4. **决策点**：识别关键决策点和可能的分支路线
5. **可复用性**：提取可以复用到类似情况的通用模式

请返回JSON格式：
{{
  "combo_name": "combo名称",
  "tactical_intent": "战术意图描述",
  "core_cards": ["核心卡片列表"],
  "combo_pattern": "combo模式描述",
  "key_synergies": ["卡片协同关系"],
  "decision_points": ["关键决策点"],
  "alternative_paths": ["可能的替代路线"],
  "learned_insights": "深度理解和洞察"
}}
"""
        
        prompt = f"""请深度分析以下操作序列：

{seq_str}

进行深度学习分析，理解战术意图和combo本质。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            analysis = json.loads(response)
        except:
            # 如果不是JSON，尝试提取关键信息
            analysis = {
                "raw_response": response,
                "combo_name": "未识别",
                "learned_insights": response
            }
        
        return analysis
    
    def discover_alternative_combos(self, hand_cards: List[str], deck_info: Dict, 
                                   known_combos: List[Dict] = None) -> List[Dict[str, Any]]:
        """
        发现多种可能的展开路线
        
        Args:
            hand_cards: 手牌
            deck_info: 卡组信息
            known_combos: 已知的combo（用于参考）
            
        Returns:
            多种展开路线列表
        """
        system_prompt = f"""你是游戏王{deck_info.get('deck_type', '')}卡组的combo专家。
同一手牌可能有**多种不同的展开路线**，每种都有其优缺点。
你的任务是发现所有可能的展开方式，而不仅仅是最优的一种。

对于每种展开路线，分析：
- 操作步骤
- 最终场面
- 优势和劣势
- 适用场景（先攻/后攻/对局情况）
- 成功率

返回JSON数组，每个路线包含：
{{
  "route_name": "路线名称",
  "priority": "优先级（高/中/低）",
  "steps": ["步骤列表"],
  "final_board": "最终场面",
  "advantages": "优势",
  "disadvantages": "劣势",
  "best_scenario": "最佳场景"
}}
"""
        
        known_str = ""
        if known_combos:
            known_str = "\n\n已知的combo路线：\n"
            for combo in known_combos:
                known_str += f"- {combo.get('combo_name', '未知')}\n"
        
        prompt = f"""当前手牌：{', '.join(hand_cards)}
卡组类型：{deck_info.get('deck_type', '未知')}
可用额外卡组：{', '.join([c['name'] for c in deck_info.get('extra_deck', [])[:10]])}
{known_str}

请发现所有可能的展开路线（至少3种不同的方式）。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            routes = json.loads(response)
            if isinstance(routes, dict):
                routes = [routes]
        except:
            routes = [{"raw_response": response}]
        
        return routes
    
    def understand_strategic_decision(self, action: Dict, context: Dict) -> Dict[str, Any]:
        """
        理解单个操作的战术决策
        
        Args:
            action: 操作信息
            context: 上下文（场面、手牌等）
            
        Returns:
            决策理解
        """
        system_prompt = """你是游戏王策略分析专家。
分析单个操作背后的战术思考和决策逻辑。

返回JSON：
{
  "decision_reason": "决策原因",
  "tactical_value": "战术价值",
  "risk_assessment": "风险评估",
  "alternative_actions": ["可能的替代操作"],
  "expected_outcome": "预期结果"
}
"""
        
        prompt = f"""操作：{action.get('action_type')} - {action.get('card_name')}
效果：{action.get('effect_description', 'N/A')}

当前场面：
{self._format_context(context)}

请分析这个操作的战术决策。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            decision = json.loads(response)
        except:
            decision = {"raw_response": response}
        
        return decision
    
    def extract_card_synergy(self, card_pairs: List[Tuple[str, str]], 
                            action_history: List[Dict] = None) -> Dict[str, Any]:
        """
        提取卡片协同关系
        
        Args:
            card_pairs: 卡片组合列表
            action_history: 历史操作（用于学习实际协同）
            
        Returns:
            协同关系分析
        """
        system_prompt = """你是游戏王卡片协同专家。
分析卡片之间的协同关系，包括：
- 直接协同（卡片效果直接配合）
- 间接协同（通过资源/场面配合）
- 时机协同（发动时机的配合）
- combo协同（作为combo链的一部分）

返回JSON：
{
  "synergy_type": "协同类型",
  "synergy_strength": "协同强度（强/中/弱）",
  "how_it_works": "协同原理",
  "combo_potential": "combo潜力",
  "usage_tips": "使用技巧"
}
"""
        
        pairs_str = "\n".join([f"- {c1} + {c2}" for c1, c2 in card_pairs])
        
        history_str = ""
        if action_history:
            history_str = "\n\n从实际对局中观察到的使用：\n"
            history_str += self._format_action_sequence(action_history[:10])
        
        prompt = f"""卡片组合：
{pairs_str}
{history_str}

请分析这些卡片的协同关系。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        try:
            synergy = json.loads(response)
        except:
            synergy = {"raw_response": response}
        
        return synergy
    
    def _format_action_sequence(self, actions: List[Dict]) -> str:
        """格式化操作序列"""
        lines = []
        for i, action in enumerate(actions, 1):
            action_type = action.get('action_type', 'unknown')
            card_name = action.get('card_name', 'N/A')
            effect = action.get('effect_description', '')
            
            line = f"{i}. {action_type}: {card_name}"
            if effect:
                line += f" - {effect}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_context(self, context: Dict) -> str:
        """格式化上下文"""
        lines = []
        
        if 'hand' in context:
            lines.append(f"手牌：{', '.join(context['hand'])}")
        
        if 'field_monsters' in context:
            lines.append(f"场上怪兽：{len(context['field_monsters'])}只")
        
        if 'graveyard' in context:
            lines.append(f"墓地：{len(context['graveyard'])}张")
        
        return "\n".join(lines)
    
    def _format_game_state(self, state: GameState) -> str:
        """格式化游戏状态为文本"""
        lines = [
            f"回合数：{state.turn_count}",
            f"当前阶段：{state.current_phase.value}",
            f"是否我的回合：{'是' if state.is_my_turn else '否'}",
            f"我的LP：{state.my_lp}",
            f"对手LP：{state.opponent_lp}",
            f"\n手牌数量：{len(state.hand)}",
        ]
        
        if state.hand:
            hand_names = [c.name for c in state.hand if c.name]
            if hand_names:
                lines.append(f"手牌：{', '.join(hand_names)}")
        
        lines.append(f"\n我的场上：")
        lines.append(f"- 怪兽区：{len(state.my_monsters)}张")
        lines.append(f"- 魔陷区：{len(state.my_spells)}张")
        
        lines.append(f"\n对手场上：")
        lines.append(f"- 怪兽区：{len(state.opponent_monsters)}张")
        lines.append(f"- 魔陷区：{len(state.opponent_spells)}张")
        
        if state.chain_active:
            lines.append(f"\n当前连锁中，连锁数：{len(state.chain_links)}")
        
        return "\n".join(lines)


# 测试代码
if __name__ == "__main__":
    logger.info("测试LLM决策引擎...")
    
    # 初始化引擎
    engine = LLMDecisionEngine()
    
    # 测试卡片效果理解
    card_text = """①：1回合1次，以对方场上1只怪兽为对象才能发动。
那只怪兽的控制权直到结束阶段得到。
这个效果在对方回合也能发动。"""
    
    result = engine.understand_card_effect(card_text, "敌人控制器")
    logger.info(f"卡片效果分析: {result}")
    
    # 测试combo建议
    hand = ["灰流丽", "增殖的G", "无限泡影"]
    combo = engine.suggest_combo(hand, [], "手坑卡组")
    logger.info(f"Combo建议: {combo}")
