import time

from syft_rpc import rpc


def send_ping():
    start = time.time()
    future = rpc.send(
        url="syft://yash@openmined.org/api_data/pingpong/rpc/ping",
        body="Ping !!!",
        expiry_secs=120,  #! discuss expiry_secs=120 & future.timeout = 300
    )
    print(f"Request sent to {future.url}")
    response = future.wait(timeout=300)
    print(response.body.decode())
    end = time.time()
    print("Time taken: ", end - start)


if __name__ == "__main__":
    send_ping()
