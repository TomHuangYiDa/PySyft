import socket
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from statistics import mean, quantiles, stdev

import certifi
import pycurl
from typing_extensions import Deque, Generator, Optional

MAX_THREAD_POOL_SIZE = 20


@dataclass
class ConnectionMetadata:
    timestamp: datetime
    host: str
    port: int


class RateLimiter:
    """Manages connection rate limiting"""

    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.requests: Deque[datetime] = deque()
        self.lock = threading.Lock()

    def _clean_old_requests(self) -> None:
        """Remove requests older than 1 minute"""
        cutoff = datetime.now() - timedelta(minutes=1)
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

    @contextmanager
    def rate_limit(self) -> Generator[None, None, None]:
        """Context manager for rate limiting"""
        with self.lock:
            self._clean_old_requests()
            while len(self.requests) >= self.max_requests:
                time.sleep(0.1)
                self._clean_old_requests()
            self.requests.append(datetime.now())
            yield


@dataclass
class TCPConnection:
    """Handles single TCP connection measurement"""

    host: str
    port: int
    timeout: float
    previous_latency: Optional[float] = None

    def connect(self) -> tuple[float, float]:
        """Establish TCP connection and measure performance"""
        try:
            start_time = time.time()
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                latency = (time.time() - start_time) * 1000

                # Calculate jitter
                jitter = 0
                if self.previous_latency is not None:
                    jitter = abs(latency - self.previous_latency)

                return latency, jitter

        except socket.error:
            return -1, -1


class TCPPerfStats:
    """Measure TCP connection performance"""

    max_connections_per_minute: int = 30
    max_concurrent_connections: int = 3
    connection_timeout: float = 10.0
    min_delay_between_requests: float = 0.5

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.previous_latency = None
        self.jitter_values = []
        self.request_history: Deque[ConnectionMetadata] = deque()
        self.__post_init__()

    def __post_init__(self):
        self.rate_limiter = RateLimiter(self.max_connections_per_minute)
        self.connection_lock = threading.Lock()

    @contextmanager
    def _connection_context(self) -> Generator[None, None, None]:
        """Context manager for connection tracking"""
        metadata = ConnectionMetadata(datetime.now(), self.host, self.port)
        try:
            with self.connection_lock:
                self.request_history.append(metadata)
            yield
        finally:
            # Clean old history
            with self.connection_lock:
                cutoff = datetime.now() - timedelta(minutes=1)
                while self.request_history and self.request_history[0].timestamp < cutoff:
                    self.request_history.popleft()

    def measure_single_connection(self) -> tuple[float, float]:
        """Measure a single TCP connection with rate limiting"""
        with self.rate_limiter.rate_limit():
            with self._connection_context():
                conn = TCPConnection(self.host, self.port, self.connection_timeout, self.previous_latency)
                latency, jitter = conn.connect()

                if latency >= 0:
                    self.previous_latency = latency
                    if jitter >= 0:
                        self.jitter_values.append(jitter)

                time.sleep(self.min_delay_between_requests)
                return latency, jitter

    def get_stats(self, num_runs: int) -> dict:
        """Perform multiple TCP connections and gather statistics."""
        latencies = []
        jitters = []

        print(f"Measuring TCP performance for {self.host}:{self.port}...")

        # Use ThreadPoolExecutor for parallel connections
        with ThreadPoolExecutor(max_workers=self.max_concurrent_connections) as executor:
            futures = [executor.submit(self.measure_single_connection) for _ in range(num_runs)]

            for future in futures:
                try:
                    latency, jitter = future.result()
                    if latency >= 0:
                        latencies.append(latency)
                    if jitter >= 0:
                        jitters.append(jitter)
                except Exception as e:
                    print(f"Connection error: {e}")

        if not latencies:
            return {}

        return self._calculate_stats(latencies, jitters, num_runs)

    def _calculate_stats(self, latencies: list[float], jitters: list[float], num_connections: int) -> dict:
        """Generate TCP performance stats from collected data."""
        stats = {
            "tcp_latency": {},
            "tcp_jitter": {"current": jitters[-1] if jitters else 0},
        }

        for metric_name, values in [("tcp_latency", latencies), ("tcp_jitter", jitters)]:
            if not values:
                continue

            quants = quantiles(values, n=100)
            stats[metric_name].update(
                {
                    "min": min(values),
                    "max": max(values),
                    "avg": mean(values),
                    "median": quants[49],
                    "stddev": stdev(values) if len(values) > 1 else 0,
                    "p95": quants[94],
                    "p99": quants[98],
                }
            )

        stats["connection_success_rate"] = len(latencies) / num_connections * 100

        # Add rate limiting stats
        stats["rate_limiting"] = {
            "requests_in_last_minute": len(self.request_history),
            "max_requests_per_minute": self.max_connections_per_minute,
            "max_concurrent_connections": self.max_concurrent_connections,
        }

        return stats


class HTTPPerfStats:
    """Measure HTTP connection performance"""

    def __init__(self, url: str):
        self.url = url
        self.buffer = BytesIO()

    def _create_curl(self) -> pycurl.Curl:
        """Create and configure a PycURL object."""
        c = pycurl.Curl()
        for option, value in self._get_default_options().items():
            c.setopt(option, value)
        return c

    def _get_default_options(self) -> dict:
        """Get default options for PycURL object."""
        return {
            pycurl.URL: self.url,
            pycurl.WRITEDATA: self.buffer,
            pycurl.CAINFO: certifi.where(),
            pycurl.FOLLOWLOCATION: 1,
            pycurl.MAXREDIRS: 5,
            pycurl.CONNECTTIMEOUT: 30,
            pycurl.TIMEOUT: 60,
            pycurl.SSL_VERIFYPEER: 1,
            pycurl.SSL_VERIFYHOST: 2,
        }

    def __calc_server_processing_time(self, stats: dict) -> float:
        """
        Calculate actual server processing time by subtracting connection times from TTFB.
        Server Processing Time = TTFB - (DNS + TCP + SSL)
        """

        ttfb = stats["starttransfer_time"]
        dns_time = stats["dns_time"]
        tcp_time = stats["tcp_time"]
        ssl_time = stats["ssl_time"]

        server_processing = ttfb - (dns_time + tcp_time + ssl_time)
        return max(0, server_processing)  # Ensure we don't return negative values

    def _get_stats(self) -> dict:
        """HTTP performance stats using PycURL."""

        curl = self._create_curl()

        # Clear buffer before each request
        self.buffer.seek(0)
        self.buffer.truncate()

        try:
            curl.perform()

            # Standard HTTP stats
            stats = {
                "dns_time": curl.getinfo(pycurl.NAMELOOKUP_TIME) * 1000,
                "connect_time": curl.getinfo(pycurl.CONNECT_TIME) * 1000,
                "ssl_time": (curl.getinfo(pycurl.APPCONNECT_TIME) - curl.getinfo(pycurl.CONNECT_TIME)) * 1000,
                "starttransfer_time": curl.getinfo(pycurl.STARTTRANSFER_TIME) * 1000,
                "total_time": curl.getinfo(pycurl.TOTAL_TIME) * 1000,
                "size_download": curl.getinfo(pycurl.SIZE_DOWNLOAD),
                "speed_download": curl.getinfo(pycurl.SPEED_DOWNLOAD),
                "header_size": curl.getinfo(pycurl.HEADER_SIZE),
                "request_size": curl.getinfo(pycurl.REQUEST_SIZE),
                "http_code": curl.getinfo(pycurl.HTTP_CODE),
                "primary_ip": curl.getinfo(pycurl.PRIMARY_IP),
                "primary_port": curl.getinfo(pycurl.PRIMARY_PORT),
                "tcp_time": (curl.getinfo(pycurl.CONNECT_TIME) - curl.getinfo(pycurl.NAMELOOKUP_TIME)) * 1000,
                "content_transfer_time": (curl.getinfo(pycurl.TOTAL_TIME) - curl.getinfo(pycurl.STARTTRANSFER_TIME))
                * 1000,
            }
            stats["server_processing_time"] = self.__calc_server_processing_time(stats)

        except pycurl.error as e:
            stats = {}
            print(f"Error: {e}")
        finally:
            curl.close()

        return stats

    def get_stats(self, n_runs: int) -> dict:
        """Aggregate percentile stats from multiple runs."""
        print("Measuring HTTP performance for", self.url)

        all_stats = []
        for _ in range(n_runs):
            stats = self._get_stats()
            all_stats.append(stats)

        agg_stats = defaultdict(dict)

        # Aggregate stats
        cols = [
            "dns_time",
            "connect_time",
            "ssl_time",
            "starttransfer_time",
            "total_time",
            "speed_download",
            "tcp_time",
            "content_transfer_time",
            "server_processing_time",
        ]

        # Calculate percentiles for each metric
        for col in cols:
            if col not in all_stats[0]:
                continue
            values = [s[col] for s in all_stats if col in s]
            quants = quantiles(values, n=100)
            agg_stats[col]["min"] = min(values) if values else 0
            agg_stats[col]["max"] = max(values) if values else 0
            agg_stats[col]["avg"] = mean(values) if values else 0
            agg_stats[col]["median"] = quants[49]  # median
            agg_stats[col]["stddev"] = stdev(values) if len(values) > 1 else 0
            agg_stats[col]["p95"] = quants[94]  # 95th percentile
            agg_stats[col]["p99"] = quants[98]  # 99th percentile

        return agg_stats
