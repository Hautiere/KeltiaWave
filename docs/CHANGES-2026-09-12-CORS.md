# Capacitor CORS support

Allow explicit Capacitor WebView origins in the shared FastAPI backend:
`http://localhost`, `https://localhost`, and `capacitor://localhost`.
Existing web origins remain allowed by default. An explicit CORS_ALLOW_ORIGINS
value replaces defaults; wildcard origins are rejected at startup.

Local and OVH Compose defaults and environment examples include mobile origins.
Existing deployment environment values must be updated separately, preserving
existing origins. No production environment or deployment has been changed.

Validation: 31 backend tests passed, including nine CORS tests covering Record
preflights, validation-error responses, rejected foreign origins, explicit
configuration precedence and wildcard rejection.

Staging validation and Android end-to-end Whisper transcription remain required.
The mobile UI changes are deferred until that flow is validated.
