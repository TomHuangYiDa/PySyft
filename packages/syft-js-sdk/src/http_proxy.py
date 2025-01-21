from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from syft_url import SyftBoxURL
from asyncio import Future
import asyncio


app = FastAPI()

# Example futures dictionary
future1 = Future()
future1.set_result({
    "status": "success",
    "data": {
        "user_id": 123,
        "message": "Data processing complete",
        "results": [1, 2, 3]
    }
})

future2 = Future()
future2.set_result({
    "status": "error",
    "error": "Timeout occurred",
    "error_code": 408
})


futures = {
    "abc123": {
        "future": future1,  # The actual Future object
        "created_at": "2025-01-21T10:30:00",
        "request_id": "req_789",
        "status": "completed"
    },
    "def456": {
        "future": future2,
        "created_at": "2025-01-21T10:35:00",
        "request_id": "req_790",
        "status": "error"
    }
}

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
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    client_ip = request.client.host
    # we need to forward LLM and get back the Future?
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


# allows checking of futures
@app.get(
    "/rpc/status/{request_key}"
)
async def rpc_status(request_key: str, request: Request):
    # import pdb; pdb.set_trace()
    future_response = futures[request_key]["future"]
    # del futures[request_key]  # Cleanup once resolved
    # return create_response(response)
    try:
        response = await asyncio.wait_for(future_response, timeout=3)
        return response
    except asyncio.TimeoutError:
        return {"status": "pending", "message": "Request still processing"}


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
    
    # calls .get
    future_response = rpc.send(syftbox_url, body=body, headers=headers, method="get")
    
    # returns future
    # return future_response.wait(timeout=timeout - 1.1)
    return "SyftFuture is waiting for you!"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("http_proxy:app", host="0.0.0.0", port=8000, reload=True)