#!/usr/bin/env python3
"""Prepare and import a reviewed Common Voice CSV through the local admin API."""
import argparse
import csv
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def prepare(csv_path, corpus, name, theme):
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        selected = list(csv.DictReader(stream, delimiter=";"))
    if not selected:
        raise ValueError("Le CSV est vide.")
    index = {}
    for partition in ("validated", "invalidated", "other"):
        with (corpus / f"{partition}.tsv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                index[row["path"]] = {**row, "partition": partition}
    items, provenance, seen, ids = [], [], set(), set()
    clips = (corpus / "clips").resolve()
    for row in selected:
        identifier = row["komz_id"]
        if identifier in ids:
            raise ValueError(f"Identifiant répété : {identifier}")
        ids.add(identifier)
        text = row["phrase_br"]
        if not text or text != row["source_phrase_br"]:
            raise ValueError(f"{identifier} : texte différent du texte source.")
        if row["level"] not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
            raise ValueError(f"{identifier} : niveau invalide.")
        filenames = [part.strip() for part in row["audio_reference_path"].split("|") if part.strip()]
        if not filenames:
            raise ValueError(f"{identifier} : aucune référence audio.")
        for filename in filenames:
            path = (clips / filename).resolve()
            source = index.get(filename)
            if path.parent != clips or not path.is_file() or not source or source["sentence"] != text:
                raise ValueError(f"{identifier} : audio absent ou texte incohérent : {filename}")
            if row["source_phrase_id"] not in {source.get("sentence_id"), hashlib.sha256(text.encode()).hexdigest()}:
                raise ValueError(f"{identifier} : identifiant source incohérent.")
            if filename in seen:
                raise ValueError(f"Référence audio répétée : {filename}")
            seen.add(filename)
            digest = hashlib.sha256(name.encode() + b"\0" + text.encode() + b"\0" + path.read_bytes()).hexdigest()[:16]
            storage_name = f"import-{name}-{digest}{path.suffix.lower()}"
            items.append({"texte": text, "traduction_fr": row["translation_fr"],
                          "theme": theme, "niveau": row["level"], "langue": "br",
                          "source": name, "phrase_source": "common_voice", "auteur": "import-common-voice",
                          "domain": theme, "audio_path": filename, "origin": "dataset",
                          "status": "pending", "speaker_accent": source.get("accents", "")})
            provenance.append({"selection": row, "common_voice": source,
                               "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                               "storage_name": storage_name})
    return items, provenance


class API:
    def __init__(self, base, token=""):
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("Seul un backend HTTP local est accepté.")
        self.base, self.token = base.rstrip("/"), token

    def call(self, route, data=None, content_type="application/json"):
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        # Refuse redirects so credentials and uploaded data stay on the chosen local API.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        request = urllib.request.Request(self.base + route, data=data, headers=headers)
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=180) as response:
            return json.load(response)


def multipart(values, files):
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in values.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    for key, filename, content_type, data in files:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode() + data + b"\r\n")
    return b"".join(parts) + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--corpus", type=Path, default=ROOT.parent / "datasets/br")
    parser.add_argument("--name", default="common-voice-faire-connaissance-pilote")
    parser.add_argument("--theme", default="faire-connaissance")
    parser.add_argument("--api", default="http://127.0.0.1:8100")
    parser.add_argument("--email", help="Compte administrateur local ; mot de passe demandé sans affichage.")
    parser.add_argument("--apply", action="store_true", help="Importer ; sinon préparer et vérifier seulement.")
    args = parser.parse_args()
    if not args.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.name):
        raise ValueError("Nom du lot : lettres minuscules, chiffres, tirets et underscores uniquement.")
    api = API(args.api, os.getenv("KELTIAWAVE_ADMIN_TOKEN", ""))
    items, provenance = prepare(args.csv, args.corpus, args.name, args.theme)
    out = ROOT / "backend/generated" / args.name
    out.mkdir(parents=True, exist_ok=True)
    # Keep every original field: current API has no columns for English, intent or rights.
    (out / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "metadata.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Vérifié : {len({r['texte'] for r in items})} phrases, {len(items)} audios ; thème {args.theme}.")
    print(f"Métadonnées et provenance : {out}")
    if not args.apply:
        print("Aucun import effectué. Ajouter --apply pour charger le lot.")
        return
    if not api.token:
        email = args.email or input("Email administrateur local : ").strip()
        password = getpass.getpass("Mot de passe : ")
        api.token = api.call("/api/auth/login", json.dumps({"email": email, "password": password}).encode())["access_token"]
    if api.call("/api/auth/me")["role"] != "admin":
        raise ValueError("Un compte administrateur est requis.")
    route = "/api/admin-data/segments?" + urllib.parse.urlencode({"dataset": args.name, "limit": 1000})
    existing = api.call(route)
    if len(existing) >= 1000:
        raise ValueError("Lot trop grand pour vérifier tous les doublons via cette API.")
    existing_names = {Path(r["filename"]).name for r in existing}
    # Skip existing audio completely: never reset an admin's approval or corrections.
    pending = [(item, prov) for item, prov in zip(items, provenance) if prov["storage_name"] not in existing_names]
    existing_phrases = {r["texte"]: r for r in api.call("/api/phrases/?langue=br")}
    for item, _ in pending:
        old = existing_phrases.get(item["texte"])
        if old and (old["source"] != args.name or old["theme"] != args.theme):
            raise ValueError(f"Phrase déjà présente dans un autre lot/thème : {item['texte']}. Aucun import effectué.")
        if old:
            # Existing importer updates these fields: preserve manual corrections.
            for target, source in (("traduction_fr", "traduction_fr"), ("niveau", "niveau"), ("auteur", "auteur")):
                item[target] = old.get(source)
    if pending:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as bundle:
            for item, _ in pending:
                bundle.write(args.corpus / "clips" / item["audio_path"], "audios/" + item["audio_path"])
        body, content_type = multipart({"name": args.name, "source": args.name, "initial_status": "pending", "audio_root": "audios", "langue": "br"}, [
            ("metadata", "metadata.json", "application/json", json.dumps([r for r, _ in pending], ensure_ascii=False).encode()),
            ("audio_archive", "audios.zip", "application/zip", archive.getvalue())])
        result = api.call("/api/admin-data/datasets/import", body, content_type)
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("Tous les audios sont déjà présents ; aucune modification.")
    after = api.call(route)
    mapping = {Path(r["filename"]).name: r for r in after}
    for prov in provenance:
        segment = mapping.get(prov["storage_name"])
        if not segment:
            raise ValueError("Import incomplet : relancer le script pour reprendre.")
        prov["local_segment"] = segment
    (out / "import-result.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Import vérifié : {len(provenance)} audios. Admin : http://127.0.0.1:4200/admin")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, urllib.error.URLError) as exc:
        raise SystemExit(f"Erreur : {exc}") from exc
