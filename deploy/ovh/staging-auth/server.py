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


def encode_token(expires: int) -> str:
    payload = f"{USERNAME}:{expires}".encode()
    signature = hmac.new(SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode().rstrip("=")


def valid_token(token: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        payload, signature = raw.rsplit(b".", 1)
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


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
