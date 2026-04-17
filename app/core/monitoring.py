"""
RAG 知识库 - 监控/可观测性模块

提供：结构化日志、指标采集、请求追踪、健康检查
"""

import logging
import os
import sys
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import threading

# ============================================================
# 1. 配置
# ============================================================

MONITORING_DIR = Path("logs")
MONITORING_DIR.mkdir(exist_ok=True)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


# ============================================================
# 2. 结构化日志系统
# ============================================================

class StructuredLogger:
    """
    结构化日志器，输出 JSON 格式日志（便于日志收集系统解析）
    同时保留人类可读的普通格式输出
    """

    _instances: Dict[str, "StructuredLogger"] = {}
    _lock = threading.Lock()

    def __new__(cls, name: str):
        with cls._lock:
            if name not in cls._instances:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[name] = instance
            return cls._instances[name]

    def __init__(self, name: str):
        if self._initialized:
            return
        self._initialized = True
        self.name = name

        # 普通 handler（控制台）
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(getattr(logging, LOG_LEVEL))

        # JSON 文件 handler（结构化日志）
        json_log_file = MONITORING_DIR / f"{name}.log"
        self.file_handler = logging.FileHandler(
            json_log_file, encoding="utf-8"
        )
        self.file_handler.setLevel(logging.DEBUG)

        # Logger 本身
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        self.logger.handlers.clear()
        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.file_handler)
        self.logger.propagate = False

    def _format_json(self, level: str, message: str, **kwargs) -> str:
        """生成 JSON 格式日志行"""
        import json
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            "module": self.name,
        }
        record.update(kwargs)
        return json.dumps(record, ensure_ascii=False, default=str)

    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format_json("DEBUG", message, **kwargs))

    def info(self, message: str, **kwargs):
        self.logger.info(self._format_json("INFO", message, **kwargs))

    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_json("WARNING", message, **kwargs))

    def error(self, message: str, **kwargs):
        self.logger.error(self._format_json("ERROR", message, **kwargs))

    def critical(self, message: str, **kwargs):
        self.logger.critical(self._format_json("CRITICAL", message, **kwargs))

    def exception(self, message: str, **kwargs):
        kwargs["exc_info"] = traceback.format_exc()
        self.logger.error(self._format_json("ERROR", message, **kwargs))


# 全局日志器工厂
def get_logger(name: str = "rag-kb") -> StructuredLogger:
    return StructuredLogger(name)


# ============================================================
# 3. 指标采集系统
# ============================================================

class MetricType(Enum):
    COUNTER = "counter"      # 只增不减计数器
    GAUGE = "gauge"          # 上报时当前值
    HISTOGRAM = "histogram"  # 统计分布


@dataclass
class Metric:
    name: str
    description: str = ""
    metric_type: MetricType = MetricType.COUNTER
    labels: Dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, value: float = 1, labels: Optional[Dict[str, str]] = None):
        with self._lock:
            self._value += value

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        with self._lock:
            self._value = value

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        with self._lock:
            self._value = value

    def get(self) -> float:
        return self._value


class MetricsCollector:
    """
    应用指标采集器，支持 Counter/Gauge/Histogram
    输出 Prometheus 兼容格式
    """

    def __init__(self, namespace: str = "rag_kb"):
        self.namespace = namespace
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self._histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._histogram_data: Dict[str, List[float]] = defaultdict(list)

    def _full_name(self, name: str) -> str:
        return f"{self.namespace}_{name}"

    def counter(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
        with self._lock:
            key = self._full_name(name)
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    name=key,
                    description=description,
                    metric_type=MetricType.COUNTER,
                    labels=labels or {}
                )
            return self._metrics[key]

    def gauge(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
        with self._lock:
            key = self._full_name(name)
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    name=key,
                    description=description,
                    metric_type=MetricType.GAUGE,
                    labels=labels or {}
                )
            return self._metrics[key]

    def histogram(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
        with self._lock:
            key = self._full_name(name)
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    name=key,
                    description=description,
                    metric_type=MetricType.HISTOGRAM,
                    labels=labels or {}
                )
            return self._metrics[key]

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """记录 HTTP 请求指标"""
        labels = {"method": method, "path": path, "status": str(status_code)}

        # 请求计数
        self.counter(
            "http_requests_total",
            "Total HTTP requests",
            labels=labels
        ).inc(1)

        # 请求延迟直方图
        hist_key = self._full_name("http_request_duration_ms")
        if hist_key not in self._histogram_data:
            self._histogram_data[hist_key] = []
        self._histogram_data[hist_key].append(duration_ms)

        # 活跃请求
        self.gauge(
            "http_requests_active",
            "Active HTTP requests"
        ).inc(1)
        self.gauge(
            "http_requests_active",
            "Active HTTP requests"
        ).inc(-1)

    def record_retrieval(self, query: str, doc_count: int, duration_ms: float, search_type: str):
        """记录检索操作指标"""
        labels = {"search_type": search_type}
        self.counter(
            "retrieval_requests_total",
            "Total retrieval requests",
            labels=labels
        ).inc(1)
        self.histogram(
            "retrieval_duration_ms",
            "Retrieval duration in ms",
            labels=labels
        ).observe(duration_ms)

    def record_llm_call(self, model: str, duration_ms: float, success: bool):
        """记录 LLM 调用指标"""
        labels = {"model": model, "success": str(success)}
        self.counter(
            "llm_calls_total",
            "Total LLM calls",
            labels=labels
        ).inc(1)
        self.histogram(
            "llm_duration_ms",
            "LLM call duration in ms",
            labels=labels
        ).observe(duration_ms)

    def record_cache_hit(self, hit: bool):
        """记录缓存命中率"""
        self.counter(
            "cache_operations_total",
            "Cache operations",
            labels={"result": "hit" if hit else "miss"}
        ).inc(1)

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式指标"""
        lines = ["# HELP rag_kb_info Application info", "# TYPE rag_kb_info gauge",
                 'rag_kb_info{version="2.0"} 1.0', ""]

        for key, metric in self._metrics.items():
            if metric.description:
                lines.append(f"# HELP {key} {metric.description}")
                lines.append(f"# TYPE {key} {metric.metric_type.value}")
            value = metric.get()
            if metric.labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                lines.append(f"{key}{{{label_str}}} {value}")
            else:
                lines.append(f"{key} {value}")

        # 直方图
        for hist_key, values in self._histogram_data.items():
            if values:
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                lines.append(f"# HELP {hist_key}_histogram {hist_key} distribution")
                lines.append(f"# TYPE {hist_key}_histogram summary")
                for percentile in [0.5, 0.9, 0.95, 0.99]:
                    idx = min(int(n * percentile), n - 1)
                    lines.append(f'{hist_key}{{quantile="{percentile}"}} {sorted_vals[idx]:.3f}')
                lines.append(f"{hist_key}_count {n}")
                lines.append(f"{hist_key}_sum {sum(sorted_vals):.3f}")

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {"total_metrics": len(self._metrics)}
        for key, metric in self._metrics.items():
            if metric.metric_type == MetricType.COUNTER:
                summary[key] = {"type": "counter", "value": metric.get()}
            elif metric.metric_type == MetricType.GAUGE:
                summary[key] = {"type": "gauge", "value": metric.get()}
        return summary


# 全局指标采集器
metrics = MetricsCollector()


# ============================================================
# 4. 请求追踪
# ============================================================

class RequestTracer:
    """
    请求追踪器，为每个请求生成唯一 trace_id
    支持嵌套 Span
    """

    def __init__(self):
        self._traces: Dict[str, List[Dict]] = defaultdict(list)
        self._active: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def start_trace(self, trace_id: str, operation: str, **metadata) -> Dict:
        span = {
            "trace_id": trace_id,
            "operation": operation,
            "start_time": time.perf_counter(),
            "metadata": metadata,
            "spans": [],
        }
        with self._lock:
            self._active[trace_id] = span
            self._traces[trace_id].append(span)
        return span

    def end_trace(self, trace_id: str, status: str = "ok", error: Optional[str] = None):
        with self._lock:
            if trace_id in self._active:
                span = self._active[trace_id]
                span["end_time"] = time.perf_counter()
                span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000
                span["status"] = status
                if error:
                    span["error"] = error
                del self._active[trace_id]

    def add_span(self, trace_id: str, operation: str, **metadata) -> Dict:
        span = {
            "operation": operation,
            "start_time": time.perf_counter(),
            "metadata": metadata,
        }
        with self._lock:
            if trace_id in self._active:
                self._active[trace_id]["spans"].append(span)
        return span

    def end_span(self, trace_id: str, span: Dict, status: str = "ok"):
        span["end_time"] = time.perf_counter()
        span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000
        span["status"] = status

    def get_trace(self, trace_id: str) -> Optional[List[Dict]]:
        with self._lock:
            return self._traces.get(trace_id)

    def get_recent_traces(self, limit: int = 10) -> List[Dict]:
        with self._lock:
            traces = []
            for trace_id in list(self._traces.keys())[-limit:]:
                if self._traces[trace_id]:
                    traces.append(self._traces[trace_id][0])
            return traces


# 全局追踪器
tracer = RequestTracer()


# ============================================================
# 5. 健康检查
# ============================================================

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    component: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "details": self.details,
        }


class HealthChecker:
    """
    健康检查器，支持多项检查
    """

    def __init__(self):
        self._checks: List[Callable[[], HealthCheckResult]] = []

    def register_check(self, name: str, check_fn: Callable[[], HealthCheckResult]):
        """注册健康检查项"""
        self._checks.append(lambda: check_fn())

    def check_all(self) -> Dict[str, Any]:
        """执行所有检查"""
        results = []
        overall_status = HealthStatus.HEALTHY

        for check_fn in self._checks:
            try:
                result = check_fn()
            except Exception as e:
                result = HealthCheckResult(
                    component=check_fn.__name__,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}",
                )
            results.append(result.to_dict())

            # 确定整体状态
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": results,
        }


def health_check_vectorstore() -> HealthCheckResult:
    """检查向量存储"""
    start = time.perf_counter()
    try:
        from app.core.vectorstore import VectorStore
        from langchain_core.documents import Document
        import numpy as np

        vs = VectorStore(embeddings=None, persist_directory="./chroma_db")
        count = vs.document_count()
        return HealthCheckResult(
            component="vectorstore",
            status=HealthStatus.HEALTHY,
            message=f"ChromaDB accessible, {count} docs",
            latency_ms=(time.perf_counter() - start) * 1000,
            details={"document_count": count}
        )
    except Exception as e:
        return HealthCheckResult(
            component="vectorstore",
            status=HealthStatus.UNHEALTHY,
            message=f"VectorStore error: {str(e)}",
            latency_ms=(time.perf_counter() - start) * 1000,
        )


def health_check_llm() -> HealthCheckResult:
    """检查 LLM 连接"""
    start = time.perf_counter()
    try:
        from app.core.config import config

        provider = config.llm.provider
        return HealthCheckResult(
            component="llm",
            status=HealthStatus.HEALTHY,
            message=f"LLM provider: {provider}",
            latency_ms=(time.perf_counter() - start) * 1000,
            details={"provider": provider, "model": config.llm.model}
        )
    except Exception as e:
        return HealthCheckResult(
            component="llm",
            status=HealthStatus.DEGRADED,
            message=f"LLM check warning: {str(e)}",
            latency_ms=(time.perf_counter() - start) * 1000,
        )


def health_check_disk() -> HealthCheckResult:
    """检查磁盘空间"""
    start = time.perf_counter()
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        usage_pct = (used / total) * 100
        status = HealthStatus.HEALTHY
        if usage_pct > 90:
            status = HealthStatus.UNHEALTHY
        elif usage_pct > 75:
            status = HealthStatus.DEGRADED
        return HealthCheckResult(
            component="disk",
            status=status,
            message=f"Disk usage: {usage_pct:.1f}%",
            latency_ms=(time.perf_counter() - start) * 1000,
            details={"total_gb": total // (2**30), "free_gb": free // (2**30)}
        )
    except Exception as e:
        return HealthCheckResult(
            component="disk",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            latency_ms=(time.perf_counter() - start) * 1000,
        )


# 全局健康检查器
health_checker = HealthChecker()
health_checker.register_check("vectorstore", health_check_vectorstore)
health_checker.register_check("llm", health_check_llm)
health_checker.register_check("disk", health_check_disk)


# ============================================================
# 6. 性能监控装饰器
# ============================================================

def monitor(metric_name: str, metric_type: str = "counter"):
    """监控函数执行的装饰器"""
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.histogram(
                    f"{metric_name}_duration_ms",
                    f"{func.__name__} duration"
                ).observe(duration_ms)
                metrics.counter(
                    f"{metric_name}_total",
                    f"{func.__name__} calls"
                ).inc(1)
                metrics.counter(
                    f"{metric_name}_success",
                    f"{func.__name__} successes"
                ).inc(1)
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.counter(
                    f"{metric_name}_errors",
                    f"{func.__name__} errors"
                ).inc(1)
                logger = get_logger()
                logger.error(f"{func.__name__} failed", error=str(e), duration_ms=duration_ms)
                raise
        return sync_wrapper
    return decorator


@contextmanager
def trace_operation(operation: str, trace_id: Optional[str] = None, **metadata):
    """追踪代码块的执行"""
    import uuid
    tid = trace_id or str(uuid.uuid4())[:8]
    tracer.start_trace(tid, operation, **metadata)
    start = time.perf_counter()
    try:
        yield tid
        tracer.end_trace(tid, status="ok")
    except Exception as e:
        tracer.end_trace(tid, status="error", error=str(e))
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        metadata["duration_ms"] = duration_ms
