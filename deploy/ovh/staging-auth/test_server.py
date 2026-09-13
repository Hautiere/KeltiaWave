"""Authentication regression tests; only dummy credentials are used."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('staging_auth', Path(__file__).with_name('server.py'))
auth = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, STAGING_AUTH_USERNAME='test', STAGING_AUTH_PASSWORD='test', STAGING_AUTH_COOKIE_SECRET='test'):
    spec.loader.exec_module(auth)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'DEPLOY_SLOT': 'staging',
            'STAGING_RECORD_TOKEN_SHA256': hashlib.sha256(b'test-only').hexdigest(),
            'STAGING_RECORD_TOKEN_EXPIRES_AT': str(int(time.time()) + 7200),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.headers = {'X-Forwarded-Host': auth.RECORD_HOST,
                        'X-Forwarded-Method': 'POST',
                        'X-Forwarded-Uri': '/api/record/transcribe',
                        'Authorization': 'Bearer test-only', 'Origin': 'https://localhost'}

    def request(self, path='/verify-record', headers=None):
        handler = object.__new__(auth.Handler)
        handler.path = path
        handler.headers = self.headers if headers is None else headers
        handler.wfile = io.BytesIO()
        response = {'headers': {}}
        handler.send_response = lambda status: response.update(status=status)
        handler.send_header = lambda key, value: response['headers'].update({key: value})
        handler.end_headers = lambda: None
        handler.do_GET()
        response['body'] = handler.wfile.getvalue()
        return response

    def test_allowed_endpoints(self):
        for path in auth.RECORD_PATHS:
            with self.subTest(path=path):
                self.headers['X-Forwarded-Uri'] = path
                self.assertEqual(self.request()['status'], 200)

    def test_scope_is_exact(self):
        for key, values in {
            'X-Forwarded-Host': ['record.keltiawave.com', 'transcribe.staging.keltiawave.com', 'record.staging.keltiawave.com.evil.test'],
            'X-Forwarded-Method': ['GET', 'OPTIONS', 'PUT'],
            'X-Forwarded-Uri': ['/', '/api/transcribe', '/api/record/transcribe/', '/api/record/transcribe?x=1'],
            'Authorization': ['', 'Bearer wrong', 'Basic test-only'],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    self.assertEqual(self.request(headers={**self.headers, key: value})['status'], 401)

    def test_disabled_expired_and_wrong_slot(self):
        for key, values in {
            'DEPLOY_SLOT': ['', 'production', 'candidate'],
            'STAGING_RECORD_TOKEN_EXPIRES_AT': ['', 'invalid', '0', str(int(time.time()) - 1)],
            'STAGING_RECORD_TOKEN_SHA256': ['', 'invalid'],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}):
                    self.assertEqual(self.request()['status'], 401)

    def test_unauthorized_cors_and_no_redirect(self):
        for origin in [*auth.MOBILE_ORIGINS, 'null', 'https://evil.test']:
            response = self.request(headers={**self.headers, 'Authorization': '', 'Origin': origin})
            self.assertEqual(response['status'], 401)
            self.assertNotIn('Location', response['headers'])
            self.assertEqual(response['headers'].get('Access-Control-Allow-Origin'), origin if origin in auth.MOBILE_ORIGINS else None)
            self.assertEqual(response['headers']['Cache-Control'], 'no-store')

    def test_token_never_unlocks_regular_staging(self):
        response = self.request('/verify')
        self.assertEqual(response['status'], 302)
        self.assertIn('/staging-login?', response['headers']['Location'])

    def test_cookie_binary_signature_roundtrip(self):
        expires = int(time.time()) + 3600
        for offset in range(100):
            self.assertTrue(auth.valid_token(auth.encode_token(expires + offset)))
        self.assertFalse(auth.valid_token('malformed'))
        self.assertFalse(auth.valid_token(auth.encode_token(1)))

    def test_existing_browser_session(self):
        token = auth.encode_token(int(time.time()) + 3600)
        headers = {**self.headers, 'Authorization': '', 'Cookie': f'{auth.COOKIE_NAME}={token}'}
        self.assertEqual(self.request(headers=headers)['status'], 200)
        self.assertEqual(self.request('/verify', headers=headers)['status'], 200)


if __name__ == '__main__':
    unittest.main()
