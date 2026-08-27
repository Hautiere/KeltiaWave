import hashlib


LESSON_PAYLOAD = {
    "title": "An amzer-vremañ",
    "level": "A2",
    "domain": "Keleier",
    "description": "Kompren ur berrvideo.",
    "segments": [
        {
            "position": 0,
            "start_ms": 1000,
            "end_ms": 4000,
            "text": "Mont a ran da Kemper.",
            "translation": "Je vais à Quimper.",
            "blanks": [{
                "position": 14,
                "answer": "Kemper",
                "accepted_variants": ["Quimper"],
                "accept_mutations": True,
            }],
        }
    ],
    "vocabulary": [
        {"position": 0, "term": "mont", "translation": "aller", "note": "Verbe verbal"}
    ],
    "grammar": [
        {
            "position": 0,
            "title": "Mont a ran da",
            "explanation": "Construction exprimant un déplacement.",
            "example": "Mont a ran da Gemper.",
            "translation": "Je vais à Quimper.",
        }
    ],
}


def test_lesson_writes_require_an_admin(client, auth_headers):
    response = client.post("/api/learning/lessons", json=LESSON_PAYLOAD)
    assert response.status_code == 401

    response = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["learner"],
    )
    assert response.status_code == 403


def test_draft_is_only_visible_to_admin(client, auth_headers):
    created = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    )
    assert created.status_code == 201
    lesson = created.json()
    assert lesson["status"] == "draft"
    assert lesson["segments"][0]["blanks"][0]["answer"] == "Kemper"
    assert lesson["segments"][0]["blanks"][0]["accepted_variants"] == ["Quimper"]
    assert lesson["segments"][0]["blanks"][0]["accept_mutations"] is True
    assert lesson["vocabulary"][0]["term"] == "mont"
    assert lesson["grammar"][0]["title"] == "Mont a ran da"

    assert client.get("/api/learning/lessons").json() == []
    assert client.get(f"/api/learning/lessons/{lesson['id']}").status_code == 404

    response = client.get(
        "/api/learning/lessons?include_unpublished=true",
        headers=auth_headers["admin"],
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [lesson["id"]]


def test_video_metadata_storage_and_publication(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()
    video_bytes = b"\x00\x00\x00\x18ftypisomfake-mp4-content-for-storage-test"
    thumbnail_bytes = b"\x89PNG\r\n\x1a\nthumbnail-content-for-storage-test"

    thumbnail = client.post(
        f"/api/learning/lessons/{lesson['id']}/thumbnail",
        headers=auth_headers["admin"],
        files={"file": ("cover.png", thumbnail_bytes, "image/png")},
    )
    assert thumbnail.status_code == 200, thumbnail.text
    assert thumbnail.json()["thumbnail_url"] == f"/api/learning/lessons/{lesson['id']}/thumbnail"
    assert client.get(thumbnail.json()["thumbnail_url"]).status_code == 404

    uploaded = client.post(
        f"/api/learning/lessons/{lesson['id']}/videos",
        headers=auth_headers["admin"],
        data={"duration_seconds": "42", "position": "1"},
        files={"file": ("lesson.mp4", video_bytes, "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    video = uploaded.json()
    assert video["original_filename"] == "lesson.mp4"
    assert video["content_type"] == "video/mp4"
    assert video["size_bytes"] == len(video_bytes)
    assert video["checksum_sha256"] == hashlib.sha256(video_bytes).hexdigest()
    assert video["duration_seconds"] == 42
    assert video["position"] == 1

    updated = client.patch(
        f"/api/learning/videos/{video['id']}",
        headers=auth_headers["admin"],
        json={"duration_seconds": 43, "position": 2, "source_url": "https://example.test/original-video"},
    )
    assert updated.status_code == 200
    assert updated.json()["duration_seconds"] == 43
    assert updated.json()["position"] == 2
    assert updated.json()["source_url"] == "https://example.test/original-video"

    hidden_media = client.get(f"/api/learning/videos/{video['id']}/file")
    assert hidden_media.status_code == 404

    published = client.post(
        f"/api/learning/lessons/{lesson['id']}/publish",
        headers=auth_headers["admin"],
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    catalog = client.get("/api/learning/lessons")
    assert catalog.status_code == 200
    assert catalog.json()[0]["videos"][0]["checksum_sha256"] == video["checksum_sha256"]

    media = client.get(f"/api/learning/videos/{video['id']}/file")
    assert media.status_code == 200
    assert media.content == video_bytes
    public_thumbnail = client.get(f"/api/learning/lessons/{lesson['id']}/thumbnail")
    assert public_thumbnail.status_code == 200
    assert public_thumbnail.content == thumbnail_bytes


def test_publication_requires_a_video(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()

    response = client.post(
        f"/api/learning/lessons/{lesson['id']}/publish",
        headers=auth_headers["admin"],
    )
    assert response.status_code == 409


def test_video_type_is_validated(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()

    response = client.post(
        f"/api/learning/lessons/{lesson['id']}/videos",
        headers=auth_headers["admin"],
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )
    assert response.status_code == 415

    invalid_thumbnail = client.post(
        f"/api/learning/lessons/{lesson['id']}/thumbnail",
        headers=auth_headers["admin"],
        files={"file": ("cover.png", b"not an image", "image/png")},
    )
    assert invalid_thumbnail.status_code == 415


def test_mp3_can_be_used_as_lesson_media(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()
    mp3_bytes = b"ID3\x04\x00\x00\x00\x00\x00\x00fake-mp3-content"
    uploaded = client.post(
        f"/api/learning/lessons/{lesson['id']}/videos",
        headers=auth_headers["admin"],
        data={"duration_seconds": "75"},
        files={"file": ("lesson.mp3", mp3_bytes, "audio/mpeg")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["content_type"] == "audio/mpeg"
    assert uploaded.json()["duration_seconds"] == 75

    published = client.post(
        f"/api/learning/lessons/{lesson['id']}/publish",
        headers=auth_headers["admin"],
    )
    assert published.status_code == 200
    media = client.get(f"/api/learning/videos/{uploaded.json()['id']}/file")
    assert media.status_code == 200
    assert media.content == mp3_bytes
    partial = client.get(
        f"/api/learning/videos/{uploaded.json()['id']}/file",
        headers={"Range": "bytes=3-9"},
    )
    assert partial.status_code == 206
    assert partial.content == mp3_bytes[3:10]
    assert partial.headers["accept-ranges"] == "bytes"


def test_upload_can_replace_the_existing_lesson_media(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()
    first = client.post(
        f"/api/learning/lessons/{lesson['id']}/videos",
        headers=auth_headers["admin"],
        files={"file": ("original.mp3", b"ID3-original", "audio/mpeg")},
    )
    replacement = client.post(
        f"/api/learning/lessons/{lesson['id']}/videos",
        headers=auth_headers["admin"],
        data={"replace_existing": "true"},
        files={"file": ("replacement.mp3", b"ID3-replacement", "audio/mpeg")},
    )
    assert replacement.status_code == 201, replacement.text
    assert client.get(f"/api/learning/videos/{first.json()['id']}/file", headers=auth_headers["admin"]).status_code == 404
    media = client.get(f"/api/learning/videos/{replacement.json()['id']}/file", headers=auth_headers["admin"])
    assert media.status_code == 200
    assert media.content == b"ID3-replacement"

    lessons = client.get("/api/learning/lessons?include_unpublished=true", headers=auth_headers["admin"]).json()
    saved = next(item for item in lessons if item["id"] == lesson["id"])
    assert [video["original_filename"] for video in saved["videos"]] == ["replacement.mp3"]


def test_nested_lesson_content_can_be_replaced(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()

    response = client.put(
        f"/api/learning/lessons/{lesson['id']}",
        headers=auth_headers["admin"],
        json={
            "segments": [
                {
                    "position": 0,
                    "start_ms": 5000,
                    "end_ms": 8000,
                    "text": "Brav eo an amzer.",
                    "translation": "Il fait beau.",
                    "blanks": [{"position": 11, "answer": "amzer"}],
                }
            ],
            "vocabulary": [],
            "grammar": [],
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert len(updated["segments"]) == 1
    assert updated["segments"][0]["text"] == "Brav eo an amzer."
    assert updated["segments"][0]["blanks"][0]["answer"] == "amzer"
    assert updated["vocabulary"] == []
    assert updated["grammar"] == []


def test_segment_contract_rejects_invalid_timestamps(client, auth_headers):
    payload = {**LESSON_PAYLOAD, "segments": [{**LESSON_PAYLOAD["segments"][0], "end_ms": 500}]}
    response = client.post(
        "/api/learning/lessons",
        json=payload,
        headers=auth_headers["admin"],
    )
    assert response.status_code == 422


def test_progress_is_optional_and_synced_for_authenticated_learner(client, auth_headers):
    lesson = client.post(
        "/api/learning/lessons",
        json=LESSON_PAYLOAD,
        headers=auth_headers["admin"],
    ).json()
    video_bytes = b"\x00\x00\x00\x18ftypisomprogress-test"
    client.post(
        f"/api/learning/lessons/{lesson['id']}/videos",
        headers=auth_headers["admin"],
        files={"file": ("lesson.mp4", video_bytes, "video/mp4")},
    )
    client.post(f"/api/learning/lessons/{lesson['id']}/publish", headers=auth_headers["admin"])

    assert client.get("/api/learning/progress").status_code == 401
    started = client.put(
        f"/api/learning/lessons/{lesson['id']}/progress",
        headers=auth_headers["learner"],
        json={"status": "started", "score": 0, "total_questions": 1},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "started"
    completed = client.put(
        f"/api/learning/lessons/{lesson['id']}/progress",
        headers=auth_headers["learner"],
        json={"status": "completed", "score": 1, "total_questions": 1},
    )
    assert completed.status_code == 200
    assert completed.json()["best_score"] == 1
    assert completed.json()["attempts"] == 1
    progress = client.get("/api/learning/progress", headers=auth_headers["learner"])
    assert progress.status_code == 200
    assert progress.json()[0]["lesson_id"] == lesson["id"]
