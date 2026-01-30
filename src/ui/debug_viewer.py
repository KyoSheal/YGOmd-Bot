"""
调试查看器 UI
参考 MaaAssistantArknights 的设计
实时显示截图、识别结果和调试信息
"""
import sys
import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QTextEdit, QPushButton, QGroupBox, QSplitter, QTabWidget,
        QScrollArea, QComboBox, QCheckBox, QSpinBox, QLineEdit
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt5.QtGui import QImage, QPixmap, QFont
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    print("PyQt5 未安装，请运行: pip install PyQt5")

from loguru import logger


class ScreenshotThread(QThread):
    """截图线程"""
    screenshot_ready = pyqtSignal(np.ndarray)
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = False
        self.interval = 500  # 毫秒
    
    def run(self):
        """运行截图循环"""
        self.running = True
        while self.running:
            try:
                screenshot = self.controller.screenshot()
                if screenshot is not None:
                    self.screenshot_ready.emit(screenshot)
            except Exception as e:
                logger.error(f"截图失败: {e}")
            
            self.msleep(self.interval)
    
    def stop(self):
        """停止线程"""
        self.running = False


class DebugViewer(QMainWindow):
    """调试查看器主窗口"""
    
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.current_screenshot = None
        self.recognition_results = {}
        self.screenshot_thread = None
        
        # 初始化 UI
        self.init_ui()
        
        # 如果提供了控制器，启动自动截图
        if self.controller:
            self.start_auto_capture()
    
    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("Yu-Gi-Oh! Master Duel - 调试查看器")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：截图显示区域
        left_panel = self.create_screenshot_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：信息面板
        right_panel = self.create_info_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # 设置样式
        self.set_style()
    
    def create_screenshot_panel(self) -> QWidget:
        """创建截图显示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 控制栏
        control_layout = QHBoxLayout()
        
        # 截图按钮
        self.btn_capture = QPushButton("📷 截图")
        self.btn_capture.clicked.connect(self.capture_screenshot)
        control_layout.addWidget(self.btn_capture)
        
        # 自动截图开关
        self.chk_auto_capture = QCheckBox("自动截图")
        self.chk_auto_capture.stateChanged.connect(self.toggle_auto_capture)
        control_layout.addWidget(self.chk_auto_capture)
        
        # 截图间隔
        control_layout.addWidget(QLabel("间隔(ms):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(100, 5000)
        self.spin_interval.setValue(500)
        self.spin_interval.setSingleStep(100)
        self.spin_interval.valueChanged.connect(self.update_capture_interval)
        control_layout.addWidget(self.spin_interval)
        
        # 保存截图
        self.btn_save = QPushButton("💾 保存")
        self.btn_save.clicked.connect(self.save_screenshot)
        control_layout.addWidget(self.btn_save)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 截图显示区域
        screenshot_group = QGroupBox("实时截图")
        screenshot_layout = QVBoxLayout(screenshot_group)
        
        # 使用 QScrollArea 支持大图显示
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter)
        
        self.lbl_screenshot = QLabel("等待截图...")
        self.lbl_screenshot.setAlignment(Qt.AlignCenter)
        self.lbl_screenshot.setMinimumSize(800, 450)
        self.lbl_screenshot.setStyleSheet("background-color: #2b2b2b; color: #888;")
        
        scroll_area.setWidget(self.lbl_screenshot)
        screenshot_layout.addWidget(scroll_area)
        
        layout.addWidget(screenshot_group)
        
        return panel
    
    def create_info_panel(self) -> QWidget:
        """创建信息面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标签页
        tab_widget = QTabWidget()
        
        # 识别结果标签页
        tab_recognition = self.create_recognition_tab()
        tab_widget.addTab(tab_recognition, "🔍 识别结果")
        
        # 调试信息标签页
        tab_debug = self.create_debug_tab()
        tab_widget.addTab(tab_debug, "🐛 调试信息")
        
        # 设置标签页
        tab_settings = self.create_settings_tab()
        tab_widget.addTab(tab_settings, "⚙️ 设置")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    def create_recognition_tab(self) -> QWidget:
        """创建识别结果标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 游戏状态
        state_group = QGroupBox("游戏状态")
        state_layout = QVBoxLayout(state_group)
        
        self.lbl_game_state = QLabel("状态: 未知")
        self.lbl_game_state.setFont(QFont("Arial", 10, QFont.Bold))
        state_layout.addWidget(self.lbl_game_state)
        
        self.lbl_phase = QLabel("阶段: -")
        state_layout.addWidget(self.lbl_phase)
        
        self.lbl_lp = QLabel("LP: - / -")
        state_layout.addWidget(self.lbl_lp)
        
        layout.addWidget(state_group)
        
        # 卡片识别
        card_group = QGroupBox("卡片识别")
        card_layout = QVBoxLayout(card_group)
        
        self.txt_cards = QTextEdit()
        self.txt_cards.setReadOnly(True)
        self.txt_cards.setMaximumHeight(200)
        self.txt_cards.setPlaceholderText("等待识别卡片...")
        card_layout.addWidget(self.txt_cards)
        
        layout.addWidget(card_group)
        
        # OCR 结果
        ocr_group = QGroupBox("OCR 识别")
        ocr_layout = QVBoxLayout(ocr_group)
        
        self.txt_ocr = QTextEdit()
        self.txt_ocr.setReadOnly(True)
        self.txt_ocr.setPlaceholderText("等待 OCR 识别...")
        ocr_layout.addWidget(self.txt_ocr)
        
        layout.addWidget(ocr_group)
        
        layout.addStretch()
        
        return tab
    
    def create_debug_tab(self) -> QWidget:
        """创建调试信息标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 连接信息
        conn_group = QGroupBox("连接信息")
        conn_layout = QVBoxLayout(conn_group)
        
        self.lbl_device = QLabel("设备: 未连接")
        conn_layout.addWidget(self.lbl_device)
        
        self.lbl_resolution = QLabel("分辨率: -")
        conn_layout.addWidget(self.lbl_resolution)
        
        layout.addWidget(conn_group)
        
        # 性能统计
        perf_group = QGroupBox("性能统计")
        perf_layout = QVBoxLayout(perf_group)
        
        self.lbl_fps = QLabel("截图 FPS: 0")
        perf_layout.addWidget(self.lbl_fps)
        
        self.lbl_latency = QLabel("延迟: 0 ms")
        perf_layout.addWidget(self.lbl_latency)
        
        layout.addWidget(perf_group)
        
        # 日志输出
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout(log_group)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(300)
        log_layout.addWidget(self.txt_log)
        
        # 清空日志按钮
        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.clicked.connect(self.txt_log.clear)
        log_layout.addWidget(btn_clear_log)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        return tab
    
    def create_settings_tab(self) -> QWidget:
        """创建设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 设备选择
        device_group = QGroupBox("设备设置")
        device_layout = QVBoxLayout(device_group)
        
        device_layout.addWidget(QLabel("模拟器类型:"))
        self.combo_emulator = QComboBox()
        self.combo_emulator.addItems([
            "自动检测",
            "BlueStacks 5",
            "BlueStacks 5 Hyper-V",
            "MuMu 12",
            "MuMu 6",
            "雷电模拟器",
            "夜神模拟器"
        ])
        device_layout.addWidget(self.combo_emulator)
        
        btn_reconnect = QPushButton("🔄 重新连接")
        btn_reconnect.clicked.connect(self.reconnect_device)
        device_layout.addWidget(btn_reconnect)
        
        layout.addWidget(device_group)
        
        # 识别设置
        recog_group = QGroupBox("识别设置")
        recog_layout = QVBoxLayout(recog_group)
        
        self.chk_enable_ocr = QCheckBox("启用 OCR 识别")
        self.chk_enable_ocr.setChecked(True)
        recog_layout.addWidget(self.chk_enable_ocr)
        
        self.chk_enable_template = QCheckBox("启用模板匹配")
        self.chk_enable_template.setChecked(True)
        recog_layout.addWidget(self.chk_enable_template)
        
        self.chk_show_debug = QCheckBox("显示调试信息")
        self.chk_show_debug.setChecked(True)
        recog_layout.addWidget(self.chk_show_debug)
        
        layout.addWidget(recog_group)
        
        # 保存设置
        btn_save_settings = QPushButton("💾 保存设置")
        btn_save_settings.clicked.connect(self.save_settings)
        layout.addWidget(btn_save_settings)
        
        layout.addStretch()
        
        return tab
    
    def set_style(self):
        """设置样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0a3d91;
            }
            QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QLabel {
                padding: 2px;
            }
            QComboBox {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QSpinBox {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #e0e0e0;
                padding: 8px 16px;
                border: 1px solid #3a3a3a;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0d47a1;
            }
            QScrollArea {
                border: none;
            }
        """)
    
    def capture_screenshot(self):
        """手动截图"""
        if not self.controller:
            self.log_message("错误: 未连接设备")
            return
        
        try:
            screenshot = self.controller.screenshot()
            if screenshot is not None:
                self.update_screenshot(screenshot)
                self.log_message("截图成功")
            else:
                self.log_message("截图失败")
        except Exception as e:
            self.log_message(f"截图错误: {e}")
    
    def toggle_auto_capture(self, state):
        """切换自动截图"""
        if state == Qt.Checked:
            self.start_auto_capture()
        else:
            self.stop_auto_capture()
    
    def start_auto_capture(self):
        """启动自动截图"""
        if not self.controller:
            self.log_message("错误: 未连接设备")
            self.chk_auto_capture.setChecked(False)
            return
        
        if not self.screenshot_thread or not self.screenshot_thread.isRunning():
            self.screenshot_thread = ScreenshotThread(self.controller)
            self.screenshot_thread.screenshot_ready.connect(self.update_screenshot)
            self.screenshot_thread.interval = self.spin_interval.value()
            self.screenshot_thread.start()
            self.log_message("自动截图已启动")
    
    def stop_auto_capture(self):
        """停止自动截图"""
        if self.screenshot_thread and self.screenshot_thread.isRunning():
            self.screenshot_thread.stop()
            self.screenshot_thread.wait()
            self.log_message("自动截图已停止")
    
    def update_capture_interval(self, value):
        """更新截图间隔"""
        if self.screenshot_thread:
            self.screenshot_thread.interval = value
    
    def update_screenshot(self, screenshot: np.ndarray):
        """更新截图显示"""
        self.current_screenshot = screenshot
        
        # 转换为 QPixmap
        height, width, channel = screenshot.shape
        bytes_per_line = 3 * width
        
        # BGR to RGB
        rgb_image = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # 缩放以适应显示区域
        scaled_pixmap = pixmap.scaled(
            self.lbl_screenshot.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.lbl_screenshot.setPixmap(scaled_pixmap)
    
    def save_screenshot(self):
        """保存截图"""
        if self.current_screenshot is None:
            self.log_message("没有可保存的截图")
            return
        
        # 创建保存目录
        save_dir = Path("screenshots")
        save_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"screenshot_{timestamp}.png"
        
        # 保存
        cv2.imwrite(str(filename), self.current_screenshot)
        self.log_message(f"截图已保存: {filename}")
    
    def update_recognition_results(self, results: Dict):
        """更新识别结果"""
        self.recognition_results = results
        
        # 更新游戏状态
        if "game_state" in results:
            self.lbl_game_state.setText(f"状态: {results['game_state']}")
        
        if "phase" in results:
            self.lbl_phase.setText(f"阶段: {results['phase']}")
        
        if "lp" in results:
            lp = results['lp']
            self.lbl_lp.setText(f"LP: {lp.get('player', '-')} / {lp.get('opponent', '-')}")
        
        # 更新卡片识别
        if "cards" in results:
            cards_text = "\n".join([
                f"• {card['name']} ({card['position']})"
                for card in results['cards']
            ])
            self.txt_cards.setText(cards_text)
        
        # 更新 OCR 结果
        if "ocr" in results:
            ocr_text = "\n".join([
                f"[{item['confidence']:.2f}] {item['text']}"
                for item in results['ocr']
            ])
            self.txt_ocr.setText(ocr_text)
    
    def update_device_info(self, device_id: str, resolution: Tuple[int, int]):
        """更新设备信息"""
        self.lbl_device.setText(f"设备: {device_id}")
        self.lbl_resolution.setText(f"分辨率: {resolution[0]}x{resolution[1]}")
    
    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {message}")
        
        # 自动滚动到底部
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def reconnect_device(self):
        """重新连接设备"""
        self.log_message("正在重新连接设备...")
        # TODO: 实现重新连接逻辑
    
    def save_settings(self):
        """保存设置"""
        self.log_message("设置已保存")
        # TODO: 实现设置保存逻辑
    
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_auto_capture()
        event.accept()


def main():
    """主函数"""
    if not PYQT5_AVAILABLE:
        print("请先安装 PyQt5: pip install PyQt5")
        return
    
    app = QApplication(sys.argv)
    
    # 尝试连接设备
    try:
        from src.control.adb_controller import ADBController
        
        logger.info("正在连接设备...")
        emulator_type = ADBController.auto_detect_emulator()
        
        if emulator_type:
            controller = ADBController(emulator_type=emulator_type)
            if controller.connected:
                logger.success("设备连接成功")
                viewer = DebugViewer(controller)
                
                # 更新设备信息
                width, height = controller.get_screen_size()
                viewer.update_device_info(controller.device_id, (width, height))
            else:
                logger.warning("设备连接失败，启动无设备模式")
                viewer = DebugViewer()
        else:
            logger.warning("未检测到设备，启动无设备模式")
            viewer = DebugViewer()
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        viewer = DebugViewer()
    
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
