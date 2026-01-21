"""
自动测试脚本 - 无需手动输入
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.smart_deck_scanner import SmartDeckScanner
import time

if __name__ == "__main__":
    print("=" * 60)
    print("自动测试扫描器")
    print("=" * 60)
    
    deck_name = f"test_{int(time.time())}"
    
    scanner = SmartDeckScanner()
    result = scanner.scan_deck(deck_name)
    
    if result:
        print()
        print("=" * 60)
        print("✅ 扫描完成！")
        print("=" * 60)
        print(f"📦 卡组: {result['deck_name']}")
        print(f"📊 卡片数: {len(result['cards'])}")
        print()
        
        # 显示所有卡片
        print("识别的卡片:")
        for i, card in enumerate(result['cards'], 1):
            print(f"  {i}. {card['name']}")
    else:
        print("❌ 扫描失败")
