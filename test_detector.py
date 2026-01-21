"""
测试MasterDuelDetector检测功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import cv2
import json
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG")

# 加载卡组信息
deck_file = project_root / "data" / "standard_deck.json"
if deck_file.exists():
    with open(deck_file, 'r', encoding='utf-8') as f:
        deck_data = json.load(f)
    
    # 提取所有卡片名称
    card_names = []
    for card in deck_data.get('main_deck', []):
        if card['name'] not in card_names:
            card_names.append(card['name'])
    for card in deck_data.get('extra_deck', []):
        if card['name'] not in card_names:
            card_names.append(card['name'])
    
    logger.info(f"加载了 {len(card_names)} 个不同的卡片名称")
else:
    logger.error(f"卡组文件不存在: {deck_file}")
    card_names = []

# 导入检测器
try:
    from src.vision.master_duel_detector import MasterDuelDetector
    detector = MasterDuelDetector(deck_card_names=card_names)
    logger.info("MasterDuelDetector 初始化成功")
except Exception as e:
    logger.error(f"初始化检测器失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试图片路径 - 仅测试用户上传的决斗截图
test_images = [
    # 用户上传的决斗截图
    r"C:\Users\kyosh\.gemini\antigravity\brain\9d803c74-ae04-49ca-a137-44b6761889e2\uploaded_image_1768988337887.jpg",
]

for img_path in test_images:
    if Path(img_path).exists():
        logger.info(f"\n=== 测试图片: {Path(img_path).name} ===")
        
        # 加载图片
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"无法加载图片: {img_path}")
            continue
        
        h, w = img.shape[:2]
        logger.info(f"图片尺寸: {w}x{h}")
        
        # 测试UI状态检测
        ui_state = detector.detect_ui_state(img)
        logger.info(f"UI状态: {ui_state}")
        
        # 如果检测到有卡片信息，尝试OCR识别
        if ui_state.get('has_card_info'):
            # 提取卡片名称区域
            card_name_region = ui_state.get('card_name_region')
            if card_name_region:
                x, y, w_r, h_r = card_name_region
                roi = img[y:y+h_r, x:x+w_r]
                
                # 保存ROI用于调试
                cv2.imwrite(str(project_root / "debug_card_name_roi.png"), roi)
                logger.info(f"卡片名称区域已保存到 debug_card_name_roi.png")
                
                # OCR识别
                ocr_result = detector.ocr_card_name(roi)
                logger.info(f"OCR识别结果: {ocr_result}")
                
                # 卡片匹配
                if ocr_result.get('text'):
                    match_name, match_score = detector.match_card_name(ocr_result['text'])
                    logger.info(f"卡片匹配: {match_name} (分数: {match_score:.2f})")
        
        # 测试阶段检测
        phase = detector.detect_game_phase(img)
        logger.info(f"当前阶段: {phase}")
        
        # 测试LP检测
        my_lp, opp_lp = detector.detect_lp(img)
        logger.info(f"LP: 我方 {my_lp} vs 对手 {opp_lp}")
        
        # 保存区域调试图
        debug_img = img.copy()
        for region_name, region_coords in detector.REGIONS.items():
            x_pct, y_pct, w_pct, h_pct = region_coords
            x = int(w * x_pct)
            y = int(h * y_pct)
            rw = int(w * w_pct)
            rh = int(h * h_pct)
            cv2.rectangle(debug_img, (x, y), (x+rw, y+rh), (0, 255, 0), 2)
            cv2.putText(debug_img, region_name, (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        debug_output = str(project_root / "debug_regions.png")
        cv2.imwrite(debug_output, debug_img)
        logger.info(f"区域标注图已保存到 {debug_output}")
        
    else:
        logger.warning(f"图片不存在: {img_path}")

logger.info("\n测试完成！")
