"""
卡组转换器 - Deck Converter
将Deck.json文本格式转换为标准化的JSON格式
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from loguru import logger


class DeckConverter:
    """卡组格式转换器"""
    
    # 已知的额外卡组关键词
    EXTRA_DECK_KEYWORDS = [
        "额外卡组", "extra deck", "extra", "额外",
        "⸻", "---", "====", "----"
    ]
    
    # 已知的怪兽卡关键词（用于分类）
    MONSTER_KEYWORDS = [
        "龙", "魔", "恶魔", "骑士", "战士", "岩石", "天使", "兽",
        "鸟", "鱼", "昆虫", "植物", "机械", "雷", "水", "炎",
        "女", "男", "王", "使", "者", "师", "士"
    ]
    
    # 已知的魔法卡关键词
    SPELL_KEYWORDS = [
        "融合", "仪式", "装备", "场地", "速攻", "永续魔法",
        "之力", "之书", "召唤", "复活", "觉醒", "起誓"
    ]
    
    # 已知的陷阱卡关键词
    TRAP_KEYWORDS = [
        "陷阱", "反击", "警告", "宣告", "通告", "魔防阵",
        "泡影", "锁链", "区域", "壁垒"
    ]
    
    # 同步怪兽关键词
    SYNCHRO_KEYWORDS = ["升龙", "暗红", "赤龙", "耀变龙"]
    
    # XYZ怪兽关键词
    XYZ_KEYWORDS = ["超量", "No.", "混沌", "神渊兽"]
    
    # 连接怪兽关键词
    LINK_KEYWORDS = ["链接", "码语", "女男爵"]
    
    def __init__(self, deck_file: str = None):
        """
        初始化转换器
        
        Args:
            deck_file: Deck.json文件路径
        """
        self.deck_file = deck_file
        
    def parse_deck_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析Deck.json文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            标准化的卡组字典
        """
        logger.info(f"开始解析卡组文件: {file_path}")
        
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割主卡组和额外卡组
        main_deck_text, extra_deck_text = self._split_main_extra(content)
        
        # 解析主卡组
        main_deck = self._parse_card_list(main_deck_text, is_extra=False)
        
        # 解析额外卡组
        extra_deck = self._parse_card_list(extra_deck_text, is_extra=True)
        
        # 计算总数
        total_main = sum(card['quantity'] for card in main_deck)
        total_extra = sum(card['quantity'] for card in extra_deck)
        
        # 推测卡组类型
        deck_type = self._infer_deck_type(main_deck, extra_deck)
        
        # 构建标准格式
        deck_data = {
            "deck_name": deck_type,
            "deck_type": deck_type,
            "main_deck": main_deck,
            "extra_deck": extra_deck,
            "total_main": total_main,
            "total_extra": total_extra,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"解析完成: {total_main}张主卡组, {total_extra}张额外卡组")
        logger.info(f"推测卡组类型: {deck_type}")
        
        return deck_data
    
    def _split_main_extra(self, content: str) -> Tuple[str, str]:
        """
        分割主卡组和额外卡组
        
        Args:
            content: 文件内容
            
        Returns:
            (主卡组文本, 额外卡组文本)
        """
        lines = content.strip().split('\n')
        
        # 查找额外卡组分隔符
        extra_start_idx = -1
        for i, line in enumerate(lines):
            line_clean = line.strip()
            for keyword in self.EXTRA_DECK_KEYWORDS:
                if keyword in line_clean:
                    extra_start_idx = i
                    break
            if extra_start_idx != -1:
                break
        
        if extra_start_idx == -1:
            # 没找到分隔符，全部当作主卡组
            logger.warning("未找到额外卡组分隔符")
            return content, ""
        
        # 分割
        main_text = '\n'.join(lines[:extra_start_idx])
        extra_text = '\n'.join(lines[extra_start_idx+1:])
        
        return main_text, extra_text
    
    def _parse_card_list(self, text: str, is_extra: bool = False) -> List[Dict[str, Any]]:
        """
        解析卡片列表
        
        Args:
            text: 卡片列表文本
            is_extra: 是否是额外卡组
            
        Returns:
            卡片列表
        """
        cards = []
        
        # 正则：匹配 "卡名 ×数量" 或 "卡名 x数量"
        pattern = r'(.+?)\s*[×x]\s*(\d+)'
        
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 跳过分隔符
            if any(kw in line for kw in self.EXTRA_DECK_KEYWORDS):
                continue
            
            # 尝试匹配
            match = re.match(pattern, line)
            if match:
                card_name = match.group(1).strip()
                quantity = int(match.group(2))
                
                # 分类
                if is_extra:
                    category = "extra"
                    summon_type = self._classify_extra_card(card_name)
                    card = {
                        "name": card_name,
                        "quantity": quantity,
                        "summon_type": summon_type
                    }
                else:
                    category = self._classify_card(card_name)
                    card = {
                        "name": card_name,
                        "quantity": quantity,
                        "category": category
                    }
                
                cards.append(card)
                logger.debug(f"解析卡片: {card_name} x{quantity} ({category if not is_extra else summon_type})")
        
        return cards
    
    def _classify_card(self, card_name: str) -> str:
        """
        分类卡片（怪兽/魔法/陷阱）
        
        Args:
            card_name: 卡片名称
            
        Returns:
            类别字符串
        """
        # 陷阱判断（优先级高）
        for keyword in self.TRAP_KEYWORDS:
            if keyword in card_name:
                return "trap"
        
        # 魔法判断
        for keyword in self.SPELL_KEYWORDS:
            if keyword in card_name:
                return "spell"
        
        # 怪兽判断（默认）
        for keyword in self.MONSTER_KEYWORDS:
            if keyword in card_name:
                return "monster"
        
        # 默认为怪兽（游戏王主卡组大多数是怪兽）
        return "monster"
    
    def _classify_extra_card(self, card_name: str) -> str:
        """
        分类额外卡组怪兽类型
        
        Args:
            card_name: 卡片名称
            
        Returns:
            召唤类型
        """
        # 同步
        for keyword in self.SYNCHRO_KEYWORDS:
            if keyword in card_name:
                return "synchro"
        
        # XYZ
        for keyword in self.XYZ_KEYWORDS:
            if keyword in card_name:
                return "xyz"
        
        # 连接
        for keyword in self.LINK_KEYWORDS:
            if keyword in card_name:
                return "link"
        
        # 默认同步（暗红恶魔卡组主要是同步）
        return "synchro"
    
    def _infer_deck_type(self, main_deck: List[Dict], extra_deck: List[Dict]) -> str:
        """
        推测卡组类型
        
        Args:
            main_deck: 主卡组
            extra_deck: 额外卡组
            
        Returns:
            卡组类型名称
        """
        # 统计关键词出现次数
        keyword_count = {}
        
        # 检查所有卡片名称
        all_cards = main_deck + extra_deck
        for card in all_cards:
            name = card['name']
            
            # 暗红恶魔
            if "暗红" in name or "绯暗红" in name or "赤龙" in name:
                keyword_count["暗红恶魔"] = keyword_count.get("暗红恶魔", 0) + card['quantity']
            
            # 百夫骑士
            if "百夫骑" in name:
                keyword_count["百夫骑士"] = keyword_count.get("百夫骑士", 0) + card['quantity']
            
            # 共鸣者
            if "共鸣者" in name:
                keyword_count["共鸣者"] = keyword_count.get("共鸣者", 0) + card['quantity']
            
            # 渊兽
            if "渊兽" in name:
                keyword_count["渊兽"] = keyword_count.get("渊兽", 0) + card['quantity']
        
        # 返回出现最多的
        if keyword_count:
            deck_type = max(keyword_count, key=keyword_count.get)
            return deck_type
        
        return "混合卡组"
    
    def save_standard_deck(self, deck_data: Dict[str, Any], output_path: str):
        """
        保存标准化卡组
        
        Args:
            deck_data: 卡组数据
            output_path: 输出路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(deck_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"标准卡组已保存: {output_path}")
    
    def convert(self, input_file: str, output_file: str = None) -> Dict[str, Any]:
        """
        转换卡组文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径（可选）
            
        Returns:
            标准化的卡组数据
        """
        # 解析
        deck_data = self.parse_deck_file(input_file)
        
        # 保存
        if output_file:
            self.save_standard_deck(deck_data, output_file)
        
        return deck_data


# 测试代码
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 转换当前的Deck.json
    converter = DeckConverter()
    
    # 使用绝对路径
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / "Deck.json"
    output_path = project_root / "data" / "standard_deck.json"
    
    try:
        deck = converter.convert(str(input_path), str(output_path))
        
        print("\n=== 卡组转换结果 ===")
        print(f"卡组类型: {deck['deck_type']}")
        print(f"主卡组: {deck['total_main']}张")
        print(f"额外卡组: {deck['total_extra']}张")
        print(f"\n主卡组卡片:")
        for card in deck['main_deck'][:5]:
            print(f"  - {card['name']} x{card['quantity']} ({card['category']})")
        print(f"\n额外卡组卡片:")
        for card in deck['extra_deck'][:5]:
            print(f"  - {card['name']} x{card['quantity']} ({card['summon_type']})")
        
    except Exception as e:
        logger.error(f"转换失败: {e}")
        import traceback
        traceback.print_exc()
