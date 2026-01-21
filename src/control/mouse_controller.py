"""
鼠标控制模块
提供人性化的鼠标操作
"""
import pyautogui
import time
import random
import numpy as np
from typing import Tuple, Optional
from loguru import logger


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
