from pathlib import Path

import pytest

from syftbox.client.benchmark.network import NetworkBenchmark
from syftbox.client.benchmark.runner import SyftBenchmarkRunner
from syftbox.client.benchmark.sync import SyncBenchmark


@pytest.fixture
def config(monkeypatch):
    """Create a config fixture using monkeypatch."""

    class MockConfig:
        server_url = "http://test-server.com"

    return MockConfig()


@pytest.fixture
def reporter(monkeypatch):
    """Create a reporter fixture using monkeypatch."""

    class MockReporter:
        def __init__(self):
            self.generated_metrics = None
            self.generated_path = None

        def generate(self, metrics, path):
            self.generated_metrics = metrics
            self.generated_path = path

    return MockReporter()


@pytest.fixture
def benchmark_runner(config, reporter):
    return SyftBenchmarkRunner(config=config, reporter=reporter)


def test_initialization(config, reporter):
    """Test that the SyftBenchmarkRunner initializes correctly."""
    runner = SyftBenchmarkRunner(config=config, reporter=reporter)

    assert runner.config == config
    assert runner.reporter == reporter


def test_get_collectors(benchmark_runner):
    """Test that get_collectors returns the correct collector types."""
    collectors = benchmark_runner.get_collectors()

    assert isinstance(collectors, dict)
    assert len(collectors) == 2
    assert collectors["network"] == NetworkBenchmark
    assert collectors["sync"] == SyncBenchmark


def test_run_with_default_path(benchmark_runner, monkeypatch):
    """Test run method with default report path."""
    mock_network_metrics = {"latency": 100, "throughput": 50}
    mock_sync_metrics = {"sync_time": 200, "success_rate": 0.95}

    class MockNetworkCollector:
        def __init__(self, config):
            pass

        def collect_metrics(self, runs):
            return mock_network_metrics

    class MockSyncCollector:
        def __init__(self, config):
            pass

        def collect_metrics(self, runs):
            return mock_sync_metrics

    monkeypatch.setattr("syftbox.client.benchmark.runner.ServerNetworkMetricCollector", MockNetworkCollector)
    monkeypatch.setattr("syftbox.client.benchmark.runner.SyncPerformanceCollector", MockSyncCollector)

    # Run the benchmark
    num_runs = 5
    benchmark_runner.run(num_runs=num_runs)

    # Verify reporter was called with correct arguments
    expected_metrics = {"network": mock_network_metrics, "sync": mock_sync_metrics}
    assert benchmark_runner.reporter.generated_metrics == expected_metrics
    assert benchmark_runner.reporter.generated_path is None


def test_run_with_custom_path(benchmark_runner, monkeypatch):
    """Test run method with custom report path."""
    mock_network_metrics = {"latency": 100}
    mock_sync_metrics = {"sync_time": 200}

    class MockNetworkCollector:
        def __init__(self, config):
            pass

        def collect_metrics(self, runs):
            return mock_network_metrics

    class MockSyncCollector:
        def __init__(self, config):
            pass

        def collect_metrics(self, runs):
            return mock_sync_metrics

    monkeypatch.setattr("syftbox.client.benchmark.runner.ServerNetworkMetricCollector", MockNetworkCollector)
    monkeypatch.setattr("syftbox.client.benchmark.runner.SyncPerformanceCollector", MockSyncCollector)

    # Run the benchmark with custom path
    num_runs = 3
    custom_path = Path("/path/to/report")
    benchmark_runner.run(num_runs=num_runs, report_path=custom_path)

    # Verify reporter was called with correct arguments
    expected_metrics = {"network": mock_network_metrics, "sync": mock_sync_metrics}
    assert benchmark_runner.reporter.generated_metrics == expected_metrics
    assert benchmark_runner.reporter.generated_path == custom_path


def test_run_with_collector_error(benchmark_runner, monkeypatch):
    """Test run method when a collector raises an error."""
    error_message = "Failed to connect to server"

    class MockNetworkCollector:
        def __init__(self, config):
            raise ConnectionError(error_message)

    monkeypatch.setattr("syftbox.client.benchmark.runner.ServerNetworkMetricCollector", MockNetworkCollector)

    with pytest.raises(ConnectionError, match=error_message):
        benchmark_runner.run(num_runs=3)


def test_run_with_metric_collection_error(benchmark_runner, monkeypatch):
    """Test run method when metric collection fails."""
    error_message = "Failed to collect metrics"

    class MockNetworkCollector:
        def __init__(self, config):
            pass

        def collect_metrics(self, runs):
            raise ValueError(error_message)

    monkeypatch.setattr("syftbox.client.benchmark.runner.ServerNetworkMetricCollector", MockNetworkCollector)

    with pytest.raises(ValueError, match=error_message):
        benchmark_runner.run(num_runs=3)
