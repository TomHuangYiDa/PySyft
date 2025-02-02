import syft_core
import syft_event
import syft_files
import syft_requests
import syft_rpc


def main():
    print("syft-core", syft_core.__version__)
    print("syft-event", syft_event.__version__)
    print("syft-requests", syft_rpc.__version__)
    print("syft-rpc", syft_requests.__version__)
    print("syft-files", syft_files.__version__)
