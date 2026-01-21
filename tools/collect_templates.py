"""
卡片模板采集工具
用于从游戏截图中提取和保存卡片图像作为模板
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List
from loguru import logger
import json


class TemplateCollector:
    """卡片模板采集器"""
    
    def __init__(self, output_dir: str = "data/templates"):
        """
        初始化采集器
        
        Args:
            output_dir: 模板输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 已采集的卡片集合（避免重复）
        self.collected_cards = self._load_collected_list()
    
    def collect_from_screenshot(self, screenshot_path: str):
        """
        从截图中采集卡片模板
        
        Args:
            screenshot_path: 截图路径
        """
        image = cv2.imread(screenshot_path)
        if image is None:
            logger.error(f"无法加载截图: {screenshot_path}")
            return
        
        logger.info(f"开始从截图采集卡片模板: {screenshot_path}")
        
        # 显示图像并让用户选择卡片区域
        self._interactive_collect(image, screenshot_path)
    
    def _interactive_collect(self, image: np.ndarray, source: str):
        """
        交互式采集
        用户可以框选卡片区域
        """
        clone = image.copy()
        
        logger.info("请在图像中框选卡片区域...")
        logger.info("按 's' 保存当前选择，'r' 重置，'q' 退出")
        
        # 使用OpenCV的选择ROI功能
        cv2.namedWindow("Select Card", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Select Card", 1280, 720)
        
        while True:
            # 让用户选择区域
            roi = cv2.selectROI("Select Card", clone, fromCenter=False, showCrosshair=True)
            
            if roi[2] == 0 or roi[3] == 0:  # 没有选择区域
                logger.info("未选择区域，退出")
                break
            
            x, y, w, h = roi
            card_image = image[y:y+h, x:x+w]
            
            # 显示选择的卡片
            cv2.imshow("Selected Card", card_image)
            
            # 等待用户输入
            key = cv2.waitKey(0) & 0xFF
            
            if key == ord('s'):  # 保存
                self._save_card_template(card_image)
            elif key == ord('r'):  # 重置
                cv2.destroyWindow("Selected Card")
                continue
            elif key == ord('q'):  # 退出
                break
        
        cv2.destroyAllWindows()
    
    def _save_card_template(self, card_image: np.ndarray):
        """保存卡片模板"""
        # 提取卡片艺术图（上半部分）
        h, w = card_image.shape[:2]
        art_h = int(h * 0.6)
        art_image = card_image[0:art_h, :]
        
        # 显示并让用户输入卡片信息
        cv2.imshow("Card Art", art_image)
        
        print("\n" + "="*60)
        print("请输入卡片信息:")
        card_id = input("卡片ID (可选，直接回车跳过): ").strip()
        card_name = input("卡片名称: ").strip()
        
        if not card_name:
            logger.warning("未输入卡片名称，跳过保存")
            cv2.destroyWindow("Card Art")
            return
        
        # 如果没有ID，使用名称生成
        if not card_id:
            # 简单hash作为ID
            card_id = str(abs(hash(card_name)) % 10000000)
        
        # 检查是否已存在
        if card_id in self.collected_cards:
            logger.warning(f"卡片 {card_name} (ID: {card_id}) 已存在，跳过")
            cv2.destroyWindow("Card Art")
            return
        
        # 保存图像
        img_path = self.output_dir / f"{card_id}.png"
        cv2.imwrite(str(img_path), art_image)
        
        # 保存元数据
        meta_path = self.output_dir / f"{card_id}.json"
        metadata = {
            'card_id': card_id,
            'name': card_name,
            'collected_date': str(np.datetime64('now'))
        }
        
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 添加到已采集列表
        self.collected_cards[card_id] = card_name
        self._save_collected_list()
        
        logger.info(f"✅ 成功保存卡片模板: {card_name} (ID: {card_id})")
        print("="*60 + "\n")
        
        cv2.destroyWindow("Card Art")
    
    def auto_collect_from_hand(self, screenshot: np.ndarray, 
                               card_names: List[str]):
        """
        自动从手牌截图采集（已知卡片名称）
        
        Args:
            screenshot: 手牌截图
            card_names: 手牌中的卡片名称列表
        """
        # 检测手牌中的卡片区域
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤并排序卡片区域
        card_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = w / h if h > 0 else 0
            
            # 卡片的典型特征
            if area > 5000 and 0.5 < aspect_ratio < 0.9:
                card_regions.append((x, y, w, h))
        
        # 按x坐标排序（从左到右）
        card_regions.sort(key=lambda r: r[0])
        
        # 匹配卡片名称
        if len(card_regions) != len(card_names):
            logger.warning(f"检测到{len(card_regions)}张卡片，但提供了{len(card_names)}个名称")
            return
        
        for (x, y, w, h), name in zip(card_regions, card_names):
            card_image = screenshot[y:y+h, x:x+w]
            
            # 生成ID并保存
            card_id = str(abs(hash(name)) % 10000000)
            
            if card_id in self.collected_cards:
                logger.info(f"卡片 {name} 已存在，跳过")
                continue
            
            # 提取艺术图
            h_card, w_card = card_image.shape[:2]
            art_h = int(h_card * 0.6)
            art_image = card_image[0:art_h, :]
            
            # 保存
            img_path = self.output_dir / f"{card_id}.png"
            cv2.imwrite(str(img_path), art_image)
            
            meta_path = self.output_dir / f"{card_id}.json"
            metadata = {
                'card_id': card_id,
                'name': name,
                'collected_date': str(np.datetime64('now'))
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.collected_cards[card_id] = name
            logger.info(f"✅ 自动采集: {name}")
        
        self._save_collected_list()
    
    def _load_collected_list(self) -> dict:
        """加载已采集卡片列表"""
        list_path = self.output_dir / "collected_list.json"
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_collected_list(self):
        """保存已采集卡片列表"""
        list_path = self.output_dir / "collected_list.json"
        with open(list_path, 'w', encoding='utf-8') as f:
            json.dump(self.collected_cards, f, ensure_ascii=False, indent=2)
    
    def list_collected_cards(self):
        """列出已采集的卡片"""
        logger.info(f"\n已采集卡片 ({len(self.collected_cards)} 张):")
        for card_id, name in self.collected_cards.items():
            print(f"  - {name} (ID: {card_id})")


# 使用示例
if __name__ == "__main__":
    collector = TemplateCollector()
    
    print("卡片模板采集工具")
    print("="*60)
    print("1. 从截图交互式采集")
    print("2. 查看已采集卡片")
    print("="*60)
    
    choice = input("请选择 [1-2]: ").strip()
    
    if choice == "1":
        screenshot_path = input("请输入截图路径: ").strip()
        collector.collect_from_screenshot(screenshot_path)
    elif choice == "2":
        collector.list_collected_cards()
