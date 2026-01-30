"""
Master Duel 游戏数据读取器
从本地游戏数据中提取卡片数据库
"""
import json
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


class GameDataReader:
    """
    Master Duel 游戏数据读取器
    
    从YgoMaster数据或游戏本地缓存中读取卡片信息
    """
    
    # 默认游戏数据路径
    DEFAULT_PATHS = [
        # YgoMaster数据路径
        Path(r"D:\SteamLibrary\steamapps\common\Yu-Gi-Oh!  Master Duel\YgoMaster\Data"),
        # Steam默认安装路径
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\Yu-Gi-Oh!  Master Duel\YgoMaster\Data"),
    ]
    
    def __init__(self, data_path: Optional[str] = None):
        """
        初始化数据读取器
        
        Args:
            data_path: YgoMaster/Data 目录路径，如果为None则自动检测
        """
        self.data_path = self._find_data_path(data_path)
        
        # 缓存数据
        self._ydk_id_map: Optional[Dict[int, int]] = None  # YDK ID -> MD ID
        self._md_id_map: Optional[Dict[int, int]] = None   # MD ID -> YDK ID  
        self._card_names: Optional[Dict[int, str]] = None  # MD ID -> 卡片名称
        self._card_rarities: Optional[Dict[int, int]] = None  # MD ID -> 稀有度
        
        if self.data_path:
            logger.info(f"找到游戏数据目录: {self.data_path}")
        else:
            logger.warning("未找到游戏数据目录，部分功能不可用")
    
    def _find_data_path(self, custom_path: Optional[str]) -> Optional[Path]:
        """查找游戏数据目录"""
        if custom_path:
            path = Path(custom_path)
            if path.exists():
                return path
            logger.warning(f"指定路径不存在: {custom_path}")
        
        # 尝试默认路径
        for path in self.DEFAULT_PATHS:
            if path.exists():
                return path
        
        return None
    
    def load_ydk_id_mapping(self) -> Dict[int, int]:
        """
        加载YDK ID到Master Duel ID的映射
        
        YDK是通用的卡组格式，使用TCG/OCG官方卡片ID
        Master Duel使用自己的内部ID系统
        
        Returns:
            {ydk_id: md_id, ...}
        """
        if self._ydk_id_map is not None:
            return self._ydk_id_map
        
        if not self.data_path:
            return {}
        
        ydk_file = self.data_path / "YdkIds.txt"
        if not ydk_file.exists():
            logger.error(f"YdkIds.txt 不存在: {ydk_file}")
            return {}
        
        self._ydk_id_map = {}
        self._md_id_map = {}
        
        with open(ydk_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        ydk_id = int(parts[0])
                        md_id = int(parts[1])
                        self._ydk_id_map[ydk_id] = md_id
                        self._md_id_map[md_id] = ydk_id
                    except ValueError:
                        continue
        
        logger.info(f"加载了 {len(self._ydk_id_map)} 个卡片ID映射")
        return self._ydk_id_map
    
    def load_card_rarities(self) -> Dict[int, int]:
        """
        加载卡片稀有度
        
        稀有度: 1=N, 2=R, 3=SR, 4=UR
        
        Returns:
            {md_id: rarity, ...}
        """
        if self._card_rarities is not None:
            return self._card_rarities
        
        if not self.data_path:
            return {}
        
        card_list_file = self.data_path / "CardList.json"
        if not card_list_file.exists():
            logger.error(f"CardList.json 不存在: {card_list_file}")
            return {}
        
        with open(card_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._card_rarities = {}
        for md_id_str, rarity in data.items():
            try:
                self._card_rarities[int(md_id_str)] = rarity
            except ValueError:
                continue
        
        logger.info(f"加载了 {len(self._card_rarities)} 个卡片稀有度")
        return self._card_rarities
    
    def get_md_id_from_ydk(self, ydk_id: int) -> Optional[int]:
        """从YDK ID获取Master Duel内部ID"""
        if self._ydk_id_map is None:
            self.load_ydk_id_mapping()
        return self._ydk_id_map.get(ydk_id)
    
    def get_ydk_id_from_md(self, md_id: int) -> Optional[int]:
        """从Master Duel内部ID获取YDK ID"""
        if self._md_id_map is None:
            self.load_ydk_id_mapping()
        return self._md_id_map.get(md_id)
    
    def get_rarity_name(self, rarity: int) -> str:
        """获取稀有度名称"""
        rarity_names = {
            1: "N",
            2: "R", 
            3: "SR",
            4: "UR"
        }
        return rarity_names.get(rarity, "Unknown")
    
    def get_all_md_card_ids(self) -> List[int]:
        """获取所有Master Duel卡片ID"""
        if self._card_rarities is None:
            self.load_card_rarities()
        return list(self._card_rarities.keys())
    
    def build_card_database(self) -> Dict[int, Dict[str, Any]]:
        """
        构建完整的卡片数据库
        
        Returns:
            {
                md_id: {
                    'md_id': int,
                    'ydk_id': int,
                    'rarity': int,
                    'rarity_name': str
                },
                ...
            }
        """
        self.load_ydk_id_mapping()
        self.load_card_rarities()
        
        database = {}
        
        for md_id, rarity in self._card_rarities.items():
            database[md_id] = {
                'md_id': md_id,
                'ydk_id': self._md_id_map.get(md_id),
                'rarity': rarity,
                'rarity_name': self.get_rarity_name(rarity)
            }
        
        logger.info(f"构建了 {len(database)} 张卡片的数据库")
        return database
    
    def export_card_database(self, output_path: str) -> bool:
        """
        导出卡片数据库为JSON
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            database = self.build_card_database()
            
            # 转换为可序列化格式（key必须是字符串）
            export_data = {
                'total_cards': len(database),
                'cards': {str(k): v for k, v in database.items()}
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"卡片数据库已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False


class CardNameResolver:
    """
    卡片名称解析器
    
    使用游戏数据和外部API解析卡片名称
    """
    
    # YGOProDeck API (可选的外部数据源)
    YGOPRODECK_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    
    def __init__(self, game_data_reader: GameDataReader):
        """
        初始化名称解析器
        
        Args:
            game_data_reader: GameDataReader实例
        """
        self.reader = game_data_reader
        self._name_cache: Dict[int, str] = {}  # ydk_id -> name
    
    def get_card_name_by_ydk_id(self, ydk_id: int) -> Optional[str]:
        """
        通过YDK ID获取卡片名称
        
        首先检查缓存，然后可以扩展为调用外部API
        
        Args:
            ydk_id: YDK卡片ID
            
        Returns:
            卡片名称或None
        """
        if ydk_id in self._name_cache:
            return self._name_cache[ydk_id]
        
        # TODO: 可以扩展为从YGOProDeck API获取名称
        # 或者解析本地的CARD_Name.bytes
        
        return None
    
    def get_card_name_by_md_id(self, md_id: int) -> Optional[str]:
        """
        通过Master Duel ID获取卡片名称
        
        Args:
            md_id: Master Duel内部卡片ID
            
        Returns:
            卡片名称或None
        """
        ydk_id = self.reader.get_ydk_id_from_md(md_id)
        if ydk_id:
            return self.get_card_name_by_ydk_id(ydk_id)
        return None
    
    def load_name_mapping_from_json(self, json_path: str) -> int:
        """
        从JSON文件加载卡片名称映射
        
        JSON格式: {"ydk_id": "卡片名称", ...}
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            加载的名称数量
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for ydk_id_str, name in data.items():
                try:
                    self._name_cache[int(ydk_id_str)] = name
                except ValueError:
                    continue
            
            logger.info(f"从 {json_path} 加载了 {len(self._name_cache)} 个卡片名称")
            return len(self._name_cache)
        except Exception as e:
            logger.error(f"加载名称映射失败: {e}")
            return 0


# 测试代码
if __name__ == "__main__":
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 测试数据读取
    reader = GameDataReader()
    
    if reader.data_path:
        # 加载ID映射
        ydk_map = reader.load_ydk_id_mapping()
        print(f"加载了 {len(ydk_map)} 个ID映射")
        
        # 加载稀有度
        rarities = reader.load_card_rarities()
        print(f"加载了 {len(rarities)} 个稀有度信息")
        
        # 导出数据库
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        output_file = project_root / "data" / "card_database.json"
        reader.export_card_database(str(output_file))
        
        # 显示一些示例
        print("\n示例卡片 (前5张):")
        for i, (md_id, rarity) in enumerate(list(rarities.items())[:5]):
            ydk_id = reader.get_ydk_id_from_md(md_id)
            print(f"  MD ID: {md_id}, YDK ID: {ydk_id}, 稀有度: {reader.get_rarity_name(rarity)}")
    else:
        print("未找到游戏数据目录")
