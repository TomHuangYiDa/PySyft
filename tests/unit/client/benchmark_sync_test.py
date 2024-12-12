import time
from pathlib import Path

import pytest
from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
from requests import HTTPError

from syftbox.client.benchmark.sync_metric import (
    PerformanceMetrics,
    SampleBenchmarkData,
    SyncPerformanceCollector,
    SyncPerformanceMetric,
)


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file for upload testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def config():
    class MockConfig:
        server_url = "https://test.example.com/"
        access_token = "test-token"
        email = "test@example.com"
        data_dir = "/tmp/test-data"

    return MockConfig()


@pytest.fixture
def collector(config):
    return SyncPerformanceCollector(config)


@pytest.fixture
def mock_workspace(monkeypatch):
    class MockWorkspace:
        datasites = Path("/tmp/test-data/datasites")

    monkeypatch.setattr("syftbox.client.benchmark.sync_metric.SyftWorkspace", lambda x: MockWorkspace())
    return MockWorkspace()


def test_calculate_metrics_empty_data(collector):
    """Test metrics calculation with empty data."""
    metrics = collector.calculate_metrics({"times": [], "successes": 0}, total_runs=5)

    assert isinstance(metrics, PerformanceMetrics)
    assert metrics.min_time == 0.0
    assert metrics.max_time == 0.0
    assert metrics.avg_time == 0.0
    assert metrics.median_time == 0.0
    assert metrics.stddev_time == 0.0
    assert metrics.p95 == 0.0
    assert metrics.p99 == 0.0
    assert metrics.success_rate == 0.0


def test_calculate_metrics_single_datapoint(collector, monkeypatch):
    """Test metrics calculation with a single data point."""

    # Mock statistics functions to handle single data point
    def mock_stdev(data):
        if len(data) < 2:
            return 0.0
        raise RuntimeError("Should not be called")

    monkeypatch.setattr("syftbox.client.benchmark.sync_metric.stdev", mock_stdev)

    metrics = collector.calculate_metrics({"times": [100.0], "successes": 1}, total_runs=1)

    assert isinstance(metrics, PerformanceMetrics)
    assert metrics.min_time == 100.0
    assert metrics.max_time == 100.0
    assert metrics.avg_time == 100.0
    assert metrics.median_time == 100.0
    assert metrics.stddev_time == 0.0
    assert metrics.p95 == 100.0
    assert metrics.p99 == 100.0
    assert metrics.success_rate == 100.0


def test_collect_metrics_with_failures(collector, monkeypatch, mock_workspace, test_file):
    """Test metrics collection with failed uploads."""

    def mock_error_post(*args, **kwargs):
        raise HTTPError("Upload failed")

    # Mock both the delete and upload operations
    monkeypatch.setattr(requests, "post", mock_error_post)
    monkeypatch.setattr(collector, "delete_file", lambda x: None)
    monkeypatch.setattr(time, "sleep", lambda x: None)

    # Mock file creation to avoid actual file operations
    def mock_create(self):
        return test_file

    monkeypatch.setattr(SampleBenchmarkData, "create", mock_create)
    monkeypatch.setattr(SampleBenchmarkData, "cleanup", lambda self: None)

    result = collector.collect_metrics(num_runs=3, file_sizes_mb=[1])

    assert isinstance(result, SyncPerformanceMetric)
    size_data = result.size_metrics[0]
    assert size_data.upload_metrics.success_rate == 0.0
    assert size_data.upload_metrics.stddev_time == 0.0


def test_collect_metrics_success(collector, monkeypatch, mock_workspace, test_file):
    """Test successful metrics collection."""

    class MockResponse:
        content = b"test content"

        def raise_for_status(self):
            pass

    def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr(collector, "delete_file", lambda x: None)
    monkeypatch.setattr(time, "sleep", lambda x: None)

    # Mock file operations
    def mock_create(self):
        return test_file

    monkeypatch.setattr(SampleBenchmarkData, "create", mock_create)
    monkeypatch.setattr(SampleBenchmarkData, "cleanup", lambda self: None)

    # Mock time measurements
    times = [100.0, 150.0, 200.0]
    current_index = 0

    def mock_measure_time(self, func, *args):
        nonlocal current_index
        time = times[current_index % len(times)]
        current_index += 1
        return None, time

    monkeypatch.setattr(SyncPerformanceCollector, "_measure_operation_time", mock_measure_time)

    result = collector.collect_metrics(num_runs=3, file_sizes_mb=[1])

    assert isinstance(result, SyncPerformanceMetric)
    size_data = result.size_metrics[0]
    assert size_data.upload_metrics.success_rate == 100.0
    assert size_data.upload_metrics.min_time == 100.0
    assert size_data.upload_metrics.max_time == 200.0
    assert size_data.upload_metrics.avg_time == 150.0


@pytest.mark.parametrize(
    "error_class,error_msg",
    [
        (HTTPError, "HTTP error"),
        (RequestsError, "Network error"),
    ],
)
def test_upload_errors(collector, test_file, monkeypatch, error_class, error_msg):
    """Test file upload with different error types."""

    def mock_error_post(*args, **kwargs):
        raise error_class(error_msg)

    monkeypatch.setattr(requests, "post", mock_error_post)

    with pytest.raises(error_class, match=error_msg):
        collector.upload_file(test_file)


def test_download_error(collector, monkeypatch):
    """Test file download with error."""

    def mock_error_post(*args, **kwargs):
        raise HTTPError("Download failed")

    monkeypatch.setattr(requests, "post", mock_error_post)

    with pytest.raises(HTTPError, match="Download failed"):
        collector.download_file(Path("test.txt"))


@pytest.mark.parametrize("file_size", [1, 5, 9])
def test_default_file_sizes(collector, file_size):
    """Test default file sizes handling."""
    assert file_size in collector.DEFAULT_FILE_SIZES
