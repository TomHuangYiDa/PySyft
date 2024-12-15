from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from typing_extensions import Protocol

from syftbox.lib.client_config import SyftClientConfig


@dataclass
class BaseMetric:
    """Base class for all metrics with common fields."""

    num_runs: int


class MetricCollector(Protocol):
    """
    Protocol for classes that collect performance metrics.
    """

    client_config: SyftClientConfig

    def collect_metrics(self, num_runs: int) -> BaseMetric:
        """Calculate performance metrics."""
        ...


class BenchmarkReporter(Protocol):
    """Protocol defining the interface for benchmark result reporters."""

    def generate(self, metrics: dict[str, BaseMetric], report_path: Optional[Path] = None) -> Any:
        """Generate the benchmark report."""
        ...
