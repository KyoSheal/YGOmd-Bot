"""
手动录制界面 - Manual Recorder UI
提供简单的UI来控制游戏录制和查看分析结果
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import json
from typing import Optional
from loguru import logger

from src.learning.action_recorder import ActionRecorder
from src.learning.llm_engine import LLMDecisionEngine


class ManualRecorderUI:
    """手动录制界面"""
    
    def __init__(self, deck_file: str):
        """
        初始化界面
        
        Args:
            deck_file: 卡组文件路径
        """
        self.deck_file = deck_file
        self.recorder = ActionRecorder(deck_file)
        self.llm_engine = LLMDecisionEngine()
        
        # 录制状态
        self.recording_thread: Optional[threading.Thread] = None
        self.should_stop = False
        
        # 创建窗口
        self.root = tk.Tk()
        self.root.title("游戏王 Master Duel - 深度学习录制器")
        self.root.geometry("800x600")
        
        self._create_widgets()
        self._load_deck_info()
    
    def _create_widgets(self):
        """创建UI组件"""
        # 顶部控制区
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)
        
        # 录制按钮
        self.record_btn = ttk.Button(
            control_frame,
            text="▶ 开始录制",
            command=self.toggle_recording,
            style="Accent.TButton"
        )
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(
            control_frame,
            text="未录制",
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # 分隔线
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # 中间信息区（分栏）
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：卡组信息
        left_frame = ttk.LabelFrame(paned, text="卡组信息", padding=10)
        paned.add(left_frame, weight=1)
        
        self.deck_info_text = scrolledtext.ScrolledText(
            left_frame,
            height=10,
            width=30,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.deck_info_text.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：实时操作
        right_frame = ttk.LabelFrame(paned, text="检测到的操作", padding=10)
        paned.add(right_frame, weight=2)
        
        self.actions_text = scrolledtext.ScrolledText(
            right_frame,
            height=10,
            font=("Microsoft YaHei UI", 9),
            state=tk.DISABLED
        )
        self.actions_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部：LLM分析结果
        analysis_frame = ttk.LabelFrame(self.root, text="LLM深度分析", padding=10)
        analysis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.analysis_text = scrolledtext.ScrolledText(
            analysis_frame,
            height=10,
            font=("Microsoft YaHei UI", 9),
            state=tk.DISABLED
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部按钮
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="分析当前序列",
            command=self.analyze_current_sequence
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="清空显示",
            command=self.clear_display
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="保存录像",
            command=self.save_replay
        ).pack(side=tk.RIGHT, padx=5)
    
    def _load_deck_info(self):
        """加载并显示卡组信息"""
        try:
            with open(self.deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            info_text = f"""卡组名称：{deck_data['deck_name']}
类型：{deck_data['deck_type']}

主卡组：{deck_data['total_main']}张
额外卡组：{deck_data['total_extra']}张

核心卡片：
"""
            # 显示前10张主卡组卡片
            for card in deck_data['main_deck'][:10]:
                info_text += f"  • {card['name']} x{card['quantity']}\n"
            
            if len(deck_data['main_deck']) > 10:
                info_text += f"  ... 还有 {len(deck_data['main_deck']) - 10} 种卡片"
            
            self._update_text(self.deck_info_text, info_text)
        
        except Exception as e:
            logger.error(f"加载卡组信息失败: {e}")
    
    def toggle_recording(self):
        """切换录制状态"""
        if not self.recorder.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """开始录制"""
        self.recorder.start_recording()
        self.record_btn.config(text="⏸ 停止录制")
        self.status_label.config(text="录制中...", foreground="red")
        
        self._append_text(self.actions_text, "=== 开始录制 ===\n", "green")
        
        # 启动检测线程
        self.should_stop = False
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        
        logger.info("开始录制")
    
    def stop_recording(self):
        """停止录制"""
        self.should_stop = True
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        
        save_path = self.recorder.stop_recording()
        
        self.record_btn.config(text="▶ 开始录制")
        self.status_label.config(text="已停止", foreground="gray")
        
        self._append_text(self.actions_text, f"\n=== 录制结束 ===\n已保存: {save_path}\n", "blue")
        
        logger.info("停止录制")
    
    def _recording_loop(self):
        """录制循环（在后台线程运行）"""
        while not self.should_stop:
            try:
                # 检测操作
                action = self.recorder.detect_action()
                
                if action:
                    # 显示操作
                    action_text = f"[{time.strftime('%H:%M:%S')}] {action.action_type.value}: {action.card_name}\n"
                    if action.effect_description:
                        action_text += f"  效果: {action.effect_description}\n"
                    action_text += f"  置信度: {action.ocr_confidence:.2%}\n\n"
                    
                    self._append_text(self.actions_text, action_text, "black")
                
                time.sleep(self.recorder.detection_interval)
            
            except Exception as e:
                logger.error(f"录制循环错误: {e}")
                time.sleep(1)
    
    def analyze_current_sequence(self):
        """分析当前序列"""
        if not self.recorder.current_sequence:
            messagebox.showinfo("提示", "当前没有正在进行的操作序列")
            return
        
        self._append_text(self.analysis_text, "\n=== 正在分析... ===\n", "blue")
        
        # 在后台线程进行分析
        threading.Thread(target=self._do_analysis, daemon=True).start()
    
    def _do_analysis(self):
        """执行LLM分析"""
        try:
            sequence = self.recorder.current_sequence
            actions_dict = [action.to_dict() for action in sequence.actions]
            
            # LLM深度学习
            analysis = self.llm_engine.learn_from_action_sequence(
                actions_dict,
                deck_type=self.recorder.deck_data['deck_type']
            )
            
            # 格式化分析结果
            result_text = f"""
Combo名称：{analysis.get('combo_name', '未识别')}

战术意图：
{analysis.get('tactical_intent', 'N/A')}

核心卡片：
{', '.join(analysis.get('core_cards', []))}

Combo模式：
{analysis.get('combo_pattern', 'N/A')}

关键协同：
"""
            for synergy in analysis.get('key_synergies', []):
                result_text += f"  • {synergy}\n"
            
            result_text += f"\n决策点：\n"
            for point in analysis.get('decision_points', []):
                result_text += f"  • {point}\n"
            
            result_text += f"\n可能的替代路线：\n"
            for path in analysis.get('alternative_paths', []):
                result_text += f"  • {path}\n"
            
            result_text += f"\n深度洞察：\n{analysis.get('learned_insights', 'N/A')}\n"
            
            self._append_text(self.analysis_text, result_text, "black")
            
            # 保存分析结果到序列
            sequence.llm_analysis = analysis
            
        except Exception as e:
            logger.error(f"分析失败: {e}")
            self._append_text(self.analysis_text, f"\n分析失败: {e}\n", "red")
    
    def save_replay(self):
        """手动保存录像"""
        if not self.recorder.current_replay:
            messagebox.showinfo("提示", "没有录像可保存")
            return
        
        # 结束当前序列
        if self.recorder.current_sequence:
            self.recorder._end_current_sequence()
        
        save_path = self.recorder._save_replay()
        messagebox.showinfo("成功", f"录像已保存:\n{save_path}")
    
    def clear_display(self):
        """清空显示"""
        self._update_text(self.actions_text, "")
        self._update_text(self.analysis_text, "")
    
    def _update_text(self, text_widget, content: str):
        """更新文本框内容"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)
    
    def _append_text(self, text_widget, content: str, color: str = "black"):
        """追加文本"""
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, content)
        text_widget.see(tk.END)
        text_widget.config(state=tk.DISABLED)
    
    def run(self):
        """运行界面"""
        logger.info("启动手动录制界面")
        self.root.mainloop()


# 启动脚本
if __name__ == "__main__":
    import sys
    from loguru import logger
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 找到卡组文件 (tools/manual_recorder_ui.py -> YGO/)
    deck_file = project_root / "data" / "standard_deck.json"
    
    if not deck_file.exists():
        print(f"错误：找不到卡组文件 {deck_file}")
        print("请先运行 deck_converter.py 转换卡组")
        sys.exit(1)
    
    # 启动UI
    ui = ManualRecorderUI(str(deck_file))
    ui.run()
