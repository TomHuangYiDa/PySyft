import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Expiration time in seconds (configurable)
FUTURE_EXPIRATION_SECONDS = 60
# Futures dictionary to store futures and their timestamps
futures = {}

def add_future(request_key, future_response):
    """Add a future to the futures dict with a timestamp."""
    futures[request_key] = {"future": future_response, "timestamp": time.time()}


def clean_expired_futures():
    """Remove expired futures from the dictionary."""
    current_time = time.time()
    expired_keys = [
        key
        for key, value in futures.items()
        if current_time - value["timestamp"] > FUTURE_EXPIRATION_SECONDS
    ]
    for key in expired_keys:
        logger.info(f"Removing expired future: {key}")
        del futures[key]
