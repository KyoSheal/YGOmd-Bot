"""
任务系统
参考 MAA 的任务流程设计
"""
from .task_base import Task, TaskChain
from .daily_tasks import WatchReplayTask

__all__ = ['Task', 'TaskChain', 'WatchReplayTask']
