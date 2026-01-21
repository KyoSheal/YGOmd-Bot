"""
查找游戏窗口工具
列出所有窗口，帮助找到正确的游戏窗口标题
"""
import win32gui
import win32process
import psutil


def list_all_windows():
    """列出所有可见窗口"""
    windows = []
    
    def enum_handler(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:  # 只显示有标题的窗口
                # 获取进程信息
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    process_name = process.name()
                except:
                    process_name = "Unknown"
                
                rect = win32gui.GetWindowRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                
                results.append({
                    'hwnd': hwnd,
                    'title': title,
                    'process': process_name,
                    'size': f"{width}x{height}",
                    'position': f"({rect[0]}, {rect[1]})"
                })
    
    win32gui.EnumWindows(enum_handler, windows)
    return windows


def find_game_window():
    """查找游戏窗口"""
    print("=" * 80)
    print("查找游戏窗口")
    print("=" * 80)
    print()
    
    windows = list_all_windows()
    
    # 过滤可能的游戏窗口
    game_candidates = []
    for window in windows:
        title_lower = window['title'].lower()
        process_lower = window['process'].lower()
        
        # 查找可能是游戏王的窗口
        if any(keyword in title_lower for keyword in ['yu-gi-oh', 'master duel', 'yugioh']) or \
           any(keyword in process_lower for keyword in ['masterduel', 'yugioh']):
            game_candidates.append(window)
    
    if game_candidates:
        print(f"找到 {len(game_candidates)} 个可能的游戏窗口:\n")
        for i, window in enumerate(game_candidates, 1):
            print(f"{i}. 窗口标题: {window['title']}")
            print(f"   进程名称: {window['process']}")
            print(f"   窗口大小: {window['size']}")
            print(f"   窗口位置: {window['position']}")
            print()
        
        return game_candidates
    else:
        print("未找到游戏窗口，显示所有窗口（可能的游戏进程）:\n")
        
        # 显示所有看起来像游戏的窗口
        for i, window in enumerate(windows[:20], 1):  # 只显示前20个
            if window['size'] not in ["0x0", "1x1"]:  # 过滤太小的窗口
                print(f"{i}. 窗口标题: {window['title']}")
                print(f"   进程名称: {window['process']}")
                print(f"   窗口大小: {window['size']}")
                print()
        
        return []


if __name__ == "__main__":
    import sys
    
    print("游戏窗口查找工具")
    print("此工具帮助你找到正确的游戏窗口标题")
    print()
    
    candidates = find_game_window()
    
    if candidates:
        print("=" * 80)
        print("建议操作:")
        print("=" * 80)
        print()
        print("请将以下内容复制到 config/settings.yaml 的 game.window_title:")
        print()
        print(f'window_title: "{candidates[0]["title"]}"')
        print()
        print("或者在代码中使用完整的窗口标题。")
    else:
        print("=" * 80)
        print("未找到游戏窗口！")
        print("=" * 80)
        print()
        print("请确保:")
        print("1. 游戏已经运行")
        print("2. 游戏窗口不是最小化状态")
        print("3. 如果游戏在另一个显示器上，这是正常的，Win32 API能找到它")
        print()
        print("如果游戏正在运行但未列出，请手动输入窗口标题。")
