import pytest
from curl_cffi import requests

from syftbox.client.benchmark import Stats
from syftbox.client.benchmark.syncstats import (
    DataTransferStats,
    FileTransferDuration,
    SyncDataTransferStats,
    generate_byte_string,
    random_filename,
)


# Mock Classes
class MockResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.RequestsError(f"HTTP Error: {self.status_code}")


class MockCurlMime:
    """Mock CurlMime that properly handles initialization and cleanup"""

    def __init__(self):
        self._form = True  # Just needs to exist for __del__
        self.parts = []

    def addpart(self, **kwargs):
        self.parts.append(kwargs)

    def close(self):
        self._form = None


# Test data
TEST_URL = "https://example.com"
TEST_TOKEN = "test-token"
TEST_EMAIL = "test@example.com"
TEST_FILE_SIZE = 1  # 1MB


@pytest.fixture
def sync_stats():
    return SyncDataTransferStats(TEST_URL, TEST_TOKEN, TEST_EMAIL)


@pytest.fixture
def mock_requests(monkeypatch):
    def mock_post(*args, **kwargs):
        return MockResponse(200)

    monkeypatch.setattr(requests, "post", mock_post)


@pytest.fixture
def mock_time(monkeypatch):
    class MockTime:
        def __init__(self):
            self.current_time = 0.0

        def time(self):
            self.current_time += 0.5  # Simulate 500ms per operation
            return self.current_time

    mock_timer = MockTime()
    monkeypatch.setattr("time.time", mock_timer.time)
    return mock_timer


@pytest.fixture
def mock_curl_mime(monkeypatch):
    def mock_curl_mime_constructor():
        return MockCurlMime()

    monkeypatch.setattr("curl_cffi.CurlMime", mock_curl_mime_constructor)
    return MockCurlMime()


def test_generate_byte_string():
    """Test byte string generation"""
    size_mb = 2
    data = generate_byte_string(size_mb)
    expected_size = size_mb * 1024 * 1024

    assert isinstance(data, bytes)
    assert len(data) == expected_size
    assert data == b"\0" * expected_size


def test_random_filename():
    """Test random filename generation"""
    size_mb = 5
    filename = random_filename(size_mb)

    assert filename.startswith("5mb-")
    assert filename.endswith(".bytes")
    assert len(filename) == len("5mb-") + 8 + len(".bytes")


def test_make_request(sync_stats, mock_requests, mock_time):
    """Test request making with timing"""
    duration = sync_stats._SyncDataTransferStats__make_request("/test/path/", json={})

    assert isinstance(duration, float)
    assert duration == 500.0  # 0.5 seconds * 1000


def test_upload_file(sync_stats, mock_requests, mock_time, monkeypatch):
    """Test file upload with timing"""
    # Track all created CurlMime instances
    mime_instances = []

    class MockCurlMime:
        def __init__(self):
            self._form = True
            self.parts = []
            mime_instances.append(self)

        def addpart(self, **kwargs):
            self.parts.append(kwargs)

        def close(self):
            self._form = None

    # Replace the CurlMime class with our mock
    monkeypatch.setattr("syftbox.client.benchmark.syncstats.CurlMime", MockCurlMime)

    # Perform the upload
    filepath = "test/path/file.txt"
    data = b"test data"
    duration = sync_stats.upload_file(filepath, data)

    # Verify the mock was used correctly
    assert len(mime_instances) == 1
    mock_mime = mime_instances[0]
    assert len(mock_mime.parts) == 1
    assert mock_mime.parts[0]["name"] == "file"
    assert mock_mime.parts[0]["filename"] == filepath
    assert mock_mime.parts[0]["data"] == data
    assert mock_mime.parts[0]["content_type"] == "text/plain"
    assert duration == 500.0


def test_download_file(sync_stats, mock_requests, mock_time):
    """Test file download with timing"""
    filepath = "test/path/file.txt"
    duration = sync_stats.download_file(filepath)

    assert isinstance(duration, float)
    assert duration == 500.0


def test_delete_file(sync_stats, mock_requests, mock_time, monkeypatch):
    """Test file deletion"""
    filepath = "test/path/file.txt"

    # Test successful deletion
    sync_stats.delete_file(filepath)

    # Test failed deletion (should not raise exception)
    def mock_failed_request(*args, **kwargs):
        return MockResponse(404)

    monkeypatch.setattr(requests, "post", mock_failed_request)
    sync_stats.delete_file(filepath)  # Should not raise exception


def test_measure_file_transfer(sync_stats, mock_requests, mock_time, mock_curl_mime):
    """Test complete file transfer measurement"""
    result = sync_stats.measure_file_transfer(TEST_FILE_SIZE)

    assert isinstance(result, FileTransferDuration)
    assert result.upload == 500.0
    assert result.download == 500.0


def test_get_stats(sync_stats, mock_requests, mock_time, mock_curl_mime):
    """Test statistics gathering for multiple transfers"""
    result = sync_stats.get_stats(TEST_FILE_SIZE, num_runs=3)

    assert isinstance(result, DataTransferStats)
    assert result.file_size_mb == TEST_FILE_SIZE
    assert isinstance(result.upload, Stats)
    assert isinstance(result.download, Stats)
    assert result.upload.mean == 500.0
    assert result.download.mean == 500.0


def test_error_handling(sync_stats, mock_time, monkeypatch):
    """Test error handling during transfers"""

    def mock_failed_request(*args, **kwargs):
        raise requests.RequestsError("Simulated failure")

    monkeypatch.setattr(requests, "post", mock_failed_request)

    with pytest.raises(requests.RequestsError):
        sync_stats.measure_file_transfer(TEST_FILE_SIZE)


def test_get_stats_empty(sync_stats, mock_time, monkeypatch):
    """Test statistics calculation with no successful transfers"""

    def mock_failed_transfer(*args, **kwargs):
        raise requests.RequestsError("Simulated failure")

    monkeypatch.setattr(sync_stats, "measure_file_transfer", mock_failed_transfer)

    with pytest.raises(Exception):
        sync_stats.get_stats(TEST_FILE_SIZE, num_runs=3)
