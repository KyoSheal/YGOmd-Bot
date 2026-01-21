"""
YGO Master Duel 智能Bot - 主程序
"""
import sys
import yaml
from pathlib import Path
from loguru import logger

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.vision.screen_capture import ScreenCapture
from src.control.mouse_controller import MouseController
from src.learning.recorder import ActionRecorder


class YGOBot:
    """YGO Master Duel Bot主类"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        初始化Bot
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 配置日志
        self._setup_logging()
        
        # 初始化各模块
        logger.info("初始化YGO Bot...")
        
        self.screen_capture = ScreenCapture(
            window_title=self.config["game"]["window_title"]
        )
        
        self.mouse_controller = MouseController(
            speed=self.config["control"]["mouse_speed"],
            humanize=self.config["control"]["humanize"]
        )
        
        self.recorder = ActionRecorder(
            save_dir=self.config["learning"]["recording_path"]
        )
        
        logger.info("Bot初始化完成！")
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config["logging"]
        
        # 移除默认handler
        logger.remove()
        
        # 添加控制台输出
        logger.add(
            sys.stderr,
            level=log_config["level"],
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>"
        )
        
        # 添加文件输出
        if log_config["save_logs"]:
            log_dir = Path(log_config["log_path"])
            log_dir.mkdir(exist_ok=True)
            
            logger.add(
                log_dir / "ygo_bot_{time}.log",
                level=log_config["level"],
                rotation=log_config["max_log_size"],
                encoding="utf-8"
            )
    
    def check_game_running(self) -> bool:
        """检查游戏是否运行"""
        if self.screen_capture.find_game_window():
            logger.info("✓ 游戏窗口已找到")
            size = self.screen_capture.get_window_size()
            logger.info(f"  窗口大小: {size[0]}x{size[1]}")
            return True
        else:
            logger.error("✗ 未找到游戏窗口，请启动游戏王Master Duel")
            return False
    
    def start_recording_mode(self):
        """启动录制模式"""
        logger.info("=" * 60)
        logger.info("录制模式 - 开始录制你的操作")
        logger.info("=" * 60)
        logger.info("")
        logger.info("请按以下步骤操作：")
        logger.info("1. 进入游戏并开始一局Solo对战")
        logger.info("2. 正常进行你的展开和操作")
        logger.info("3. Bot会记录你的所有鼠标键盘操作")
        logger.info("4. 完成后按 Ctrl+C 停止录制")
        logger.info("")
        logger.info("提示：操作时尽量清晰明确，这将帮助Bot更好地学习")
        logger.info("")
        
        session_name = input("请输入本次录制的名称（直接回车使用默认名称）: ").strip()
        if not session_name:
            session_name = None
        
        self.recorder.start_recording(session_name)
        
        try:
            import time
            while True:
                time.sleep(2)
                info = self.recorder.get_recording_info()
                logger.info(f"录制中... 时长: {info['duration']:.1f}s, "
                           f"操作数: {info['action_count']}")
        except KeyboardInterrupt:
            logger.info("\n正在保存录制...")
            file_path = self.recorder.stop_recording()
            logger.info(f"✓ 录制已保存: {file_path}")
    
    def test_card_recognition(self):
        """测试卡片识别"""
        logger.info("=" * 60)
        logger.info("测试卡片识别系统")
        logger.info("=" * 60)
        
        if not self.check_game_running():
            logger.warning("如果没有游戏，也可以测试截图文件")
            screenshot_path = input("请输入测试截图路径（直接回车跳过）: ").strip()
            if screenshot_path:
                import cv2
                img = cv2.imread(screenshot_path)
            else:
                return
        else:
            logger.info("捕获游戏画面...")
            img = self.screen_capture.capture_window()
        
        if img is None:
            logger.error("无法获取图像")
            return
        
        # 初始化卡片识别器
        from src.vision.card_detector import CardImageRecognizer
        recognizer = CardImageRecognizer()
        
        logger.info(f"当前模板库: {len(recognizer.card_templates)} 张卡片")
        
        if len(recognizer.card_templates) == 0:
            logger.warning("模板库为空！建议先使用模板采集工具添加卡片模板")
            logger.info("运行: python tools/collect_templates.py")
            return
        
        # 检测手牌区域的卡片
        logger.info("检测手牌区域的卡片...")
        cards = recognizer.detect_cards_in_image(img, zone="hand")
        
        logger.info(f"\n检测结果：共 {len(cards)} 张卡片")
        for i, card in enumerate(cards, 1):
            logger.info(f"{i}. {card['name']} (置信度: {card['confidence']:.2f})")
    
    def test_vision(self):
        """测试视觉系统"""
        logger.info("=" * 60)
        logger.info("测试视觉系统")
        logger.info("=" * 60)
        
        if not self.check_game_running():
            return
        
        logger.info("捕获游戏画面...")
        img = self.screen_capture.capture_window()
        
        if img is not None:
            import cv2
            output_path = "test_vision_output.png"
            cv2.imwrite(output_path, img)
            logger.info(f"✓ 画面捕获成功！已保存到: {output_path}")
            logger.info(f"  图像大小: {img.shape[1]}x{img.shape[0]}")
        else:
            logger.error("✗ 画面捕获失败")
    
    def show_menu(self):
        """显示主菜单"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("YGO Master Duel 智能Bot")
        logger.info("=" * 60)
        logger.info("")
        logger.info("请选择模式:")
        logger.info("1. 录制模式 - 录制你的操作并学习")
        logger.info("2. 测试视觉系统 - 测试游戏画面捕获")
        logger.info("3. 测试卡片识别 - 测试卡片图像识别")
        logger.info("4. 采集卡片模板 - 添加卡片到模板库")
        logger.info("5. 自动扫描卡组 - 在卡组界面自动识别所有卡片 ⭐")
        logger.info("6. 查找游戏窗口 - 解决找不到窗口的问题")
        logger.info("7. 自动化模式 - 自动进行对战（开发中）")
        logger.info("8. 查看录制列表")
        logger.info("0. 退出")
        logger.info("")
    
    def run(self):
        """运行Bot"""
        while True:
            self.show_menu()
            choice = input("请选择 [0-8]: ").strip()
            
            if choice == "1":
                if self.check_game_running():
                    self.start_recording_mode()
            elif choice == "2":
                self.test_vision()
            elif choice == "3":
                self.test_card_recognition()
            elif choice == "4":
                self.run_template_collector()
            elif choice == "5":
                self.run_auto_deck_scanner()
            elif choice == "6":
                self.run_window_finder()
            elif choice == "7":
                logger.warning("自动化模式正在开发中...")
            elif choice == "8":
                self.list_recordings()
            elif choice == "0":
                logger.info("感谢使用！再见！")
                break
            else:
                logger.warning("无效的选择，请重试")
    
    def run_auto_deck_scanner(self):
        """运行自动卡组扫描器"""
        logger.info("=" * 60)
        logger.info("自动卡组扫描器 ⭐")
        logger.info("=" * 60)
        logger.info("")
        logger.info("使用说明:")
        logger.info("1. 启动游戏并进入卡组编辑界面")
        logger.info("2. 确保卡组在屏幕上完全可见")
        logger.info("3. Bot会自动点击每张卡片并识别保存")
        logger.info("")
        
        import subprocess
        import sys
        
        try:
            subprocess.run([sys.executable, "tools/auto_deck_scanner.py"])
        except Exception as e:
            logger.error(f"运行扫描器失败: {e}")
    
    def run_window_finder(self):
        """运行窗口查找工具"""
        logger.info("=" * 60)
        logger.info("游戏窗口查找工具")
        logger.info("=" * 60)
        
        import subprocess
        import sys
        
        try:
            subprocess.run([sys.executable, "tools/find_window.py"])
        except Exception as e:
            logger.error(f"运行查找工具失败: {e}")
    
    def run_template_collector(self):
        """运行模板采集工具"""
        logger.info("=" * 60)
        logger.info("卡片模板采集工具")
        logger.info("=" * 60)
        
        import subprocess
        import sys
        
        # 运行采集工具
        try:
            subprocess.run([sys.executable, "tools/collect_templates.py"])
        except Exception as e:
            logger.error(f"运行采集工具失败: {e}")
            logger.info("你也可以直接运行: python tools/collect_templates.py")
    
    def list_recordings(self):
        """列出所有录制文件"""
        logger.info("=" * 60)
        logger.info("录制文件列表")
        logger.info("=" * 60)
        
        recording_dir = Path(self.config["learning"]["recording_path"])
        recordings = list(recording_dir.glob("*.json"))
        
        if not recordings:
            logger.info("暂无录制文件")
            return
        
        for i, rec_file in enumerate(recordings, 1):
            import json
            with open(rec_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            logger.info(f"\n{i}. {data['session_name']}")
            logger.info(f"   时间: {data['start_time']}")
            logger.info(f"   时长: {data['duration']:.1f}秒")
            logger.info(f"   操作数: {data['action_count']}")
            logger.info(f"   文件: {rec_file.name}")


def main():
    """主函数"""
    try:
        bot = YGOBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\n程序被用户中断")
    except Exception as e:
        logger.exception(f"发生错误: {e}")


if __name__ == "__main__":
    main()
