"""
手动模板提取工具
用鼠标在截图上框选区域来提取模板
"""
import cv2
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


class TemplateExtractor:
    """交互式模板提取器"""
    
    def __init__(self):
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.current_image = None
        self.display_image = None
        
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
            self.end_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.end_point = (x, y)
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.end_point = (x, y)
    
    def extract_from_image(self, image_path: str, template_name: str, output_dir: str):
        """
        从图片中交互式提取模板
        
        使用方法:
        1. 鼠标拖动框选区域
        2. 按 's' 保存当前选区
        3. 按 'r' 重置选区
        4. 按 'q' 退出
        """
        # 读取图片
        self.current_image = cv2.imread(image_path)
        if self.current_image is None:
            logger.error(f"无法读取图片: {image_path}")
            return False
        
        logger.info(f"图片尺寸: {self.current_image.shape}")
        logger.info("操作说明:")
        logger.info("  - 鼠标拖动框选区域")
        logger.info("  - 按 's' 保存")
        logger.info("  - 按 'r' 重置")
        logger.info("  - 按 'q' 退出")
        
        # 创建窗口
        window_name = f"提取模板: {template_name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        while True:
            # 复制图片用于显示
            self.display_image = self.current_image.copy()
            
            # 绘制选区
            if self.start_point and self.end_point:
                cv2.rectangle(
                    self.display_image,
                    self.start_point,
                    self.end_point,
                    (0, 255, 0),
                    2
                )
                
                # 显示坐标信息
                x1, y1 = self.start_point
                x2, y2 = self.end_point
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                
                info_text = f"Region: [{min(x1,x2)}, {min(y1,y2)}, {w}, {h}]"
                cv2.putText(
                    self.display_image,
                    info_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
            
            cv2.imshow(window_name, self.display_image)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                # 退出
                break
                
            elif key == ord('r'):
                # 重置
                self.start_point = None
                self.end_point = None
                logger.info("已重置选区")
                
            elif key == ord('s'):
                # 保存
                if self.start_point and self.end_point:
                    x1, y1 = self.start_point
                    x2, y2 = self.end_point
                    
                    # 确保坐标正确
                    x = min(x1, x2)
                    y = min(y1, y2)
                    w = abs(x2 - x1)
                    h = abs(y2 - y1)
                    
                    if w > 10 and h > 10:
                        # 提取区域
                        region = self.current_image[y:y+h, x:x+w]
                        
                        # 保存
                        output_path = Path(output_dir)
                        output_path.mkdir(parents=True, exist_ok=True)
                        
                        filename = output_path / f"{template_name}.png"
                        cv2.imwrite(str(filename), region)
                        
                        logger.success(f"✅ 保存模板: {filename}")
                        logger.info(f"   坐标: [{x}, {y}, {w}, {h}]")
                        logger.info(f"   尺寸: {w}x{h}")
                        
                        # 重置选区
                        self.start_point = None
                        self.end_point = None
                    else:
                        logger.warning("选区太小，请重新选择")
                else:
                    logger.warning("请先框选区域")
        
        cv2.destroyAllWindows()
        return True


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("手动模板提取工具 - 实时截图版")
    logger.info("=" * 60)
    
    # 连接 ADB
    logger.info("\n连接设备...")
    from src.control.adb_controller import ADBController
    adb = ADBController(emulator_type="LDPlayer")
    
    if not adb.connected:
        logger.error("❌ 设备连接失败")
        logger.info("将使用本地截图...")
        adb = None
    else:
        logger.success("✅ 设备已连接")
    
    extractor = TemplateExtractor()
    
    # 定义要提取的模板
    templates = [
        {
            "name": "main_right_arrow",
            "description": "主界面右箭头",
            "instruction": "请切换到【主界面】，确保右箭头可见"
        },
        {
            "name": "duel_live_button",
            "description": "DUEL LIVE 按钮",
            "instruction": "请点击右箭头，切换到【DUEL LIVE 界面】"
        },
        {
            "name": "replay_settings_gear",
            "description": "录像界面设置齿轮",
            "instruction": "请进入【录像播放界面】，确保左上角齿轮可见"
        },
        {
            "name": "end_replay_button",
            "description": "重放再生结束按钮",
            "instruction": "请点击齿轮，打开【设置菜单】"
        },
        {
            "name": "confirm_yes_button",
            "description": "确认是按钮",
            "instruction": "请点击结束重放，打开【确认对话框】"
        }
    ]
    
    output_dir = "data/templates/daily"
    
    logger.info("\n" + "=" * 60)
    logger.info("操作说明:")
    logger.info("  1. 根据提示切换到对应界面")
    logger.info("  2. 按任意键进行截图")
    logger.info("  3. 鼠标拖动框选目标区域")
    logger.info("  4. 按 's' 保存，按 'r' 重新框选")
    logger.info("  5. 按 'q' 进入下一个模板")
    logger.info("=" * 60)
    
    for i, template in enumerate(templates, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"[{i}/{len(templates)}] {template['description']}")
        logger.info(f"{'='*60}")
        logger.info(f"📋 {template['instruction']}")
        
        if adb and adb.connected:
            input("\n按 Enter 键截图...")
            
            # 实时截图
            logger.info("正在截图...")
            screenshot = adb.screenshot()
            
            if screenshot is None:
                logger.error("截图失败，跳过")
                continue
            
            # 保存临时截图
            temp_path = f"screenshots/temp_extract_{template['name']}.png"
            cv2.imwrite(temp_path, screenshot)
            logger.success(f"✅ 截图保存: {temp_path}")
            
            image_path = temp_path
        else:
            # 使用本地截图
            image_path = f"screenshots/{template['name']}.png"
            if not Path(image_path).exists():
                logger.warning(f"图片不存在，跳过: {image_path}")
                continue
        
        # 提取模板
        extractor.extract_from_image(
            image_path,
            template['name'],
            output_dir
        )
    
    logger.success("\n" + "=" * 60)
    logger.success("✅ 提取完成！")
    logger.success("=" * 60)
    logger.info(f"模板保存在: {output_dir}")
    logger.info("运行 python run_watch_replay_v2.py 测试")


if __name__ == "__main__":
    main()
