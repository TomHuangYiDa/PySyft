import json
from dataclasses import asdict
from pathlib import Path

from typing_extensions import Optional

from syftbox.client.benchmark import BenchmarkReporter, BenchmarkResult
from syftbox.client.benchmark.network_metric import NetworkMetric
from syftbox.client.benchmark.sync_metric import SyncPerformanceMetric


class JsonBenchmarkReport(BenchmarkReporter):
    """JSON format benchmark report."""

    def generate(self, metrics: dict[str, BenchmarkResult], report_path: Optional[Path] = None) -> dict:
        """Generate the benchmark report in JSON format."""
        report = {
            "metrics": {name: asdict(metric) for name, metric in metrics.items()},
        }

        print("Benchmark report:", json.dumps(report, indent=2))
        if report_path:
            self.save(report, report_path)

        return report

    def save(self, report: dict, output_path: Path):
        """Save the benchmark report in JSON format."""
        with open(output_path / "benchmark.json", "w") as f:
            json.dump(report, f, indent=4)

        print("Benchmark report saved to:", output_path / "benchmark.json")


class HumanReadableBenchmarkReport(BenchmarkReporter):
    """Human readable format benchmark report."""

    def generate(self, metrics: dict[str, BenchmarkResult], report_path: Optional[Path] = None) -> str:
        """Generate the benchmark report in human readable format."""

        sections = ["\nBenchmark Report", "=" * 16, ""]

        for name, metric in metrics.items():
            if isinstance(metric, NetworkMetric):
                sections.extend(
                    [
                        f"Network Metrics for : {metric.url}",
                        f"Timestamp: {metric.timestamp} UTC",
                        f"Number of runs: {metric.num_runs}",
                        "\nHTTP Statistics: ",
                        "--------------------",
                        f"DNS lookup time (ms): {self.dict_to_str(asdict(metric.http_stats.dns_time))}",
                        f"Connection Time (ms): {self.dict_to_str(asdict(metric.http_stats.connect_time))}",
                        f"SSL Handshake (ms): {self.dict_to_str(asdict(metric.http_stats.ssl_time))}",
                        f"TCP Time (ms): {self.dict_to_str(asdict(metric.http_stats.tcp_time))}",
                        f"Time to First Byte (ms): {self.dict_to_str(asdict(metric.http_stats.starttransfer_time))}",
                        f"Total Time (ms): {self.dict_to_str(asdict(metric.http_stats.total_time))}",
                        f"Server Processing Time (ms): {self.dict_to_str(asdict(metric.http_stats.server_processing_time))}",
                        f"Succeeded Requests: {metric.http_stats.success_rate} %",
                        "\nTCP Statistics: ",
                        "-------------------",
                        f"TCP Latency (ms): {self.dict_to_str(asdict(metric.tcp_stats.latency_stats))}",
                        f"TCP Jitter (ms): {self.dict_to_str(asdict(metric.tcp_stats.jitter_stats))}",
                        f"Connection Success Rate: {metric.tcp_stats.connection_success_rate} %",
                        "=" * 16,
                    ]
                )
            if isinstance(metric, SyncPerformanceMetric):
                sync_comb_report = [
                    "\nSync Performance Metrics: ",
                    "------------------------------",
                    f"{'Size(MB)':>8} {'Operation':>10} {'Min(ms)':>10} {'Max(ms)':>10} {'Avg(ms)':>10} {'P95(ms)':>10} {'Success%':>10}",
                ]
                for metric in metric.size_metrics:
                    sync_report = [
                        f"{metric.file_size_mb:>8} {'Upload':>10} ",
                        f"{metric.upload_metrics.min_time:>10.1f} ",
                        f"{metric.upload_metrics.max_time:>10.1f} ",
                        f"{metric.upload_metrics.avg_time:>10.1f} ",
                        f"{metric.upload_metrics.p95:>10.1f} ",
                        f"{metric.upload_metrics.success_rate:>9.0f}%",
                        f"\n{'':>8} {'Download':>10} "
                        f"{metric.download_metrics.min_time:>10.1f} "
                        f"{metric.download_metrics.max_time:>10.1f} "
                        f"{metric.download_metrics.avg_time:>10.1f} "
                        f"{metric.download_metrics.p95:>10.1f} "
                        f"{metric.download_metrics.success_rate:>9.0f}%",
                    ]
                    sync_comb_report.append("".join(sync_report))

                sync_comb_report.append("=" * 16)

                sections.extend(sync_comb_report)

        report = "\n".join(sections)
        print(report)

        if report_path:
            self.save(report, report_path)

        return report

    def dict_to_str(self, data: dict) -> str:
        """Convert dataclass to string representation."""
        return ", ".join([f"{name}: {value}" for name, value in data.items()])

    def save(self, report: str, output_path: Path):
        """Save the benchmark report in human readable format."""
        with open(output_path / "benchmark.txt", "w") as f:
            f.write(report)

        print("Benchmark report saved to:", output_path / "benchmark.txt")
