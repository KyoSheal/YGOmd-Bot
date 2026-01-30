"""
卡片名称获取工具
从YGOProDeck API获取卡片中文名称
"""
import json
import requests
import time
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger

# YGOProDeck API
YGOPRODECK_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


def fetch_card_info(ydk_id: int) -> Optional[Dict]:
    """
    从YGOProDeck获取单张卡片信息
    
    Args:
        ydk_id: YDK卡片ID (即TCG/OCG官方ID)
        
    Returns:
        卡片信息字典或None
    """
    try:
        response = requests.get(
            YGOPRODECK_API,
            params={"id": ydk_id},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if "data" in data and len(data["data"]) > 0:
            card = data["data"][0]
            return {
                "id": card.get("id"),
                "name_en": card.get("name"),
                "name_zh": card.get("name"),  # API可能没有中文名
                "type": card.get("type"),
                "desc": card.get("desc"),
                "atk": card.get("atk"),
                "def": card.get("def"),
                "level": card.get("level"),
                "race": card.get("race"),
                "attribute": card.get("attribute"),
            }
    except Exception as e:
        logger.debug(f"获取卡片 {ydk_id} 失败: {e}")
    return None


def batch_fetch_cards(ydk_ids: List[int], delay: float = 0.1) -> Dict[int, Dict]:
    """
    批量获取卡片信息
    
    Args:
        ydk_ids: YDK ID列表
        delay: 请求间隔（秒）
        
    Returns:
        {ydk_id: card_info, ...}
    """
    results = {}
    total = len(ydk_ids)
    
    for i, ydk_id in enumerate(ydk_ids):
        if (i + 1) % 100 == 0:
            logger.info(f"获取进度: {i+1}/{total}")
        
        card_info = fetch_card_info(ydk_id)
        if card_info:
            results[ydk_id] = card_info
        
        time.sleep(delay)
    
    logger.info(f"成功获取 {len(results)}/{total} 张卡片信息")
    return results


def enrich_card_database(
    database_path: str,
    output_path: str,
    max_cards: Optional[int] = None
) -> bool:
    """
    丰富卡片数据库，添加名称和效果信息
    
    Args:
        database_path: 原始卡片数据库路径
        output_path: 输出路径
        max_cards: 最大获取数量（用于测试）
        
    Returns:
        是否成功
    """
    try:
        # 加载现有数据库
        with open(database_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cards = data.get("cards", {})
        
        # 收集需要获取的YDK ID
        ydk_ids_to_fetch = []
        for md_id, card_info in cards.items():
            ydk_id = card_info.get("ydk_id")
            if ydk_id and not card_info.get("name_en"):  # 还没有名称
                ydk_ids_to_fetch.append(ydk_id)
        
        if max_cards:
            ydk_ids_to_fetch = ydk_ids_to_fetch[:max_cards]
        
        logger.info(f"需要获取 {len(ydk_ids_to_fetch)} 张卡片的信息")
        
        # 批量获取
        fetched = batch_fetch_cards(ydk_ids_to_fetch)
        
        # 更新数据库
        for md_id, card_info in cards.items():
            ydk_id = card_info.get("ydk_id")
            if ydk_id and ydk_id in fetched:
                card_info.update(fetched[ydk_id])
        
        # 保存
        data["cards"] = cards
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"丰富后的数据库已保存到: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"丰富数据库失败: {e}")
        return False


# 快速创建卡片名称映射的备选方案
# 使用已知的中文卡片数据

KNOWN_CARDS = {
    # 深红恶魔相关
    89631139: {"name_zh": "深红恶魔龙", "name_en": "Red Dragon Archfiend"},
    89943724: {"name_zh": "暗红恶魔龙 深渊", "name_en": "Hot Red Dragon Archfiend Abyss"},
    46986418: {"name_zh": "青眼白龙", "name_en": "Blue-Eyes White Dragon"},
    
    # 常用卡
    24224830: {"name_zh": "灰流丽", "name_en": "Ash Blossom & Joyous Spring"},
    14558127: {"name_zh": "增殖的G", "name_en": "Maxx \"C\""},
    73642297: {"name_zh": "无限泡影", "name_en": "Infinite Impermanence"},
    
    # 共鸣者系列
    67321588: {"name_zh": "深红共鸣者", "name_en": "Crimson Resonator"},
    77292062: {"name_zh": "红莲共鸣者", "name_en": "Red Resonator"},
    27748077: {"name_zh": "同调士 共鸣者", "name_en": "Synkron Resonator"},
}


def create_quick_name_mapping(database_path: str, output_path: str) -> bool:
    """
    使用已知卡片快速创建名称映射
    """
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cards = data.get("cards", {})
        matched = 0
        
        for md_id, card_info in cards.items():
            ydk_id = card_info.get("ydk_id")
            if ydk_id and ydk_id in KNOWN_CARDS:
                card_info.update(KNOWN_CARDS[ydk_id])
                matched += 1
        
        data["cards"] = cards
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"匹配了 {matched} 张已知卡片")
        return True
    
    except Exception as e:
        logger.error(f"创建名称映射失败: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    project_root = Path(__file__).parent.parent.parent
    database_path = project_root / "data" / "card_database.json"
    enriched_path = project_root / "data" / "card_database_enriched.json"
    
    # 测试获取几张卡片
    logger.info("测试获取卡片信息...")
    
    # 测试已知卡片
    test_ids = [89631139, 24224830, 14558127]  # 深红恶魔龙, 灰流丽, 增G
    
    for ydk_id in test_ids:
        info = fetch_card_info(ydk_id)
        if info:
            logger.info(f"YDK ID {ydk_id}: {info.get('name_en')}")
        else:
            logger.warning(f"YDK ID {ydk_id}: 未找到")
    
    # 使用已知映射快速更新
    logger.info("\n使用已知卡片映射更新数据库...")
    create_quick_name_mapping(str(database_path), str(enriched_path))
