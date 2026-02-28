"""
工具函数模块
"""

from .logger import setup_logger

__all__ = [
    "setup_logger",
    "PerformanceMonitor",
    "timed_tool",
    "monitor",
]


def __getattr__(name: str):
    """延迟加载高开销模块，避免导入 logger 时触发 monitor 副作用。"""
    if name in {"PerformanceMonitor", "timed_tool", "monitor"}:
        from .monitor import PerformanceMonitor, timed_tool, monitor

        exports = {
            "PerformanceMonitor": PerformanceMonitor,
            "timed_tool": timed_tool,
            "monitor": monitor,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
