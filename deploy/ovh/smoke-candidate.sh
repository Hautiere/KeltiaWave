#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${1:-deploy/ovh/.env.candidate}"
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

check_json_count() {
  local label="$1" url="$2" minimum="$3"
  local count
  count="$(curl --fail --silent --show-error "$url" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
  (( count >= minimum )) || { echo "FAIL $label: $count < $minimum" >&2; return 1; }
  echo "OK   $label: $count"
}

check_page() {
  local label="$1" port="$2"
  curl --fail --silent --show-error --max-time 15 "http://127.0.0.1:${port}/" >/dev/null
  echo "OK   $label on 127.0.0.1:${port}"
}

wait_for_url() {
  local url="$1"
  local attempt
  for attempt in $(seq 1 90); do
    if curl --fail --silent --show-error --max-time 10 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  echo "Timed out waiting for $url" >&2
  return 1
}

wait_for_url "http://127.0.0.1:${BACKEND_CANDIDATE_PORT:-18100}/"
curl --fail --silent --show-error --max-time 15 "http://127.0.0.1:${BACKEND_CANDIDATE_PORT:-18100}/" >/dev/null
echo "OK   backend"

models_status="$(curl --fail --silent --show-error --max-time 15 "http://127.0.0.1:${BACKEND_CANDIDATE_PORT:-18100}/api/transcription/models/status")"
vosk_br_available="$(python3 -c 'import json,sys; print(str(json.load(sys.stdin)["engines"]["vosk"]["languages"]["br"]["available"]).lower())' <<<"$models_status")"
[[ "$vosk_br_available" == "true" ]] || { echo "FAIL Vosk Breton model unavailable" >&2; exit 1; }
echo "OK   Vosk Breton model available"

check_page portal "${PORTAL_CANDIDATE_PORT:-14100}"
check_page corpus "${CORPUS_CANDIDATE_PORT:-14200}"
check_page learning "${LEARNING_CANDIDATE_PORT:-14300}"
check_page record "${RECORD_CANDIDATE_PORT:-14400}"
check_page transcribe "${TRANSCRIBE_CANDIDATE_PORT:-14500}"
check_page subtitles "${SUBTITLES_CANDIDATE_PORT:-14600}"

# These minimums deliberately prevent promotion of an empty content database.
check_json_count "Komz phrases" "http://127.0.0.1:${CORPUS_CANDIDATE_PORT:-14200}/api/phrases/?langue=br" "${EXPECTED_MIN_PHRASES:-105}"
check_json_count "Learning lessons" "http://127.0.0.1:${LEARNING_CANDIDATE_PORT:-14300}/api/learning/lessons" "${EXPECTED_MIN_LESSONS:-4}"

lessons_url="http://127.0.0.1:${LEARNING_CANDIDATE_PORT:-14300}/api/learning/lessons"
lessons_json="$(curl --fail --silent --show-error "$lessons_url")"
video_count="$(python3 -c 'import json,sys; print(sum(len(item.get("videos", [])) for item in json.load(sys.stdin)))' <<<"$lessons_json")"
(( video_count >= ${EXPECTED_MIN_VIDEOS:-4} )) || {
  echo "FAIL Learning videos: $video_count < ${EXPECTED_MIN_VIDEOS:-4}" >&2
  exit 1
}
video_id="$(python3 -c 'import json,sys; print(next(video["id"] for lesson in json.load(sys.stdin) for video in lesson.get("videos", [])))' <<<"$lessons_json")"
range_size="$(curl --fail --silent --show-error --range 0-1023 "http://127.0.0.1:${LEARNING_CANDIDATE_PORT:-14300}/api/learning/videos/${video_id}/file" | wc -c | tr -d ' ')"
(( range_size == 1024 )) || { echo "FAIL Learning video range: $range_size bytes" >&2; exit 1; }
echo "OK   Learning videos: $video_count; range request: $range_size bytes"

echo "Candidate smoke tests passed. Production has not been modified."
