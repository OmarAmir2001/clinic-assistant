# labs/answer_check.py
"""Check /answer on questions we know: it must answer, citing the right document, or say "I don't know".

    uv run python -m labs.answer_check
"""
import httpx

from labs.helpers import API

# (question, the document the answer must come from) or (question, None) for "must say I don't know"
CHECKS = [
    ("Do you take Allianz cards?", "insurance_and_policies.txt"),
    ("How much is a dermatology visit?", "services_and_prices.pdf"),
    ("Do I need to fast before a cholesterol test?", "lab_tests.md|prep_guidelines.md"),
    ("When does Dr. Omar Nabil work?", "doctors_bios.md"),
    ("بكام كشف الجلدية؟", "services_and_prices.pdf"),
    ("لازم أصوم قبل تحليل السكر؟", "lab_tests.md|prep_guidelines.md"),
    ("بتقبلوا تأمين ميتلايف؟", "insurance_and_policies.txt"),
    ("العيادة عنوانها إيه؟", "visiting_info.md"),
    # Search finds something close, but the answer isn't in it
    ("How much is teeth whitening?", None),
    ("Does Dr. Omar Nabil do dental implants?", None),
    # Nothing about it in the clinic's documents at all
    ("Do you do LASIK eye surgery?", None),
    ("عندكم دكتور عيون؟", None),
    ("What will the weather be in Cairo tomorrow?", None),
    ("بكام تذكرة القطر لإسكندرية؟", None),
]


def passed(body: dict, expected: str | None) -> bool:
    if expected is None:
        return not body["answered"]
    cited = {source["document_name"] for source in body["sources"]}
    return body["answered"] and bool(cited & set(expected.split("|")))


if __name__ == "__main__":
    good = 0
    with httpx.Client(base_url=API, timeout=600) as client:
        for question, expected in CHECKS:
            body = client.post("/answer", json={"question": question}).json()
            ok = passed(body, expected)
            good += ok
            cited = ", ".join(sorted({s["document_name"] for s in body["sources"]})) or "-"
            print(f"{'PASS' if ok else 'FAIL'}  answered={body['answered']!s:<5}  {question[:44]:<44}  {cited}")
    print(f"\n{good} of {len(CHECKS)} passed")
