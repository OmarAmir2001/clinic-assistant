# Capstone 1: Build It

At the end of Program 1, each pair shows its assistant working, one place where it fails, and two choices they can
defend. About 10 minutes per pair: 6 to show, 4 for questions.

Use the clinic's documents, or your own: upload them from the chat page's sidebar.

## What to show

### 1. Three flows that work (live, on the chat page)

| Flow | What we must see |
| --- | --- |
| A document question | The answer, and the source it came from (open "Sources") |
| A schedule question | Real free times, from the database |
| A booking that needs more than one tool | Free times → the confirmation card → "Yes" → a booking reference |

For one of the three, also say **what it cost**: how many model calls it made, the tokens in and out (the API log prints
`LLM call done: ... tokens in, ... tokens out` for every call), and the price. Use your model's current price per million
tokens from the provider's pricing page; on a free key the bill is zero, but the tokens are the same.

### 2. One failure, diagnosed

Find a message your assistant gets wrong. Then:

1. **The symptom:** what the patient saw.
2. **The trace:** `uv run python -m labs.trace <conversation_id>`. Read it from the top.
3. **The layer:** which one of the three below went wrong first. Point at the line in the trace that proves it.
4. **The fix:** what you changed (or would change), and the same message after the fix.

| Layer | The question | Where it shows in the trace |
| --- | --- | --- |
| Tool selection | Did the model call the right tool, with the right arguments? Or no tool at all? | The `model →` lines |
| Retrieval | Did the tool bring back the right information? | The `tool ←` lines |
| Generation (grounding) | Does the answer say what the tools returned, and nothing else? | The `Agent` line, next to the `tool ←` lines |

Check them in this order: it is the order they happen in. A wrong answer after a wrong tool call is a tool-selection
failure, even if the answer is also wrong.

### 3. Two engineering decisions, defended

For each one: the decision, the other options, why this one, and what it costs. Your RFC's decision records (AD-1 to
AD-6) are good places to start.

## How it is marked

| Part | Points |
| --- | --- |
| Three flows work live, including the multi-tool booking, and what one of them cost | 4 |
| The failure: symptom, trace, the right layer with evidence, a fix | 4 |
| Two decisions: options, reason and cost for each | 2 |

## Our example (the instructors' demo)

**The failure.** The patient asked in Arabic: «هل دكتور الأطفال فاضي يوم الاثنين؟» (is the pediatrician free on
Monday?). The assistant answered: «عذرًا، لا يوجد دكتور للأطفال متوفر يوم الاثنين» (no pediatrician is free on
Monday). It sounds right. It isn't: Dr. Karim Hassan had six free times that Monday.

**The trace:**

```text
Turn 2
  You       هل دكتور الأطفال فاضي يوم الاثنين؟
  model →   check_availability {"doctor": "儿科医生", "day": "monday"}
  tool ←    {"error": "No single doctor matches '儿科医生'. The doctors are: Dr. Mona Adel
            (dermatology); Dr. Karim Hassan (pediatrics); ..."}
  Agent     عذرًا، لا يوجد دكتور للأطفال متوفر يوم الاثنين. هل يمكنك التحقق من يوم آخر؟
```

**The layer: tool selection (the arguments).** The model translated "pediatrician" into Chinese. Then a second
failure, in generation: it read an error as "no free times". The first wrong line is the `model →` line.

**The fix.** The `doctor` field's description now says "in the patient's own words, Arabic or English, like
dermatology or أطفال", and the name matching drops the Arabic "ال" (so «الأطفال» matches «أطفال»). After the fix:

```text
  model →   check_availability {"doctor": "أطفال", "day": "monday"}
  tool ←    {"doctor": "Dr. Karim Hassan", "day": "2026-11-30", "weekday": "Monday", "free_times":
            ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]}
  Agent     دكتور الأطفال متاح يوم الاثنين في هذه الأوقات: 12:00، 13:00، 14:00، 15:00، 16:00، 17:00. ...
```

**Still open:** a model that reads a tool error as "not available" (the generation failure). That one is for you.
