"""
实时监控游戏状态变化
记录发动效果前后的内存变化
"""
import sys
import struct
import time
from pathlib import Path
from typing import Dict, List, Set
from loguru import logger

try:
    import pymem
    HAS_PYMEM = True
except ImportError:
    HAS_PYMEM = False

# 卡片ID映射
CARD_NAMES = {
    8933: "效果遮蔽者",
    4030: "骸骨恶魔",
    3892: "无限泡影",
    6341: "骸骨魔导王",
}

# 已知的关键地址
KNOWN_ADDRESSES = {
    'veiler': 0x7ff9a4e65644,  # 效果遮蔽者
    'skull1': 0x7ff9a4e74190,  # 骸骨恶魔 #1
    'skull2': 0x7ff9a4e7419c,  # 骸骨恶魔 #2
    'skull3': 0x7ff9a4e741a8,  # 骸骨恶魔 #3
}


class GameStateMonitor:
    """游戏状态监控器"""
    
    def __init__(self):
        self.pm = None
        self.snapshots: List[Dict] = []
    
    def connect(self) -> bool:
        try:
            self.pm = pymem.Pymem("masterduel.exe")
            logger.info(f"连接成功! PID: {self.pm.process_id}")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        if self.pm:
            self.pm.close_process()
            self.pm = None
    
    def read_card_at(self, address: int) -> Dict:
        """读取指定地址的卡片信息"""
        try:
            # 读取12字节（一张卡片的完整数据）
            data = self.pm.read_bytes(address, 12)
            card_id = struct.unpack('<I', data[0:4])[0]
            field1 = struct.unpack('<I', data[4:8])[0]
            field2 = struct.unpack('<I', data[8:12])[0]
            
            return {
                'address': hex(address),
                'card_id': card_id,
                'card_name': CARD_NAMES.get(card_id, f"未知({card_id})"),
                'field1': field1,
                'field2': field2,
                'raw': data.hex()
            }
        except Exception as e:
            return {'address': hex(address), 'error': str(e)}
    
    def scan_region_for_cards(self, base: int, size: int = 2000) -> List[Dict]:
        """扫描区域中的所有已知卡片"""
        found = []
        try:
            data = self.pm.read_bytes(base, size)
            for i in range(0, len(data) - 4, 4):
                value = struct.unpack('<I', data[i:i+4])[0]
                if value in CARD_NAMES:
                    found.append({
                        'address': hex(base + i),
                        'offset': i,
                        'card_id': value,
                        'card_name': CARD_NAMES[value]
                    })
        except Exception as e:
            logger.error(f"扫描失败: {e}")
        return found
    
    def take_snapshot(self, label: str = "") -> Dict:
        """拍摄当前状态快照"""
        snapshot = {
            'label': label,
            'timestamp': time.time(),
            'known_cards': {},
            'hand_region_scan': [],
        }
        
        # 读取已知地址的卡片
        for name, addr in KNOWN_ADDRESSES.items():
            snapshot['known_cards'][name] = self.read_card_at(addr)
        
        # 扫描骸骨恶魔区域附近
        skull_base = KNOWN_ADDRESSES['skull1'] - 200
        snapshot['hand_region_scan'] = self.scan_region_for_cards(skull_base, 1000)
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def compare_snapshots(self, before: Dict, after: Dict) -> Dict:
        """比较两个快照"""
        changes = {
            'cards_removed': [],
            'cards_added': [],
            'cards_changed': [],
            'value_changes': [],
        }
        
        # 比较已知地址的卡片
        for name in KNOWN_ADDRESSES.keys():
            before_card = before['known_cards'].get(name, {})
            after_card = after['known_cards'].get(name, {})
            
            before_id = before_card.get('card_id', 0)
            after_id = after_card.get('card_id', 0)
            
            if before_id != after_id:
                if before_id in CARD_NAMES and after_id not in CARD_NAMES:
                    changes['cards_removed'].append({
                        'position': name,
                        'card': CARD_NAMES.get(before_id, str(before_id)),
                        'address': before_card.get('address')
                    })
                elif after_id in CARD_NAMES and before_id not in CARD_NAMES:
                    changes['cards_added'].append({
                        'position': name,
                        'card': CARD_NAMES.get(after_id, str(after_id)),
                        'address': after_card.get('address')
                    })
                else:
                    changes['cards_changed'].append({
                        'position': name,
                        'before': CARD_NAMES.get(before_id, str(before_id)),
                        'after': CARD_NAMES.get(after_id, str(after_id)),
                        'address': before_card.get('address')
                    })
        
        # 比较扫描区域
        before_cards = {c['address']: c for c in before.get('hand_region_scan', [])}
        after_cards = {c['address']: c for c in after.get('hand_region_scan', [])}
        
        # 找出消失的卡片
        for addr, card in before_cards.items():
            if addr not in after_cards:
                changes['cards_removed'].append({
                    'address': addr,
                    'card': card['card_name'],
                    'from_scan': True
                })
        
        # 找出新增的卡片
        for addr, card in after_cards.items():
            if addr not in before_cards:
                changes['cards_added'].append({
                    'address': addr,
                    'card': card['card_name'],
                    'from_scan': True
                })
        
        return changes
    
    def print_snapshot(self, snapshot: Dict):
        """打印快照信息"""
        print(f"\n📸 快照: {snapshot['label']}")
        print("-" * 50)
        
        print("已知地址的卡片:")
        for name, card in snapshot['known_cards'].items():
            if 'error' not in card:
                print(f"  {name}: {card['card_name']} (ID:{card['card_id']}) @ {card['address']}")
            else:
                print(f"  {name}: 错误 - {card['error']}")
        
        print(f"\n区域扫描 (找到 {len(snapshot['hand_region_scan'])} 张卡):")
        for card in snapshot['hand_region_scan']:
            print(f"  {card['address']}: {card['card_name']}")


def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    
    print("=" * 60)
    print("🎮 Master Duel 状态监控器")
    print("   监控骸骨恶魔效果发动前后的变化")
    print("=" * 60)
    
    monitor = GameStateMonitor()
    
    if not monitor.connect():
        print("❌ 无法连接到游戏")
        return
    
    # 第一次快照 - 发动效果前
    print("\n📌 记录发动效果前的状态...")
    before = monitor.take_snapshot("发动效果前")
    monitor.print_snapshot(before)
    
    print("\n" + "=" * 60)
    print("🎯 请现在发动骸骨恶魔的效果！")
    print("   (丢弃一张手牌，特殊召唤骸骨恶魔)")
    print("=" * 60)
    input("\n按 Enter 键继续（在发动效果完成后）...")
    
    # 第二次快照 - 发动效果后
    print("\n📌 记录发动效果后的状态...")
    after = monitor.take_snapshot("发动效果后")
    monitor.print_snapshot(after)
    
    # 比较变化
    print("\n" + "=" * 60)
    print("📊 分析变化")
    print("=" * 60)
    
    changes = monitor.compare_snapshots(before, after)
    
    if changes['cards_removed']:
        print("\n🔴 从手牌移除的卡片:")
        for c in changes['cards_removed']:
            print(f"   - {c['card']} @ {c.get('address', c.get('position'))}")
    
    if changes['cards_added']:
        print("\n🟢 新增的卡片:")
        for c in changes['cards_added']:
            print(f"   + {c['card']} @ {c.get('address', c.get('position'))}")
    
    if changes['cards_changed']:
        print("\n🔄 位置上的卡片变化:")
        for c in changes['cards_changed']:
            print(f"   {c['position']}: {c['before']} → {c['after']}")
    
    if not any([changes['cards_removed'], changes['cards_added'], changes['cards_changed']]):
        print("\n⚠️ 未检测到明显变化")
        print("   可能原因: 游戏数据结构不同于预期，或地址已变化")
    
    monitor.disconnect()
    print("\n✅ 监控完成!")


if __name__ == "__main__":
    main()
