"""The whole booking flow, end to end: a policy question, the schedule, a confirmation, then the booking.

    uv run python -m labs.booking_flow
"""
import re

import httpx

from labs.helpers import API

PHONE = "01098765432"
STEPS = [
    "Do you take Allianz cards?",
    "Is the dermatologist free on Sunday?",
    f"Please book 19:00 for me. My name is Lab Patient, phone {PHONE}.",
    "yes",
]


def check(name: str, ok: bool) -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    return ok


if __name__ == "__main__":
    results, conversation_id = [], None
    with httpx.Client(base_url=API, timeout=900) as client:
        replies = []
        for message in STEPS:
            body = client.post("/chat", json={"conversation_id": conversation_id, "message": message}).json()
            conversation_id = body["conversation_id"]
            replies.append(body)
            print(f"You:   {message}\nAgent: {body['reply']}\n       tools: {', '.join(body['tools_used'])}\n")

        policy, schedule, booking, confirmed = replies
        results.append(check("1. searched the clinic's documents", "search_clinic_docs" in policy["tools_used"]))
        results.append(check("1. the answer mentions Allianz", "Allianz" in policy["reply"]))
        results.append(check("2. looked at the schedule", "check_availability" in schedule["tools_used"]))
        results.append(check("3. asked for a yes before booking", booking["waiting_for_confirmation"]))
        results.append(check("3. the confirmation shows 19:00", "19:00" in booking["reply"]))
        results.append(check("4. booked after the yes", "book_appointment" in confirmed["tools_used"]))
        found = re.search(r"NFC-[0-9A-F]{6}", confirmed["reply"])
        booked = found and client.get(f"/appointments/{found.group()}", headers={"X-Patient-Phone": PHONE})
        at_19 = bool(booked) and booked.json().get("time") == "19:00"
        results.append(check("4. the reference is real, at 19:00", at_19))
    print(f"\n{sum(results)} of {len(results)} checks passed")
