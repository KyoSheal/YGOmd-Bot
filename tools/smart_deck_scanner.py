"""
智能卡组扫描器 V2
使用图像识别动态检测卡片位置，不依赖固定坐标
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


class SmartDeckScanner:
    """智能卡组扫描器"""
    
    def __init__(self):
        """初始化扫描器"""
        self.screen_capture = ScreenCapture("masterduel")
        # 1. 鼠标加速：使用 fastest 且减少 humanize 延迟
        self.mouse = MouseController(speed='fastest', humanize=False)
        self.recognizer = CardImageRecognizer()
        
        # 2. 区域调整：必须避开顶部的按钮（撤销、删除等）
        # 之前的 y_start=0.10 太靠上了，包含了解散卡组按钮
        self.deck_area = {
            'x_start': 0.25,  
            'x_end': 0.65,    # 修复：排除第11列（预览面板）
            'y_start': 0.18,  # 下移避开顶部工具栏
            'y_end': 0.96,    # 稍微加深
        }
        
        # 左侧详情区域
        self.detail_area = {
            'x': 0.02,
            'y': 0.05,
            'width': 0.20,
            'height': 0.60
        }
        
    def scan_deck(self, deck_name: str = "auto_scan") -> dict:
        """智能扫描卡组"""
        logger.info("=" * 60)
        logger.info(f"开始智能扫描卡组: {deck_name}")
        logger.info("=" * 60)
        
        if not self.screen_capture.find_game_window():
            logger.error("未找到游戏窗口！")
            return None
        
        window_rect = self.screen_capture.window_rect
        self.window_x = window_rect[0]
        self.window_y = window_rect[1]
        
        screenshot = self.screen_capture.capture_window()
        if screenshot is None:
            logger.error("截图失败！")
            return None
        
        logger.info("检测卡片位置...")
        card_positions = self._detect_card_positions(screenshot)
        
        logger.info(f"检测到 {len(card_positions)} 个可能的卡片位置")
        
        if len(card_positions) == 0:
            logger.error("未检测到卡片！请检查 debug_detection.png")
            return None
        
        deck_data = {
            'deck_name': deck_name,
            'cards': [],
            'timestamp': time.time()
        }
        
        # 去重集合 (基于位置)
        clicked_positions = set()
        
        for i, (cx, cy) in enumerate(card_positions, 1):
            # 简单的距离去重，防止重复点击同一张卡
            pos_key = (cx // 10, cy // 10) # 10像素网格去重
            if pos_key in clicked_positions:
                continue
            clicked_positions.add(pos_key)
            
            # 进度日志
            if i % 5 == 0:
                logger.info(f"进度: {i}/{len(card_positions)}...")
            
            abs_x = self.window_x + cx
            abs_y = self.window_y + cy
            
            self.mouse.click(abs_x, abs_y)
            # 减少等待时间：0.4s -> 0.15s (只要界面刷新这一瞬间就行)
            # 实际上游戏里点击卡片切换详情是非常快的
            time.sleep(0.15)
            
            detail_screenshot = self.screen_capture.capture_window()
            if detail_screenshot is None: continue
            
            # 识别卡片
            # 既然OCR乱码，我们这里暂时只记录索引，或者给个Unknown名字
            # 重要的是我们拿到了图片模板
            card_info = self._recognize_card_from_detail(detail_screenshot)
            
            # 如果 OCR 结果太乱，就用 Card_Index 临时命名
            # 防止 JSON 文件里全是乱码
            final_name = card_info['name'] if card_info else f"Card_{i}"
            if "Card_" in final_name or len(final_name) > 20: 
                 # 如果名字还是很长的一串乱码，强制改名
                 if len(final_name) > 30 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in final_name):
                     final_name = f"Card_{i:02d}_{int(time.time())}"
            
            deck_data['cards'].append({
                'index': i,
                'name': final_name,
                'x': cx,
                'y': cy
            })
            
            logger.info(f"Card {i}: {final_name}")
        
        self._save_deck(deck_data)
        return deck_data
    
    def _detect_card_positions(self, screenshot: np.ndarray) -> list:
        """
        使用轮廓检测法检测卡片位置
        """
        h, w = screenshot.shape[:2]
        
        # 保存调试图
        cv2.imwrite("debug_screenshot_full.png", screenshot)
        
        # 区域截取
        x1 = int(w * self.deck_area['x_start'])
        x2 = int(w * self.deck_area['x_end'])
        y1 = int(h * self.deck_area['y_start'])
        y2 = int(h * self.deck_area['y_end'])
        
        deck_region = screenshot[y1:y2, x1:x2]
        debug_img = deck_region.copy()
        region_h, region_w = deck_region.shape[:2]
        
        # 1. 预处理
        gray = cv2.cvtColor(deck_region, cv2.COLOR_BGR2GRAY)
        
        # 2. 边缘检测
        edges = cv2.Canny(gray, 30, 100)
        
        # 3. 形态学操作 - 闭运算连接断裂的边缘
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # 4. 查找轮廓
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 5. 过滤轮廓 - 找到卡片大小的矩形
        est_card_w = region_w / 12
        est_card_h = region_h / 6  # 改为6行（看debug图实际约5-6行）
        
        min_w = est_card_w * 0.4  # 放宽到0.4
        max_w = est_card_w * 2.0  # 放宽到2.0
        min_h = est_card_h * 0.4  # 放宽到0.4
        max_h = est_card_h * 2.0  # 放宽到2.0
        
        min_area = min_w * min_h * 0.5  # 降低最小面积要求
        
        card_rects = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = h / w if w > 0 else 0
            
            # 卡片应该是竖直的矩形，高度>宽度
            if (min_w < w < max_w and 
                min_h < h < max_h and 
                area > min_area and
                0.8 < aspect_ratio < 2.5):  # 放宽长宽比范围
                card_rects.append((x, y, w, h))
        
        logger.info(f"轮廓检测: 找到 {len(contours)} 个轮廓, 过滤后 {len(card_rects)} 个卡片")
        
        # 6. 如果轮廓检测失败，使用网格扫描作为后备
        if len(card_rects) < 40:  # 降低阈值到40
            logger.warning("轮廓检测卡片数量不足，使用网格扫描后备方案")
            card_rects = self._grid_scan_fallback(deck_region)
        
        # 7. 去重并排序
        card_rects = self._merge_overlapping_rects(card_rects)
        
        # 8. 按行排序（从上到下，从左到右）
        card_rects.sort(key=lambda r: (r[1] // int(est_card_h), r[0]))
        
        # 9. 转换为中心点坐标
        card_positions = []
        for i, (x, y, w, h) in enumerate(card_rects, 1):
            cx = x + w // 2
            cy = y + h // 2
            
            # 转换回全屏坐标
            abs_cx = x1 + cx
            abs_cy = y1 + cy
            
            card_positions.append((abs_cx, abs_cy))
            
            # 调试可视化
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(debug_img, str(i), (x+5, y+25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imwrite("debug_detection.png", debug_img)
        return card_positions
    
    def _grid_scan_fallback(self, deck_region: np.ndarray) -> list:
        """网格扫描后备方案"""
        region_h, region_w = deck_region.shape[:2]
        
        # 固定网格：10列 x 6行
        cols = 10
        rows = 6
        
        card_w = region_w // cols
        card_h = region_h // rows
        
        rects = []
        for row in range(rows):
            for col in range(cols):
                x = col * card_w + card_w // 4
                y = row * card_h + card_h // 4
                w = card_w // 2
                h = card_h // 2
                
                # 检查该位置是否有内容
                roi = deck_region[y:y+h, x:x+w]
                if roi.size == 0:
                    continue
                    
                mean_intensity = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).mean()
                if mean_intensity > 20:  # 不是纯黑
                    rects.append((x, y, w, h))
        
        logger.info(f"网格扫描后备: 找到 {len(rects)} 个位置")
        return rects
    
    def _merge_overlapping_rects(self, rects: list) -> list:
        """合并重叠的矩形"""
        if not rects:
            return []
        
        # 简单的非极大值抑制
        rects = sorted(rects, key=lambda r: r[2] * r[3], reverse=True)  # 按面积排序
        
        merged = []
        used = [False] * len(rects)
        
        for i, (x1, y1, w1, h1) in enumerate(rects):
            if used[i]:
                continue
                
            # 检查是否与已有矩形重叠
            overlap = False
            for (x2, y2, w2, h2) in merged:
                # 计算IoU
                ix1 = max(x1, x2)
                iy1 = max(y1, y2)
                ix2 = min(x1+w1, x2+w2)
                iy2 = min(y1+h1, y2+h2)
                
                if ix1 < ix2 and iy1 < iy2:
                    inter_area = (ix2 - ix1) * (iy2 - iy1)
                    union_area = w1*h1 + w2*h2 - inter_area
                    iou = inter_area / union_area if union_area > 0 else 0
                    
                    if iou > 0.3:  # 重叠超过30%
                        overlap = True
                        break
            
            if not overlap:
                merged.append((x1, y1, w1, h1))
                used[i] = True
        
        return merged
    
    
    def _recognize_card_from_detail(self, screenshot: np.ndarray) -> dict:
        """从左侧详情区域识别卡片"""
        h, w = screenshot.shape[:2]
        
        # 提取详情区域
        x1 = int(w * self.detail_area['x'])
        y1 = int(h * self.detail_area['y'])
        w_detail = int(w * self.detail_area['width'])
        h_detail = int(h * self.detail_area['height'])
        
        detail_img = screenshot[y1:y1+h_detail, x1:x1+w_detail]
        
        # 方法1：图像识别
        if len(self.recognizer.card_templates) > 0:
            result = self.recognizer.recognize_card(detail_img)
            if result and result['confidence'] > 0.7:
                # 保存模板
                self._save_template(detail_img, result['name'])
                return result
        
        # 方法2：OCR识别卡名
        card_name = self._ocr_card_name(screenshot)
        
        if card_name:
            # 保存模板
            self._save_template(detail_img, card_name)
            return {'name': card_name, 'confidence': 0.8, 'method': 'ocr'}
        
        # 都失败了，至少保存图像
        self._save_template(detail_img, f"unknown_{int(time.time())}")
        
        return None
    
    def _ocr_card_name(self, screenshot: np.ndarray) -> str:
        """OCR识别卡片名称"""
        try:
            import pytesseract
            import re
            
            h, w = screenshot.shape[:2]
            
            # 策略：使用颜色检测找到紫色标题栏
            hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
            
            # 检测紫色范围（H: 280-320度 -> 140-160）
            lower_purple = np.array([140, 50, 50])
            upper_purple = np.array([160, 255, 255])
            purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)
            
            # 形态学操作去噪
            kernel = np.ones((5, 5), np.uint8)
            purple_mask = cv2.morphologyEx(purple_mask, cv2.MORPH_CLOSE, kernel)
            purple_mask = cv2.morphologyEx(purple_mask, cv2.MORPH_OPEN, kernel)
            
            # 找到最大的紫色区域
            contours, _ = cv2.findContours(purple_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                logger.debug("未检测到紫色标题栏，使用默认区域")
                name_x = int(w * 0.015)
                name_y = int(h * 0.055)
                name_w = int(w * 0.35)
                name_h = int(h * 0.055)
                name_img = screenshot[name_y:name_y+name_h, name_x:name_x+name_w]
            else:
                # 找到最大的紫色轮廓（应该是标题栏）
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w_box, h_box = cv2.boundingRect(largest_contour)
                
                logger.debug(f"检测到紫色区域: x={x}, y={y}, w={w_box}, h={h_box}")
                
                # 裁剪出紫色标题栏（加一点padding）
                pad = 5
                name_x = max(0, x - pad)
                name_y = max(0, y - pad)
                name_w = min(w - name_x, w_box + 2*pad)
                name_h = min(h - name_y, h_box + 2*pad)
                
                name_img = screenshot[name_y:name_y+name_h, name_x:name_x+name_w]
            
            # 保存调试图
            debug_path = f"debug_ocr_{int(time.time()*1000)}.png"
            cv2.imwrite(debug_path, name_img)
            
            # 预处理管线
            # 关键：紫色背景 + 白色文字
            # 策略1：使用HSV颜色空间提取白色文字
            hsv = cv2.cvtColor(name_img, cv2.COLOR_BGR2HSV)
            
            # 白色范围（高亮度，低饱和度）
            lower_white = np.array([0, 0, 200])
            upper_white = np.array([180, 30, 255])
            white_mask = cv2.inRange(hsv, lower_white, upper_white)
            
            # 应用mask
            white_text = cv2.bitwise_and(name_img, name_img, mask=white_mask)
            gray = cv2.cvtColor(white_text, cv2.COLOR_BGR2GRAY)
            
            # 1. 放大 (4倍)
            scale = 4
            scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            
            # 2. 反转（让文字变成黑色）
            inverted = cv2.bitwise_not(scaled)
            
            # 3. 二值化
            _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 4. 降噪
            denoised = cv2.medianBlur(binary, 3)
            
            candidates = [denoised]
            
            # 策略2：也试试直接转灰度
            gray_direct = cv2.cvtColor(name_img, cv2.COLOR_BGR2GRAY)
            scaled2 = cv2.resize(gray_direct, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            _, bin2 = cv2.threshold(scaled2, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            candidates.append(bin2)

            best_name = ""
            max_len = 0
            
            for i, binary in enumerate(candidates):
                # OCR 配置优化：使用LSTM OCR引擎(oem 1)，单行文本模式(psm 7)
                name = pytesseract.image_to_string(
                    binary,
                    lang='chi_sim+eng',  # 同时支持中文和英文
                    config='--oem 1 --psm 7 -c preserve_interword_spaces=0'
                ).strip()
                
                # 清洗字符：只保留中文、数字、英文字母、常见标点
                # unicode范围: \u4e00-\u9fa5 (中文汉字)
                clean_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9·•、，。！？]', '', name)
                
                logger.debug(f"OCR候选 {i+1}: raw='{name}' -> clean='{clean_name}'")
                
                if len(clean_name) > max_len:
                    max_len = len(clean_name)
                    best_name = clean_name
            
            # 额外验证：如果识别结果太短或太长，可能是错误的
            if best_name and 2 <= len(best_name) <= 25:
                return best_name
                
        except Exception as e:
            logger.debug(f"OCR失败: {e}")
        
        return None
    
    def _save_template(self, card_img: np.ndarray, card_name: str):
        """保存卡片模板"""
        # 提取艺术图部分
        h, w = card_img.shape[:2]
        art_h = int(h * 0.6)
        art_img = card_img[0:art_h, :]
        
        card_id = str(abs(hash(card_name)) % 10000000)
        
        template_dir = Path("data/templates")
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存图像
        img_path = template_dir / f"{card_id}.png"
        cv2.imwrite(str(img_path), art_img)
        
        # 保存元数据
        meta_path = template_dir / f"{card_id}.json"
        metadata = {
            'card_id': card_id,
            'name': card_name,
            'auto_scanned': True,
            'smart_scan': True
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
        
        logger.info(f"✅ 卡组已保存: {filepath}")
        logger.info(f"📊 总计: {len(deck_data['cards'])} 张卡片")


# 主程序
if __name__ == "__main__":
    print("=" * 60)
    print("智能卡组扫描器 V2.0 🤖")
    print("=" * 60)
    print()
    print("✨ 新特性:")
    print("  - 自动检测卡片位置，无需固定坐标")
    print("  - 适应任何卡组数量（主卡组+额外卡组）")
    print("  - 自动按顺序扫描")
    print()
    print("📋 使用说明:")
    print("1. 启动游戏并进入卡组编辑界面")
    print("2. 确保卡组完全可见")
    print("3. 不要移动鼠标，让Bot自动操作")
    print()
    
    deck_name = input("请输入卡组名称: ").strip()
    if not deck_name:
        deck_name = f"deck_{int(time.time())}"
    
    print()
    print("准备开始...")
    input("按Enter开始扫描...")
    
    scanner = SmartDeckScanner()
    result = scanner.scan_deck(deck_name)
    
    if result:
        print()
        print("=" * 60)
        print("✅ 扫描完成！")
        print("=" * 60)
        print(f"📦 卡组: {result['deck_name']}")
        print(f"📊 卡片数: {len(result['cards'])}")
        print()
        print("💾 已保存:")
        print(f"  - 卡组数据: data/decks/{result['deck_name']}.json")
        print(f"  - 卡片模板: data/templates/")
        print()
        
        # 显示识别的卡片
        print("识别的卡片:")
        for i, card in enumerate(result['cards'][:10], 1):  # 只显示前10张
            print(f"  {i}. {card['name']}")
        if len(result['cards']) > 10:
            print(f"  ... 还有 {len(result['cards']) - 10} 张")
