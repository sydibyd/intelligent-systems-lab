import asyncio
import hashlib
import json
from fastapi import FastAPI
from security import install_security


def test_http_security(monkeypatch):
    token = "test-only-viewer-token-" + "x" * 32
    monkeypatch.setenv("EVAP_AUTH_MODE", "required")
    monkeypatch.setenv("EVAP_IDENTITIES_JSON", json.dumps([
        {"name": "viewer-test", "role": "viewer",
         "digest": hashlib.sha256(token.encode()).hexdigest()}
    ]))
    app = FastAPI()
    install_security(app)

    @app.get("/api/health")
    @app.get("/api/jobs")
    @app.post("/api/jobs")
    def endpoint():
        return {"ok": True}

    async def call(method, path, credential=None):
        messages = []
        headers = [] if credential is None else [(b"authorization", ("Bearer " + credential).encode())]
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        async def send(message):
            messages.append(message)
        await app({"type":"http","asgi":{"version":"3.0","spec_version":"2.4"},
                   "http_version":"1.1","method":method,"scheme":"http",
                   "path":path,"raw_path":path.encode(),"query_string":b"",
                   "headers":headers,"client":("127.0.0.1",1234),
                   "server":("test",80),"root_path":""}, receive, send)
        return next(m["status"] for m in messages if m["type"] == "http.response.start")

    async def scenario():
        assert await call("GET", "/api/health") == 200
        assert await call("GET", "/api/jobs") == 401
        assert await call("GET", "/api/jobs", "invalid") == 401
        assert await call("GET", "/api/jobs", token) == 200
        assert await call("POST", "/api/jobs", token) == 403
    asyncio.run(scenario())
