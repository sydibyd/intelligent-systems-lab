import http.client
import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from ci.evap_http import send

URL = 'http://backend:8000/api/ci-builds'

def response():
    return io.BytesIO(b'{"id": 42, "status": "RUNNING"}')

def error(code):
    return HTTPError(URL, code, 'test', {}, io.BytesIO(b''))

class ClientTests(unittest.TestCase):
    def run_request(self, effects, method='POST', url=URL):
        opener = Mock()
        opener.open.side_effect = effects
        delay = Mock()
        result = send(method, url, {'status': 'SUCCESS'}, opener=opener, sleep=delay)
        return result, opener, delay

    def test_nominal(self):
        result, opener, delay = self.run_request([response()])
        self.assertEqual(result['id'], 42)
        self.assertEqual(opener.open.call_count, 1)
        delay.assert_not_called()

    def test_transient_http(self):
        for code in (408, 429, 500, 502, 503, 504):
            with self.subTest(code=code):
                _, opener, delay = self.run_request([error(code), response()])
                self.assertEqual(opener.open.call_count, 2)
                delay.assert_called_once_with(1)

    def test_registration_response_lost(self):
        _, opener, _ = self.run_request([http.client.RemoteDisconnected(), response()])
        first, second = [c.args[0] for c in opener.open.call_args_list]
        self.assertEqual(first.data, second.data)
        self.assertEqual(first.full_url, second.full_url)

    def test_finalization_response_lost(self):
        _, opener, _ = self.run_request([http.client.RemoteDisconnected(), response()], 'PATCH', URL + '/42')
        self.assertEqual(opener.open.call_count, 2)
        self.assertEqual(opener.open.call_args.args[0].get_method(), 'PATCH')

    def test_network_failures(self):
        for exc in (URLError('network'), TimeoutError(), ConnectionResetError(), http.client.IncompleteRead(b'x')):
            with self.subTest(exc=type(exc).__name__):
                _, opener, _ = self.run_request([exc, response()])
                self.assertEqual(opener.open.call_count, 2)

    def test_permanent_http(self):
        for code in (302, 400, 401, 403, 404, 409, 422):
            with self.subTest(code=code):
                opener, delay = Mock(), Mock()
                opener.open.side_effect = error(code)
                with self.assertRaises(HTTPError):
                    send('POST', URL, {}, opener=opener, sleep=delay)
                self.assertEqual(opener.open.call_count, 1)
                delay.assert_not_called()

    def test_exhaustion(self):
        opener, delay = Mock(), Mock()
        opener.open.side_effect = [error(503), error(503), error(503)]
        with self.assertRaises(HTTPError):
            send('POST', URL, {}, opener=opener, sleep=delay)
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual([c.args[0] for c in delay.call_args_list], [1, 2])

    def test_invalid_json(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'not json')
        with self.assertRaises(json.JSONDecodeError):
            send('POST', URL, {}, opener=opener)
        self.assertEqual(opener.open.call_count, 1)

    def test_scope(self):
        opener = Mock()
        with self.assertRaises(ValueError):
            send('POST', 'http://backend:8000/api/campaigns', {}, opener=opener)
        opener.open.assert_not_called()

if __name__ == '__main__':
    unittest.main()
