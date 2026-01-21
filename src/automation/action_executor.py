"""
操作执行器
将ActionStep转换为实际的游戏操作
"""
import time
from typing import Optional
from loguru import logger
from ..core.action_schema import ActionStep, ActionType
from ..control.mouse_controller import MouseController
from ..vision.screen_capture import ScreenCapture


class ActionExecutor:
    """操作执行器"""
    
    def __init__(self, mouse_controller: MouseController, 
                 screen_capture: ScreenCapture):
        """
        初始化执行器
        
        Args:
            mouse_controller: 鼠标控制器
            screen_capture: 屏幕捕获器
        """
        self.mouse = mouse_controller
        self.capture = screen_capture
        
        # UI位置映射（需要根据实际游戏调整）
        self.ui_positions = {
            'confirm_button': (1600, 900),
            'cancel_button': (1500, 900),
            'next_button': (1650, 900),
            'hand_start': (400, 850),
            'field_monster_1': (500, 600),
            'field_spell_1': (500, 700),
        }
    
    def execute_action(self, action: ActionStep, 
                      verify: bool = True) -> bool:
        """
        执行一个操作
        
        Args:
            action: 要执行的操作
            verify: 是否验证执行结果
            
        Returns:
            是否成功
        """
        logger.info(f"执行操作: {action.type} - {action.card_name}")
        
        try:
            # 根据操作类型执行
            if action.type == ActionType.SUMMON.value:
                return self._execute_summon(action)
            
            elif action.type == ActionType.ACTIVATE.value:
                return self._execute_activate(action)
            
            elif action.type == ActionType.SET.value:
                return self._execute_set(action)
            
            elif action.type == ActionType.ATTACK.value:
                return self._execute_attack(action)
            
            elif action.type == "CLICK":
                return self._execute_click(action)
            
            elif action.type == "KEY_PRESS":
                return self._execute_key_press(action)
            
            else:
                logger.warning(f"未知操作类型: {action.type}")
                return False
            
        except Exception as e:
            logger.error(f"执行操作失败: {e}")
            return False
        
        finally:
            # 等待
            time.sleep(action.wait_time)
    
    def _execute_summon(self, action: ActionStep) -> bool:
        """执行通常召唤"""
        # 1. 从手牌中找到卡片
        card_pos = self._find_card_in_hand(action.card_name)
        
        if not card_pos:
            logger.error(f"在手牌中找不到卡片: {action.card_name}")
            return False
        
        # 2. 点击卡片
        self.mouse.click(card_pos[0], card_pos[1])
        time.sleep(0.5)
        
        # 3. 选择召唤方式（通常召唤）
        # TODO: 根据实际UI位置调整
        
        # 4. 选择怪兽区位置
        if action.zone_index is not None:
            monster_zone = self._get_monster_zone_position(action.zone_index)
            self.mouse.click(monster_zone[0], monster_zone[1])
        
        # 5. 选择表示形式（攻击/守备）
        if action.position == "attack":
            # TODO: 点击攻击表示
            pass
        elif action.position == "defense":
            # TODO: 点击守备表示
            pass
        
        # 6. 确认
        self._click_confirm()
        
        return True
    
    def _execute_activate(self, action: ActionStep) -> bool:
        """执行发动效果"""
        # 1. 找到卡片
        card_pos = self._find_card_position(action.card_name, action.from_zone)
        
        if not card_pos:
            logger.error(f"找不到卡片: {action.card_name}")
            return False
        
        # 2. 点击卡片
        self.mouse.click(card_pos[0], card_pos[1])
        time.sleep(0.5)
        
        # 3. 选择发动
        # TODO: 识别并点击"发动"按钮
        
        # 4. 选择目标（如果有）
        if action.targets:
            for target in action.targets:
                target_pos = self._find_card_position(target)
                if target_pos:
                    self.mouse.click(target_pos[0], target_pos[1])
                    time.sleep(0.3)
        
        # 5. 确认
        self._click_confirm()
        
        return True
    
    def _execute_set(self, action: ActionStep) -> bool:
        """执行盖放"""
        # 类似召唤，但选择盖放
        card_pos = self._find_card_in_hand(action.card_name)
        
        if not card_pos:
            return False
        
        self.mouse.click(card_pos[0], card_pos[1])
        time.sleep(0.5)
        
        # TODO: 选择盖放
        
        return True
    
    def _execute_attack(self, action: ActionStep) -> bool:
        """执行攻击"""
        # 1. 选择攻击怪兽
        attacker_pos = self._find_card_in_monster_zone(action.card_name)
        
        if not attacker_pos:
            return False
        
        self.mouse.click(attacker_pos[0], attacker_pos[1])
        time.sleep(0.5)
        
        # 2. 选择攻击目标
        if action.targets and action.targets[0]:
            target_pos = self._find_card_in_monster_zone(action.targets[0], my_side=False)
            if target_pos:
                self.mouse.click(target_pos[0], target_pos[1])
        else:
            # 直接攻击
            # TODO: 点击直接攻击
            pass
        
        # 3. 确认
        self._click_confirm()
        
        return True
    
    def _execute_click(self, action: ActionStep) -> bool:
        """执行点击操作"""
        # 解析位置
        if action.position:
            # 格式: (x, y)
            pos_str = action.position.strip('()')
            x, y = map(int, pos_str.split(','))
            self.mouse.click(x, y)
            return True
        return False
    
    def _execute_key_press(self, action: ActionStep) -> bool:
        """执行按键操作"""
        # TODO: 实现键盘输入
        logger.warning("键盘输入暂未实现")
        return False
    
    def _find_card_in_hand(self, card_name: str) -> Optional[tuple]:
        """在手牌中查找卡片位置"""
        # TODO: 使用卡片识别系统找到卡片
        # 这里返回估计的位置
        return self.ui_positions.get('hand_start')
    
    def _find_card_position(self, card_name: str, 
                           zone: Optional[str] = None) -> Optional[tuple]:
        """查找卡片位置"""
        # TODO: 实现完整的卡片定位
        return None
    
    def _find_card_in_monster_zone(self, card_name: str, 
                                   my_side: bool = True) -> Optional[tuple]:
        """在怪兽区查找卡片"""
        # TODO: 实现
        return None
    
    def _get_monster_zone_position(self, index: int) -> tuple:
        """获取怪兽区位置"""
        # 5个怪兽区，从左到右编号0-4
        base_x = 400
        base_y = 600
        spacing = 150
        
        return (base_x + index * spacing, base_y)
    
    def _click_confirm(self):
        """点击确认按钮"""
        pos = self.ui_positions.get('confirm_button')
        if pos:
            self.mouse.click(pos[0], pos[1])
            time.sleep(0.5)
    
    def _click_cancel(self):
        """点击取消按钮"""
        pos = self.ui_positions.get('cancel_button')
        if pos:
            self.mouse.click(pos[0], pos[1])
            time.sleep(0.5)


# 测试代码
if __name__ == "__main__":
    from ..control.mouse_controller import MouseController
    from ..vision.screen_capture import ScreenCapture
    
    logger.info("测试操作执行器...")
    
    mouse = MouseController()
    capture = ScreenCapture()
    executor = ActionExecutor(mouse, capture)
    
    # 测试操作
    test_action = ActionStep(
        type=ActionType.SUMMON.value,
        card_name="青眼白龙",
        position="attack",
        zone_index=2
    )
    
    # executor.execute_action(test_action)
    logger.info("测试完成")
