"""Explicit bearer-token identities and deny-by-default API policy."""
import hashlib
import hmac
import json
import os
from dataclasses import dataclass

from starlette.responses import JSONResponse

ROLES = frozenset({"admin", "architect", "engineer", "viewer", "ci"})
HUMAN_WRITERS = frozenset({"admin", "architect", "engineer"})


@dataclass(frozen=True)
class Identity:
    name: str
    role: str
    digest: str


def load_identities(raw):
    records = json.loads(raw)
    if not isinstance(records, list) or not records:
        raise ValueError("At least one identity is required")
    identities = []
    for record in records:
        identity = Identity(**record)
        if (not identity.name or identity.role not in ROLES
                or len(identity.digest) != 64
                or any(c not in "0123456789abcdef" for c in identity.digest)):
            raise ValueError("Invalid identity configuration")
        identities.append(identity)
    if (len({i.name for i in identities}) != len(identities)
            or len({i.digest for i in identities}) != len(identities)):
        raise ValueError("Duplicate identity")
    return tuple(identities)


def authenticate(header, identities):
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not 32 <= len(token) <= 512:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    return next((i for i in identities if hmac.compare_digest(i.digest, digest)), None)


def allowed(role, method, path):
    if role not in ROLES:
        return False
    if method in {"GET", "HEAD"}:
        return path.startswith("/api/")
    if method == "POST" and path == "/api/jobs":
        return role in HUMAN_WRITERS | {"ci"}
    if method == "POST" and path == "/api/requirements/import":
        return role in HUMAN_WRITERS
    if method == "POST" and (path == "/api/campaigns" or path.startswith("/api/executions/")):
        return role in HUMAN_WRITERS | {"ci"}
    if path == "/api/ci-builds" and method == "POST":
        return role == "ci"
    if path.startswith("/api/ci-builds/") and method == "PATCH":
        return role == "ci"
    return False


def install_security(app):
    mode = os.getenv("EVAP_AUTH_MODE", "required")
    if mode not in {"required", "development"}:
        raise ValueError("Invalid authentication mode")
    identities = load_identities(os.environ["EVAP_IDENTITIES_JSON"]) if mode == "required" else ()

    @app.middleware("http")
    async def authorize(request, call_next):
        path = request.url.path
        if mode == "development" or (path == "/api/health" and request.method == "GET"):
            return await call_next(request)
        identity = authenticate(request.headers.get("authorization", ""), identities)
        if identity is None:
            return JSONResponse({"detail": "Authentication required"}, status_code=401,
                                headers={"WWW-Authenticate": "Bearer"})
        if not allowed(identity.role, request.method, path):
            return JSONResponse({"detail": "Permission denied"}, status_code=403)
        request.state.identity = identity
        return await call_next(request)
