import syft_core
import syft_event
import syft_proxy
import syft_requests
import syft_rpc
import syft_files


def main():
    print("syft-core", syft_core.__version__)
    print("syft-event", syft_event.__version__)
    print("syft-proxy", syft_proxy.__version__)
    print("syft-requests", syft_rpc.__version__)
    print("syft-rpc", syft_requests.__version__)
    print("syft-files", syft_files.__version__)
