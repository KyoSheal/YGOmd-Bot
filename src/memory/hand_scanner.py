"""
针对特定手牌的内存扫描
用户手牌: 1x效果遮蔽者, 3x骸骨恶魔, 2x无限泡影
LP: 8000
"""
import sys
import struct
from pathlib import Path
from typing import List, Dict, Set
from loguru import logger

try:
    import pymem
    HAS_PYMEM = True
except ImportError:
    HAS_PYMEM = False

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.game_data_reader import GameDataReader


# 已知卡片ID (从YGOProDeck)
KNOWN_CARDS = {
    # 效果遮蔽者 Effect Veiler
    97268402: "效果遮蔽者",
    # 无限泡影 Infinite Impermanence  
    10045474: "无限泡影",
    # 骸骨恶魔 Skull Servant
    32274490: "骸骨恶魔",
    # 备选 - 骸骨魔导 King of the Skull Servants
    36021814: "骸骨魔导王",
}


def find_md_ids_for_cards():
    """查找这些卡片在Master Duel中的ID"""
    reader = GameDataReader()
    reader.load_ydk_id_mapping()
    
    results = {}
    for ydk_id, name in KNOWN_CARDS.items():
        md_id = reader.get_md_id_from_ydk(ydk_id)
        if md_id:
            results[name] = {'ydk_id': ydk_id, 'md_id': md_id}
            logger.info(f"{name}: YDK={ydk_id} -> MD={md_id}")
        else:
            logger.warning(f"{name}: YDK={ydk_id} -> 未找到MD ID")
    
    return results


def scan_for_specific_cards(target_md_ids: Set[int], scan_heap: bool = True):
    """扫描内存中的特定卡片ID"""
    if not HAS_PYMEM:
        logger.error("pymem未安装")
        return []
    
    try:
        pm = pymem.Pymem("masterduel.exe")
        logger.info(f"连接成功! PID: {pm.process_id}")
    except Exception as e:
        logger.error(f"连接失败: {e}")
        return []
    
    found = []
    
    # 获取所有模块
    modules_to_scan = []
    for module in pm.list_modules():
        name = module.name.lower()
        # 扫描关键模块
        if name in ['gameassembly.dll', 'unityplayer.dll', 'masterduel.exe']:
            modules_to_scan.append({
                'name': module.name,
                'base': module.lpBaseOfDll,
                'size': module.SizeOfImage
            })
    
    for mod in modules_to_scan:
        logger.info(f"扫描 {mod['name']} (大小: {mod['size']//1024//1024}MB)...")
        
        base = mod['base']
        size = mod['size']
        chunk_size = 65536  # 64KB chunks
        
        for offset in range(0, size, chunk_size):
            try:
                read_size = min(chunk_size, size - offset)
                data = pm.read_bytes(base + offset, read_size)
                
                # 搜索4字节整数
                for i in range(0, len(data) - 4, 4):
                    value = struct.unpack('<I', data[i:i+4])[0]
                    
                    if value in target_md_ids:
                        addr = base + offset + i
                        found.append({
                            'address': hex(addr),
                            'module': mod['name'],
                            'offset_in_module': hex(offset + i),
                            'md_id': value
                        })
                        
            except Exception as e:
                continue
        
        logger.info(f"  {mod['name']} 扫描完成")
    
    pm.close_process()
    return found


def scan_for_lp_8000():
    """专门搜索LP值8000"""
    if not HAS_PYMEM:
        return []
    
    try:
        pm = pymem.Pymem("masterduel.exe")
    except:
        return []
    
    found = []
    target = 8000
    
    # 扫描UnityPlayer.dll (游戏逻辑可能在这里)
    for module in pm.list_modules():
        if module.name.lower() == 'unityplayer.dll':
            base = module.lpBaseOfDll
            size = module.SizeOfImage
            chunk_size = 65536
            
            logger.info(f"在 UnityPlayer.dll 中搜索 LP=8000...")
            
            for offset in range(0, min(size, 10000000), chunk_size):
                try:
                    data = pm.read_bytes(base + offset, chunk_size)
                    for i in range(0, len(data) - 4, 4):
                        value = struct.unpack('<I', data[i:i+4])[0]
                        if value == target:
                            # 检查附近是否也有8000（双方LP）
                            nearby_8000 = False
                            for j in range(-100, 100, 4):
                                if i + j >= 0 and i + j + 4 <= len(data):
                                    try:
                                        nearby = struct.unpack('<I', data[i+j:i+j+4])[0]
                                        if nearby == 8000 and j != 0:
                                            nearby_8000 = True
                                            break
                                    except:
                                        pass
                            
                            found.append({
                                'address': hex(base + offset + i),
                                'has_nearby_8000': nearby_8000
                            })
                except:
                    continue
            break
    
    pm.close_process()
    return found


def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {message}")
    
    print("=" * 60)
    print("Master Duel 手牌扫描器")
    print("目标手牌: 1x效果遮蔽者, 3x骸骨恶魔, 2x无限泡影")
    print("=" * 60)
    
    # 1. 找出这些卡的MD ID
    print("\n📋 查找卡片ID...")
    card_info = find_md_ids_for_cards()
    
    if not card_info:
        print("❌ 无法找到卡片ID")
        return
    
    # 收集所有MD ID
    target_ids = set()
    for name, info in card_info.items():
        target_ids.add(info['md_id'])
        print(f"  ✓ {name}: MD ID = {info['md_id']}")
    
    # 2. 扫描LP
    print("\n🔍 搜索LP值 (8000)...")
    lp_results = scan_for_lp_8000()
    paired_lp = [r for r in lp_results if r.get('has_nearby_8000')]
    print(f"  找到 {len(lp_results)} 个值为8000的地址")
    print(f"  其中 {len(paired_lp)} 个附近也有8000 (可能是双方LP)")
    
    if paired_lp:
        print("  可能的LP地址对:")
        for r in paired_lp[:5]:
            print(f"    {r['address']}")
    
    # 3. 扫描手牌卡片ID
    print("\n🔍 搜索手牌卡片ID...")
    card_results = scan_for_specific_cards(target_ids)
    
    if card_results:
        print(f"\n  找到 {len(card_results)} 个匹配的卡片ID:")
        
        # 按模块分组
        by_module = {}
        for r in card_results:
            mod = r['module']
            if mod not in by_module:
                by_module[mod] = []
            by_module[mod].append(r)
        
        for mod, results in by_module.items():
            print(f"\n  [{mod}]")
            # 找出现次数最多的地址附近区域
            for r in results[:10]:
                card_name = next((n for n, i in card_info.items() if i['md_id'] == r['md_id']), "?")
                print(f"    {r['address']}: {card_name} (MD ID: {r['md_id']})")
    else:
        print("  未找到匹配的卡片ID")
        print("  注意: 游戏可能使用加密或压缩的内存格式")
    
    print("\n✅ 扫描完成!")


if __name__ == "__main__":
    main()
