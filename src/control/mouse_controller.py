"""
高级输入控制模块
提供更接近真实用户行为的输入操作
支持多种输入方式：鼠标模拟、Windows API、触摸模拟
"""
import pyautogui
import time
import random
import numpy as np
import ctypes
from ctypes import wintypes, Structure, c_long, c_ulong, c_short, c_ushort, byref
from typing import Tuple, Optional, List
from loguru import logger


# Windows API 常量和结构体
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

class MOUSEINPUT(Structure):
    _fields_ = [("dx", c_long),
                ("dy", c_long),
                ("mouseData", c_ulong),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", ctypes.POINTER(c_ulong))]

class INPUT(Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [("type", c_ulong),
                ("_input", _INPUT)]


class AdvancedInputController:
    """高级输入控制器 - 使用 Windows API"""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # 获取屏幕尺寸
        self.screen_width = self.user32.GetSystemMetrics(0)
        self.screen_height = self.user32.GetSystemMetrics(1)
        
    def _to_absolute_coords(self, x: int, y: int) -> Tuple[int, int]:
        """转换为绝对坐标系统"""
        abs_x = int(x * 65535 / self.screen_width)
        abs_y = int(y * 65535 / self.screen_height)
        return abs_x, abs_y
    
    def send_mouse_input(self, x: int, y: int, flags: int):
        """发送鼠标输入事件"""
        abs_x, abs_y = self._to_absolute_coords(x, y)
        
        extra = c_ulong(0)
        ii_ = INPUT()
        ii_.type = INPUT_MOUSE
        ii_.mi.dx = abs_x
        ii_.mi.dy = abs_y
        ii_.mi.mouseData = 0
        ii_.mi.dwFlags = flags
        ii_.mi.time = 0
        ii_.mi.dwExtraInfo = ctypes.pointer(extra)
        
        self.user32.SendInput(1, ctypes.byref(ii_), ctypes.sizeof(ii_))
    
    def click_at(self, x: int, y: int, button: str = "left"):
        """在指定位置点击"""
        # 移动到目标位置
        self.send_mouse_input(x, y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        time.sleep(random.uniform(0.01, 0.03))
        
        # 按下和释放
        if button == "left":
            self.send_mouse_input(x, y, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE)
            time.sleep(random.uniform(0.05, 0.15))
            self.send_mouse_input(x, y, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE)
        elif button == "right":
            self.send_mouse_input(x, y, MOUSEEVENTF_RIGHTDOWN | MOUSEEVENTF_ABSOLUTE)
            time.sleep(random.uniform(0.05, 0.15))
            self.send_mouse_input(x, y, MOUSEEVENTF_RIGHTUP | MOUSEEVENTF_ABSOLUTE)
    
    def drag_from_to(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                     duration: float = 0.5):
        """拖拽操作"""
        # 移动到起始位置
        self.send_mouse_input(start_x, start_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        time.sleep(0.05)
        
        # 按下鼠标
        self.send_mouse_input(start_x, start_y, MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE)
        time.sleep(0.05)
        
        # 生成拖拽路径
        steps = max(10, int(duration * 60))  # 60 FPS
        for i in range(steps):
            t = i / (steps - 1)
            # 使用缓动函数使移动更自然
            t_eased = self._ease_in_out_cubic(t)
            
            current_x = int(start_x + (end_x - start_x) * t_eased)
            current_y = int(start_y + (end_y - start_y) * t_eased)
            
            self.send_mouse_input(current_x, current_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
            time.sleep(duration / steps)
        
        # 释放鼠标
        self.send_mouse_input(end_x, end_y, MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE)
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """三次缓动函数"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2


class TouchGestureSimulator:
    """触摸手势模拟器"""
    
    def __init__(self, input_controller: AdvancedInputController):
        self.input_controller = input_controller
    
    def tap(self, x: int, y: int, pressure: float = 0.5):
        """模拟触摸点击"""
        # 添加轻微的随机偏移模拟真实触摸
        offset_x = random.randint(-2, 2)
        offset_y = random.randint(-2, 2)
        
        actual_x = x + offset_x
        actual_y = y + offset_y
        
        self.input_controller.click_at(actual_x, actual_y)
        logger.debug(f"触摸点击: ({actual_x}, {actual_y}), 压力: {pressure}")
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, 
              duration: float = 0.3, steps: int = 20):
        """模拟滑动手势"""
        logger.debug(f"滑动手势: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        
        # 生成更自然的滑动路径
        path_points = self._generate_swipe_path(start_x, start_y, end_x, end_y, steps)
        
        # 开始触摸
        self.input_controller.send_mouse_input(
            start_x, start_y, 
            MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE
        )
        time.sleep(0.05)
        
        # 执行滑动
        step_duration = duration / len(path_points)
        for px, py in path_points:
            self.input_controller.send_mouse_input(
                px, py, 
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
            )
            time.sleep(step_duration)
        
        # 结束触摸
        self.input_controller.send_mouse_input(
            end_x, end_y, 
            MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE
        )
    
    def _generate_swipe_path(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                           steps: int) -> List[Tuple[int, int]]:
        """生成自然的滑动路径"""
        path = []
        
        for i in range(steps):
            t = i / (steps - 1)
            
            # 添加轻微的曲线和抖动
            base_x = start_x + (end_x - start_x) * t
            base_y = start_y + (end_y - start_y) * t
            
            # 添加自然的手指抖动
            jitter_x = random.uniform(-1, 1) * (1 - abs(t - 0.5) * 2)  # 中间抖动更大
            jitter_y = random.uniform(-1, 1) * (1 - abs(t - 0.5) * 2)
            
            path.append((int(base_x + jitter_x), int(base_y + jitter_y)))
        
        return path
    
    def long_press(self, x: int, y: int, duration: float = 1.0):
        """模拟长按"""
        logger.debug(f"长按: ({x}, {y}), 持续时间: {duration}s")
        
        self.input_controller.send_mouse_input(
            x, y, 
            MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE
        )
        time.sleep(duration)
        self.input_controller.send_mouse_input(
            x, y, 
            MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE
        )


class MouseController:
    """鼠标控制器"""
    
    def __init__(self, speed: str = "medium", humanize: bool = True):
        """
        初始化鼠标控制器
        
        Args:
            speed: 移动速度 (slow, medium, fast)
            humanize: 是否启用人性化移动
        """
        self.speed = speed
        self.humanize = humanize
        
        # 速度配置
        self.speed_map = {
            "slow": (0.3, 0.6),
            "medium": (0.15, 0.35),
            "fast": (0.05, 0.15)
        }
        
        # 禁用PyAutoGUI的安全机制（移到屏幕角落时暂停）
        pyautogui.FAILSAFE = False
        
    def _get_random_delay(self) -> float:
        """获取随机延迟"""
        min_delay, max_delay = self.speed_map.get(self.speed, (0.15, 0.35))
        return random.uniform(min_delay, max_delay)
    
    def _add_human_offset(self, x: int, y: int, radius: int = 3) -> Tuple[int, int]:
        """
        添加人性化偏移
        
        Args:
            x, y: 目标坐标
            radius: 偏移半径
            
        Returns:
            偏移后的坐标
        """
        if not self.humanize:
            return x, y
        
        offset_x = random.randint(-radius, radius)
        offset_y = random.randint(-radius, radius)
        return x + offset_x, y + offset_y
    
    def _bezier_curve(self, start: Tuple[int, int], end: Tuple[int, int], 
                      control_points: int = 2) -> list:
        """
        生成贝塞尔曲线路径
        
        Args:
            start: 起点
            end: 终点
            control_points: 控制点数量
            
        Returns:
            路径点列表
        """
        points = [start]
        
        # 生成控制点
        for _ in range(control_points):
            cx = random.randint(min(start[0], end[0]), max(start[0], end[0]))
            cy = random.randint(min(start[1], end[1]), max(start[1], end[1]))
            points.append((cx, cy))
        
        points.append(end)
        
        # 计算贝塞尔曲线
        n = len(points) - 1
        curve_points = []
        steps = max(10, int(np.linalg.norm(np.array(end) - np.array(start)) / 10))
        
        for t in np.linspace(0, 1, steps):
            x = sum(self._bernstein(n, i, t) * points[i][0] for i in range(n + 1))
            y = sum(self._bernstein(n, i, t) * points[i][1] for i in range(n + 1))
            curve_points.append((int(x), int(y)))
        
        return curve_points
    
    def _bernstein(self, n: int, i: int, t: float) -> float:
        """伯恩斯坦多项式"""
        from math import comb
        return comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
    
    def move_to(self, x: int, y: int, duration: Optional[float] = None):
        """
        移动鼠标到指定位置
        
        Args:
            x, y: 目标坐标
            duration: 移动持续时间
        """
        if duration is None:
            duration = self._get_random_delay()
        
        target_x, target_y = self._add_human_offset(x, y)
        
        if self.humanize:
            # 使用贝塞尔曲线移动
            current = pyautogui.position()
            path = self._bezier_curve(current, (target_x, target_y))
            
            step_duration = duration / len(path)
            for px, py in path:
                pyautogui.moveTo(px, py, duration=step_duration)
        else:
            pyautogui.moveTo(target_x, target_y, duration=duration)
        
        logger.debug(f"鼠标移动到: ({target_x}, {target_y})")
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = "left", clicks: int = 1):
        """
        点击鼠标
        
        Args:
            x, y: 点击坐标（None则点击当前位置）
            button: 按钮类型 (left, right, middle)
            clicks: 点击次数
        """
        if x is not None and y is not None:
            self.move_to(x, y)
        
        time.sleep(random.uniform(0.05, 0.15))  # 移动到点击的延迟
        pyautogui.click(button=button, clicks=clicks)
        logger.debug(f"点击: {button} 按钮, {clicks}次")
        time.sleep(self._get_random_delay())
    
    def drag_to(self, x: int, y: int, duration: Optional[float] = None):
        """
        拖拽到指定位置
        
        Args:
            x, y: 目标坐标
            duration: 拖拽持续时间
        """
        if duration is None:
            duration = random.uniform(0.3, 0.6)
        
        target_x, target_y = self._add_human_offset(x, y)
        
        pyautogui.mouseDown()
        time.sleep(0.05)
        
        if self.humanize:
            current = pyautogui.position()
            path = self._bezier_curve(current, (target_x, target_y))
            step_duration = duration / len(path)
            for px, py in path:
                pyautogui.moveTo(px, py, duration=step_duration)
        else:
            pyautogui.moveTo(target_x, target_y, duration=duration)
        
        time.sleep(0.05)
        pyautogui.mouseUp()
        logger.debug(f"拖拽到: ({target_x}, {target_y})")
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None):
        """
        滚动鼠标滚轮
        
        Args:
            clicks: 滚动量（正数向上，负数向下）
            x, y: 滚动位置（None则在当前位置）
        """
        if x is not None and y is not None:
            self.move_to(x, y)
        
        pyautogui.scroll(clicks)
        logger.debug(f"滚动: {clicks}")
        time.sleep(self._get_random_delay())
    
    def get_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置"""
        return pyautogui.position()


# 测试代码
if __name__ == "__main__":
    logger.info("测试鼠标控制器...")
    controller = MouseController(speed="medium", humanize=True)
    
    logger.info("当前鼠标位置: {}".format(controller.get_position()))
    logger.info("5秒后开始测试，请准备...")
    time.sleep(5)
    
    # 测试移动
    logger.info("测试移动...")
    controller.move_to(500, 500)
    
    # 测试点击
    logger.info("测试点击...")
    controller.click(600, 600)
    
    logger.info("测试完成！")
