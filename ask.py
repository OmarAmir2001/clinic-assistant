import os
import time

from dotenv import load_dotenv
from openai import OpenAI

# Read the settings from the .env file
load_dotenv()

# One client for any OpenAI-compatible provider (Gemini, Ollama, ...)
client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY"),
)
MODEL = os.getenv("LLM_MODEL")


def ask(question, context=None):
    """Send one question to the LLM and print the answer, the tokens and the time."""
    messages = []

    if context is not None:
        messages.append({
            "role": "system",
            "content": "You are the assistant of Nile Family Clinic. "
                       "Answer only from the clinic information below. "
                       "If the answer is not there, say you don't know.\n\n"
                       + context,
        })

    messages.append({"role": "user", "content": question})

    start = time.time()
    response = client.chat.completions.create(model=MODEL, messages=messages)
    seconds = time.time() - start

    print("Answer:", response.choices[0].message.content)
    print("Tokens in:", response.usage.prompt_tokens,
          "| Tokens out:", response.usage.completion_tokens,
          "| Time:", round(seconds, 1), "seconds")
    print("-" * 60)


def main():
    question = "Is Dr. Mona Adel available on Thursday, and how much is the visit?"

    # Attempt 1: ask directly
    print("ATTEMPT 1: ask directly")
    ask(question)

    # Attempt 2: give it the clinic's document
    print("ATTEMPT 2: give it the clinic's document")
    with open("clinic_info.md", encoding="utf-8") as file:
        clinic_info = file.read()
    ask(question, context=clinic_info)

    # Attempt 3: give it everything (pretend the clinic has 200 documents)
    print("ATTEMPT 3: give it everything (200 documents)")
    all_documents = clinic_info * 200
    ask(question, context=all_documents)

    # Attempt 4: ask it to book
    print("ATTEMPT 4: ask it to book")
    booking = ("Please book me with Dr. Mona Adel this Thursday at 6 PM. "
               "My name is Ahmed Hassan and my phone is 01000000000.")
    ask(booking, context=clinic_info)


if __name__ == "__main__":
    main()
