"""
卡片图像识别模块
使用模板匹配和特征匹配识别卡片
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from loguru import logger
import json


class CardImageRecognizer:
    """卡片图像识别器"""
    
    def __init__(self, template_dir: str = "data/templates"):
        """
        初始化识别器
        
        Args:
            template_dir: 卡片模板图像目录
        """
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # 卡片模板数据库 {card_id: {"name": "", "template": img, "features": {}}}
        self.card_templates = {}
        
        # 特征检测器（使用ORB，SIFT需要额外安装）
        self.feature_detector = cv2.ORB_create(nfeatures=500)
        
        # 特征匹配器
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # 加载已有模板
        self._load_templates()
        
        logger.info(f"卡片识别器初始化完成，已加载 {len(self.card_templates)} 张卡片模板")
    
    def detect_cards_in_image(self, image: np.ndarray, 
                              zone: str = "unknown") -> List[Dict]:
        """
        在图像中检测卡片
        
        Args:
            image: 输入图像（BGR格式）
            zone: 区域标识（hand/field/grave等）
            
        Returns:
            检测到的卡片列表
        """
        detected_cards = []
        
        # 预处理图像
        processed = self._preprocess_image(image)
        
        # 检测卡片轮廓/区域
        card_regions = self._detect_card_regions(processed)
        
        logger.info(f"在 {zone} 区域检测到 {len(card_regions)} 个卡片区域")
        
        # 识别每个卡片
        for i, region in enumerate(card_regions):
            card_img = self._extract_card_image(image, region)
            if card_img is None:
                continue
            
            # 识别卡片
            result = self.recognize_card(card_img)
            
            if result:
                result['zone'] = zone
                result['zone_index'] = i
                result['position'] = region  # (x, y, w, h)
                detected_cards.append(result)
        
        return detected_cards
    
    def recognize_card(self, card_image: np.ndarray, 
                      top_k: int = 3) -> Optional[Dict]:
        """
        识别单张卡片
        
        Args:
            card_image: 卡片图像
            top_k: 返回前k个最可能的匹配
            
        Returns:
            识别结果 {card_id, name, confidence, method}
        """
        if len(self.card_templates) == 0:
            logger.warning("没有可用的卡片模板，请先添加模板")
            return None
        
        # 提取卡片图像的艺术图部分（通常在卡片上半部分）
        art_region = self._extract_card_art(card_image)
        
        # 方法1：特征匹配（主要方法）
        feature_matches = self._match_by_features(art_region, top_k)
        
        # 方法2：模板匹配（辅助方法）
        template_matches = self._match_by_template(art_region, top_k)
        
        # 综合两种方法的结果
        final_result = self._combine_results(feature_matches, template_matches)
        
        if final_result:
            logger.info(f"识别到卡片: {final_result['name']} "
                       f"(置信度: {final_result['confidence']:.2f})")
        
        return final_result
    
    def add_card_template(self, card_image: np.ndarray, 
                         card_id: str, card_name: str):
        """
        添加卡片模板
        
        Args:
            card_image: 卡片图像
            card_id: 卡片ID
            card_name: 卡片名称
        """
        # 提取艺术图区域
        art_region = self._extract_card_art(card_image)
        
        # 提取特征
        keypoints, descriptors = self.feature_detector.detectAndCompute(art_region, None)
        
        # 保存模板
        template_data = {
            'card_id': card_id,
            'name': card_name,
            'art_image': art_region,
            'keypoints': keypoints,
            'descriptors': descriptors
        }
        
        self.card_templates[card_id] = template_data
        
        # 保存到磁盘
        self._save_template(card_id, card_name, art_region)
        
        logger.info(f"添加卡片模板: {card_name} (ID: {card_id})")
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        # 转灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 降噪
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 自适应阈值
        thresh = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return thresh
    
    def _detect_card_regions(self, processed_image: np.ndarray) -> List[Tuple]:
        """
        检测卡片区域
        
        Returns:
            区域列表 [(x, y, w, h), ...]
        """
        # 查找轮廓
        contours, _ = cv2.findContours(
            processed_image, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        regions = []
        for contour in contours:
            # 计算边界矩形
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤太小或太大的区域
            area = w * h
            if area < 1000 or area > processed_image.size * 0.5:
                continue
            
            # 检查宽高比（卡片通常是竖向的，约 0.7 的宽高比）
            aspect_ratio = w / h if h > 0 else 0
            if 0.5 < aspect_ratio < 0.9:  # 卡片的典型宽高比
                regions.append((x, y, w, h))
        
        return regions
    
    def _extract_card_image(self, image: np.ndarray, 
                           region: Tuple) -> Optional[np.ndarray]:
        """提取卡片图像"""
        x, y, w, h = region
        
        # 确保坐标在图像范围内
        h_img, w_img = image.shape[:2]
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        if w <= 0 or h <= 0:
            return None
        
        return image[y:y+h, x:x+w]
    
    def _extract_card_art(self, card_image: np.ndarray) -> np.ndarray:
        """
        提取卡片艺术图区域
        游戏王卡片的艺术图通常在上半部分
        """
        h, w = card_image.shape[:2]
        
        # 艺术图大约在卡片的上半部分（前60%）
        art_h = int(h * 0.6)
        art_region = card_image[0:art_h, :]
        
        return art_region
    
    def _match_by_features(self, query_image: np.ndarray, 
                          top_k: int = 3) -> List[Dict]:
        """使用特征匹配识别卡片"""
        # 提取查询图像的特征
        query_kp, query_desc = self.feature_detector.detectAndCompute(query_image, None)
        
        if query_desc is None:
            return []
        
        matches_list = []
        
        # 与每个模板匹配
        for card_id, template in self.card_templates.items():
            if template['descriptors'] is None:
                continue
            
            # 特征匹配
            matches = self.matcher.match(query_desc, template['descriptors'])
            
            # 计算匹配得分
            if len(matches) > 0:
                # 按距离排序，距离越小越好
                matches = sorted(matches, key=lambda x: x.distance)
                
                # 取前N个最佳匹配
                good_matches = matches[:min(50, len(matches))]
                
                # 计算平均距离（越小越好）
                avg_distance = np.mean([m.distance for m in good_matches])
                
                # 转换为置信度分数（0-1，越大越好）
                confidence = max(0, 1 - avg_distance / 100)
                
                matches_list.append({
                    'card_id': card_id,
                    'name': template['name'],
                    'confidence': confidence,
                    'match_count': len(good_matches),
                    'method': 'feature'
                })
        
        # 按置信度排序
        matches_list.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches_list[:top_k]
    
    def _match_by_template(self, query_image: np.ndarray, 
                          top_k: int = 3) -> List[Dict]:
        """使用模板匹配识别卡片"""
        matches_list = []
        
        # 调整查询图像大小
        query_resized = cv2.resize(query_image, (200, 120))
        
        for card_id, template in self.card_templates.items():
            template_img = template['art_image']
            template_resized = cv2.resize(template_img, (200, 120))
            
            # 模板匹配
            result = cv2.matchTemplate(
                query_resized, template_resized, 
                cv2.TM_CCOEFF_NORMED
            )
            
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            matches_list.append({
                'card_id': card_id,
                'name': template['name'],
                'confidence': float(max_val),
                'method': 'template'
            })
        
        # 按置信度排序
        matches_list.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches_list[:top_k]
    
    def _combine_results(self, feature_matches: List[Dict], 
                        template_matches: List[Dict]) -> Optional[Dict]:
        """综合两种匹配方法的结果"""
        if not feature_matches and not template_matches:
            return None
        
        # 创建综合评分
        combined_scores = {}
        
        # 特征匹配权重更高（0.7）
        for match in feature_matches:
            card_id = match['card_id']
            combined_scores[card_id] = {
                'card_id': card_id,
                'name': match['name'],
                'score': match['confidence'] * 0.7,
                'feature_conf': match['confidence']
            }
        
        # 模板匹配权重较低（0.3）
        for match in template_matches:
            card_id = match['card_id']
            if card_id in combined_scores:
                combined_scores[card_id]['score'] += match['confidence'] * 0.3
                combined_scores[card_id]['template_conf'] = match['confidence']
            else:
                combined_scores[card_id] = {
                    'card_id': card_id,
                    'name': match['name'],
                    'score': match['confidence'] * 0.3,
                    'template_conf': match['confidence']
                }
        
        # 选择得分最高的
        best_match = max(combined_scores.values(), key=lambda x: x['score'])
        
        return {
            'card_id': best_match['card_id'],
            'name': best_match['name'],
            'confidence': best_match['score'],
            'method': 'combined'
        }
    
    def _save_template(self, card_id: str, card_name: str, art_image: np.ndarray):
        """保存模板到磁盘"""
        # 保存图像
        img_path = self.template_dir / f"{card_id}.png"
        cv2.imwrite(str(img_path), art_image)
        
        # 保存元数据
        meta_path = self.template_dir / f"{card_id}.json"
        metadata = {
            'card_id': card_id,
            'name': card_name
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _load_templates(self):
        """从磁盘加载模板"""
        if not self.template_dir.exists():
            return
        
        # 查找所有模板文件
        for img_path in self.template_dir.glob("*.png"):
            card_id = img_path.stem
            meta_path = img_path.with_suffix('.json')
            
            if not meta_path.exists():
                continue
            
            # 加载元数据
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 加载图像
            art_image = cv2.imread(str(img_path))
            
            # 提取特征
            keypoints, descriptors = self.feature_detector.detectAndCompute(
                art_image, None
            )
            
            # 添加到模板库
            self.card_templates[card_id] = {
                'card_id': card_id,
                'name': metadata['name'],
                'art_image': art_image,
                'keypoints': keypoints,
                'descriptors': descriptors
            }


# 测试代码
if __name__ == "__main__":
    logger.info("测试卡片图像识别器...")
    
    recognizer = CardImageRecognizer()
    
    # 示例：添加一个模板（需要实际的卡片图像）
    # card_img = cv2.imread("path/to/card.png")
    # recognizer.add_card_template(card_img, "12345", "青眼白龙")
    
    logger.info(f"当前模板数: {len(recognizer.card_templates)}")
