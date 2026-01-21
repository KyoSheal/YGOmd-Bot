"""
操作录制器 - Action Recorder
实时录制玩家的游戏操作并进行深度学习
"""
import cv2
import numpy as np
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from loguru import logger
import pyautogui

from .action_schema import (
    GameAction, ActionSequence, GameReplay,
    ActionType, Zone, GamePhase
)

# 尝试导入完整版本模块
try:
    from ..vision.master_duel_detector import MasterDuelDetector
    from ..core.window_manager import WindowManager
    FULL_VERSION = True
    logger.info("使用MasterDuelDetector进行游戏识别")
except ImportError as e:
    FULL_VERSION = False
    logger.warning(f"完整版本模块未找到: {e}，使用简化版本用于测试")


class ActionRecorder:
    """游戏操作录制器"""
    
    def __init__(self, deck_file: str, output_dir: str = "data/replays"):
        """
        初始化录制器
        
        Args:
            deck_file: 标准化的卡组JSON文件路径
            output_dir: 录像输出目录
        """
        self.deck_file = deck_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载卡组信息
        self.deck_data = self._load_deck()
        self.card_names = self._get_all_card_names()
        
        # 初始化检测器
        if FULL_VERSION:
            self.window_manager = WindowManager()
            self.detector = MasterDuelDetector(deck_card_names=self.card_names)
        else:
            # 简化版本（用于测试）
            self.window_manager = None
            self.detector = None
            logger.info("使用简化版本（无OCR功能），仅用于系统测试")
        
        # 当前录像
        self.current_replay: Optional[GameReplay] = None
        self.current_sequence: Optional[ActionSequence] = None
        
        # 状态追踪
        self.is_recording = False
        self.last_screenshot = None
        self.last_action_time = 0
        
        # 检测配置
        self.detection_interval = 0.5  # 检测间隔（秒）
        self.action_cooldown = 1.0  # 操作冷却时间
        
        logger.info(f"ActionRecorder初始化完成")
        logger.info(f"已加载卡组: {self.deck_data['deck_name']}")
        logger.info(f"卡组包含 {len(self.card_names)} 张不同的卡片")
    
    def _load_deck(self) -> Dict[str, Any]:
        """加载卡组数据"""
        with open(self.deck_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_all_card_names(self) -> List[str]:
        """获取所有卡片名称（用于OCR匹配）"""
        names = []
        
        # 主卡组
        for card in self.deck_data.get('main_deck', []):
            if card['name'] not in names:
                names.append(card['name'])
        
        # 额外卡组
        for card in self.deck_data.get('extra_deck', []):
            if card['name'] not in names:
                names.append(card['name'])
        
        return names
    
    def start_recording(self, replay_id: Optional[str] = None):
        """
        开始录制
        
        Args:
            replay_id: 录像ID（可选，自动生成）
        """
        if self.is_recording:
            logger.warning("已经在录制中")
            return
        
        replay_id = replay_id or f"replay_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_replay = GameReplay(
            replay_id=replay_id,
            created_at=datetime.now().isoformat(),
            deck_used=self.deck_data['deck_name']
        )
        
        self.is_recording = True
        self.last_action_time = time.time()
        
        logger.info(f"开始录制: {replay_id}")
    
    def stop_recording(self) -> Optional[str]:
        """
        停止录制
        
        Returns:
            保存的文件路径
        """
        if not self.is_recording:
            logger.warning("没有正在进行的录制")
            return None
        
        # 结束当前序列
        if self.current_sequence:
            self._end_current_sequence()
        
        # 保存录像
        save_path = self._save_replay()
        
        self.is_recording = False
        self.current_replay = None
        
        logger.info(f"录制已停止，已保存: {save_path}")
        return save_path
    
    def detect_action(self) -> Optional[GameAction]:
        """
        检测当前屏幕上的操作
        
        Returns:
            检测到的操作，如果没有则返回None
        """
        if not self.is_recording:
            return None
        
        # 冷却时间检查
        current_time = time.time()
        if current_time - self.last_action_time < self.action_cooldown:
            return None
        
        # 捕获游戏窗口
        if not FULL_VERSION or not self.window_manager:
            logger.debug("简化版本，跳过窗口捕获")
            return None
        
        screenshot = self.window_manager.capture_window()
        if screenshot is None:
            return None
        
        self.last_screenshot = screenshot
        
        # 使用MasterDuelDetector检测UI状态
        ui_state = self.detector.detect_ui_state(screenshot)
        
        # 检测卡片发动
        action = None
        if ui_state.get('card_activation_detected') or ui_state.get('effect_window_open'):
            action = self._detect_card_activation(screenshot, ui_state)
        elif ui_state.get('summon_detected'):
            action = self._detect_summon(screenshot, ui_state)
        
        if action:
            self.last_action_time = current_time
            self._record_action(action)
        
        return action
    
    def _detect_card_activation(self, screenshot: np.ndarray, ui_state: Dict) -> Optional[GameAction]:
        """
        检测卡片发动
        
        Args:
            screenshot: 游戏截图
            ui_state: UI状态
            
        Returns:
            检测到的操作
        """
        # 提取卡片名称区域进行OCR
        card_name_region = ui_state.get('card_name_region')
        if card_name_region is None:
            return None
        
        # OCR识别卡片名称
        card_name, confidence = self._ocr_card_name(screenshot, card_name_region)
        
        if card_name and confidence > 0.6:
            logger.info(f"检测到卡片发动: {card_name} (置信度: {confidence:.2f})")
            
            action = GameAction(
                timestamp=time.time(),
                action_type=ActionType.USE_CARD,
                card_name=card_name,
                source_zone=Zone.HAND,  # 默认来自手牌
                ocr_confidence=confidence,
                screenshot_path=self._save_screenshot(screenshot)
            )
            
            return action
        
        return None
    
    def _detect_summon(self, screenshot: np.ndarray, ui_state: Dict) -> Optional[GameAction]:
        """检测召唤操作"""
        card_name, confidence = self._ocr_card_name(screenshot, ui_state.get('summon_card_region'))
        
        if card_name and confidence > 0.6:
            # 判断是通常召唤还是特殊召唤
            summon_type = ActionType.SPECIAL_SUMMON if ui_state.get('special_summon') else ActionType.NORMAL_SUMMON
            
            logger.info(f"检测到召唤: {card_name} ({summon_type.value})")
            
            action = GameAction(
                timestamp=time.time(),
                action_type=summon_type,
                card_name=card_name,
                target_zone=Zone.FIELD_MONSTER,
                ocr_confidence=confidence,
                screenshot_path=self._save_screenshot(screenshot)
            )
            
            return action
        
        return None
    
    def _detect_effect_activation(self, screenshot: np.ndarray, ui_state: Dict) -> Optional[GameAction]:
        """检测效果发动"""
        card_name, confidence = self._ocr_card_name(screenshot, ui_state.get('effect_card_region'))
        effect_text = ui_state.get('effect_text', '')
        
        if card_name and confidence > 0.6:
            logger.info(f"检测到效果发动: {card_name}")
            
            action = GameAction(
                timestamp=time.time(),
                action_type=ActionType.ACTIVATE_EFFECT,
                card_name=card_name,
                effect_description=effect_text,
                ocr_confidence=confidence,
                screenshot_path=self._save_screenshot(screenshot)
            )
            
            return action
        
        return None
    
    def _ocr_card_name(self, screenshot: np.ndarray, region: Optional[Tuple] = None) -> Tuple[str, float]:
        """
        使用OCR识别卡片名称，并与卡组中的卡片匹配
        
        Args:
            screenshot: 截图
            region: 识别区域 (x, y, w, h)
            
        Returns:
            (卡片名称, 置信度)
        """
        if region is not None:
            x, y, w, h = region
            roi = screenshot[y:y+h, x:x+w]
        else:
            roi = screenshot
        
        # 使用MasterDuelDetector进行OCR
        if not FULL_VERSION or not self.detector:
            # 简化版本：返回模拟结果
            return "测试卡片", 1.0
        
        # 使用检测器的OCR功能
        ocr_result = self.detector.ocr_card_name(roi)
        raw_text = ocr_result.get('text', '')
        ocr_confidence = ocr_result.get('confidence', 0.0)
        
        if not raw_text:
            return "", 0.0
        
        # 在卡组中查找最匹配的卡片名称
        best_match, match_score = self.detector.match_card_name(raw_text)
        
        # 综合置信度
        final_confidence = ocr_confidence * match_score
        
        return best_match, final_confidence
    
    def _find_best_match(self, text: str, candidates: List[str]) -> Tuple[str, float]:
        """
        在候选卡片中查找最佳匹配
        
        Args:
            text: OCR识别的文本
            candidates: 候选卡片列表
            
        Returns:
            (最佳匹配, 匹配分数)
        """
        if not text:
            return "", 0.0
        
        best_match = ""
        best_score = 0.0
        
        for candidate in candidates:
            # 计算相似度
            score = self._similarity(text, candidate)
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return best_match, best_score
    
    def _similarity(self, s1: str, s2: str) -> float:
        """
        计算两个字符串的相似度
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            相似度分数 (0-1)
        """
        # 简化版Levenshtein距离
        if s1 == s2:
            return 1.0
        
        # 如果s2包含s1或s1包含s2
        if s1 in s2 or s2 in s1:
            return 0.9
        
        # 计算字符交集
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _record_action(self, action: GameAction):
        """记录操作"""
        if not self.current_replay:
            return
        
        # 如果是新序列的开始
        if self.current_sequence is None:
            self._start_new_sequence(action)
        else:
            # 检查是否应该开始新序列
            time_gap = action.timestamp - self.current_sequence.end_time
            if time_gap > 5.0:  # 5秒间隔认为是新序列
                self._end_current_sequence()
                self._start_new_sequence(action)
            else:
                self.current_sequence.add_action(action)
        
        logger.info(f"已记录操作: {action.action_type.value} - {action.card_name}")
    
    def _start_new_sequence(self, first_action: GameAction):
        """开始新序列"""
        seq_id = f"seq_{len(self.current_replay.sequences) + 1:03d}"
        self.current_sequence = ActionSequence(
            sequence_id=seq_id,
            start_time=first_action.timestamp,
            end_time=first_action.timestamp
        )
        self.current_sequence.add_action(first_action)
        
        logger.info(f"开始新序列: {seq_id}")
    
    def _end_current_sequence(self):
        """结束当前序列"""
        if self.current_sequence and self.current_replay:
            self.current_replay.add_sequence(self.current_sequence)
            logger.info(f"序列结束: {self.current_sequence.sequence_id}, "
                       f"包含 {len(self.current_sequence.actions)} 个操作")
            self.current_sequence = None
    
    def _save_screenshot(self, screenshot: np.ndarray) -> str:
        """保存截图"""
        if self.current_replay is None:
            return ""
        
        screenshots_dir = self.output_dir / self.current_replay.replay_id / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        filename = f"action_{timestamp}.png"
        filepath = screenshots_dir / filename
        
        cv2.imwrite(str(filepath), screenshot)
        
        return str(filepath)
    
    def _save_replay(self) -> str:
        """保存录像"""
        if self.current_replay is None:
            return ""
        
        replay_file = self.output_dir / f"{self.current_replay.replay_id}.json"
        
        with open(replay_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_replay.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"录像已保存: {replay_file}")
        logger.info(f"总序列数: {len(self.current_replay.sequences)}")
        logger.info(f"总操作数: {self.current_replay.total_actions}")
        
        return str(replay_file)
    
    def manual_verify_action(self, action: GameAction, correct_name: str = None):
        """
        手动验证/修正操作
        
        Args:
            action: 需要验证的操作
            correct_name: 正确的卡片名称（如果OCR错误）
        """
        if correct_name:
            action.card_name = correct_name
        action.verified = True
        logger.info(f"操作已验证: {action.card_name}")


# 测试代码
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 测试录制器
    project_root = Path(__file__).parent.parent.parent
    deck_file = project_root / "data" / "standard_deck.json"
    
    if deck_file.exists():
        recorder = ActionRecorder(str(deck_file))
        logger.info("ActionRecorder 测试成功")
    else:
        logger.error(f"卡组文件不存在: {deck_file}")
