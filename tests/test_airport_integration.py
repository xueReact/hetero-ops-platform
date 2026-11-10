"""Exercise the HTTP boundary without touching the running airport mission."""
import http.client
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from platform_app.http_server import PlatformHandler
from platform_app.routes.pages import resolve_static_path
from platform_app.routes.tasks import handle_feedback


class Upstream(BaseHTTPRequestHandler):
    received = None

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/stream/overview':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\nFRAME\r\n')
            self.wfile.flush()
            self.server.release.wait(3)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'path': self.path, 'ready': True}).encode())

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        type(self).received = (self.path, body)
        self.send_response(409)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"error":"mission already running"}')


class AirportIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        cls.upstream.release = threading.Event()
        cls.platform = ThreadingHTTPServer(('127.0.0.1', 0), PlatformHandler)
        cls.override = patch('platform_app.airport_gateway.AIRPORT_UPSTREAM',
                             f'http://127.0.0.1:{cls.upstream.server_port}')
        cls.override.start()
        for server in (cls.upstream, cls.platform):
            threading.Thread(target=server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.upstream.release.set()
        for server in (cls.platform, cls.upstream):
            server.shutdown()
            server.server_close()
        cls.override.stop()

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.platform.server_port, timeout=2)
        connection.request(method, path, body=body, headers={'Content-Type':'application/json'})
        response = connection.getresponse()
        status, payload = response.status, response.read()
        connection.close()
        return status, payload

    def test_feedback_includes_operation_feed(self):
        with patch('platform_app.routes.tasks.operation_feed', return_value=[{'id':'operation'}]), \
             patch('platform_app.routes.tasks.list_feedback', return_value=[{'id':'manual'}]):
            status, body = handle_feedback('GET')
        self.assertEqual(status, 200)
        self.assertEqual([item['id'] for item in body], ['operation','manual'])

    def test_console_deep_link_and_source_assets(self):
        status, body = self.request('GET','/airport-console')
        self.assertEqual(status, 200)
        self.assertIn(b'data-page="airport"', body)
        status, body = self.request('GET','/airport-console/view/')
        self.assertEqual(status, 200)
        self.assertIn(b'id="devices"', body)
        self.assertIsNone(resolve_static_path('/airport-console/view/../../portal.py'))
        self.assertIsNone(resolve_static_path('/../run.py'))

    def test_api_prefix_and_query_are_forwarded(self):
        status, body = self.request('GET','/airport-runtime/api/status?probe=1')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['path'],'/api/status?probe=1')

    def test_command_body_and_upstream_error_are_preserved(self):
        status, body = self.request('POST','/airport-runtime/api/mission', b'{"example":1}')
        self.assertEqual(status,409)
        self.assertEqual(Upstream.received,('/api/mission',b'{"example":1}'))
        self.assertEqual(json.loads(body)['error'],'mission already running')

    def test_only_airport_endpoints_are_forwarded(self):
        status, _ = self.request('GET','/airport-runtime/api/tasks')
        self.assertEqual(status,404)

    def test_stream_delivers_first_bytes_without_waiting_for_close(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.platform.server_port, timeout=1)
        connection.request('GET','/airport-runtime/stream/overview')
        response = connection.getresponse()
        self.assertIn('multipart/', response.getheader('Content-Type'))
        try:
            self.assertEqual(response.read(7), b'--frame')
        finally:
            self.upstream.release.set()
            connection.close()

    def test_disconnected_upstream_returns_json_error(self):
        with patch('platform_app.airport_gateway.AIRPORT_UPSTREAM','http://127.0.0.1:0'):
            status, body = self.request('GET','/airport-runtime/api/status')
        self.assertEqual(status,502)
        self.assertIn('error',json.loads(body))


if __name__ == '__main__':
    unittest.main()
