"""
验证找到的手牌地址区域
"""
import sys
import struct
from pathlib import Path
from loguru import logger

try:
    import pymem
    HAS_PYMEM = True
except ImportError:
    HAS_PYMEM = False

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.game_data_reader import GameDataReader


def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    
    # 加载卡片数据库
    reader = GameDataReader()
    reader.load_ydk_id_mapping()
    reader.load_card_rarities()
    
    # 已知的MD ID映射
    card_names = {
        8933: "效果遮蔽者",
        4030: "骸骨恶魔",
        13631: "无限泡影",
        6341: "骸骨魔导王",
    }
    
    print("=" * 60)
    print("验证手牌地址区域")
    print("=" * 60)
    
    try:
        pm = pymem.Pymem("masterduel.exe")
        print(f"\n✅ 连接成功 (PID: {pm.process_id})")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return
    
    # 发现的关键地址 - 3个连续的骸骨恶魔附近
    # 0x7ff9a4e74190, 0x7ff9a4e7419c, 0x7ff9a4e741a8
    # 相差12字节，可能每个卡片占用12字节
    
    suspect_base = 0x7ff9a4e74190 - 100 * 12  # 往前看一些
    
    print(f"\n🔍 分析地址区域 {hex(suspect_base)} 附近...")
    print("   (每12字节读取一个潜在的卡片ID)")
    print()
    
    # 读取更大范围
    try:
        data = pm.read_bytes(suspect_base, 2400)  # 200个潜在位置
        
        found_cards = []
        
        for i in range(0, len(data), 12):
            # 尝试不同的偏移
            for offset in [0, 4, 8]:
                if i + offset + 4 <= len(data):
                    value = struct.unpack('<I', data[i+offset:i+offset+4])[0]
                    
                    # 检查是否是有效卡片ID
                    if value in card_names:
                        addr = suspect_base + i + offset
                        found_cards.append({
                            'address': hex(addr),
                            'slot': i // 12,
                            'offset_in_slot': offset,
                            'md_id': value,
                            'name': card_names[value]
                        })
        
        if found_cards:
            print("  找到的手牌卡片:")
            print("-" * 50)
            
            # 按地址排序
            found_cards.sort(key=lambda x: int(x['address'], 16))
            
            prev_addr = None
            for card in found_cards:
                if prev_addr:
                    gap = int(card['address'], 16) - prev_addr
                    gap_info = f" (间隔: {gap} bytes)"
                else:
                    gap_info = ""
                    
                print(f"  {card['address']}: {card['name']:<12} (MD ID: {card['md_id']}){gap_info}")
                prev_addr = int(card['address'], 16)
        else:
            print("  未找到已知卡片")
            
    except Exception as e:
        print(f"❌ 读取失败: {e}")
    
    # 也看看效果遮蔽者附近
    print("\n" + "=" * 60)
    print("🔍 分析效果遮蔽者地址 0x7ff9a4e65644 附近...")
    
    veiler_addr = 0x7ff9a4e65644
    try:
        data = pm.read_bytes(veiler_addr - 200, 600)
        
        print("   读取前后200字节，搜索所有已知卡片ID...")
        
        for i in range(0, len(data) - 4, 4):
            value = struct.unpack('<I', data[i:i+4])[0]
            if value in card_names:
                actual_addr = veiler_addr - 200 + i
                relative = i - 200
                print(f"   {hex(actual_addr)}: {card_names[value]} (相对位置: {relative:+d})")
                
    except Exception as e:
        print(f"❌ 读取失败: {e}")
    
    pm.close_process()
    print("\n✅ 分析完成!")


if __name__ == "__main__":
    main()
