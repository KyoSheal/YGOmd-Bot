"""
Solo模式自动化
完整的自动对战流程
"""
import time
from typing import Optional
from loguru import logger
from ..core.game_state import GameState, Phase
from ..core.decision_engine import DecisionEngine
from ..vision.screen_capture import ScreenCapture
from ..vision.card_detector import CardImageRecognizer
from ..vision.ui_detector import GameStateDetector
from ..control.mouse_controller import MouseController
from ..automation.action_executor import ActionExecutor


class SoloModeAutomation:
    """Solo模式自动化"""
    
    def __init__(self, config: dict):
        """
        初始化自动化系统
        
        Args:
            config: 配置字典
        """
        self.config = config
        
        # 初始化各个组件
        logger.info("初始化Solo模式自动化系统...")
        
        # 视觉组件
        self.screen_capture = ScreenCapture()
        self.card_recognizer = CardImageRecognizer()
        self.state_detector = GameStateDetector()
        
        # 控制组件
        self.mouse_controller = MouseController(
            speed=config.get('control', {}).get('mouse_speed', 'medium'),
            humanize=config.get('control', {}).get('humanize', True)
        )
        
        # 执行器
        self.action_executor = ActionExecutor(
            self.mouse_controller,
            self.screen_capture
        )
        
        # 决策引擎
        use_llm = config.get('decision', {}).get('use_llm', True)
        self.decision_engine = DecisionEngine(
            use_llm=use_llm
        )
        
        # 状态
        self.running = False
        self.current_duel = None
        
        logger.info("Solo模式自动化系统初始化完成")
    
    def start_automation(self, deck_type: Optional[str] = None):
        """
        开始自动化
        
        Args:
            deck_type: 卡组类型
        """
        logger.info("=" * 60)
        logger.info("开始Solo模式自动化")
        logger.info("=" * 60)
        
        if not self.screen_capture.find_game_window():
            logger.error("未找到游戏窗口！请先启动游戏")
            return
        
        self.running = True
        self.current_duel = {
            'deck_type': deck_type,
            'turn_count': 0,
            'actions_taken': 0
        }
        
        try:
            # 主循环
            while self.running:
                # 获取当前游戏状态
                game_state = self._capture_game_state()
                
                if game_state is None:
                    logger.warning("无法获取游戏状态，等待...")
                    time.sleep(1)
                    continue
                
                # 决策并执行
                self._process_turn(game_state, deck_type)
                
                # 等待一段时间
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            logger.info("用户中断自动化")
        except Exception as e:
            logger.error(f"自动化过程出错: {e}")
        finally:
            self.running = False
            logger.info("自动化已停止")
    
    def _capture_game_state(self) -> Optional[GameState]:
        """捕获当前游戏状态"""
        try:
            # 捕获屏幕
            screenshot = self.screen_capture.capture_window()
            if screenshot is None:
                return None
            
            # 检测游戏状态（回合、阶段、LP等）
            state = self.state_detector.detect_game_state(screenshot)
            
            # 识别手牌
            if state.is_my_turn:
                hand_cards = self.card_recognizer.detect_cards_in_image(
                    screenshot, zone='hand'
                )
                
                # 更新状态
                from ..core.game_state import Card, Zone
                state.hand = []
                for card_data in hand_cards:
                    card = Card(
                        card_id=card_data.get('card_id'),
                        name=card_data.get('name'),
                        zone=Zone.HAND,
                        zone_index=card_data.get('zone_index', 0)
                    )
                    state.hand.append(card)
            
            return state
            
        except Exception as e:
            logger.error(f"捕获游戏状态失败: {e}")
            return None
    
    def _process_turn(self, game_state: GameState, deck_type: Optional[str]):
        """处理一个回合"""
        # 检查是否是我的回合
        if not game_state.is_my_turn:
            logger.debug("等待对手回合结束...")
            return
        
        # 检查当前阶段
        logger.info(f"当前阶段: {game_state.current_phase.value}")
        
        # 根据阶段执行不同的操作
        if game_state.current_phase == Phase.MAIN1:
            self._process_main_phase(game_state, deck_type)
        
        elif game_state.current_phase == Phase.BATTLE:
            self._process_battle_phase(game_state)
        
        elif game_state.current_phase == Phase.MAIN2:
            self._process_main_phase(game_state, deck_type)
        
        elif game_state.current_phase == Phase.END:
            self._end_turn()
    
    def _process_main_phase(self, game_state: GameState, deck_type: Optional[str]):
        """处理主要阶段"""
        logger.info("处理主要阶段...")
        
        # 使用决策引擎决定下一步
        action = self.decision_engine.decide_next_action(
            game_state,
            deck_type=deck_type
        )
        
        if action:
            logger.info(f"执行决策: {action.type} - {action.card_name}")
            
            # 执行操作
            success = self.action_executor.execute_action(action)
            
            if success:
                self.current_duel['actions_taken'] += 1
                logger.info(f"操作成功！已执行 {self.current_duel['actions_taken']} 个操作")
            else:
                logger.warning("操作失败")
        else:
            logger.info("无可用操作，进入战斗阶段")
            self._enter_battle_phase()
    
    def _process_battle_phase(self, game_state: GameState):
        """处理战斗阶段"""
        logger.info("处理战斗阶段...")
        
        # 简单策略：攻击所有可攻击的怪兽
        # TODO: 实现更智能的战斗决策
        
        # 进入主要阶段2
        self._enter_main2()
    
    def _enter_battle_phase(self):
        """进入战斗阶段"""
        logger.info("进入战斗阶段...")
        # TODO: 点击"战斗阶段"按钮
        time.sleep(0.5)
    
    def _enter_main2(self):
        """进入主要阶段2"""
        logger.info("进入主要阶段2...")
        # TODO: 点击相应按钮
        time.sleep(0.5)
    
    def _end_turn(self):
        """结束回合"""
        logger.info("结束回合...")
        # TODO: 点击"结束回合"按钮
        self.current_duel['turn_count'] += 1
        time.sleep(1)
    
    def stop(self):
        """停止自动化"""
        logger.info("停止自动化...")
        self.running = False


# 测试代码
if __name__ == "__main__":
    logger.info("测试Solo模式自动化...")
    
    config = {
        'control': {
            'mouse_speed': 'medium',
            'humanize': True
        },
        'decision': {
            'use_llm': False  # 测试时先不用LLM
        }
    }
    
    automation = SoloModeAutomation(config)
    # automation.start_automation(deck_type="青眼")
