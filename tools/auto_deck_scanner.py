"""
自动化卡组识别工具
自动点击卡组编辑界面的每张卡片并识别
"""
import time
import cv2
import numpy as np
from pathlib import Path
from loguru import logger
import json
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.vision.screen_capture import ScreenCapture
from src.control.mouse_controller import MouseController
from src.vision.card_detector import CardImageRecognizer


class AutoDeckScanner:
    """自动化卡组扫描器"""
    
    def __init__(self):
        """初始化扫描器"""
        self.screen_capture = ScreenCapture("masterduel")
        self.mouse = MouseController(speed='fast', humanize=True)
        self.recognizer = CardImageRecognizer()
        
        # 卡组界面的卡片网格位置（根据截图调整）
        # 基于1920x1080分辨率
        self.main_deck_grid = {
            'start_x': 285,  # 主卡组第一张卡的x坐标
            'start_y': 130,  # 主卡组第一张卡的y坐标
            'card_width': 42,  # 卡片宽度
            'card_height': 60,  # 卡片高度
            'spacing_x': 48,  # 水平间距
            'spacing_y': 68,  # 垂直间距
            'cols': 10,  # 每行10张卡
            'rows': 5,   # 5行（可能有空位）
        }
        
        self.extra_deck_grid = {
            'start_x': 285,
            'start_y': 435,
            'card_width': 42,
            'card_height': 60,
            'spacing_x': 48,
            'spacing_y': 68,
            'cols': 10,
            'rows': 2,
        }
        
        # 放大后的卡片区域（左侧详情）
        self.detail_card_region = {
            'x': 30,
            'y': 70,
            'width': 210,
            'height': 310
        }
        
        # 卡片名称文本区域
        self.card_name_region = {
            'x': 30,
            'y': 55,
            'width': 200,
            'height': 30
        }
        
    def scan_deck(self, deck_name: str = "auto_scanned_deck") -> dict:
        """
        扫描整个卡组
        
        Args:
            deck_name: 卡组名称
            
        Returns:
            卡组数据
        """
        logger.info("=" * 60)
        logger.info(f"开始自动扫描卡组: {deck_name}")
        logger.info("=" * 60)
        
        # 确保游戏窗口激活
        if not self.screen_capture.find_game_window():
            logger.error("未找到游戏窗口！")
            return None
        
        # 激活窗口
        self.screen_capture.activate_window()
        time.sleep(0.5)
        
        # 获取窗口位置偏移量（用于坐标转换）
        window_rect = self.screen_capture.window_rect
        self.window_offset_x = window_rect[0]  # 窗口左上角x坐标
        self.window_offset_y = window_rect[1]  # 窗口左上角y坐标
        
        logger.info(f"窗口偏移: ({self.window_offset_x}, {self.window_offset_y})")
        
        deck_data = {
            'deck_name': deck_name,
            'main_deck': [],
            'extra_deck': [],
            'timestamp': time.time()
        }
        
        # 扫描主卡组
        logger.info("扫描主卡组...")
        main_cards = self._scan_card_grid(
            self.main_deck_grid,
            max_cards=60  # 主卡组最多60张
        )
        deck_data['main_deck'] = main_cards
        logger.info(f"主卡组识别完成: {len(main_cards)} 张卡片")
        
        # 扫描额外卡组
        logger.info("扫描额外卡组...")
        extra_cards = self._scan_card_grid(
            self.extra_deck_grid,
            max_cards=15  # 额外卡组最多15张
        )
        deck_data['extra_deck'] = extra_cards
        logger.info(f"额外卡组识别完成: {len(extra_cards)} 张卡片")
        
        # 保存结果
        self._save_deck(deck_data)
        
        return deck_data
    
    def _scan_card_grid(self, grid_config: dict, max_cards: int) -> list:
        """扫描一个卡片网格区域"""
        cards = []
        card_count = 0
        
        for row in range(grid_config['rows']):
            for col in range(grid_config['cols']):
                if card_count >= max_cards:
                    break
                
                # 计算卡片中心位置（窗口相对坐标）
                rel_x = grid_config['start_x'] + col * grid_config['spacing_x']
                rel_y = grid_config['start_y'] + row * grid_config['spacing_y']
                
                # 转换为屏幕绝对坐标
                abs_x = self.window_offset_x + rel_x
                abs_y = self.window_offset_y + rel_y
                
                # 点击卡片
                logger.info(f"点击卡片 (rel:{rel_x},{rel_y} -> abs:{abs_x},{abs_y})...")
                self.mouse.click(abs_x, abs_y)
                time.sleep(0.3)  # 等待卡片详情显示
                
                # 捕获详情区域
                screenshot = self.screen_capture.capture_window()
                if screenshot is None:
                    logger.warning("截图失败，跳过")
                    continue
                
                # 提取卡片图像
                card_detail = self._extract_card_detail(screenshot)
                
                if card_detail is not None:
                    # 识别卡片
                    result = self._recognize_card(card_detail, screenshot)
                    
                    if result:
                        cards.append(result)
                        logger.info(f"✓ 识别成功: {result['name']}")
                        
                        # 保存卡片模板
                        self._save_card_template(card_detail, result['name'])
                    else:
                        # 如果识别失败，至少保存图像
                        unknown_name = f"unknown_card_{card_count}"
                        self._save_card_template(card_detail, unknown_name)
                        cards.append({'name': unknown_name, 'confidence': 0})
                        logger.warning(f"? 识别失败，保存为: {unknown_name}")
                
                card_count += 1
        
        return cards
    
    def _extract_card_detail(self, screenshot: np.ndarray) -> np.ndarray:
        """从截图中提取卡片详情区域"""
        region = self.detail_card_region
        card_img = screenshot[
            region['y']:region['y']+region['height'],
            region['x']:region['x']+region['width']
        ]
        return card_img
    
    def _recognize_card(self, card_image: np.ndarray, 
                       full_screenshot: np.ndarray) -> dict:
        """识别卡片"""
        # 方法1：图像识别
        if len(self.recognizer.card_templates) > 0:
            result = self.recognizer.recognize_card(card_image)
            if result and result['confidence'] > 0.7:
                return result
        
        # 方法2：OCR识别卡片名称
        try:
            import pytesseract
            name_region = self.card_name_region
            name_img = full_screenshot[
                name_region['y']:name_region['y']+name_region['height'],
                name_region['x']:name_region['x']+name_region['width']
            ]
            
            # 预处理
            gray = cv2.cvtColor(name_img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR识别
            name = pytesseract.image_to_string(
                binary,
                lang='chi_sim',
                config='--psm 7'
            ).strip()
            
            if name:
                return {'name': name, 'confidence': 0.8, 'method': 'ocr'}
        except Exception as e:
            logger.debug(f"OCR识别失败: {e}")
        
        return None
    
    def _save_card_template(self, card_image: np.ndarray, card_name: str):
        """保存卡片为模板"""
        # 提取艺术图部分
        h, w = card_image.shape[:2]
        art_h = int(h * 0.6)
        art_image = card_image[0:art_h, :]
        
        # 生成ID
        card_id = str(abs(hash(card_name)) % 10000000)
        
        # 保存
        template_dir = Path("data/templates")
        template_dir.mkdir(parents=True, exist_ok=True)
        
        img_path = template_dir / f"{card_id}.png"
        cv2.imwrite(str(img_path), art_image)
        
        meta_path = template_dir / f"{card_id}.json"
        metadata = {
            'card_id': card_id,
            'name': card_name,
            'auto_scanned': True
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _save_deck(self, deck_data: dict):
        """保存卡组数据"""
        output_dir = Path("data/decks")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{deck_data['deck_name']}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(deck_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"卡组数据已保存: {filepath}")
        
        # 打印统计
        main_count = len(deck_data['main_deck'])
        extra_count = len(deck_data['extra_deck'])
        logger.info(f"\n卡组统计:")
        logger.info(f"  主卡组: {main_count} 张")
        logger.info(f"  额外卡组: {extra_count} 张")
        logger.info(f"  总计: {main_count + extra_count} 张")
    
    def calibrate_positions(self):
        """校准卡片位置（辅助功能）"""
        logger.info("开始位置校准...")
        logger.info("请确保游戏在卡组编辑界面")
        
        input("按Enter开始校准第一张卡片位置...")
        
        # 让用户点击第一张卡
        logger.info("请手动点击主卡组的第一张卡片（左上角）")
        time.sleep(3)
        
        screenshot = self.screen_capture.capture_window()
        cv2.imwrite("calibration_screenshot.png", screenshot)
        logger.info("截图已保存: calibration_screenshot.png")
        logger.info("请根据截图调整 main_deck_grid 的 start_x 和 start_y")


# 主程序
if __name__ == "__main__":
    print("=" * 60)
    print("自动化卡组识别工具")
    print("=" * 60)
    print()
    print("使用说明:")
    print("1. 启动游戏并进入卡组编辑界面")
    print("2. 确保卡组在屏幕上完全可见")
    print("3. 运行本工具，它会自动点击每张卡片并识别")
    print()
    
    choice = input("选择模式 [1=开始扫描, 2=校准位置]: ").strip()
    
    scanner = AutoDeckScanner()
    
    if choice == "1":
        deck_name = input("请输入卡组名称 (或直接回车使用默认名称): ").strip()
        if not deck_name:
            deck_name = f"deck_{int(time.time())}"
        
        print()
        print("准备开始扫描...")
        print("请确保游戏窗口在卡组编辑界面！")
        input("按Enter开始...")
        
        result = scanner.scan_deck(deck_name)
        
        if result:
            print()
            print("=" * 60)
            print("扫描完成！")
            print("=" * 60)
            print(f"主卡组: {len(result['main_deck'])} 张")
            print(f"额外卡组: {len(result['extra_deck'])} 张")
            print()
            print("卡片模板已自动保存到 data/templates/")
            print("卡组数据已保存到 data/decks/")
    
    elif choice == "2":
        scanner.calibrate_positions()
