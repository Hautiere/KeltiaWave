# KeltiaWave: task map

- Start with `rg --files`, then `rg -n` in the smallest relevant directory. Read nearby lines before full files; expand only for a concrete dependency. Do not preload all apps, histories, generated assets, lockfiles or models.
- For app changes, inspect its component/API/template/styles; for API changes, its route/dependencies/focused tests. External documentation: focused excerpts first; report failed searches instead of guessing.
- Preserve unrelated working-tree changes. Never expose/commit `.env`, credentials or local model binaries.

## Entry points

- `apps/portal/`: static portal. `apps/corpus/`: web Komz/Listen, voices, accounts, review. `apps/learning/`: lessons/exercises.
- `apps/{record,transcribe,subtitles}/`: audio tools. `apps/live/`: component/template/styles, `live-audio.service.ts`, `public/live-pcm-worklet.js`.
- `backend/app/api/endpoints/`: corpus/accounts; `backend/app/{record,transcribe,subtitles,learning,live}/`: feature APIs.
- `backend/app/live/routes.py`: capabilities, WebSocket stream, Whisper improve. Shared Whisper: `backend/app/transcribe/service.py`; Vosk: `backend/app/vosk_utils.py`.
- `backend/tests/`: tests; `deploy/`, `scripts/`: delivery/local commands. README and feature READMEs only as needed.
- Native Android is in sibling `../keltiawave-mobile`; start with its `AGENTS.md`. Its Breton Vosk is local in Record/Transcribe/Live; web Vosk still uses the server. Phone updates require an APK.

## Focused verification

- Build only the changed frontend: `npm run build:<app>` from root.
- Run focused backend tests; widen only for a concrete integration risk.
- Live: `npm --prefix apps/live test`; `backend/.venv/bin/python -m pytest backend/tests/test_live.py -q`.
- Browser HTTP/WebSocket must use frontend origin through Nginx (`Host $http_host`) or `apps/live/proxy.conf.json`, not direct port 8100.
- Finish with `git diff --check` and review changed lines. Docs-only edits need no rebuild.
