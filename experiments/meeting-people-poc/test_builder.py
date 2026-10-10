import csv
import json
import tempfile
import unittest
from pathlib import Path

from builder import ROOT, classify, export, normalize, read_corpus, search


class BuilderTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize('  C’H\u00c3Z ! '), "c'hãz")
        self.assertEqual(normalize('deskin\u0303'), 'deskiñ')
        self.assertEqual(normalize('Demat,dit.'), 'demat dit')

    def test_boundaries(self):
        for score, label in [(1, 'EXACT'), (.98, 'EXACT'), (.979, 'VERY_CLOSE'),
                             (.85, 'VERY_CLOSE'), (.70, 'CLOSE'), (.699, 'WEAK')]:
            self.assertEqual(classify(score), label)

    def test_tsv_aliases_missing_audio_and_original_text(self):
        for column in ('sentence', 'text', 'sentence_text'):
            with self.subTest(column=column), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                (folder / 'clips').mkdir()
                (folder / 'validated.tsv').write_text(f'{column}\tpath\nDemat !\tmissing.mp3\n', encoding='utf-8')
                row = list(read_corpus(folder, 'test'))[0]
                self.assertEqual(row['sentence'], 'Demat !')
                self.assertFalse(row['audio_exists'])
                (folder / 'clips/missing.mp3').touch()
                row = list(read_corpus(folder, 'test'))[0]
                self.assertTrue(row['audio_exists'])
                self.assertFalse(row['publication_audio'])
                self.assertEqual(row['audio_rights'], 'TO_CHECK')

    def test_unsafe_audio_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'validated.tsv').write_text('sentence\tpath\nDemat\t../../secret.mp3\n')
            with self.assertRaises(ValueError):
                list(read_corpus(folder, 'test'))

    def test_search_and_exports(self):
        intentions = json.loads((ROOT / 'data/intentions.json').read_text())
        report = search(intentions, read_corpus(ROOT / 'data/demo', 'demo_synthetic'), 3)
        self.assertEqual(len(report['intentions']), 16)
        first = report['intentions'][0]['matches'][0]
        self.assertEqual(first['score'], 1)
        self.assertEqual(first['source'], 'demo_synthetic')
        self.assertEqual(first['sentence'], 'Demat !')
        self.assertTrue(any(0 < m['score'] < 1 for m in report['intentions'][4]['matches']))
        for item in report['intentions']:
            self.assertEqual(len(item['matches']), 3)
            self.assertEqual(item['breton_status'], 'candidate')
        with tempfile.TemporaryDirectory() as tmp:
            stem = export(report, tmp)
            self.assertEqual(json.loads(stem.with_suffix('.json').read_text()), report)
            with stem.with_suffix('.csv').open(encoding='utf-8-sig') as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 48)

    def test_empty_corpus(self):
        report = search([{'breton_candidate': 'Demat'}], [], 3)
        self.assertEqual(report['intentions'][0]['matches'], [])
        self.assertEqual(report['intentions'][0]['audio_status'], 'missing')


if __name__ == '__main__':
    unittest.main()
