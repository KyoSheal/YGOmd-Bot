"""
ADB 控制器
用于控制 Android 模拟器中的 Master Duel
参考 MaaAssistantArknights 的架构设计
"""
import time
import random
import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict
from loguru import logger
import io

try:
    from ppadb.client import Client as AdbClient
    from ppadb.device import Device as AdbDevice
    PPADB_AVAILABLE = True
except ImportError:
    PPADB_AVAILABLE = False
    logger.warning("pure-python-adb 未安装，将使用命令行 ADB")
    import subprocess
    import tempfile
    import os


class ADBController:
    """
    ADB 控制器 - 参考 MAA 架构设计
    支持多种连接方式和模拟器
    """
    
    # 常见模拟器配置
    EMULATOR_CONFIGS = {
        "BlueStacks5": {
            "adb_port": 5555,
            "display_id": 0,
            "name": "BlueStacks 5"
        },
        "BlueStacks5_Hyper-V": {
            "adb_port": 5555,
            "display_id": 0,
            "name": "BlueStacks 5 Hyper-V"
        },
        "MuMu12": {
            "adb_port": 16384,
            "display_id": 0,
            "name": "MuMu 模拟器 12"
        },
        "MuMu6": {
            "adb_port": 7555,
            "display_id": 0,
            "name": "MuMu 模拟器 6"
        },
        "LDPlayer": {
            "adb_port": 5555,
            "display_id": 0,
            "name": "雷电模拟器"
        },
        "Nox": {
            "adb_port": 62001,
            "display_id": 0,
            "name": "夜神模拟器"
        }
    }
    
    def __init__(self, 
                 host: str = "127.0.0.1", 
                 port: int = 5037,
                 device_id: Optional[str] = None,
                 emulator_type: Optional[str] = None):
        """
        初始化 ADB 控制器
        
        Args:
            host: ADB 服务器地址
            port: ADB 服务器端口
            device_id: 设备 ID (如 127.0.0.1:5555)
            emulator_type: 模拟器类型 (如 BlueStacks5, MuMu12)
        """
        self.host = host
        self.port = port
        self.device_id = device_id
        self.emulator_type = emulator_type
        self.device: Optional[AdbDevice] = None
        self.client: Optional[AdbClient] = None
        self.connected = False
        
        # 屏幕信息缓存
        self._screen_size: Optional[Tuple[int, int]] = None
        
        # 尝试连接
        self.connect()
    
    def connect(self) -> bool:
        """连接到 Android 设备"""
        try:
            if PPADB_AVAILABLE:
                return self._connect_with_ppadb()
            else:
                return self._connect_with_subprocess()
        except Exception as e:
            logger.error(f"ADB 连接失败: {e}")
            return False
    
    def _connect_with_ppadb(self) -> bool:
        """使用 pure-python-adb 连接"""
        try:
            # 创建 ADB 客户端
            self.client = AdbClient(host=self.host, port=self.port)
            
            # 如果指定了模拟器类型，尝试连接
            if self.emulator_type and self.emulator_type in self.EMULATOR_CONFIGS:
                config = self.EMULATOR_CONFIGS[self.emulator_type]
                device_addr = f"{self.host}:{config['adb_port']}"
                
                # 尝试连接到模拟器
                try:
                    self.client.remote_connect(self.host, config['adb_port'])
                    time.sleep(0.5)
                except:
                    pass  # 可能已经连接
                
                self.device_id = device_addr
            
            # 获取设备列表
            devices = self.client.devices()
            
            if not devices:
                logger.error("未找到任何 Android 设备")
                return False
            
            # 选择设备
            if self.device_id:
                # 使用指定的设备
                for dev in devices:
                    if dev.serial == self.device_id:
                        self.device = dev
                        break
                
                if not self.device:
                    logger.error(f"未找到设备: {self.device_id}")
                    return False
            else:
                # 使用第一个设备
                self.device = devices[0]
                self.device_id = self.device.serial
            
            self.connected = True
            logger.success(f"成功连接到设备: {self.device_id}")
            
            # 获取屏幕尺寸
            self._screen_size = self.get_screen_size()
            logger.info(f"屏幕尺寸: {self._screen_size}")
            
            return True
            
        except Exception as e:
            logger.error(f"pure-python-adb 连接失败: {e}")
            return False
    
    def _connect_with_subprocess(self) -> bool:
        """使用命令行 ADB 连接（备用方案）"""
        try:
            # 如果指定了模拟器类型，尝试连接
            if self.emulator_type and self.emulator_type in self.EMULATOR_CONFIGS:
                config = self.EMULATOR_CONFIGS[self.emulator_type]
                device_addr = f"{self.host}:{config['adb_port']}"
                
                result = subprocess.run(
                    f"adb connect {device_addr}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"ADB 连接结果: {result.stdout}")
                self.device_id = device_addr
            
            # 验证连接
            result = subprocess.run(
                "adb devices",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if self.device_id and self.device_id in result.stdout:
                self.connected = True
                logger.success(f"成功连接到设备: {self.device_id}")
                return True
            else:
                logger.error("ADB 连接失败")
                return False
                
        except Exception as e:
            logger.error(f"命令行 ADB 连接失败: {e}")
            return False
    
    def screenshot(self) -> Optional[np.ndarray]:
        """截取屏幕截图 - 参考 MAA 的高效截图方式"""
        if not self.connected:
            logger.error("设备未连接")
            return None
        
        try:
            if PPADB_AVAILABLE and self.device:
                return self._screenshot_with_ppadb()
            else:
                return self._screenshot_with_subprocess()
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    def _screenshot_with_ppadb(self) -> Optional[np.ndarray]:
        """使用 pure-python-adb 截图（更快）"""
        try:
            # 直接从设备读取截图数据
            result = self.device.screencap()
            
            if result:
                # 将字节数据转换为图像
                image = cv2.imdecode(
                    np.frombuffer(result, np.uint8), 
                    cv2.IMREAD_COLOR
                )
                
                if image is not None:
                    logger.debug(f"截图成功，尺寸: {image.shape}")
                    return image
            
            logger.error("截图数据为空")
            return None
            
        except Exception as e:
            logger.error(f"pure-python-adb 截图失败: {e}")
            return None
    
    def _screenshot_with_subprocess(self) -> Optional[np.ndarray]:
        """使用命令行 ADB 截图（备用方案）"""
        try:
            import tempfile
            import os
            
            # 在设备上截图
            subprocess.run(
                f"adb -s {self.device_id} shell screencap -p /sdcard/screenshot.png",
                shell=True,
                check=True
            )
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # 拉取截图到本地
            subprocess.run(
                f"adb -s {self.device_id} pull /sdcard/screenshot.png {tmp_path}",
                shell=True,
                check=True
            )
            
            # 读取图像
            image = cv2.imread(tmp_path)
            
            # 清理临时文件
            os.unlink(tmp_path)
            
            if image is not None:
                logger.debug(f"截图成功，尺寸: {image.shape}")
                return image
            
            return None
            
        except Exception as e:
            logger.error(f"命令行 ADB 截图失败: {e}")
            return None
    
    def tap(self, x: int, y: int, delay: float = None):
        """点击指定坐标"""
        if not self.connected:
            logger.error("设备未连接")
            return
        
        try:
            # 添加随机偏移模拟真实触摸
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            actual_x = x + offset_x
            actual_y = y + offset_y
            
            if PPADB_AVAILABLE and self.device:
                self.device.shell(f"input tap {actual_x} {actual_y}")
            else:
                subprocess.run(
                    f"adb -s {self.device_id} shell input tap {actual_x} {actual_y}",
                    shell=True,
                    check=True
                )
            
            logger.debug(f"点击: ({actual_x}, {actual_y})")
            
            # 随机延迟
            if delay is None:
                delay = random.uniform(0.1, 0.3)
            time.sleep(delay)
            
        except Exception as e:
            logger.error(f"点击失败: {e}")
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300):
        """滑动操作"""
        if not self.connected:
            logger.error("设备未连接")
            return
        
        try:
            if PPADB_AVAILABLE and self.device:
                self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
            else:
                subprocess.run(
                    f"adb -s {self.device_id} shell input swipe {x1} {y1} {x2} {y2} {duration}",
                    shell=True,
                    check=True
                )
            
            logger.debug(f"滑动: ({x1}, {y1}) -> ({x2}, {y2}), 持续时间: {duration}ms")
            time.sleep(duration / 1000 + 0.1)
            
        except Exception as e:
            logger.error(f"滑动失败: {e}")
    
    def long_press(self, x: int, y: int, duration: int = 1000):
        """长按操作"""
        if not self.connected:
            logger.error("设备未连接")
            return
        
        try:
            # 使用滑动命令实现长按（起点和终点相同）
            if PPADB_AVAILABLE and self.device:
                self.device.shell(f"input swipe {x} {y} {x} {y} {duration}")
            else:
                subprocess.run(
                    f"adb -s {self.device_id} shell input swipe {x} {y} {x} {y} {duration}",
                    shell=True,
                    check=True
                )
            
            logger.debug(f"长按: ({x}, {y}), 持续时间: {duration}ms")
            time.sleep(duration / 1000 + 0.1)
            
        except Exception as e:
            logger.error(f"长按失败: {e}")
    
    def key_event(self, keycode: int):
        """发送按键事件"""
        if not self.connected:
            logger.error("设备未连接")
            return
        
        try:
            if PPADB_AVAILABLE and self.device:
                self.device.shell(f"input keyevent {keycode}")
            else:
                subprocess.run(
                    f"adb -s {self.device_id} shell input keyevent {keycode}",
                    shell=True,
                    check=True
                )
            
            logger.debug(f"按键事件: {keycode}")
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"按键事件失败: {e}")
    
    def back(self):
        """返回键"""
        self.key_event(4)  # KEYCODE_BACK
    
    def home(self):
        """主页键"""
        self.key_event(3)  # KEYCODE_HOME
    
    def menu(self):
        """菜单键"""
        self.key_event(82)  # KEYCODE_MENU
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        if self._screen_size:
            return self._screen_size
        
        try:
            if PPADB_AVAILABLE and self.device:
                result = self.device.shell("wm size")
            else:
                result = subprocess.run(
                    f"adb -s {self.device_id} shell wm size",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
            
            # 解析输出: Physical size: 1920x1080
            size_str = result.split(": ")[1] if ": " in result else result
            width, height = map(int, size_str.split("x"))
            self._screen_size = (width, height)
            return width, height
            
        except Exception as e:
            logger.error(f"获取屏幕尺寸失败: {e}")
            return 1920, 1080  # 默认值
    
    def get_current_activity(self) -> str:
        """获取当前活动的应用"""
        try:
            if PPADB_AVAILABLE and self.device:
                result = self.device.shell("dumpsys window windows | grep -E 'mCurrentFocus'")
            else:
                result = subprocess.run(
                    f"adb -s {self.device_id} shell dumpsys window windows | grep -E 'mCurrentFocus'",
                    shell=True,
                    capture_output=True,
                    text=True
                ).stdout.strip()
            
            return result
            
        except Exception as e:
            logger.error(f"获取当前活动失败: {e}")
            return ""
    
    def is_master_duel_running(self) -> bool:
        """检查 Master Duel 是否在运行"""
        try:
            activity = self.get_current_activity()
            return "masterduel" in activity.lower() or "yugioh" in activity.lower()
            
        except Exception as e:
            logger.error(f"检查游戏状态失败: {e}")
            return False
    
    def start_master_duel(self, package_name: str = "jp.konami.masterduel"):
        """启动 Master Duel"""
        try:
            if PPADB_AVAILABLE and self.device:
                self.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
            else:
                subprocess.run(
                    f"adb -s {self.device_id} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1",
                    shell=True,
                    check=True
                )
            
            logger.info("正在启动 Master Duel...")
            time.sleep(5)  # 等待游戏启动
            
        except Exception as e:
            logger.error(f"启动游戏失败: {e}")
    
    def close_app(self, package_name: str = "jp.konami.masterduel"):
        """关闭应用"""
        try:
            if PPADB_AVAILABLE and self.device:
                self.device.shell(f"am force-stop {package_name}")
            else:
                subprocess.run(
                    f"adb -s {self.device_id} shell am force-stop {package_name}",
                    shell=True,
                    check=True
                )
            
            logger.info(f"已关闭应用: {package_name}")
            
        except Exception as e:
            logger.error(f"关闭应用失败: {e}")
    
    @staticmethod
    def list_devices() -> List[Dict[str, str]]:
        """列出所有可用设备"""
        devices = []
        
        try:
            if PPADB_AVAILABLE:
                client = AdbClient(host="127.0.0.1", port=5037)
                for device in client.devices():
                    devices.append({
                        "serial": device.serial,
                        "state": device.get_state()
                    })
            else:
                result = subprocess.run(
                    "adb devices",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                lines = result.stdout.strip().split("\n")[1:]  # 跳过第一行
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            devices.append({
                                "serial": parts[0],
                                "state": parts[1]
                            })
            
            return devices
            
        except Exception as e:
            logger.error(f"列出设备失败: {e}")
            return []
    
    @staticmethod
    def auto_detect_emulator() -> Optional[str]:
        """自动检测模拟器类型"""
        for emu_type, config in ADBController.EMULATOR_CONFIGS.items():
            try:
                if PPADB_AVAILABLE:
                    client = AdbClient(host="127.0.0.1", port=5037)
                    try:
                        client.remote_connect("127.0.0.1", config['adb_port'])
                        time.sleep(0.5)
                    except:
                        pass
                    
                    devices = client.devices()
                    device_addr = f"127.0.0.1:{config['adb_port']}"
                    
                    for device in devices:
                        if device.serial == device_addr:
                            logger.info(f"检测到模拟器: {config['name']}")
                            return emu_type
                else:
                    device_addr = f"127.0.0.1:{config['adb_port']}"
                    result = subprocess.run(
                        f"adb connect {device_addr}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    if "connected" in result.stdout.lower():
                        logger.info(f"检测到模拟器: {config['name']}")
                        return emu_type
                        
            except:
                continue
        
        return None


class AndroidGestureController:
    """Android 手势控制器"""
    
    def __init__(self, adb_controller: ADBController):
        self.adb = adb_controller
    
    def natural_tap(self, x: int, y: int):
        """自然的点击操作"""
        # 添加随机延迟和偏移
        pre_delay = random.uniform(0.05, 0.15)
        time.sleep(pre_delay)
        
        self.adb.tap(x, y)
    
    def natural_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                     steps: int = 10):
        """自然的滑动操作"""
        # 计算距离和持续时间
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        duration = int(max(300, min(1000, distance * 2)))  # 根据距离调整持续时间
        
        # 生成中间点以模拟更自然的滑动
        points = []
        for i in range(steps + 1):
            t = i / steps
            # 添加轻微的曲线
            curve_offset = random.uniform(-5, 5) * (1 - abs(t - 0.5) * 2)
            
            x = int(start_x + (end_x - start_x) * t + curve_offset)
            y = int(start_y + (end_y - start_y) * t + curve_offset)
            points.append((x, y))
        
        # 执行分段滑动
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            step_duration = duration // steps
            
            self.adb.swipe(x1, y1, x2, y2, step_duration)
            time.sleep(0.05)  # 短暂间隔
    
    def card_drag(self, card_x: int, card_y: int, target_x: int, target_y: int):
        """卡片拖拽操作"""
        logger.info(f"拖拽卡片: ({card_x}, {card_y}) -> ({target_x}, {target_y})")
        
        # 长按选中卡片
        self.adb.long_press(card_x, card_y, 500)
        time.sleep(0.2)
        
        # 拖拽到目标位置
        self.natural_swipe(card_x, card_y, target_x, target_y)
        
        # 短暂停留后释放
        time.sleep(0.1)


# 测试代码
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ADB 控制器测试 - 参考 MAA 架构")
    logger.info("=" * 60)
    
    # 检查 pure-python-adb 是否可用
    if PPADB_AVAILABLE:
        logger.success("pure-python-adb 已安装，将使用高效模式")
    else:
        logger.warning("pure-python-adb 未安装，将使用命令行模式")
        logger.info("安装命令: pip install pure-python-adb")
    
    # 列出所有设备
    logger.info("\n检测可用设备...")
    devices = ADBController.list_devices()
    if devices:
        logger.info(f"找到 {len(devices)} 个设备:")
        for dev in devices:
            logger.info(f"  - {dev['serial']} ({dev['state']})")
    else:
        logger.warning("未找到任何设备")
    
    # 自动检测模拟器
    logger.info("\n自动检测模拟器...")
    emulator_type = ADBController.auto_detect_emulator()
    
    if emulator_type:
        logger.success(f"检测到模拟器类型: {emulator_type}")
        
        # 创建控制器
        logger.info("\n创建 ADB 控制器...")
        adb = ADBController(emulator_type=emulator_type)
        
        if adb.connected:
            logger.success("ADB 连接成功！")
            
            # 获取屏幕信息
            width, height = adb.get_screen_size()
            logger.info(f"屏幕尺寸: {width}x{height}")
            
            # 测试截图
            logger.info("\n测试截图功能...")
            screenshot = adb.screenshot()
            if screenshot is not None:
                logger.success(f"截图成功，尺寸: {screenshot.shape}")
                
                # 保存截图
                cv2.imwrite("test_screenshot.png", screenshot)
                logger.info("截图已保存为 test_screenshot.png")
            
            # 测试手势控制器
            logger.info("\n创建手势控制器...")
            gesture = AndroidGestureController(adb)
            
            logger.info("5秒后开始测试点击...")
            time.sleep(5)
            
            # 测试点击
            logger.info("测试点击屏幕中心...")
            gesture.natural_tap(width // 2, height // 2)
            
            logger.info("\n测试完成！")
            
        else:
            logger.error("ADB 连接失败")
    else:
        logger.error("未检测到支持的模拟器")
        logger.info("\n支持的模拟器:")
        for emu_type, config in ADBController.EMULATOR_CONFIGS.items():
            logger.info(f"  - {config['name']} (端口: {config['adb_port']})")