"""
操作录制模块
录制用户的操作和游戏状态
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict
from pynput import mouse, keyboard
from loguru import logger

from ..core.game_state import GameState


class ActionRecorder:
    """操作录制器"""
    
    def __init__(self, save_dir: str = "data/recordings"):
        """
        初始化录制器
        
        Args:
            save_dir: 录制文件保存目录
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.recording = False
        self.actions = []
        self.game_states = []
        self.start_time = None
        
        # 输入监听器
        self.mouse_listener = None
        self.keyboard_listener = None
        
    def start_recording(self, session_name: Optional[str] = None):
        """
        开始录制
        
        Args:
            session_name: 录制会话名称
        """
        if self.recording:
            logger.warning("已经在录制中")
            return
        
        self.recording = True
        self.actions = []
        self.game_states = []
        self.start_time = time.time()
        
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = session_name
        
        # 启动输入监听
        self._start_listeners()
        
        logger.info(f"开始录制会话: {session_name}")
    
    def stop_recording(self) -> str:
        """
        停止录制并保存
        
        Returns:
            保存的文件路径
        """
        if not self.recording:
            logger.warning("当前没有在录制")
            return ""
        
        self.recording = False
        self._stop_listeners()
        
        # 保存录制数据
        file_path = self._save_recording()
        
        logger.info(f"录制结束，共录制 {len(self.actions)} 个操作")
        logger.info(f"录制文件已保存: {file_path}")
        
        return file_path
    
    def record_action(self, action_type: str, data: Dict):
        """
        记录一个操作
        
        Args:
            action_type: 操作类型 (mouse_click, mouse_move, key_press等)
            data: 操作数据
        """
        if not self.recording:
            return
        
        action = {
            "timestamp": time.time() - self.start_time,
            "type": action_type,
            "data": data
        }
        self.actions.append(action)
        logger.debug(f"记录操作: {action_type} - {data}")
    
    def record_game_state(self, state: GameState):
        """
        记录游戏状态
        
        Args:
            state: 游戏状态对象
        """
        if not self.recording:
            return
        
        state_dict = {
            "timestamp": time.time() - self.start_time,
            "state": state.to_dict()
        }
        self.game_states.append(state_dict)
        logger.debug(f"记录游戏状态: 回合{state.turn_count}, {state.current_phase.value}")
    
    def _start_listeners(self):
        """启动输入监听器"""
        # 鼠标监听
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
            on_move=self._on_mouse_move
        )
        self.mouse_listener.start()
        
        # 键盘监听
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        self.keyboard_listener.start()
    
    def _stop_listeners(self):
        """停止输入监听器"""
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击回调"""
        if pressed:  # 只记录按下事件
            self.record_action("mouse_click", {
                "x": x,
                "y": y,
                "button": str(button)
            })
    
    def _on_mouse_move(self, x, y):
        """鼠标移动回调（采样记录，避免过多数据）"""
        # 每0.5秒最多记录一次移动
        if len(self.actions) == 0 or \
           time.time() - self.start_time - self.actions[-1]["timestamp"] > 0.5:
            self.record_action("mouse_move", {
                "x": x,
                "y": y
            })
    
    def _on_key_press(self, key):
        """键盘按键回调"""
        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)
        
        self.record_action("key_press", {
            "key": key_str
        })
    
    def _save_recording(self) -> str:
        """
        保存录制数据
        
        Returns:
            保存的文件路径
        """
        recording_data = {
            "session_name": self.session_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "duration": time.time() - self.start_time,
            "action_count": len(self.actions),
            "state_count": len(self.game_states),
            "actions": self.actions,
            "game_states": self.game_states
        }
        
        file_path = self.save_dir / f"{self.session_name}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(recording_data, f, ensure_ascii=False, indent=2)
        
        return str(file_path)
    
    @staticmethod
    def load_recording(file_path: str) -> Dict:
        """
        加载录制文件
        
        Args:
            file_path: 录制文件路径
            
        Returns:
            录制数据
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_recording_info(self) -> Dict:
        """获取当前录制信息"""
        if not self.recording:
            return {}
        
        return {
            "session_name": self.session_name,
            "duration": time.time() - self.start_time,
            "action_count": len(self.actions),
            "state_count": len(self.game_states)
        }


# 测试代码
if __name__ == "__main__":
    logger.info("操作录制器测试")
    logger.info("按 Ctrl+C 停止录制")
    
    recorder = ActionRecorder()
    recorder.start_recording("test_session")
    
    try:
        while True:
            time.sleep(1)
            info = recorder.get_recording_info()
            logger.info(f"录制中... 时长: {info['duration']:.1f}s, "
                       f"操作数: {info['action_count']}")
    except KeyboardInterrupt:
        file_path = recorder.stop_recording()
        logger.info(f"录制已保存到: {file_path}")
