from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from syft_url import SyftBoxURL
# import httpx
# import os

app = FastAPI()
futures = {}  # Store futures for later retrieval. 

# client_config = Client.load()

def syftbox_url_from_params(params: dict) -> SyftBoxURL:
    return SyftBoxURL(f"syft://{params['datasite']}/{params['path']}")


def syftbox_url_from_full_path(full_path: str) -> SyftBoxURL:
    return SyftBoxURL(f"syft://{full_path}")


# Add CORS middleware - insecure
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

@app.post("/ask", include_in_schema=False)
async def ask(request: Request) -> JSONResponse:
    body = await request.json()
    print(">>> body", body)
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    client_ip = request.client.host
    result = {
        "response": f"Got the message: {body['content']} from IP: {client_ip}",
        "files": [
            {
                "name": "nuclear_weapons.pdf",
                "size": "12,458 KB",
                "modified": "2024-01-15 14:23:45",
                "type": "PDF"
            },
            {
                "name": "national_secrets.xlsx",
                "size": "8,234 KB",
                "modified": "2024-01-10 09:15:30",
                "type": "XLSX"
            },
    ]}
    return JSONResponse(result)


@app.get("/rpc")
async def rpc(request: Request):
    sender = request.client.host
    headers = dict(request.headers)
    query_params = dict(request.query_params)

    # Add forwarding headers
    headers["x-forwarded-for"] = sender
    headers["x-forwarded-proto"] = "http"

    syftbox_url = syftbox_url_from_params(query_params)
    print(">>> syftbox_url_from_params", syftbox_url)

    # calls .get
    # future_response = rpc.get(syftbox_url, body=body, headers=headers)
    
    # returns future
    # return future_response.wait(timeout=timeout - 1.1)

    return "SyftFuture is waiting for you!"


# accepts normal HTTP
@app.get("/rpc/{full_path:path}")
async def rpc(full_path: str, request: Request):
    sender = request.client.host
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    # turns into SyftBox RPC message
    headers["x-forwarded-for"] = sender
    headers["x-forwarded-proto"] = "http"
    # rpc = RPCRequest()
    syftbox_url = syftbox_url_from_full_path(full_path)
    print(">>> syftbox_url_from_full_path", syftbox_url)
    
    # # calls .get
    # future_response = rpc.get(syftbox_url, body=body, headers=headers)
    
    # returns future
    # return future_response.wait(timeout=timeout - 1.1)
    return "SyftFuture is waiting for you!"


# allows checking of futures
# @app.get(
#     "/rpc/status/{request_key}"
# )
# async def rpc_status(request_key: str, request: Request):
#     future_response = futures[request_key]["future"]
#     response = future_response.wait(timeout=timeout - 1.1)
#     del futures[request_key]  # Cleanup once resolved
#     return create_response(response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("http_proxy:app", host="0.0.0.0", port=8000, reload=True)