"""
Pipeline 任务执行引擎
参考 MAA 的 Pipeline 设计
"""
import json
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


class TaskConfig:
    """任务配置"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.algorithm = config.get("algorithm", "MatchTemplate")
        self.action = config.get("action", "DoNothing")
        self.template = config.get("template", f"{name}.png")
        self.roi = config.get("roi", [0, 0, 1280, 720])
        self.templThreshold = config.get("templThreshold", 0.8)
        self.next = config.get("next", [])
        self.onErrorNext = config.get("onErrorNext", [])
        self.maxTimes = config.get("maxTimes", 999999)
        self.preDelay = config.get("preDelay", 0)
        self.postDelay = config.get("postDelay", 0)
        self.cache = config.get("cache", False)
        
        self.exec_count = 0
        self.cached_position = None
    
    def can_execute(self) -> bool:
        """是否可以执行"""
        return self.exec_count < self.maxTimes
    
    def increment_count(self):
        """增加执行计数"""
        self.exec_count += 1


class Pipeline:
    """Pipeline 执行引擎"""
    
    def __init__(self, controller, template_dir: str = "data/templates"):
        self.controller = controller
        self.template_dir = Path(template_dir)
        self.templates = {}
        self.tasks = {}
        self.screen_size = (1920, 1080)  # 实际屏幕尺寸
        
        self.load_templates()
    
    def load_templates(self):
        """加载所有模板"""
        if not self.template_dir.exists():
            logger.warning(f"模板目录不存在: {self.template_dir}")
            return
        
        for template_file in self.template_dir.rglob("*.png"):
            template_name = template_file.name
            template = cv2.imread(str(template_file))
            if template is not None:
                self.templates[template_name] = template
                logger.debug(f"加载模板: {template_name}")
    
    def load_task_config(self, config_file: str):
        """加载任务配置"""
        config_path = Path(config_file)
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_file}")
            return False
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        for task_name, task_config in config_data.items():
            self.tasks[task_name] = TaskConfig(task_name, task_config)
            logger.debug(f"加载任务: {task_name}")
        
        logger.success(f"✅ 加载了 {len(self.tasks)} 个任务")
        return True
    
    def scale_roi(self, roi: List[int]) -> List[int]:
        """
        将 ROI 从 1280x720 缩放到实际屏幕尺寸
        
        Args:
            roi: [x, y, width, height] 基于 1280x720
            
        Returns:
            缩放后的 [x, y, width, height]
        """
        scale_x = self.screen_size[0] / 1280
        scale_y = self.screen_size[1] / 720
        
        return [
            int(roi[0] * scale_x),
            int(roi[1] * scale_y),
            int(roi[2] * scale_x),
            int(roi[3] * scale_y)
        ]
    
    def recognize(self, screenshot: np.ndarray, task: TaskConfig) -> Optional[Tuple[int, int, float]]:
        """
        识别任务
        
        Returns:
            (x, y, confidence) 或 None
        """
        if task.algorithm != "MatchTemplate":
            logger.warning(f"不支持的算法: {task.algorithm}")
            return None
        
        # 检查缓存
        if task.cache and task.cached_position:
            logger.debug(f"使用缓存位置: {task.cached_position}")
            return task.cached_position
        
        # 获取模板
        template_name = task.template
        if template_name not in self.templates:
            logger.error(f"模板不存在: {template_name}")
            return None
        
        template = self.templates[template_name]
        
        # 缩放 ROI
        roi = self.scale_roi(task.roi)
        x, y, w, h = roi
        
        # 提取 ROI 区域
        roi_img = screenshot[y:y+h, x:x+w]
        
        if roi_img.size == 0:
            logger.error(f"ROI 区域无效: {roi}")
            return None
        
        # 模板匹配
        try:
            result = cv2.matchTemplate(roi_img, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= task.templThreshold:
                # 计算在原图中的位置（中心点）
                th, tw = template.shape[:2]
                center_x = x + max_loc[0] + tw // 2
                center_y = y + max_loc[1] + th // 2
                
                position = (center_x, center_y, max_val)
                
                # 缓存位置
                if task.cache:
                    task.cached_position = position
                
                return position
            
        except cv2.error as e:
            logger.error(f"模板匹配失败: {e}")
            return None
        
        return None
    
    def execute_action(self, task: TaskConfig, position: Optional[Tuple[int, int, float]]):
        """执行动作"""
        if task.action == "DoNothing":
            logger.debug("动作: DoNothing")
            return
        
        if task.action == "ClickSelf":
            if position:
                x, y, conf = position
                logger.info(f"点击: ({x}, {y}), 置信度: {conf:.3f}")
                
                # 执行点击
                from src.control.adb_controller import AndroidGestureController
                gesture = AndroidGestureController(self.controller)
                gesture.natural_tap(x, y)
            else:
                logger.warning("没有识别到目标，无法点击")
        else:
            logger.warning(f"不支持的动作: {task.action}")
    
    def run_task(self, task_name: str, max_depth: int = 50) -> bool:
        """
        运行任务
        
        Args:
            task_name: 任务名称
            max_depth: 最大递归深度
            
        Returns:
            是否成功
        """
        if max_depth <= 0:
            logger.error("任务链过深，可能存在循环")
            return False
        
        if task_name not in self.tasks:
            logger.error(f"任务不存在: {task_name}")
            return False
        
        task = self.tasks[task_name]
        
        if not task.can_execute():
            logger.warning(f"任务 {task_name} 已达到最大执行次数")
            return False
        
        logger.info(f"\n{'='*60}")
        logger.info(f"执行任务: {task_name}")
        logger.info(f"  算法: {task.algorithm}")
        logger.info(f"  动作: {task.action}")
        logger.info(f"  ROI: {task.roi}")
        logger.info(f"  阈值: {task.templThreshold}")
        logger.info(f"{'='*60}")
        
        # 前置延迟
        if task.preDelay > 0:
            logger.debug(f"前置延迟: {task.preDelay}ms")
            time.sleep(task.preDelay / 1000.0)
        
        # 截图
        screenshot = self.controller.screenshot()
        if screenshot is None:
            logger.error("截图失败")
            return False
        
        # 识别
        position = self.recognize(screenshot, task)
        
        if position:
            x, y, conf = position
            logger.success(f"✅ 识别成功: ({x}, {y}), 置信度: {conf:.3f}")
            
            # 执行动作
            self.execute_action(task, position)
            
            # 增加执行计数
            task.increment_count()
            
            # 后置延迟
            if task.postDelay > 0:
                logger.debug(f"后置延迟: {task.postDelay}ms")
                time.sleep(task.postDelay / 1000.0)
            
            # 执行 next 任务
            if task.next:
                for next_task_name in task.next:
                    logger.info(f"→ 执行下一个任务: {next_task_name}")
                    if self.run_task(next_task_name, max_depth - 1):
                        break
                    else:
                        logger.warning(f"任务 {next_task_name} 失败，尝试下一个")
            
            return True
        else:
            logger.warning(f"❌ 识别失败: {task_name}")
            
            # 如果是等待类任务（DoNothing），继续尝试
            if task.action == "DoNothing" and task.can_execute():
                logger.info("等待中，继续尝试...")
                time.sleep(0.5)
                return self.run_task(task_name, max_depth)
            
            # 执行 onErrorNext 任务
            if task.onErrorNext:
                logger.info(f"识别失败，执行 onErrorNext")
                for error_task_name in task.onErrorNext:
                    logger.info(f"→ 执行错误处理任务: {error_task_name}")
                    if self.run_task(error_task_name, max_depth - 1):
                        return True
                    else:
                        logger.warning(f"错误处理任务 {error_task_name} 失败")
            
            return False
    
    def run(self, start_task: str) -> bool:
        """
        运行 Pipeline
        
        Args:
            start_task: 起始任务名称
            
        Returns:
            是否成功
        """
        logger.info("=" * 60)
        logger.info("Pipeline 开始执行")
        logger.info(f"起始任务: {start_task}")
        logger.info("=" * 60)
        
        try:
            success = self.run_task(start_task)
            
            if success:
                logger.success("\n" + "=" * 60)
                logger.success("✅ Pipeline 执行成功")
                logger.success("=" * 60)
            else:
                logger.error("\n" + "=" * 60)
                logger.error("❌ Pipeline 执行失败")
                logger.error("=" * 60)
            
            return success
            
        except Exception as e:
            logger.error(f"Pipeline 异常: {e}")
            import traceback
            traceback.print_exc()
            return False
