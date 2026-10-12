#!/usr/bin/env python3
"""Send editorial CSV phrases through the existing REST API (dry-run by default)."""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

OPTIONAL_FIELDS = ('traduction_fr', 'source', 'source_url', 'langue', 'auteur')


class APIError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials or turn a redirected POST into a GET.


class API:
    def __init__(self, base, token=''):
        parsed = urlsplit(base)
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query
                or parsed.fragment or parsed.path not in ('', '/')
                or (parsed.scheme != 'https' and not (parsed.scheme == 'http'
                    and parsed.hostname in ('localhost', '127.0.0.1', '::1')))):
            raise ValueError('API URL : origine HTTPS requise (HTTP accepté uniquement en local).')
        self.url = base.rstrip('/') + '/api/phrases/'
        self.token = token
        self.opener = build_opener(NoRedirect())

    def request(self, payload=None):
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        request = Request(self.url, data=data, headers=headers, method='GET' if data is None else 'POST')
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            # Do not print response bodies: gateways may echo credentials or private data.
            raise APIError(f'HTTP {exc.code} (pas de nouvelle tentative automatique)') from None
        except (URLError, OSError, ValueError):
            raise APIError('Réponse indisponible ou invalide ; résultat serveur incertain après un POST. Vérifier avant de relancer.') from None

    def list_phrases(self):
        result = self.request()
        if not isinstance(result, list) or any(not isinstance(row, dict) or not isinstance(row.get('texte'), str)
                                              or row.get('langue') is not None and not isinstance(row['langue'], str)
                                              for row in result):
            raise APIError('GET phrases : format inattendu ; détection des doublons impossible.')
        return result

    def create_phrase(self, payload):
        return self.request(payload)


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(stream, dialect=dialect)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError('En-têtes CSV dupliqués.')
        missing = {'phrase_br', 'theme', 'niveau'} - set(headers)
        if missing:
            raise ValueError('Colonnes requises manquantes : ' + ', '.join(sorted(missing)))
        return [(index, row) for index, row in enumerate(reader, start=2)]


def payload_for(row):
    if None in row or any(value is None for value in row.values()):
        raise ValueError('Nombre de cellules différent des en-têtes.')
    text = row['phrase_br']
    if not text.strip():
        raise ValueError('phrase_br vide.')
    theme, level = row['theme'].strip(), row['niveau'].strip()
    if not theme:
        raise ValueError('theme obligatoire.')
    if level not in {'A1', 'A2', 'B1', 'B2', 'C1', 'C2'}:
        raise ValueError('niveau obligatoire : A1, A2, B1, B2, C1 ou C2.')
    payload = {'texte': text, 'theme': theme, 'niveau': level}
    payload.update({field: (row.get(field, '').strip() or None) for field in OPTIONAL_FIELDS})
    if payload['source'] == 'internet':
        url = payload['source_url'] or ''
        try:
            parsed = urlsplit(url)
            valid = (len(url) <= 2048 and re.match(r'^https?://[^/?#]', url, re.I)
                     and not re.search(r'[\\\s]', url) and parsed.hostname
                     and not re.search(r'[%<>"{}|^`]', parsed.hostname))
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('source=internet exige une URL HTTP(S) valide de 2048 caractères maximum.')
    else:
        payload['source_url'] = None
    # Explicit allowlist above: even url_audio, a PhraseCreate field, is never sent.
    return payload


def phrase_key(payload):
    return payload['texte'].strip().casefold(), (payload.get('langue') or '').strip().casefold()


def run(rows, api, *, apply=False, offline=False, limit=None, emit=print):
    stats = {'analysed': 0, 'created': 0, 'exists': 0, 'ignored': 0, 'errors': 0, 'planned': 0}
    emit('=== IMPORT (--apply) ===' if apply else '=== DRY-RUN : aucun POST ===')
    if apply and offline:
        raise ValueError('--offline est réservé au dry-run.')
    existing = set()
    if not offline:
        try:
            existing = {phrase_key(row) for row in api.list_phrases()}
        except APIError as exc:
            if apply:
                raise APIError(f'Import annulé avant tout POST : {exc}') from None
            emit(f'[WARN  ] {exc} Doublons serveur non vérifiés.')
    else:
        emit('[INFO  ] Hors ligne : seuls les doublons du CSV sont vérifiés.')
    seen = set()
    for number, row in rows[:limit]:
        stats['analysed'] += 1
        if not any(str(value or '').strip() for value in row.values()):
            stats['ignored'] += 1
            emit(f'[SKIP  ] ligne {number} vide')
            continue
        try:
            payload = payload_for(row)
            key = phrase_key(payload)
            label = json.dumps(payload['texte'], ensure_ascii=False)
            if key in existing:
                stats['exists'] += 1
                emit(f'[EXISTS] ligne {number} {label}')
                continue
            if key in seen:
                stats['ignored'] += 1
                emit(f'[SKIP  ] ligne {number} doublon CSV {label}')
                continue
            seen.add(key)
            if apply:
                api.create_phrase(payload)
                stats['created'] += 1
                existing.add(key)
                emit(f'[CREATE] ligne {number} {label}')
            else:
                stats['planned'] += 1
                emit(f'[CREATE] ligne {number} (simulation) {json.dumps(payload, ensure_ascii=False)}')
        except (ValueError, APIError) as exc:
            stats['errors'] += 1
            emit(f'[ERROR ] ligne {number} : {exc}')
    emit('\nPhrases analysées : {analysed}\nCréées : {created}\nDéjà existantes : {exists}\nIgnorées : {ignored}\nErreurs : {errors}'.format(**stats))
    if not apply:
        emit(f"Créations prévues : {stats['planned']}")
    return stats


def positive(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError('La limite doit être strictement positive.')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Simulation, comportement par défaut.')
    mode.add_argument('--apply', action='store_true', help='Autoriser les POST des nouvelles phrases.')
    parser.add_argument('--offline', action='store_true', help='Dry-run sans même effectuer de GET.')
    parser.add_argument('--limit', type=positive, help='Nombre maximal de lignes de données examinées.')
    args = parser.parse_args(argv)
    if args.apply and args.offline:
        parser.error('--offline ne peut pas être combiné avec --apply')
    try:
        rows = read_csv(args.csv)
        token = os.getenv('KELTIAWAVE_API_TOKEN', '')
        if args.apply and not token:
            raise ValueError('KELTIAWAVE_API_TOKEN requis pour --apply (enseignant ou administrateur).')
        api = API(os.getenv('KELTIAWAVE_API_URL', 'http://127.0.0.1:8100'), token)
        stats = run(rows, api, apply=args.apply, offline=args.offline, limit=args.limit)
        return 1 if stats['errors'] else 0
    except (OSError, UnicodeError, csv.Error, ValueError, APIError) as exc:
        print(f'[ERROR ] {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
