import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.corpus.push_phrases import API, APIError, NoRedirect, main, payload_for, read_csv, run


ROW = {'phrase_br': 'Demat !', 'traduction_fr': 'Bonjour !', 'theme': 'vie-quotidienne',
       'niveau': 'A1', 'source': 'exemple', 'source_url': '', 'langue': 'br', 'auteur': 'Test'}


class PushPhrasesTests(unittest.TestCase):
    def csv_file(self, rows, delimiter=';'):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'phrases.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(ROW), delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def api(self, existing=None):
        api = Mock(spec=API)
        api.list_phrases.return_value = existing or []
        api.create_phrase.return_value = {'id': 1}
        return api

    def test_csv_utf8_bom_and_both_delimiters(self):
        for delimiter in [';', ',', '\t']:
            with self.subTest(delimiter=delimiter):
                self.assertEqual(read_csv(self.csv_file([ROW], delimiter)), [(2, ROW)])

    def test_mapping_preserves_original_text_and_ignores_audio(self):
        row = {**ROW, 'phrase_br': '  Demat !  ', 'best_reference_audio': '/absent/audio.mp3',
               'url_audio': 'https://example.org/track.mp3', 'up_votes': '12', 'audio_rights': 'TO_CHECK'}
        payload = payload_for(row)
        self.assertEqual(payload['texte'], '  Demat !  ')
        self.assertEqual(set(payload), {'texte', 'traduction_fr', 'theme', 'niveau', 'source', 'source_url', 'langue', 'auteur'})
        api = self.api()
        run([(2, row)], api, apply=True, emit=lambda _: None)
        api.create_phrase.assert_called_once_with(payload)
        self.assertEqual([c[0] for c in api.method_calls], ['list_phrases', 'create_phrase'])

    def test_dry_run_shows_json_without_post(self):
        api, output = self.api(), []
        stats = run([(2, ROW)], api, emit=output.append)
        api.create_phrase.assert_not_called()
        self.assertEqual(stats['created'], 0)
        self.assertEqual(stats['planned'], 1)
        self.assertIn('DRY-RUN', output[0])
        self.assertIn('"texte": "Demat !"', '\n'.join(output))

    def test_existing_normalized_phrase_skipped(self):
        api = self.api([{'texte': '  DEMAT ! ', 'langue': 'BR'}])
        output = []
        stats = run([(2, ROW)], api, apply=True, emit=output.append)
        api.create_phrase.assert_not_called()
        self.assertEqual(stats['exists'], 1)
        self.assertIn('[EXISTS]', '\n'.join(output))

    def test_language_is_part_of_key(self):
        api = self.api([{'texte': ROW['phrase_br'], 'langue': 'fr'}])
        stats = run([(2, ROW)], api, apply=True, emit=lambda _: None)
        self.assertEqual(stats['created'], 1)
        api.create_phrase.assert_called_once_with(payload_for(ROW))

    def test_csv_duplicates_are_not_posted_twice(self):
        api = self.api()
        stats = run([(2, ROW), (3, {**ROW, 'phrase_br': '  DEMAT !  '})], api, emit=lambda _: None)
        self.assertEqual((stats['planned'], stats['ignored']), (1, 1))

    def test_api_error_does_not_stop_next_line(self):
        api = self.api()
        api.create_phrase.side_effect = [APIError('HTTP 400'), {'id': 2}]
        stats = run([(2, ROW), (3, {**ROW, 'phrase_br': 'Trugarez !'})], api, apply=True, emit=lambda _: None)
        self.assertEqual((stats['errors'], stats['created']), (1, 1))

    def test_uncertain_post_not_retried_for_duplicate(self):
        api = self.api()
        api.create_phrase.side_effect = APIError('timeout')
        stats = run([(2, ROW), (3, ROW)], api, apply=True, emit=lambda _: None)
        self.assertEqual((stats['errors'], stats['ignored']), (1, 1))
        api.create_phrase.assert_called_once()

    def test_get_failure_blocks_apply(self):
        api = self.api()
        api.list_phrases.side_effect = APIError('HTTP 503')
        with self.assertRaises(APIError):
            run([(2, ROW)], api, apply=True, emit=lambda _: None)
        api.create_phrase.assert_not_called()

    def test_get_failure_allows_diagnostic_with_warning(self):
        api, output = self.api(), []
        api.list_phrases.side_effect = APIError('HTTP 503')
        stats = run([(2, ROW)], api, emit=output.append)
        self.assertEqual(stats['planned'], 1)
        self.assertIn('non vérifiés', '\n'.join(output))
        api.create_phrase.assert_not_called()

    def test_limit_counts_examined_rows(self):
        api = self.api()
        stats = run([(2, ROW), (3, ROW)], api, limit=1, apply=True, emit=lambda _: None)
        self.assertEqual(stats['analysed'], 1)
        api.create_phrase.assert_called_once()

    def test_offline_default_cli_never_requests_server(self):
        path = self.csv_file([ROW])
        with patch('scripts.corpus.push_phrases.API') as api, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(main([str(path), '--offline']), 0)
            api.return_value.list_phrases.assert_not_called()
            api.return_value.create_phrase.assert_not_called()

    def test_default_cli_with_token_still_never_posts(self):
        path = self.csv_file([ROW])
        with patch.dict(os.environ, {'KELTIAWAVE_API_TOKEN': 'mock-token'}), patch('scripts.corpus.push_phrases.API') as api, patch('sys.stdout', new_callable=io.StringIO):
            api.return_value.list_phrases.return_value = []
            self.assertEqual(main([str(path)]), 0)
            api.return_value.list_phrases.assert_called_once()
            api.return_value.create_phrase.assert_not_called()

    def test_invalid_row_does_not_stop_next_line(self):
        api = self.api()
        stats = run([(2, {**ROW, 'niveau': 'invalid'}), (3, ROW)], api, apply=True, emit=lambda _: None)
        self.assertEqual((stats['errors'], stats['created']), (1, 1))
        api.create_phrase.assert_called_once_with(payload_for(ROW))

    def test_missing_token_blocks_apply(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.stderr', new_callable=io.StringIO), patch('scripts.corpus.push_phrases.API') as api:
            self.assertEqual(main([str(self.csv_file([ROW])), '--apply']), 1)
            api.assert_not_called()

    def test_required_fields_and_provenance(self):
        invalid = [{'phrase_br': ' '}, {'theme': ''}, {'niveau': ''}, {'niveau': 'native'},
                   {'source': 'internet', 'source_url': ''}, {'source': 'internet', 'source_url': 'https://'},
                   {'source': 'internet', 'source_url': 'ftp://example.org'},
                   {'source': 'internet', 'source_url': 'https://example.org/' + 'a'*2048}]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                payload_for({**ROW, **fields})
        self.assertEqual(payload_for({**ROW, 'source': 'internet', 'source_url': ' https://example.org '})['source_url'], 'https://example.org')
        self.assertIsNone(payload_for({**ROW, 'source_url': 'ignored'})['source_url'])

    def test_missing_level_in_extract_theme_requires_enrichment(self):
        path = self.csv_file([ROW])
        path.write_text('phrase_br;theme;best_reference_audio\nDemat !;vie-quotidienne;audio.mp3\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'niveau'):
            read_csv(path)

    def test_transport_uses_only_expected_get_post_and_bearer(self):
        api = API('https://staging.example.org', 'test-token')
        response = Mock()
        response.__enter__ = Mock(return_value=io.BytesIO(b'[]'))
        response.__exit__ = Mock(return_value=False)
        api.opener = Mock()
        api.opener.open.return_value = response
        self.assertEqual(api.list_phrases(), [])
        get = api.opener.open.call_args.args[0]
        self.assertEqual((get.method, get.full_url), ('GET', 'https://staging.example.org/api/phrases/'))
        response.__enter__.return_value = io.BytesIO(b'{"id": 1}')
        api.create_phrase(payload_for(ROW))
        post = api.opener.open.call_args.args[0]
        self.assertEqual(post.method, 'POST')
        self.assertEqual(post.get_header('Authorization'), 'Bearer test-token')
        self.assertEqual(json.loads(post.data), payload_for(ROW))

    def test_redirect_and_insecure_remote_rejected(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example.org'))
        for url in ['http://example.org', 'https://user:secret@example.org', 'https://example.org/api', 'https://example.org?token=secret']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                API(url)


if __name__ == '__main__':
    unittest.main()
