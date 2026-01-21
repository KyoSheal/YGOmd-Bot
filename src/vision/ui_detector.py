"""
游戏状态检测器
检测游戏的回合、阶段、按钮等UI状态
"""
import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple
from loguru import logger
from ..core.game_state import Phase, GameState


class GameStateDetector:
    """游戏状态检测器"""
    
    def __init__(self):
        """初始化检测器"""
        # UI元素模板（需要预先采集）
        self.ui_templates = {}
        
        # 区域定义（相对坐标，百分比）
        self.regions = {
            'phase_indicator': (0.45, 0.05, 0.1, 0.05),  # 阶段指示器
            'buttons': (0.7, 0.8, 0.25, 0.15),  # 按钮区域
            'my_lp': (0.85, 0.85, 0.1, 0.05),  # 我的LP
            'opponent_lp': (0.85, 0.05, 0.1, 0.05),  # 对手LP
            'hand': (0.2, 0.8, 0.6, 0.15),  # 手牌区域
            'my_field': (0.2, 0.55, 0.6, 0.2),  # 我的场地
            'opponent_field': (0.2, 0.15, 0.6, 0.2),  # 对手场地
        }
        
        # 按钮文本识别（简单颜色判断）
        self.button_colors = {
            'confirm': (0, 255, 0),  # 绿色确认按钮
            'cancel': (0, 0, 255),  # 红色取消按钮
            'next': (255, 255, 0),  # 黄色下一步
        }
    
    def detect_game_state(self, screenshot: np.ndarray) -> GameState:
        """
        检测完整游戏状态
        
        Args:
            screenshot: 游戏截图
            
        Returns:
            游戏状态对象
        """
        state = GameState()
        
        # 检测回合和阶段
        state.current_phase = self._detect_phase(screenshot)
        state.is_my_turn = self._detect_turn(screenshot)
        
        # 检测LP
        state.my_lp, state.opponent_lp = self._detect_lp(screenshot)
        
        # 检测按钮状态
        state.buttons_visible = self._detect_buttons(screenshot)
        
        # 检测对话框
        state.dialog_open = self._detect_dialog(screenshot)
        
        # 检测连锁状态
        state.chain_active = self._detect_chain(screenshot)
        
        logger.debug(f"检测游戏状态: {state.current_phase.value}, "
                    f"我的回合: {state.is_my_turn}, LP: {state.my_lp}/{state.opponent_lp}")
        
        return state
    
    def _detect_phase(self, screenshot: np.ndarray) -> Phase:
        """检测当前阶段"""
        # 提取阶段指示器区域
        region = self._get_region(screenshot, 'phase_indicator')
        
        # 简单的颜色检测（需要根据实际游戏调整）
        # 这里只是示例逻辑
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        
        # 不同阶段可能有不同颜色或图标
        # 这需要通过实际游戏观察来确定
        
        return Phase.UNKNOWN  # 默认返回未知
    
    def _detect_turn(self, screenshot: np.ndarray) -> bool:
        """检测是否是我的回合"""
        # 通过检测特定UI元素判断
        # 例如：我的回合时某个区域是高亮的
        
        return True  # 默认返回True
    
    def _detect_lp(self, screenshot: np.ndarray) -> Tuple[int, int]:
        """
        检测双方LP
        
        Returns:
            (我的LP, 对手LP)
        """
        # 提取LP显示区域
        my_lp_region = self._get_region(screenshot, 'my_lp')
        opp_lp_region = self._get_region(screenshot, 'opponent_lp')
        
        # 使用OCR识别数字（需要pytesseract）
        try:
            import pytesseract
            
            # 预处理：转灰度、二值化
            my_lp_gray = cv2.cvtColor(my_lp_region, cv2.COLOR_BGR2GRAY)
            _, my_lp_thresh = cv2.threshold(my_lp_gray, 127, 255, cv2.THRESH_BINARY)
            
            opp_lp_gray = cv2.cvtColor(opp_lp_region, cv2.COLOR_BGR2GRAY)
            _, opp_lp_thresh = cv2.threshold(opp_lp_gray, 127, 255, cv2.THRESH_BINARY)
            
            # OCR识别
            my_lp_text = pytesseract.image_to_string(
                my_lp_thresh, 
                config='--psm 7 digits'
            ).strip()
            
            opp_lp_text = pytesseract.image_to_string(
                opp_lp_thresh, 
                config='--psm 7 digits'
            ).strip()
            
            # 转换为整数
            my_lp = int(my_lp_text) if my_lp_text.isdigit() else 8000
            opp_lp = int(opp_lp_text) if opp_lp_text.isdigit() else 8000
            
            return my_lp, opp_lp
            
        except Exception as e:
            logger.warning(f"LP检测失败: {e}")
            return 8000, 8000
    
    def _detect_buttons(self, screenshot: np.ndarray) -> Dict[str, bool]:
        """检测可见的按钮"""
        buttons_region = self._get_region(screenshot, 'buttons')
        
        visible_buttons = {}
        
        # 检测各个按钮
        for button_name, color in self.button_colors.items():
            # 颜色范围检测
            lower = np.array([c - 30 for c in color])
            upper = np.array([min(c + 30, 255) for c in color])
            
            mask = cv2.inRange(buttons_region, lower, upper)
            button_pixels = cv2.countNonZero(mask)
            
            # 如果有足够的像素匹配，认为按钮可见
            visible_buttons[button_name] = button_pixels > 100
        
        return visible_buttons
    
    def _detect_dialog(self, screenshot: np.ndarray) -> bool:
        """检测是否有对话框"""
        # 对话框通常在中心区域
        h, w = screenshot.shape[:2]
        center_region = screenshot[
            int(h*0.3):int(h*0.7),
            int(w*0.3):int(w*0.7)
        ]
        
        # 检测是否有半透明遮罩层
        # 这需要根据实际游戏调整
        
        return False  # 默认无对话框
    
    def _detect_chain(self, screenshot: np.ndarray) -> bool:
        """检测是否在处理连锁"""
        # 连锁时通常有特殊的UI指示
        # 例如：连锁链条的视觉效果
        
        return False  # 默认无连锁
    
    def _get_region(self, screenshot: np.ndarray, 
                   region_name: str) -> np.ndarray:
        """
        获取指定区域的图像
        
        Args:
            screenshot: 完整截图
            region_name: 区域名称
            
        Returns:
            区域图像
        """
        if region_name not in self.regions:
            raise ValueError(f"未知区域: {region_name}")
        
        h, w = screenshot.shape[:2]
        x_pct, y_pct, w_pct, h_pct = self.regions[region_name]
        
        x = int(w * x_pct)
        y = int(h * y_pct)
        region_w = int(w * w_pct)
        region_h = int(h * h_pct)
        
        return screenshot[y:y+region_h, x:x+region_w]
    
    def calibrate_regions(self, screenshot: np.ndarray):
        """
        校准区域定义
        用于适配不同分辨率
        """
        # TODO: 实现交互式区域校准
        pass


# 测试代码
if __name__ == "__main__":
    logger.info("测试游戏状态检测器...")
    
    detector = GameStateDetector()
    
    # 测试（需要实际截图）
    # img = cv2.imread("test_screenshot.png")
    # state = detector.detect_game_state(img)
    # print(state.to_dict())
