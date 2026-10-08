from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
import uuid

PORT = int(os.environ.get("PORT", "10000"))
SECRET = os.environ.get("RELAY_SECRET", "CHANGE_THIS_SECRET")

queue = []
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/next":
            self.send_json(404, {"error": "not_found"})
            return

        with lock:
            if queue:
                item = queue.pop(0)
                self.send_json(200, item)
            else:
                self.send_json(200, {"action": "NONE"})

    def do_POST(self):
        if self.path != "/webhook":
            self.send_json(404, {"error": "not_found"})
            return

        received_secret = self.headers.get("X-Relay-Secret", "")

        if received_secret != SECRET:
            self.send_json(401, {"error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))

            data["relay_id"] = str(uuid.uuid4())
            data["received_at"] = int(time.time())

            with lock:
                queue.append(data)

            self.send_json(200, {
                "ok": True,
                "relay_id": data["relay_id"]
            })

        except Exception as e:
            self.send_json(400, {
                "ok": False,
                "error": str(e)
            })

    def log_message(self, format, *args):
        print(format % args)


server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

print("MT5 Trading Relay running on port", PORT)

server.serve_forever()
