# Transcript email (not deployed)

`POST /api/record/email` accepts `recipient`, `transcript`, and `locale`
(`fr`, `en`, `br`, or `cy`). It requires an active account through the existing
JWT authentication. The sender and reply-to are fixed to
`contact@keltiawave.com`; clients cannot override them. Messages contain plain
text and a localized thank-you footer. HTTP 202 means SMTP acceptance, not
confirmed delivery.

Email is disabled by default. Configure `TRANSCRIPT_EMAIL_ENABLED`,
`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY` (`ssl` or `starttls`),
`SMTP_USERNAME`, and `SMTP_PASSWORD` on the server only. Never commit credentials
or include them in mobile builds. The mail provider must authorize this sender;
configure its recommended domain authentication before activation.

Limits are ten attempts per account per hour and a minimum interval of sixty
seconds. These counters are process-local and reset on restart. Shared counters
are required before running multiple workers or relying on durable quotas.

The mobile form uses the existing `/api/auth/login` endpoint over HTTPS and
holds the resulting account token in memory, bound to the backend address.
The temporary Record staging token is not an account token and does not authorize
email. Existing staging proxy protection remains unchanged; login and email
routes require a separate authenticated staging access validation before this
feature can be tested end to end. No production deployment has been performed.

Backend tests mock all SMTP delivery. A real delivery test needs an explicitly
approved recipient and configured mail service.
