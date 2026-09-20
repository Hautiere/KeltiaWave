"""Prototype autonome : aucune connexion au backend, aucune publication."""
import argparse
import csv
import heapq
import json
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def normalize(text):
    text = unicodedata.normalize('NFC', text).lower()
    for apostrophe in ('’', '‘', 'ʼ', '`'):
        text = text.replace(apostrophe, "'")
    return ' '.join(''.join(
        ' ' if unicodedata.category(c).startswith('P') and c != "'" else c
        for c in text
    ).split())


def classify(score):
    for threshold, label in ((.98, 'EXACT'), (.85, 'VERY_CLOSE'), (.70, 'CLOSE')):
        if score >= threshold:
            return label
    return 'WEAK'


def read_corpus(folder, source):
    folder = Path(folder).resolve()
    clips = (folder / 'clips').resolve()
    with (folder / 'validated.tsv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        columns = [name for name in ('sentence', 'text', 'sentence_text')
                   if name in (reader.fieldnames or [])]
        if not columns:
            raise ValueError('Colonne sentence, text ou sentence_text manquante.')
        for index, row in enumerate(reader, 2):
            sentence = next((row.get(c) for c in columns if row.get(c, '').strip()), '')
            if not normalize(sentence):
                continue
            locale = row.get('locale') or 'br'
            if locale != 'br':
                continue
            filename = row.get('path') or ''
            audio = (clips / filename).resolve() if filename else None
            if audio and not audio.is_relative_to(clips):
                raise ValueError(f'Ligne {index} : chemin audio hors du dossier clips.')
            yield {
                'source': source, 'source_id': row.get('sentence_id') or f'validated.tsv:{index}',
                'sentence': sentence, 'normalized_sentence': normalize(sentence),
                'audio_filename': filename, 'reference_audio': str(audio) if audio else None,
                'audio_exists': bool(audio and audio.is_file()),
                'speaker': row.get('client_id'), 'variant': row.get('variant'), 'locale': locale,
                'license': None, 'source_url': None, 'audio_rights': 'TO_CHECK',
                'publication_audio': False,
            }


def search(intentions, records, top):
    if top < 1:
        raise ValueError('Le nombre de résultats doit être positif.')
    targets = [normalize(item['breton_candidate']) for item in intentions]
    heaps = [[] for _ in intentions]
    count = 0
    # Lecture en flux : seuls les meilleurs résultats restent en mémoire.
    for index, record in enumerate(records):
        count += 1
        for target, heap in zip(targets, heaps):
            score = SequenceMatcher(None, target, record['normalized_sentence'], autojunk=False).ratio()
            entry = (score, -index, record)
            if len(heap) < top:
                heapq.heappush(heap, entry)
            elif entry[:2] > heap[0][:2]:
                heapq.heapreplace(heap, entry)
    results = []
    for intention, heap in zip(intentions, heaps):
        matches = [{**record, 'score': score, 'match_type': classify(score)}
                   for score, _, record in sorted(heap, reverse=True)]
        results.append({**intention, 'language': 'br', 'theme': 'meeting_people',
                        'breton_status': 'candidate', 'translation_status': 'generated',
                        'level_status': 'proposed', 'publication_audio': False,
                        'audio_status': 'reference' if any(m['audio_exists'] for m in matches) else 'missing',
                        'matches': matches})
    return {'theme': 'meeting_people', 'corpus_rows': count, 'intentions': results}


def spreadsheet_text(value):
    # Les phrases d'un corpus externe peuvent être interprétées comme des formules.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def export(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stem = output / 'meeting_people_candidates'
    stem.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = ['id', 'level', 'french', 'english', 'breton_candidate', 'breton_status',
              'translation_status', 'level_status', 'rank', 'source', 'source_id', 'sentence',
              'score', 'match_type', 'reference_audio', 'audio_exists', 'audio_rights',
              'publication_audio', 'license', 'source_url']
    with stem.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for item in report['intentions']:
            for rank, match in enumerate(item['matches'] or [{}], 1):
                row = {**item, **match, 'rank': rank if match else ''}
                writer.writerow({key: spreadsheet_text(value) for key, value in row.items()})
    return stem


def main():
    parser = argparse.ArgumentParser(description='Essai autonome « Se rencontrer » : propositions à relire.')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true', help='Données artificielles, sans audio réel.')
    source.add_argument('--corpus', type=Path, help='Dossier Common Voice breton : validated.tsv et clips/.')
    parser.add_argument('--top', type=int, default=3)
    parser.add_argument('--output', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    if not 1 <= args.top <= 20:
        parser.error('--top doit être compris entre 1 et 20.')
    intentions = json.loads((ROOT / 'data/intentions.json').read_text(encoding='utf-8'))
    try:
        report = search(intentions, read_corpus(args.corpus or ROOT / 'data/demo',
                        'demo_synthetic' if args.demo else 'common_voice'), args.top)
        report['demo'] = args.demo
        stem = export(report, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Erreur : {error}\n')
    print('Se rencontrer — ' + ('DÉMONSTRATION ARTIFICIELLE' if args.demo else 'Common Voice'))
    print(f"{len(intentions)} intentions ; {report['corpus_rows']} lignes analysées")
    for label in ('EXACT', 'VERY_CLOSE', 'CLOSE', 'WEAK'):
        count = sum(bool(i['matches']) and i['matches'][0]['match_type'] == label for i in report['intentions'])
        print(f'{label} (meilleur résultat par intention) : {count}')
    print('Sans résultat :', sum(not i['matches'] for i in report['intentions']))
    print('Intentions avec un audio de référence :', sum(i['audio_status'] == 'reference' for i in report['intentions']))
    print('Phrases, traductions et niveaux à relire. Aucun audio publié.')
    print(f'Exports : {stem}.csv\n          {stem}.json')


if __name__ == '__main__':
    main()
