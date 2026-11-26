# labs/answer.py
"""Ask the running API's /answer a question and print the answer, how long it took, and its sources.

    uv run python -m labs.answer "Do you take Allianz cards?"
"""
import sys
import time

import httpx

from labs.helpers import API

if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    start = time.perf_counter()
    response = httpx.post(f"{API}/answer", json={"question": question}, timeout=600)
    seconds = time.perf_counter() - start
    body = response.json()
    if response.status_code != 200:
        raise SystemExit(f"{response.status_code} after {seconds:.1f}s: {body['error']['message']}")

    print(f"Q: {question}   ({seconds:.1f}s)")
    print(f"A: {body['answer']}")
    print(f"   answered: {body['answered']}")
    for source in body["sources"]:
        where = source["section"] or (f"page {source['page']}" if source["page"] else "")
        print(f"   source: {source['document_name']} › {where}")
