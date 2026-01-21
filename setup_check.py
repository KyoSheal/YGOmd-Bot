"""
快速开始指南脚本
帮助用户快速上手YGO Bot
"""
import os
import sys
from pathlib import Path


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def check_python_version():
    """检查Python版本"""
    print_header("检查Python版本")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低！需要Python 3.8或更高版本")
        return False
    else:
        print("✅ Python版本符合要求")
        return True


def check_dependencies():
    """检查依赖"""
    print_header("检查依赖包")
    
    required_packages = [
        "cv2",
        "numpy",
        "PIL",
        "win32gui",
        "pyautogui",
        "pynput",
        "yaml",
        "loguru"
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == "cv2":
                import cv2
            elif package == "PIL":
                from PIL import Image
            elif package == "win32gui":
                import win32gui
            elif package == "yaml":
                import yaml
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing.append(package)
    
    if missing:
        print("\n缺少以下依赖包，请运行:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("\n✅ 所有依赖包已安装")
        return True


def check_tesseract():
    """检查Tesseract OCR"""
    print_header("检查Tesseract OCR")
    
    try:
        import pytesseract
        # 尝试获取版本
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract已安装，版本: {version}")
        return True
    except Exception as e:
        print("❌ Tesseract未正确安装或配置")
        print("\n请从以下地址下载安装Tesseract:")
        print("https://github.com/tesseract-ocr/tesseract")
        print("\n安装后，可能需要设置环境变量或在代码中指定路径")
        return False


def create_directories():
    """创建必要的目录"""
    print_header("创建必要目录")
    
    dirs = [
        "data/cards",
        "data/templates",
        "data/models",
        "data/recordings",
        "logs"
    ]
    
    for dir_path in dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {dir_path}")
        else:
            print(f"✓ 目录已存在: {dir_path}")


def show_next_steps():
    """显示下一步操作"""
    print_header("下一步操作")
    
    print("恭喜！环境配置完成。现在你可以：\n")
    print("1. 启动游戏王Master Duel")
    print("2. 运行主程序:")
    print("   python main.py")
    print("\n3. 选择'录制模式'开始录制你的操作")
    print("4. Bot会学习你的展开和操作策略")
    print("\n提示：")
    print("- 录制时尽量操作清晰")
    print("- 可以多次录制不同的场景")
    print("- 查看README.md了解更多信息")
    print()


def main():
    """主函数"""
    print_header("YGO Master Duel Bot - 环境检查")
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查依赖
    deps_ok = check_dependencies()
    
    # 检查Tesseract
    tesseract_ok = check_tesseract()
    
    # 创建目录
    create_directories()
    
    # 显示结果
    print_header("检查完成")
    
    if deps_ok and tesseract_ok:
        print("✅ 所有检查通过！")
        show_next_steps()
    else:
        print("⚠️ 部分检查未通过，请按照提示修复问题")
        if not deps_ok:
            print("\n安装依赖: pip install -r requirements.txt")
        if not tesseract_ok:
            print("\n安装Tesseract OCR")


if __name__ == "__main__":
    main()
