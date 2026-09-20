import base64
import hashlib
import hmac
import html
import os
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse


USERNAME = os.environ["STAGING_AUTH_USERNAME"]
PASSWORD = os.environ["STAGING_AUTH_PASSWORD"]
SECRET = os.environ["STAGING_AUTH_COOKIE_SECRET"].encode()
COOKIE_NAME = "keltiawave_staging_session"
COOKIE_DOMAIN = os.getenv("STAGING_AUTH_COOKIE_DOMAIN", ".staging.keltiawave.com")
SESSION_TTL = int(os.getenv("STAGING_AUTH_SESSION_TTL", "43200"))
PORTAL_URL = "https://staging.keltiawave.com"



RECORD_HOST = "record.staging.keltiawave.com"
RECORD_PATHS = {"/api/record/transcribe", "/api/record/improve"}
MOBILE_ORIGINS = {"http://localhost", "https://localhost", "capacitor://localhost"}


def record_scope(headers) -> bool:
    return (
        os.getenv("DEPLOY_SLOT") == "staging"
        and headers.get("X-Forwarded-Host") == RECORD_HOST
        and headers.get("X-Forwarded-Method") == "POST"
        and headers.get("X-Forwarded-Uri") in RECORD_PATHS
    )


def valid_record_access(headers) -> bool:
    if not record_scope(headers):
        return False
    authorization = headers.get("Authorization", "")
    device_digest = os.getenv("STAGING_RECORD_DEVICE_SHA256", "")
    if authorization.startswith("Bearer ") and len(authorization) <= 256:
        credential = authorization[7:]
        if (len(credential) >= 32 and len(device_digest) == 64
                and hmac.compare_digest(hashlib.sha256(credential.encode()).hexdigest(), device_digest)):
            return True
    try:
        expires = int(os.getenv("STAGING_RECORD_TOKEN_EXPIRES_AT", "0"))
    except ValueError:
        return False
    digest = os.getenv("STAGING_RECORD_TOKEN_SHA256", "")
    authorization = headers.get("Authorization", "")
    if (expires <= time.time() or len(digest) != 64
            or not authorization.startswith("Bearer ") or len(authorization) > 256):
        return False
    token = authorization[7:]
    return bool(token) and hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), digest)


def encode_token(expires: int) -> str:
    payload = f"{USERNAME}:{expires}".encode()
    signature = hmac.new(SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode().rstrip("=")


def valid_token(token: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        # SHA-256 is 32 binary bytes and may itself contain a dot.
        if len(raw) < 34 or raw[-33:-32] != b".":
            return False
        payload, signature = raw[:-33], raw[-32:]
        expected = hmac.new(SECRET, payload, hashlib.sha256).digest()
        user, expires = payload.decode().rsplit(":", 1)
        return (
            hmac.compare_digest(signature, expected)
            and hmac.compare_digest(user, USERNAME)
            and int(expires) > int(time.time())
        )
    except (ValueError, UnicodeDecodeError):
        return False


def safe_next(value: str | None) -> str:
    if not value:
        return PORTAL_URL
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and (host == "staging.keltiawave.com" or host.endswith(".staging.keltiawave.com")):
        return value
    return PORTAL_URL


def login_page(next_url: str, error: bool = False) -> bytes:
    message = '<p class="error">Identifiants incorrects.</p>' if error else ""
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connexion au staging KeltiaWave</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f4f8ff;color:#082451;font:16px system-ui,sans-serif}}
main{{width:min(420px,calc(100% - 32px));padding:32px;border:1px solid #d8e4f5;border-radius:20px;background:white;box-shadow:0 18px 60px #1232  }}
h1{{margin:0 0 8px;font-size:26px}} p{{color:#526987}} label{{display:block;margin:18px 0 6px;font-weight:700}}
input{{width:100%;padding:13px;border:1px solid #b8c9df;border-radius:10px;font-size:16px}} button{{width:100%;margin-top:22px;padding:13px;border:0;border-radius:10px;background:#1769ff;color:white;font-weight:800;font-size:16px;cursor:pointer}}
.error{{padding:10px;border-radius:8px;background:#fff0f0;color:#a62020}}
</style></head><body><main><h1>KeltiaWave staging</h1><p>Une seule connexion donne accès à toutes les applications de test.</p>{message}
<form method="post" action="/staging-login"><input type="hidden" name="next" value="{html.escape(next_url, quote=True)}">
<label for="username">Nom d’utilisateur</label><input id="username" name="username" autocomplete="username" required autofocus>
<label for="password">Mot de passe</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<button type="submit">Se connecter</button></form></main></body></html>""".encode()


class Handler(BaseHTTPRequestHandler):
    def send_redirect(self, location: str, cookie: str | None = None) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if parsed.path == "/verify-record":
            try:
                session = cookies.SimpleCookie(self.headers.get("Cookie", "")).get(COOKIE_NAME)
            except cookies.CookieError:
                session = None
            authorized = record_scope(self.headers) and (
                valid_record_access(self.headers) or (session and valid_token(session.value))
            )
            self.send_response(200 if authorized else 401)
            self.send_header("Cache-Control", "no-store")
            if not authorized:
                self.send_header("Vary", "Origin")
                origin = self.headers.get("Origin", "")
                if origin in MOBILE_ORIGINS:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Access-Control-Allow-Credentials", "true")
                self.send_header("Content-Type", "application/json")
            self.end_headers()
            if not authorized:
                self.wfile.write(b'{"detail":"Staging Record authentication required or expired."}')
            return
        if parsed.path == "/verify":
            jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            token = jar.get(COOKIE_NAME)
            if token and valid_token(token.value):
                self.send_response(200)
                self.end_headers()
                return
            host = self.headers.get("X-Forwarded-Host", "staging.keltiawave.com")
            uri = self.headers.get("X-Forwarded-Uri", "/")
            target = safe_next(f"https://{host}{uri}")
            self.send_redirect(f"{PORTAL_URL}/staging-login?next={quote(target, safe='')}")
            return
        if parsed.path == "/staging-login":
            next_url = safe_next(parse_qs(parsed.query).get("next", [PORTAL_URL])[0])
            body = login_page(next_url)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/staging-logout":
            expired = f"{COOKIE_NAME}=; Domain={COOKIE_DOMAIN}; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax"
            self.send_redirect(f"{PORTAL_URL}/staging-login", expired)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/staging-login":
            self.send_error(404)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 8192)
        except ValueError:
            length = 0
        form = parse_qs(self.rfile.read(length).decode(errors="replace"))
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        next_url = safe_next(form.get("next", [PORTAL_URL])[0])
        if hmac.compare_digest(username, USERNAME) and hmac.compare_digest(password, PASSWORD):
            expires = int(time.time()) + SESSION_TTL
            token = encode_token(expires)
            cookie = f"{COOKIE_NAME}={token}; Domain={COOKIE_DOMAIN}; Path=/; Max-Age={SESSION_TTL}; Secure; HttpOnly; SameSite=Lax"
            self.send_redirect(next_url, cookie)
            return
        body = login_page(next_url, error=True)
        self.send_response(401)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
