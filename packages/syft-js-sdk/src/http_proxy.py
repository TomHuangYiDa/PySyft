from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
# import httpx
# import os

app = FastAPI()

# Add CORS middleware - very insecure
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask", include_in_schema=False)
async def ask(request: Request) -> JSONResponse:
    body = await request.json()
    print(">>> body", body)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)