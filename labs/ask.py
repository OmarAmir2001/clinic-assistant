# labs/ask.py
"""Ask the running API's /search a question and print what it found.

    uv run python -m labs.ask "Do you take Allianz cards?"
"""
import sys

import httpx

from labs.helpers import API

if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    body = httpx.get(f"{API}/search", params={"q": question, "top_k": 3}, timeout=60).json()
    print(f"Q: {body['query']}")
    if not body["found"]:
        print(f"   found: false. {body['message']}")
    for hit in body["results"]:
        where = hit["section"] or f"page {hit['page']}"
        # The first line of real text, after the heading
        lines = [line for line in hit["text"].splitlines() if line.strip() and not line.startswith("#")]
        print(f"   {hit['score']:.3f}  {hit['document_name']} › {where}")
        print(f"          {lines[1 if len(lines) > 1 and lines[0].isupper() else 0][:72]}")
