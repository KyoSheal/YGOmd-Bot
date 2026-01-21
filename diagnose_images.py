import cv2
import numpy as np
import os

def check_image(filename):
    if not os.path.exists(filename):
        print(f"❌ {filename} 不存在")
        return
    
    img = cv2.imread(filename)
    if img is None:
        print(f"❌ {filename} 无法读取")
        return
        
    print(f"📄 {filename}:")
    print(f"  尺寸: {img.shape}")
    print(f"  平均亮度: {np.mean(img):.2f}")
    print(f"  最大值: {np.max(img)}")
    print(f"  最小值: {np.min(img)}")
    
    if len(img.shape) == 2 or img.shape[2] == 1:
        non_zero = cv2.countNonZero(img)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        non_zero = cv2.countNonZero(gray)
        
    print(f"  非零像素数: {non_zero} ({non_zero/img.size*100:.2f}%)")
    print("-" * 30)

print("🖼️ 图像诊断报告:")
print("-" * 30)
check_image("debug_screenshot_full.png")
check_image("debug_deck_region.png")
check_image("debug_edges_closed.png")
check_image("debug_detection.png")
