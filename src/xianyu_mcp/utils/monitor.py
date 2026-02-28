"""
性能监控模块

监控 MCP 服务器性能、API 调用次数、响应时间等
"""

import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_response_time: float = 0.0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    last_call_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": f"{self.successful_calls / max(self.total_calls, 1) * 100:.1f}%",
            "avg_response_time_ms": f"{self.avg_response_time * 1000:.1f}ms",
            "min_response_time_ms": f"{self.min_response_time * 1000:.1f}ms" if self.min_response_time != float('inf') else "N/A",
            "max_response_time_ms": f"{self.max_response_time * 1000:.1f}ms",
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.start_time = datetime.now()
        logger.info("性能监控器已初始化")
    
    def record_call(self, tool_name: str, response_time: float, success: bool, error: str = None):
        """
        记录调用
        
        Args:
            tool_name: 工具名称
            response_time: 响应时间（秒）
            success: 是否成功
            error: 错误信息
        """
        if tool_name not in self.metrics:
            self.metrics[tool_name] = PerformanceMetrics()
        
        metric = self.metrics[tool_name]
        metric.total_calls += 1
        metric.last_call_time = datetime.now()
        
        if success:
            metric.successful_calls += 1
        else:
            metric.failed_calls += 1
            if error:
                metric.errors.append(error)
                # 只保留最近 10 个错误
                if len(metric.errors) > 10:
                    metric.errors = metric.errors[-10:]
        
        # 更新响应时间统计
        metric.total_response_time += response_time
        metric.avg_response_time = metric.total_response_time / metric.total_calls
        metric.min_response_time = min(metric.min_response_time, response_time)
        metric.max_response_time = max(metric.max_response_time, response_time)
        
        # 记录日志
        status = "✅" if success else "❌"
        logger.debug(f"{status} {tool_name}: {response_time*1000:.1f}ms")
    
    def get_metrics(self, tool_name: str = None) -> dict:
        """
        获取性能指标
        
        Args:
            tool_name: 工具名称（可选，不传则返回所有）
            
        Returns:
            性能指标字典
        """
        if tool_name:
            if tool_name in self.metrics:
                return self.metrics[tool_name].to_dict()
            return {}
        
        # 返回所有工具的指标
        return {
            name: metric.to_dict()
            for name, metric in self.metrics.items()
        }
    
    def get_summary(self) -> dict:
        """
        获取汇总统计
        
        Returns:
            汇总统计
        """
        total_calls = sum(m.total_calls for m in self.metrics.values())
        total_success = sum(m.successful_calls for m in self.metrics.values())
        total_failed = sum(m.failed_calls for m in self.metrics.values())
        
        uptime = datetime.now() - self.start_time
        
        return {
            "uptime": str(uptime),
            "total_tools": len(self.metrics),
            "total_calls": total_calls,
            "successful_calls": total_success,
            "failed_calls": total_failed,
            "success_rate": f"{total_success / max(total_calls, 1) * 100:.1f}%",
            "tools": list(self.metrics.keys()),
        }
    
    def reset(self):
        """重置所有统计"""
        self.metrics.clear()
        self.start_time = datetime.now()
        logger.info("性能统计已重置")


# 全局监控实例
monitor = PerformanceMonitor()


def timed_tool(tool_func):
    """
    工具执行时间装饰器
    
    用法:
        @mcp.tool()
        @timed_tool
        async def my_tool(...):
            ...
    """
    async def wrapper(*args, **kwargs):
        tool_name = tool_func.__name__
        start_time = time.time()
        success = False
        error = None
        result = None
        
        try:
            result = await tool_func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            response_time = time.time() - start_time
            monitor.record_call(tool_name, response_time, success, error)
    
    # 保留原函数信息
    wrapper.__name__ = tool_func.__name__
    wrapper.__doc__ = tool_func.__doc__
    
    return wrapper


# ============== MCP 工具 ==============

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("xianyu-monitor")


@mcp.tool()
async def get_performance_metrics(tool_name: str = None) -> dict:
    """
    获取性能指标
    
    Args:
        tool_name: 工具名称（可选）
        
    Returns:
        性能指标
    """
    return monitor.get_metrics(tool_name)


@mcp.tool()
async def get_server_summary() -> dict:
    """
    获取服务器汇总统计
    
    Returns:
        汇总统计
    """
    return monitor.get_summary()


@mcp.tool()
async def reset_performance_stats() -> dict:
    """
    重置性能统计
    
    Returns:
        结果
    """
    monitor.reset()
    return {"success": True, "message": "性能统计已重置"}
