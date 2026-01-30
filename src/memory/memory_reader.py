"""
Master Duel 内存读取器 - 探索版
尝试读取游戏内存中的数据
"""
import sys
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    import pymem
    import pymem.process
    HAS_PYMEM = True
except ImportError:
    HAS_PYMEM = False
    logger.error("pymem未安装，请运行: pip install pymem")


class MasterDuelMemoryReader:
    """Master Duel 内存读取器"""
    
    PROCESS_NAME = "masterduel.exe"
    
    def __init__(self):
        """初始化内存读取器"""
        self.pm: Optional[pymem.Pymem] = None
        self.base_address: int = 0
        self.game_assembly_base: int = 0
        
    def connect(self) -> bool:
        """连接到游戏进程"""
        if not HAS_PYMEM:
            logger.error("pymem未安装")
            return False
        
        try:
            self.pm = pymem.Pymem(self.PROCESS_NAME)
            self.base_address = self.pm.base_address
            
            # 获取GameAssembly.dll的基址（主要游戏逻辑）
            for module in self.pm.list_modules():
                if module.name.lower() == "gameassembly.dll":
                    self.game_assembly_base = module.lpBaseOfDll
                    logger.info(f"GameAssembly.dll 基址: 0x{self.game_assembly_base:X}")
                    break
            
            logger.info(f"成功连接到 {self.PROCESS_NAME}")
            logger.info(f"进程ID: {self.pm.process_id}")
            logger.info(f"主模块基址: 0x{self.base_address:X}")
            
            return True
            
        except pymem.exception.ProcessNotFound:
            logger.error(f"未找到进程: {self.PROCESS_NAME}")
            logger.error("请确保游戏正在运行")
            return False
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.pm:
            self.pm.close_process()
            self.pm = None
            logger.info("已断开连接")
    
    def read_int(self, address: int) -> Optional[int]:
        """读取整数"""
        try:
            return self.pm.read_int(address)
        except:
            return None
    
    def read_float(self, address: int) -> Optional[float]:
        """读取浮点数"""
        try:
            return self.pm.read_float(address)
        except:
            return None
    
    def read_string(self, address: int, length: int = 100) -> Optional[str]:
        """读取字符串"""
        try:
            return self.pm.read_string(address, length)
        except:
            return None
    
    def read_bytes(self, address: int, length: int) -> Optional[bytes]:
        """读取字节"""
        try:
            return self.pm.read_bytes(address, length)
        except:
            return None
    
    def scan_for_pattern(self, pattern: bytes, start: int = None, end: int = None) -> List[int]:
        """
        扫描内存中的特定模式
        
        Args:
            pattern: 要查找的字节模式
            start: 起始地址
            end: 结束地址
        """
        if not self.pm:
            return []
        
        results = []
        try:
            # 使用pymem的模式扫描
            results = pymem.pattern.pattern_scan_all(
                self.pm.process_handle,
                pattern,
                return_multiple=True
            )
        except Exception as e:
            logger.debug(f"扫描失败: {e}")
        
        return results if results else []
    
    def explore_game_assembly(self) -> Dict[str, Any]:
        """
        探索GameAssembly.dll的内存结构
        尝试找到有用的数据
        """
        info = {
            'base_address': hex(self.game_assembly_base),
            'found_data': []
        }
        
        if not self.game_assembly_base:
            logger.warning("GameAssembly.dll基址未找到")
            return info
        
        # 尝试读取一些已知偏移量的数据
        # 这些偏移量需要通过逆向工程确定
        # 这里只是探索性读取
        
        test_offsets = [
            0x1000, 0x2000, 0x3000, 0x4000, 0x5000,
            0x10000, 0x20000, 0x30000, 0x40000, 0x50000,
        ]
        
        for offset in test_offsets:
            addr = self.game_assembly_base + offset
            value = self.read_int(addr)
            if value and value != 0:
                info['found_data'].append({
                    'offset': hex(offset),
                    'address': hex(addr),
                    'value': value
                })
        
        return info
    
    def list_modules(self) -> List[Dict[str, Any]]:
        """列出所有加载的模块"""
        modules = []
        if self.pm:
            for module in self.pm.list_modules():
                modules.append({
                    'name': module.name,
                    'base': hex(module.lpBaseOfDll),
                    'size': module.SizeOfImage
                })
        return modules
    
    def get_process_info(self) -> Dict[str, Any]:
        """获取进程信息"""
        if not self.pm:
            return {}
        
        return {
            'process_name': self.PROCESS_NAME,
            'process_id': self.pm.process_id,
            'base_address': hex(self.base_address),
            'game_assembly_base': hex(self.game_assembly_base) if self.game_assembly_base else None,
        }


def main():
    """测试内存读取"""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    reader = MasterDuelMemoryReader()
    
    print("=" * 50)
    print("Master Duel 内存读取器 - 探索版")
    print("=" * 50)
    
    if not reader.connect():
        print("\n请确保 Master Duel 正在运行！")
        return
    
    # 显示进程信息
    print("\n【进程信息】")
    info = reader.get_process_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 列出关键模块
    print("\n【关键模块】")
    modules = reader.list_modules()
    key_modules = ['masterduel.exe', 'GameAssembly.dll', 'UnityPlayer.dll']
    for module in modules:
        if module['name'] in key_modules:
            print(f"  {module['name']}: 基址={module['base']}, 大小={module['size']//1024}KB")
    
    # 探索GameAssembly
    print("\n【探索 GameAssembly.dll】")
    exploration = reader.explore_game_assembly()
    if exploration['found_data']:
        print("  找到一些非零数据：")
        for item in exploration['found_data'][:10]:
            print(f"    偏移 {item['offset']}: {item['value']}")
    
    # 尝试读取一些常见的游戏数据位置
    print("\n【尝试读取游戏数据】")
    
    # 这些地址需要通过逆向工程找到
    # 目前只是演示框架
    print("  注意: 具体数据地址需要通过Cheat Engine等工具分析确定")
    print("  这里展示的是内存读取框架已经可以工作")
    
    reader.disconnect()
    print("\n完成！")


if __name__ == "__main__":
    main()
