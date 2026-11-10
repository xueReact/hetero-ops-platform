"""Same-origin HTTP gateway for airport telemetry, commands and MJPEG cameras.

This keeps the two services' /api namespaces separate and works when the browser
is on a different computer. The target is server configuration, never user input.
"""
import http.client
from urllib.parse import urlsplit

from platform_app.config import AIRPORT_UPSTREAM

PREFIX = "/airport-runtime"
READ_APIS = {"/api/status", "/api/report", "/api/trace"}
WRITE_APIS = {"/api/mission", "/api/physics", "/api/obstacle"}


def proxy_airport(handler):
    request = urlsplit(handler.path)
    path = request.path.removeprefix(PREFIX)
    allowed = (handler.command == "GET" and (
        path in READ_APIS or path.startswith(("/stream/", "/camera/", "/evidence/"))
    )) or (handler.command == "POST" and path in WRITE_APIS)
    if not allowed:
        return handler._send_json(404, {"error": "Airport endpoint not found"})
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        return handler._send_json(400, {"error": "Invalid Content-Length"})
    if length < 0 or length > 1_000_000:
        return handler._send_json(413, {"error": "Request body too large"})
    if handler.headers.get("Transfer-Encoding"):
        return handler._send_json(400, {"error": "Chunked requests are not supported"})
    target = urlsplit(AIRPORT_UPSTREAM)
    if target.scheme not in ("http", "https") or not target.hostname:
        return handler._send_json(503, {"error": "Invalid AIRPORT_UPSTREAM configuration"})
    connection_type = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
    connection = connection_type(target.hostname, target.port, timeout=30 if path.startswith("/stream/") else 12)
    sent_headers = False
    try:
        body = handler.rfile.read(length) if length else None
        headers = {"Accept-Encoding": "identity"}
        for name in ("Content-Type", "Range"):
            if handler.headers.get(name):
                headers[name] = handler.headers[name]
        # Concatenation preserves the configured host, including a // path.
        upstream_path = target.path.rstrip("/") + path
        if request.query:
            upstream_path += "?" + request.query
        connection.request(handler.command, upstream_path, body=body, headers=headers)
        response = connection.getresponse()
        handler.send_response(response.status)
        for name in ("Content-Type", "Content-Length", "Content-Disposition", "Content-Range", "Accept-Ranges"):
            value = response.getheader(name)
            if value is not None:
                handler.send_header(name, value)
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Accel-Buffering", "no")
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.close_connection = True
        sent_headers = True
        # read1 forwards available bytes immediately, rather than waiting for a
        # 64 KB buffer to fill. This is essential for a live multipart stream.
        while chunk := response.read1(64 * 1024):
            handler.wfile.write(chunk)
            handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        pass  # Navigating away closes an MJPEG connection normally.
    except (OSError, http.client.HTTPException):
        if not sent_headers:
            handler._send_json(502, {"error": "机场运行服务未连接，请启动机场服务后重试。"})
    finally:
        connection.close()
