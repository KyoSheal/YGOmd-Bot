"""
Master Duel 实时游戏状态监控
持续监控游戏状态变化
"""
import sys
import struct
import time
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
from loguru import logger

try:
    import pymem
    import pymem.process
    HAS_PYMEM = True
except ImportError:
    HAS_PYMEM = False
    print("请安装pymem: pip install pymem")

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.game_data_reader import GameDataReader


class RealTimeMonitor:
    """实时游戏状态监控器"""
    
    PROCESS_NAME = "masterduel.exe"
    
    def __init__(self):
        self.pm: Optional[pymem.Pymem] = None
        self.game_assembly_base = 0
        
        # 加载卡片数据库
        self.card_reader = GameDataReader()
        self.card_reader.load_ydk_id_mapping()
        self.all_md_ids = set(self.card_reader.get_all_md_card_ids())
        
        # 状态记录
        self.detected_cards: Dict[int, str] = {}  # address -> card_name
        self.game_events: List[Dict] = []
        
        # 监控配置
        self.scan_interval = 1.0  # 扫描间隔（秒）
        self.running = False
        
    def connect(self) -> bool:
        """连接到游戏"""
        if not HAS_PYMEM:
            return False
        try:
            self.pm = pymem.Pymem(self.PROCESS_NAME)
            for mod in self.pm.list_modules():
                if mod.name.lower() == "gameassembly.dll":
                    self.game_assembly_base = mod.lpBaseOfDll
                    break
            logger.info(f"已连接到游戏 PID: {self.pm.process_id}")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.pm:
            self.pm.close_process()
            self.pm = None
    
    def scan_for_cards_in_heap(self) -> Dict[int, int]:
        """扫描堆内存中的卡片ID"""
        found = {}
        
        # 获取进程的内存区域
        try:
            import ctypes
            from ctypes import wintypes
            
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            MEM_COMMIT = 0x1000
            PAGE_READWRITE = 0x04
            
            class MEMORY_BASIC_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("BaseAddress", ctypes.c_void_p),
                    ("AllocationBase", ctypes.c_void_p),
                    ("AllocationProtect", wintypes.DWORD),
                    ("RegionSize", ctypes.c_size_t),
                    ("State", wintypes.DWORD),
                    ("Protect", wintypes.DWORD),
                    ("Type", wintypes.DWORD),
                ]
            
            kernel32 = ctypes.windll.kernel32
            
            address = 0
            regions_scanned = 0
            
            while True:
                mbi = MEMORY_BASIC_INFORMATION()
                result = kernel32.VirtualQueryEx(
                    self.pm.process_handle,
                    ctypes.c_void_p(address),
                    ctypes.byref(mbi),
                    ctypes.sizeof(mbi)
                )
                
                if result == 0:
                    break
                
                # 只扫描已提交的可读写内存（堆内存）
                if (mbi.State == MEM_COMMIT and 
                    mbi.Protect == PAGE_READWRITE and
                    mbi.RegionSize > 0 and 
                    mbi.RegionSize < 100000000):  # 跳过太大的区域
                    
                    try:
                        data = self.pm.read_bytes(mbi.BaseAddress, min(mbi.RegionSize, 1000000))
                        
                        for i in range(0, len(data) - 4, 4):
                            value = struct.unpack('<I', data[i:i+4])[0]
                            if value in self.all_md_ids:
                                addr = mbi.BaseAddress + i
                                found[addr] = value
                        
                        regions_scanned += 1
                    except:
                        pass
                
                address = mbi.BaseAddress + mbi.RegionSize
                
                # 限制扫描范围
                if regions_scanned > 100:
                    break
            
            logger.debug(f"扫描了 {regions_scanned} 个内存区域")
            
        except Exception as e:
            logger.error(f"堆扫描失败: {e}")
        
        return found
    
    def get_card_name(self, md_id: int) -> str:
        """获取卡片名称"""
        # 常用卡片名称缓存
        known = {
            8933: "效果遮蔽者",
            4030: "骸骨恶魔", 
            3892: "无限泡影",
            6341: "骸骨魔导王",
            3801: "青眼白龙",
            4041: "黑魔导",
        }
        return known.get(md_id, f"卡片#{md_id}")
    
    def detect_changes(self, old_cards: Dict[int, int], new_cards: Dict[int, int]) -> List[Dict]:
        """检测卡片变化"""
        events = []
        
        old_set = set(old_cards.keys())
        new_set = set(new_cards.keys())
        
        # 新增的卡片
        for addr in new_set - old_set:
            card_id = new_cards[addr]
            events.append({
                'type': 'card_appeared',
                'card_id': card_id,
                'card_name': self.get_card_name(card_id),
                'address': hex(addr),
                'time': datetime.now().isoformat()
            })
        
        # 消失的卡片
        for addr in old_set - new_set:
            card_id = old_cards[addr]
            events.append({
                'type': 'card_disappeared',
                'card_id': card_id,
                'card_name': self.get_card_name(card_id),
                'address': hex(addr),
                'time': datetime.now().isoformat()
            })
        
        return events
    
    def run_continuous(self, duration: int = 60):
        """持续监控指定时间（秒）"""
        if not self.connect():
            print("❌ 无法连接到游戏")
            return
        
        print(f"\n🔄 开始持续监控 ({duration}秒)...")
        print("   按 Ctrl+C 停止\n")
        
        self.running = True
        start_time = time.time()
        previous_cards = {}
        
        try:
            while self.running and (time.time() - start_time) < duration:
                # 扫描当前状态
                current_cards = self.scan_for_cards_in_heap()
                
                # 检测变化
                if previous_cards:
                    events = self.detect_changes(previous_cards, current_cards)
                    for event in events:
                        self.game_events.append(event)
                        if event['type'] == 'card_appeared':
                            print(f"  🟢 {event['time'][-8:]}: 出现 {event['card_name']}")
                        else:
                            print(f"  🔴 {event['time'][-8:]}: 消失 {event['card_name']}")
                
                # 首次显示当前状态
                if not previous_cards and current_cards:
                    print(f"  📋 检测到 {len(current_cards)} 个卡片ID在内存中")
                    # 统计各卡片出现次数
                    card_counts = {}
                    for addr, card_id in current_cards.items():
                        name = self.get_card_name(card_id)
                        card_counts[name] = card_counts.get(name, 0) + 1
                    
                    for name, count in sorted(card_counts.items(), key=lambda x: -x[1])[:10]:
                        print(f"      {name}: {count}次")
                
                previous_cards = current_cards
                
                # 显示进度
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                sys.stdout.write(f"\r   监控中... 剩余 {remaining}秒    ")
                sys.stdout.flush()
                
                time.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            print("\n\n   用户中断")
        
        self.running = False
        self.disconnect()
        
        # 保存事件日志
        if self.game_events:
            log_path = project_root / "data" / "game_events.json"
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.game_events, f, ensure_ascii=False, indent=2)
            print(f"\n📁 事件日志已保存到: {log_path}")
        
        print("\n✅ 监控结束!")
        print(f"   共检测到 {len(self.game_events)} 个事件")


def main():
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    
    print("=" * 60)
    print("🎮 Master Duel 实时监控器")
    print("=" * 60)
    
    monitor = RealTimeMonitor()
    
    print(f"\n📊 已加载 {len(monitor.all_md_ids)} 个有效卡片ID")
    
    # 运行60秒的持续监控
    monitor.run_continuous(duration=120)


if __name__ == "__main__":
    main()
