"""仅 loopback 的自签 CA/TLS Provider 替身；不使用用户凭据或外网。"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import subprocess
import threading
import time

from scripts.devops.controlled_api_https import TLSFixture
from scripts.devops.independent_review_protocol import canonical_json


def make_tls_site(tmp_path):
    """创建仅供本地测试的临时 TLS 服务工厂。"""
    cert, key = tmp_path / "test-ca.pem", tmp_path / "test-key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        capture_output=True,
        check=True,
    )

    @contextmanager
    def running(payload, mode="normal"):
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                calls.append((self.path, json.loads(raw), self.headers.get("Authorization")))
                if mode == "timeout":
                    time.sleep(0.2)
                    return
                if mode == "disconnect":
                    return
                body = canonical_json(payload)
                self.send_response(307 if mode == "redirect" else 200)
                self.send_header("Location", "https://api.openai.com/v1/responses")
                self.send_header(
                    "Content-Length", str(len(body) + (50 if mode == "truncated" else 0))
                )
                self.end_headers()
                self.wfile.write(body)

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
            )
            thread.start()
            try:
                yield TLSFixture("127.0.0.1", server.server_port, cert), calls
            finally:
                server.shutdown()
                thread.join()

    return running
