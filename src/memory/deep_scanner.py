"""
Master Duel 深度内存扫描器
尝试找到游戏状态数据的内存地址
"""
import sys
import struct
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger
from pathlib import Path

try:
    import pymem
    import pymem.process
    import pymem.pattern
    HAS_PYMEM = True
except ImportError:
    HAS_PYMEM = False

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.game_data_reader import GameDataReader


class DeepMemoryScanner:
    """深度内存扫描器 - 尝试识别游戏状态"""
    
    PROCESS_NAME = "masterduel.exe"
    
    def __init__(self):
        self.pm: Optional[pymem.Pymem] = None
        self.game_assembly_base: int = 0
        self.unity_player_base: int = 0
        
        # 加载卡片数据库用于验证
        self.card_reader = GameDataReader()
        self.card_reader.load_ydk_id_mapping()
        self.all_md_ids = set(self.card_reader.get_all_md_card_ids())
        
        logger.info(f"已加载 {len(self.all_md_ids)} 个有效卡片ID")
    
    def connect(self) -> bool:
        """连接到游戏"""
        if not HAS_PYMEM:
            return False
        
        try:
            self.pm = pymem.Pymem(self.PROCESS_NAME)
            
            for module in self.pm.list_modules():
                name = module.name.lower()
                if name == "gameassembly.dll":
                    self.game_assembly_base = module.lpBaseOfDll
                elif name == "unityplayer.dll":
                    self.unity_player_base = module.lpBaseOfDll
            
            logger.info(f"连接成功! PID: {self.pm.process_id}")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        if self.pm:
            self.pm.close_process()
            self.pm = None
    
    def scan_for_card_ids(self, scan_size: int = 10000000) -> List[Dict]:
        """
        扫描内存中的卡片ID
        
        卡片ID通常是4字节整数，范围大约在3000-25000之间
        我们搜索连续的有效卡片ID序列（可能是手牌、场上卡片等）
        """
        if not self.pm:
            return []
        
        logger.info("开始扫描卡片ID...")
        found_sequences = []
        
        # 扫描GameAssembly.dll区域
        base = self.game_assembly_base
        
        try:
            # 读取一块内存
            chunk_size = 4096
            checked = 0
            
            for offset in range(0, min(scan_size, 60000000), chunk_size):
                try:
                    data = self.pm.read_bytes(base + offset, chunk_size)
                    
                    # 搜索连续的有效卡片ID
                    for i in range(0, len(data) - 20, 4):
                        # 读取5个连续的4字节整数
                        values = struct.unpack('<5I', data[i:i+20])
                        
                        # 检查是否是有效的卡片ID序列
                        valid_count = sum(1 for v in values if v in self.all_md_ids)
                        
                        if valid_count >= 3:  # 至少3个有效卡片ID
                            addr = base + offset + i
                            found_sequences.append({
                                'address': hex(addr),
                                'offset': hex(offset + i),
                                'card_ids': values,
                                'valid_count': valid_count
                            })
                            logger.info(f"发现卡片ID序列 @ {hex(addr)}: {values}")
                    
                    checked += chunk_size
                    if checked % 1000000 == 0:
                        logger.info(f"已扫描 {checked // 1000000}MB...")
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"扫描出错: {e}")
        
        logger.info(f"扫描完成，找到 {len(found_sequences)} 个可能的卡片序列")
        return found_sequences
    
    def scan_for_lp(self, target_lp: int = 8000) -> List[Dict]:
        """
        扫描LP值
        
        LP通常在游戏开始时是8000，可以搜索这个值
        """
        if not self.pm:
            return []
        
        logger.info(f"搜索LP值: {target_lp}")
        found = []
        
        base = self.game_assembly_base
        chunk_size = 4096
        
        for offset in range(0, 10000000, chunk_size):
            try:
                data = self.pm.read_bytes(base + offset, chunk_size)
                
                for i in range(0, len(data) - 4, 4):
                    value = struct.unpack('<I', data[i:i+4])[0]
                    if value == target_lp:
                        addr = base + offset + i
                        found.append({
                            'address': hex(addr),
                            'offset': hex(offset + i),
                            'value': value
                        })
                        
            except:
                continue
        
        logger.info(f"找到 {len(found)} 个LP候选地址")
        return found[:20]  # 返回前20个
    
    def read_potential_hand(self, address: int, count: int = 10) -> List[int]:
        """
        尝试读取指定地址的手牌数据
        """
        if not self.pm:
            return []
        
        try:
            data = self.pm.read_bytes(address, count * 4)
            values = struct.unpack(f'<{count}I', data)
            
            # 过滤有效的卡片ID
            valid_ids = [v for v in values if v in self.all_md_ids]
            return valid_ids
        except:
            return []
    
    def get_game_state_summary(self) -> Dict:
        """
        尝试获取游戏状态摘要
        """
        summary = {
            'connected': self.pm is not None,
            'process_id': self.pm.process_id if self.pm else None,
            'game_assembly_base': hex(self.game_assembly_base) if self.game_assembly_base else None,
            'found_card_sequences': [],
            'found_lp_addresses': [],
        }
        
        # 快速扫描
        card_seqs = self.scan_for_card_ids(scan_size=5000000)
        summary['found_card_sequences'] = card_seqs[:5]
        
        # 搜索LP
        lp_addrs = self.scan_for_lp(8000)
        summary['found_lp_addresses'] = lp_addrs[:5]
        
        return summary


def main():
    """测试深度扫描"""
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    
    print("=" * 60)
    print("Master Duel 深度内存扫描器")
    print("=" * 60)
    
    scanner = DeepMemoryScanner()
    
    if not scanner.connect():
        print("\n❌ 无法连接到游戏！请确保 Master Duel 正在运行。")
        return
    
    print(f"\n✅ 已连接到游戏 (PID: {scanner.pm.process_id})")
    print(f"   GameAssembly.dll: {hex(scanner.game_assembly_base)}")
    
    # 搜索LP值 (快速测试)
    print("\n🔍 搜索LP值 (8000)...")
    lp_results = scanner.scan_for_lp(8000)
    if lp_results:
        print(f"   找到 {len(lp_results)} 个候选地址")
        for r in lp_results[:3]:
            print(f"   - {r['address']}")
    
    # 搜索卡片ID序列 (这个会比较慢)
    print("\n🔍 搜索卡片ID序列 (这可能需要一些时间)...")
    card_results = scanner.scan_for_card_ids(scan_size=5000000)
    if card_results:
        print(f"\n   找到 {len(card_results)} 个可能的卡片序列：")
        for r in card_results[:5]:
            print(f"   - 地址: {r['address']}")
            print(f"     卡片ID: {r['card_ids']}")
            print(f"     有效数: {r['valid_count']}/5")
    else:
        print("   未找到明显的卡片ID序列")
        print("   (可能需要在决斗中运行此扫描)")
    
    scanner.disconnect()
    print("\n✅ 扫描完成！")


if __name__ == "__main__":
    main()
