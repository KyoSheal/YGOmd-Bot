"""
游戏王Master Duel - 游戏录制检测器
检测卡片发动、效果激活、召唤等关键UI状态
基于实际游戏界面分析
"""
import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from loguru import logger
from pathlib import Path

try:
    from paddleocr import PaddleOCR
    HAS_PADDLE = True
except ImportError:
    HAS_PADDLE = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

if not HAS_PADDLE and not HAS_TESSERACT:
    logger.warning("没有OCR库可用！请安装 paddleocr 或 pytesseract")


class MasterDuelDetector:
    """Master Duel 游戏状态检测器"""
    
    # 基于1024x576分辨率的参考坐标（相对比例）
    # 从实际决斗截图分析得出（显示"深红共鸣者"的界面）
    # 注意：游戏有两种主要界面 - 决斗界面和卡组编辑界面
    REGIONS = {
        # 左侧卡片信息面板（当点击卡片时显示）- 决斗界面
        'card_info_panel': (0.0, 0.01, 0.22, 0.55),  # 整个左侧信息区域
        # 卡片名称"深红共鸣者"位置分析（1024x576分辨率）：
        # 从debug_regions.png观察：名称在左侧面板中，"R"标志右侧
        # 实际位置较低: x=17px, y=50px, w=90px, h=22px
        # 转换为比例: x=0.017, y=0.087, w=0.088, h=0.038
        'card_name': (0.017, 0.085, 0.088, 0.04),  # 卡片名称
        'card_text': (0.01, 0.28, 0.20, 0.32),  # 卡片效果文本
        
        # LP显示 
        'my_lp': (0.06, 0.81, 0.10, 0.04),  # 左下角"LP 8000"
        'opponent_lp': (0.86, 0.00, 0.12, 0.05),  # 右上角对手LP
        
        # 阶段显示 - "Turn 2 Main1" 在右侧
        'phase_indicator': (0.82, 0.26, 0.15, 0.10),  # 阶段指示器
        
        # 场地区域 - 怪兽区和魔陷区
        'my_field': (0.22, 0.42, 0.56, 0.25),  # 我的怪兽区（中下）
        'opponent_field': (0.22, 0.08, 0.56, 0.22),  # 对手怪兽区（中上）
        
        # 手牌区域 - 底部弧形排列
        'hand_area': (0.10, 0.75, 0.75, 0.22),  # 手牌区域
        
        # 效果按钮区域 - "发动效果" 出现在卡片附近
        'effect_button': (0.35, 0.38, 0.15, 0.08),  # 发动效果按钮
        
        # 右侧按钮区域 - Auto, i, 设置等
        'action_buttons': (0.85, 0.75, 0.12, 0.20),
    }
    
    # 关键UI元素的颜色特征（BGR格式）
    EFFECT_BUTTON_COLOR = {
        'activate': (0, 200, 255),  # 黄色发动效果按钮
        'summon': (100, 255, 100),  # 绿色召唤
        'set': (150, 150, 255),  # 浅红/粉色盖放
    }
    
    def __init__(self, deck_card_names: List[str] = None):
        """
        初始化检测器
        
        Args:
            deck_card_names: 卡组中所有卡片名称列表（用于OCR匹配）
        """
        self.deck_card_names = deck_card_names or []
        
        # 初始化OCR（优先使用Tesseract，因为PaddlePaddle在某些系统上有兼容性问题）
        self.ocr = None
        self.ocr_type = None
        
        # 优先使用Tesseract（更稳定）
        if HAS_TESSERACT:
            self.ocr_type = "tesseract"
            logger.info("使用Tesseract OCR")
        elif HAS_PADDLE:
            try:
                # 注意：PaddlePaddle可能有oneDNN兼容性问题
                self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
                self.ocr_type = "paddle"
                logger.info("PaddleOCR初始化成功")
            except Exception as e:
                logger.warning(f"PaddleOCR初始化失败: {e}")
        
        if self.ocr_type is None:
            logger.warning("没有可用的OCR引擎")
        
        # 缓存上一次检测结果
        self.last_state = {}
        self.last_card_name = ""
        
    def detect_ui_state(self, screenshot: np.ndarray) -> Dict[str, Any]:
        """
        检测当前UI状态
        
        Args:
            screenshot: 游戏截图（BGR格式）
            
        Returns:
            UI状态字典
        """
        h, w = screenshot.shape[:2]
        state = {
            'has_card_info': False,
            'card_activation_detected': False,
            'summon_detected': False,
            'effect_window_open': False,
            'card_name_region': None,
            'effect_card_region': None,
            'summon_card_region': None,
        }
        
        # 检测左侧卡片信息面板是否有内容
        card_panel = self._get_region(screenshot, 'card_info_panel')
        if self._has_card_info(card_panel):
            state['has_card_info'] = True
            state['card_name_region'] = self._to_abs_region('card_name', w, h)
        
        # 检测效果发动按钮
        effect_btn = self._get_region(screenshot, 'effect_button')
        if self._detect_effect_button(effect_btn):
            state['effect_window_open'] = True
            state['card_activation_detected'] = True
            state['effect_card_region'] = self._to_abs_region('card_name', w, h)
        
        return state
    
    def _get_region(self, screenshot: np.ndarray, region_name: str) -> np.ndarray:
        """获取指定区域的图像"""
        if region_name not in self.REGIONS:
            raise ValueError(f"未知区域: {region_name}")
        
        h, w = screenshot.shape[:2]
        x_pct, y_pct, w_pct, h_pct = self.REGIONS[region_name]
        
        x = int(w * x_pct)
        y = int(h * y_pct)
        region_w = int(w * w_pct)
        region_h = int(h * h_pct)
        
        return screenshot[y:y+region_h, x:x+region_w]
    
    def _to_abs_region(self, region_name: str, width: int, height: int) -> Tuple[int, int, int, int]:
        """将相对坐标转换为绝对坐标"""
        x_pct, y_pct, w_pct, h_pct = self.REGIONS[region_name]
        return (
            int(width * x_pct),
            int(height * y_pct),
            int(width * w_pct),
            int(height * h_pct)
        )
    
    def _has_card_info(self, panel: np.ndarray) -> bool:
        """检测卡片信息面板是否显示卡片"""
        # 分析面板区域，判断是否有卡片信息
        # 空面板通常较暗，有卡片时较亮
        gray = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        # 如果平均亮度高于阈值，认为有卡片信息
        return mean_brightness > 40
    
    def _detect_effect_button(self, region: np.ndarray) -> bool:
        """检测效果发动按钮"""
        # 检测是否有"发动效果"按钮的特征颜色（黄色/金色）
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        
        # 黄色范围
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([40, 255, 255])
        
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        yellow_pixels = cv2.countNonZero(mask)
        
        # 如果黄色像素足够多，认为有发动按钮
        return yellow_pixels > 50
    
    def ocr_card_name(self, image: np.ndarray) -> Dict[str, Any]:
        """
        使用OCR识别卡片名称
        
        Args:
            image: 卡片名称区域图像
            
        Returns:
            {'text': 识别文本, 'confidence': 置信度}
        """
        if self.ocr_type is None:
            return {'text': '', 'confidence': 0.0}
        
        try:
            # 预处理：放大、增强对比度
            scale = 2
            enlarged = cv2.resize(image, None, fx=scale, fy=scale, 
                                 interpolation=cv2.INTER_CUBIC)
            
            # 灰度 + 对比度增强
            gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.equalizeHist(gray)
            
            if self.ocr_type == "paddle":
                # PaddleOCR - 使用predict方法
                enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
                
                # 新版PaddleOCR使用predict方法
                try:
                    result = self.ocr.predict(enhanced_bgr)
                except AttributeError:
                    # 旧版本使用ocr方法
                    result = self.ocr.ocr(enhanced_bgr)
                
                # 解析结果
                if result and isinstance(result, dict) and 'rec_texts' in result:
                    # 新版本格式
                    texts = result.get('rec_texts', [])
                    scores = result.get('rec_scores', [])
                    if texts:
                        text = texts[0]
                        confidence = scores[0] if scores else 0.7
                        logger.debug(f"PaddleOCR识别: {text} (置信度: {confidence:.2f})")
                        return {'text': text, 'confidence': confidence}
                elif result and isinstance(result, list) and result[0]:
                    # 旧版本格式
                    text = result[0][0][1][0]
                    confidence = result[0][0][1][1]
                    logger.debug(f"PaddleOCR识别: {text} (置信度: {confidence:.2f})")
                    return {'text': text, 'confidence': confidence}
            
            elif self.ocr_type == "tesseract":
                # Tesseract OCR (中文) - 优化配置
                # 使用OTSU二值化
                _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # 尝试中文简体
                try:
                    text = pytesseract.image_to_string(
                        binary, 
                        lang='chi_sim+chi_tra',  # 简体+繁体中文
                        config='--psm 7 --oem 3'  # 单行文本，LSTM引擎
                    ).strip()
                except:
                    # 如果中文包不可用，尝试英文
                    text = pytesseract.image_to_string(
                        binary, 
                        config='--psm 7'
                    ).strip()
                
                if text:
                    # 清理文本
                    text = text.replace(' ', '').replace('\n', '')
                    logger.debug(f"Tesseract识别: {text}")
                    return {'text': text, 'confidence': 0.7}
        
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
        
        return {'text': '', 'confidence': 0.0}
    
    def match_card_name(self, ocr_text: str) -> Tuple[str, float]:
        """
        将OCR文本与卡组中的卡片名称匹配
        
        Args:
            ocr_text: OCR识别的文本
            
        Returns:
            (最佳匹配卡名, 匹配分数)
        """
        if not ocr_text or not self.deck_card_names:
            return "", 0.0
        
        best_match = ""
        best_score = 0.0
        
        for card_name in self.deck_card_names:
            score = self._similarity(ocr_text, card_name)
            if score > best_score:
                best_score = score
                best_match = card_name
        
        return best_match, best_score
    
    def _similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度"""
        if not s1 or not s2:
            return 0.0
        
        # 完全匹配
        if s1 == s2:
            return 1.0
        
        # 包含关系
        if s1 in s2 or s2 in s1:
            return 0.9
        
        # 字符交集
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def detect_game_phase(self, screenshot: np.ndarray) -> str:
        """检测当前游戏阶段"""
        phase_region = self._get_region(screenshot, 'phase_indicator')
        
        if self.ocr:
            result = self.ocr_card_name(phase_region)
            text = result.get('text', '')
            
            # 解析阶段文本
            if 'Main' in text or 'main' in text.lower():
                return 'main_phase'
            elif 'Draw' in text or 'draw' in text.lower():
                return 'draw_phase'
            elif 'Battle' in text or 'battle' in text.lower():
                return 'battle_phase'
            elif 'End' in text or 'end' in text.lower():
                return 'end_phase'
        
        return 'unknown'
    
    def detect_lp(self, screenshot: np.ndarray) -> Tuple[int, int]:
        """检测双方LP"""
        my_lp_region = self._get_region(screenshot, 'my_lp')
        opp_lp_region = self._get_region(screenshot, 'opponent_lp')
        
        my_lp = 8000
        opp_lp = 8000
        
        if self.ocr:
            my_result = self.ocr_card_name(my_lp_region)
            opp_result = self.ocr_card_name(opp_lp_region)
            
            try:
                my_text = my_result.get('text', '').replace(' ', '')
                if my_text.isdigit():
                    my_lp = int(my_text)
            except:
                pass
            
            try:
                opp_text = opp_result.get('text', '').replace(' ', '')
                if opp_text.isdigit():
                    opp_lp = int(opp_text)
            except:
                pass
        
        return my_lp, opp_lp


# 使用示例
if __name__ == "__main__":
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 测试检测器
    detector = MasterDuelDetector()
    
    # 加载测试图像
    test_image = "debug_screenshot_full.png"
    if Path(test_image).exists():
        img = cv2.imread(test_image)
        
        # 检测UI状态
        state = detector.detect_ui_state(img)
        logger.info(f"UI状态: {state}")
        
        # 检测阶段
        phase = detector.detect_game_phase(img)
        logger.info(f"当前阶段: {phase}")
        
        # 检测LP
        my_lp, opp_lp = detector.detect_lp(img)
        logger.info(f"LP: {my_lp} vs {opp_lp}")
    else:
        logger.warning(f"测试图像不存在: {test_image}")
