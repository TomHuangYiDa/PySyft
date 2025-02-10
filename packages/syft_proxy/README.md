# Syft Proxy

To run an example:
* Run the syft proxy server: `cd syft_proxy && just start-server`
* If you want to run a ping pong example with yourself, run the pong server from `syft_extras`: `cd syft_extras && uv run examples/pingpong/pong_server.py` and put your email in the `datasite` field to send a request to yourself.
