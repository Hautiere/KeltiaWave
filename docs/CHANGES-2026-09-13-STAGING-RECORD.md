# Temporary Android Record staging access

Backend/proxy change: b22420c, following the CORS change b7b840d.
Mobile change: d1c98ba. No production application deployment.

- Seven authentication tests pass, including expiry, exact scope, unauthorized
  CORS, unchanged browser login, and binary cookie signature roundtrips.
- All 31 backend tests pass.
- Mobile destination allowlist test and production/development builds pass.
- Android debug APK built and installed with data preserved on emulator-5554.
- Public HTTPS preflights pass for all three Capacitor origins on both Record
  endpoints; a foreign origin is rejected.
- Missing/invalid credentials return 401 with approved CORS, without redirects.
- A valid Record credential does not unlock any staging application root or an
  unrelated Record path.
- Public authenticated synthetic one-second WAV upload returns HTTP 200 with
  engine=whisper and the expected Android CORS header.
- Android voice/UI end-to-end validation remains pending; synthetic HTTP checks
  are not a substitute for that test.

The active host Caddyfile was changed only in the Record staging block; all other
bytes were preserved. The existing single-file container mount points to an old
inode, discovered when a reload of /etc/caddy/Caddyfile returned Basic Auth.
The validated candidate was then explicitly loaded from
/tmp/record-mobile.Caddyfile. The stale mount needs separate maintenance;
reload only a freshly copied, validated host configuration in the meantime.

Rollback backup on the VPS:
/home/ubuntu/apps/keltiawave/shared/backups/record-mobile-20260913-065238

The two-hour token expires at 2026-09-13 08:52:37 UTC. Its plaintext is absent
from Git and logs. Revoke and remove the temporary Record preflight exception
when Android validation finishes, following deploy/ovh/README.md.
