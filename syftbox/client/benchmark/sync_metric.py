import json
import secrets
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import quantiles, stdev

from curl_cffi import CurlMime, requests

from syftbox.client.base import BaseMetric, MetricCollector
from syftbox.lib.workspace import SyftWorkspace


@dataclass
class PerformanceMetrics:
    """Metrics for measuring performance of operations"""

    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    stddev_time: float
    p95: float
    p99: float
    success_rate: float


@dataclass
class SizePerformanceData:
    """Performance data for a specific file size"""

    file_size_mb: int
    upload_metrics: PerformanceMetrics
    download_metrics: PerformanceMetrics


@dataclass
class SyncPerformanceMetric(BaseMetric):
    """Complete report of sync performance metrics across different file sizes"""

    size_metrics: list[SizePerformanceData]


class BenchmarkData:
    """Helper class to create and clean up sample files"""

    def __init__(self, base_dir: Path, size_mb: int):
        self.base_dir = base_dir
        self.size_mb = size_mb
        self.filepath = self._generate_filepath()

    def _generate_filepath(self) -> Path:
        """Generate a unique filepath for the test file"""
        filename = f"{self.size_mb}mb-{secrets.randbelow(10)}.bytes"
        return self.base_dir / filename

    def create(self):
        """Create a test file of specified size"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.filepath.write_bytes(b"\0" * int(1024 * 1024 * self.size_mb))
        return self.filepath

    def cleanup(self):
        """Clean up the test directory"""
        shutil.rmtree(self.base_dir, ignore_errors=True)


class SyncPerformanceCollector(MetricCollector):
    """Tests and measures sync performance metrics"""

    DEFAULT_FILE_SIZES = [1, 5, 10]  # MB

    def __init__(self, config):
        self.config = config
        self.headers = {"Authorization": f"Bearer {config.access_token}", "email": config.email}

    @property
    def workspace(self) -> SyftWorkspace:
        return SyftWorkspace(self.config.data_dir)

    def _measure_operation_time(self, operation_func, *args) -> tuple[any, float]:
        """Measure the execution time of an operation"""
        start_time = time.time()
        result = operation_func(*args)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        return result, execution_time

    def upload_file(self, filepath: Path) -> None:
        """Upload a file to the server"""
        mime = CurlMime()
        mime.addpart(
            name="file",
            filename=filepath.name,
            data=filepath.read_bytes(),
            content_type="text/plain",
        )

        response = requests.post(
            f"{self.config.server_url}sync/create/",
            headers=self.headers,
            multipart=mime,
        )

        response.raise_for_status()

    def download_file(self, filepath: Path) -> bytes:
        """Download a file from the server"""

        response = requests.post(
            f"{self.config.server_url}sync/download/",
            headers=self.headers,
            json={"path": filepath.name},
        )
        response.raise_for_status()

        return response.content

    def delete_file(self, filepath: Path) -> None:
        """Delete a file from the server"""
        response = requests.post(
            f"{self.config.server_url}sync/delete/",
            headers=self.headers,
            json={"path": filepath.name},
        )
        response.raise_for_status()

    def run_size_performance_test(self, file_size_mb: int, num_runs: int) -> dict[str, dict]:
        """Run performance tests for a specific file size"""
        print(f"\nTesting {file_size_mb}MB file performance")
        print("=" * 40)

        metrics = {"upload": {"times": [], "successes": 0}, "download": {"times": [], "successes": 0}}

        benchmark_dir = self.workspace.datasites / self.config.email / "public" / "benchmark"

        for run in range(num_runs):
            # Create a test file
            sample_file = BenchmarkData(benchmark_dir, file_size_mb)
            filepath = sample_file.create()

            try:
                print(f"\rRun {run + 1}/{num_runs}...", end="", flush=True)

                # Measure upload
                _, upload_time = self._measure_operation_time(self.upload_file, filepath)
                metrics["upload"]["times"].append(upload_time)
                metrics["upload"]["successes"] += 1

                time.sleep(5)  # Prevent rate limiting

                # Measure download
                _, download_time = self._measure_operation_time(self.download_file, filepath)
                metrics["download"]["times"].append(download_time)
                metrics["download"]["successes"] += 1

                # Update progress with latest timings
                print(
                    f"\rRun {run + 1}/{num_runs} - Upload: {upload_time:.2f}ms, Download: {download_time:.2f}ms",
                    end="",
                    flush=True,
                )

            except Exception as e:
                print(f"\nError in run {run + 1}: {e}")
            finally:
                self.delete_file(filepath)
                sample_file.cleanup()
                time.sleep(5)

        # Final newline after all runs
        print("\n")
        return metrics

    def calculate_metrics(self, operation_data: dict, total_runs: int) -> PerformanceMetrics:
        """Calculate performance metrics from operation measurements"""
        times = operation_data["times"]
        if not times:
            return PerformanceMetrics(
                min_time=0.0,
                max_time=0.0,
                avg_time=0.0,
                success_rate=0.0,
                p95=0.0,
                p99=0.0,
                median_time=0.0,
                stddev_time=0.0,
            )

        # Calculate percentiles
        if len(times) == 1:
            p95, p99, median = times[0], times[0], times[0]
        else:
            quants = quantiles(times, n=100)
            p95, p99, median = quants[94], quants[98], quants[49]

        return PerformanceMetrics(
            min_time=round(min(times), 2),
            max_time=round(max(times), 2),
            avg_time=round(sum(times) / len(times), 2),
            success_rate=round((operation_data["successes"] / total_runs) * 100, 2),
            p95=round(p95, 2),
            p99=round(p99, 2),
            median_time=round(median, 2),
            stddev_time=round(stdev(times), 2),
        )

    def collect_metrics(self, num_runs: int, file_sizes_mb: list[int] = None) -> SyncPerformanceMetric:
        """Collect and compile performance metrics for different file sizes"""
        if file_sizes_mb is None:
            file_sizes_mb = self.DEFAULT_FILE_SIZES

        size_metrics = []

        print("\nPerformance Test Configuration")
        print("=" * 40)
        print(f"File Sizes: {file_sizes_mb} MB")
        print(f"Runs per size: {num_runs}")
        print("-" * 40)

        for size_mb in file_sizes_mb:
            print(f"\nTesting size: {size_mb}MB")
            metrics = self.run_size_performance_test(size_mb, num_runs)

            size_metrics.append(
                SizePerformanceData(
                    file_size_mb=size_mb,
                    upload_metrics=self.calculate_metrics(metrics["upload"], num_runs),
                    download_metrics=self.calculate_metrics(metrics["download"], num_runs),
                )
            )

        return SyncPerformanceMetric(size_metrics=size_metrics, num_runs=num_runs)


if __name__ == "__main__":
    from syftbox.lib.client_config import SyftClientConfig

    config = SyftClientConfig.load(conf_path=".clients/a@openmined.org/config.json")
    # config = SyftClientConfig.load(conf_path="/home/shubham/.syftbox/config.json")
    tester = SyncPerformanceCollector(config)

    # Test with custom file sizes (in MB)
    custom_sizes = [1, 5, 9]  # Adjust as needed
    performance_report = tester.collect_metrics(num_runs=3, file_sizes_mb=custom_sizes)

    print("\nPerformance Report:")
    print(json.dumps(asdict(performance_report), indent=2))
