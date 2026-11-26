# labs/silent_llm.py
"""A pretend LLM server that takes every question and never answers. What does our app do?

    uv run python -m labs.silent_llm

Then point the app at it in .env:  LLM_BASE_URL=http://127.0.0.1:8099/v1
"""
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Silent(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"{time.strftime('%H:%M:%S')}  a request arrived. Not answering.", flush=True)
        time.sleep(3600)  # an hour of silence

    def log_message(self, *args):
        pass  # no default log lines; ours above are enough


if __name__ == "__main__":
    print("A silent LLM server on http://127.0.0.1:8099 (Ctrl+C to stop)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8099), Silent).serve_forever()
