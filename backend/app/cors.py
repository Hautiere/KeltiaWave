"""Explicit browser/WebView origins; deployment configuration takes precedence."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

MOBILE_ORIGINS = ("http://localhost", "https://localhost", "capacitor://localhost")
DEFAULT_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (4200, 4300, 4400, 4500, 4600)
] + list(MOBILE_ORIGINS)


def configure_cors(app: FastAPI, configured: str = "") -> None:
    origins = list(dict.fromkeys(value.strip() for value in configured.split(",") if value.strip()))
    if "*" in origins:
        raise ValueError("CORS_ALLOW_ORIGINS must contain explicit origins, not '*'.")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or DEFAULT_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
