"""
屏幕捕获模块 (MSS版)
使用 mss 替代 Win32 API 解决多显示器问题
"""
import cv2
import numpy as np
import win32gui
import mss
import time
from typing import Optional, Tuple
from loguru import logger


class ScreenCapture:
    """屏幕捕获类"""
    
    def __init__(self, window_title: str = "masterduel"):
        """
        初始化屏幕捕获
        
        Args:
            window_title: 游戏窗口标题关键词
        """
        self.window_title = window_title
        self.hwnd = None
        self.window_rect = None  # (left, top, right, bottom)
        self.sct = mss.mss()
        
        # 尝试找到窗口
        self.find_game_window()
        
    def find_game_window(self) -> bool:
        """
        查找游戏窗口
        
        Returns:
            是否找到窗口
        """
        try:
            # 1. 精确匹配
            self.hwnd = win32gui.FindWindow(None, self.window_title)
            
            # 2. 模糊匹配
            if not self.hwnd:
                self.hwnd = self._find_window_partial_match(self.window_title)
            
            if self.hwnd:
                # 获取窗口位置
                rect = win32gui.GetWindowRect(self.hwnd)
                # 处理Windows的DPI缩放导致的不可见边框（通常需要微调）
                # 这里我们假设从Win32 API获取的rect是准确的
                self.window_rect = rect
                
                title = win32gui.GetWindowText(self.hwnd)
                logger.info(f"找到窗口: {title} @ {rect}")
                return True
                
            logger.warning(f"未找到窗口: {self.window_title}")
            return False
            
        except Exception as e:
            logger.error(f"查找窗口出错: {e}")
            return False

    def _find_window_partial_match(self, search_title: str):
        """模糊匹配窗口标题"""
        search_lower = search_title.lower()
        found_hwnd = None
        
        def enum_handler(hwnd, results):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and search_lower in title.lower():
                    found_hwnd = hwnd
                    return False
            return True
        
        win32gui.EnumWindows(enum_handler, None)
        return found_hwnd

    def capture_window(self) -> Optional[np.ndarray]:
        """
        捕获窗口画面
        
        Returns:
            图像数据 (BGR格式)
        """
        if not self.hwnd:
            if not self.find_game_window():
                return None
        
        try:
            # 更新窗口位置（防止移动）
            rect = win32gui.GetWindowRect(self.hwnd)
            self.window_rect = rect
            
            # 计算客户区大小（去除标题栏和边框）
            # GetWindowRect包含边框，GetClientRect只包含内容但坐标是(0,0)
            # 简单起见，我们直接截取整个窗口区域，mss使用屏幕绝对坐标
            
            monitor = {
                "top": rect[1],
                "left": rect[0],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1]
            }
            
            # 检查尺寸合理性
            if monitor["width"] <= 0 or monitor["height"] <= 0:
                logger.warning("窗口最小化或尺寸无效")
                return None
            
            # 使用mss截取
            screenshot = self.sct.grab(monitor)
            
            # 转换为numpy数组 (BGRA -> BGR)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            return img
            
        except Exception as e:
            logger.error(f"截图失败: {e}")
            # 尝试重新查找窗口
            self.find_game_window()
            return None

    def get_window_size(self) -> Tuple[int, int]:
        """获取窗口大小"""
        if self.window_rect:
            w = self.window_rect[2] - self.window_rect[0]
            h = self.window_rect[3] - self.window_rect[1]
            return (w, h)
        return (0, 0)
        
    def activate_window(self):
        """激活并前置窗口"""
        if self.hwnd:
            try:
                # 尝试多种方法激活窗口
                import win32con
                
                # 如果最小化了，还原
                if win32gui.IsIconic(self.hwnd):
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                
                # 前置
                try:
                    win32gui.SetForegroundWindow(self.hwnd)
                except Exception:
                    # 有时候SetForegroundWindow会失败，尝试用Shell
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shell.SendKeys('%')
                    win32gui.SetForegroundWindow(self.hwnd)
                    
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"激活窗口失败: {e}")
