"""Benchmark class for Syft client."""

from syftbox.client.benchmark import Benchmark, BenchmarkReporter
from syftbox.client.benchmark.network import NetworkBenchmark
from syftbox.lib.client_config import SyftClientConfig


class SyftBenchmarkRunner:
    """Class to run the benchmark tests for the SyftBox client."""

    def __init__(
        self,
        config: SyftClientConfig,
        reporter: BenchmarkReporter,
    ):
        self.config = config
        self.reporter = reporter

    def get_collectors(self) -> dict[str, type[Benchmark]]:
        """Get the metric collectors for the benchmark tests."""
        return {
            "network": NetworkBenchmark,
            # "sync": SyncPerformanceCollector,
        }

    def run(self, num_runs: int):
        """Run the benchmark tests."""

        # Get the metric collectors
        collectors = self.get_collectors()

        # Collect all metrics
        metrics = {}
        for name, collector in collectors.items():
            collector_instance = collector(self.config)
            metrics[name] = collector_instance.collect_metrics(num_runs)

        # Generate the benchmark report
        self.reporter.generate(metrics)
