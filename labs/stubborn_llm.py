# labs/stubborn_llm.py
"""A pretend LLM server that asks for a tool every time and never answers. Does our loop stop?

    uv run python -m labs.stubborn_llm

Then point the app at it in .env:  LLM_BASE_URL=http://127.0.0.1:8099/v1
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALL = {"name": "check_availability", "arguments": json.dumps({"doctor": "dermatology", "day": "sunday"})}


class Stubborn(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))  # the request: we don't even read it
        Stubborn.calls += 1
        print(f"{time.strftime('%H:%M:%S')}  call {Stubborn.calls}: asking for check_availability again", flush=True)
        message = {"role": "assistant", "content": "",
                   "tool_calls": [{"id": f"call_{Stubborn.calls}", "type": "function", "function": CALL}]}
        body = {"id": "stubborn", "object": "chat.completion", "created": int(time.time()), "model": "stubborn",
                "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 2000, "completion_tokens": 30, "total_tokens": 2030}}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # no default log lines; ours above are enough


if __name__ == "__main__":
    print("A stubborn LLM server on http://127.0.0.1:8099 (Ctrl+C to stop)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8099), Stubborn).serve_forever()
