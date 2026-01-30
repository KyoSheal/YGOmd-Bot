"""
观看对战录像 V2 - 使用 Pipeline 系统
参考 MAA 的任务流程设计
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from src.control.adb_controller import ADBController
from src.core.pipeline import Pipeline


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("观看对战录像 V2 - Pipeline 系统")
    logger.info("=" * 60)
    
    # 1. 连接设备
    logger.info("\n[1/3] 连接设备...")
    adb = ADBController(emulator_type="LDPlayer")
    
    if not adb.connected:
        logger.error("❌ 设备连接失败")
        return False
    
    logger.success("✅ 设备连接成功")
    
    # 2. 初始化 Pipeline
    logger.info("\n[2/3] 初始化 Pipeline...")
    pipeline = Pipeline(adb)
    
    # 加载任务配置
    if not pipeline.load_task_config("data/tasks/watch_replay.json"):
        logger.error("❌ 加载任务配置失败")
        return False
    
    logger.success("✅ Pipeline 就绪")
    
    # 3. 执行任务
    logger.info("\n[3/3] 执行任务...")
    
    try:
        success = pipeline.run("WatchReplay_FindDuelLive")
        
        if success:
            logger.success("\n" + "=" * 60)
            logger.success("✅ 任务完成！")
            logger.success("=" * 60)
            return True
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ 任务失败")
            logger.error("=" * 60)
            return False
            
    except KeyboardInterrupt:
        logger.warning("\n用户中断")
        return False
    except Exception as e:
        logger.error(f"\n任务异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
