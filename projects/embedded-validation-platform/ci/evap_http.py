"""Bounded retries for EVAP build registration and finalization only."""
import argparse
import http.client
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

RETRYABLE = {408, 429, 500, 502, 503, 504}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send(method, url, payload, *, opener=None, sleep=time.sleep):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('Invalid EVAP endpoint')
    if not ((method == 'POST' and parts.path == '/api/ci-builds') or
            (method == 'PATCH' and re.fullmatch(r'/api/ci-builds/[1-9][0-9]*', parts.path))):
        raise ValueError('Only idempotent build lifecycle operations are supported')
    data = json.dumps(payload).encode('utf-8')
    opener = opener or build_opener(ProxyHandler({}), NoRedirect())
    token = os.getenv("EVAP_API_TOKEN")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        if parts.scheme != "https" and parts.hostname != "backend":
            raise ValueError("Authenticated requests require HTTPS or isolated backend")
        headers["Authorization"] = "Bearer " + token
    for attempt in range(1, 4):
        try:
            request = Request(url, data=data, method=method, headers=headers)
            with opener.open(request, timeout=15) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValueError('Response too large')
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError('Expected JSON object')
                return result
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if code not in RETRYABLE or attempt == 3:
                raise
            reason = f'HTTP {code}'
        except (URLError, TimeoutError, ConnectionError, http.client.RemoteDisconnected, http.client.IncompleteRead) as exc:
            if attempt == 3:
                raise
            reason = type(exc).__name__
        print(f'EVAP HTTP attempt {attempt}/3 failed: {reason}; retrying', file=sys.stderr)
        sleep(2 ** (attempt - 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('method', choices=['POST', 'PATCH'])
    parser.add_argument('url')
    parser.add_argument('request_file', type=Path)
    parser.add_argument('response_file', type=Path)
    args = parser.parse_args()
    tmp = None
    try:
        if args.request_file.resolve() == args.response_file.resolve():
            raise ValueError('Request and response paths must differ')
        args.response_file.unlink(missing_ok=True)
        payload = json.loads(args.request_file.read_text(encoding='utf-8'))
        if not isinstance(payload, dict):
            raise ValueError('Expected request JSON object')
        result = send(args.method, args.url, payload)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=args.response_file.parent, delete=False) as f:
            tmp = f.name
            json.dump(result, f, indent=2)
            f.write('\n')
        os.replace(tmp, args.response_file)
        return 0
    except Exception as exc:
        print(f'EVAP HTTP failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

if __name__ == '__main__':
    sys.exit(main())
