"""
深度调试投影检测算法
"""
import cv2
import numpy as np
from pathlib import Path

# 读取截图
screenshot = cv2.imread('debug_screenshot_full.png')
h, w = screenshot.shape[:2]

# 区域定义
deck_area = {
    'x_start': 0.25,
    'x_end': 0.65,
    'y_start': 0.18,
    'y_end': 0.96,
}

x1 = int(w * deck_area['x_start'])
x2 = int(w * deck_area['x_end'])
y1 = int(h * deck_area['y_start'])
y2 = int(h * deck_area['y_end'])

deck_region = screenshot[y1:y2, x1:x2]

# 边缘检测
gray = cv2.cvtColor(deck_region, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
gray = clahe.apply(gray)

sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)

edges_y = cv2.convertScaleAbs(sobel_y)
edges_x = cv2.convertScaleAbs(sobel_x)

_, thresh_y = cv2.threshold(edges_y, 20, 255, cv2.THRESH_BINARY)
_, thresh_x = cv2.threshold(edges_x, 20, 255, cv2.THRESH_BINARY)

# 投影
h_proj = np.sum(thresh_y, axis=1)
v_proj = np.sum(thresh_x, axis=0)

print("=" * 60)
print("投影分析调试")
print("=" * 60)
print(f"deck_region shape: {deck_region.shape}")
print(f"h_proj shape: {h_proj.shape}, max: {h_proj.max()}, mean: {h_proj.mean()}")
print(f"v_proj shape: {v_proj.shape}, max: {v_proj.max()}, mean: {v_proj.mean()}")
print()

# 保存投影可视化
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 1, figsize=(15, 10))

# 水平投影（行）
axes[0].plot(h_proj)
axes[0].set_title('Horizontal Projection (Rows)')
axes[0].axhline(y=h_proj.max() * 0.05, color='r', linestyle='--', label='Threshold 5%')
axes[0].axhline(y=h_proj.max() * 0.08, color='g', linestyle='--', label='Threshold 8%')
axes[0].legend()
axes[0].grid(True)

# 垂直投影（列）
axes[1].plot(v_proj)
axes[1].set_title('Vertical Projection (Columns)')
axes[1].axhline(y=v_proj.max() * 0.05, color='r', linestyle='--', label='Threshold 5%')
axes[1].axhline(y=v_proj.max() * 0.08, color='g', linestyle='--', label='Threshold 8%')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig('debug_projection.png', dpi=150)
print("✅ 保存投影可视化: debug_projection.png")

# 分析峰值
region_h, region_w = deck_region.shape[:2]
est_card_h = region_h / 15
est_card_w = region_w / 12

print(f"\n估计卡片高度: {est_card_h:.1f}px")
print(f"估计卡片宽度: {est_card_w:.1f}px")
print(f"min_height (0.3x): {est_card_h*0.3:.1f}px")
print(f"min_width (0.3x): {est_card_w*0.3:.1f}px")
