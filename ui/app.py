# ui/app.py
"""The clinic's chat page (Session 10). It talks to our API over HTTP, like any other client.

    uv run fastapi dev                            # the API, in one terminal
    uv run python -m streamlit run ui/app.py      # this page, in another: http://localhost:8501
"""
import html
import re

import streamlit as st
from pydantic_settings import BaseSettings, SettingsConfigDict

from ui.client import APIError, ClinicAPI

ARABIC = re.compile(r"[ء-ي]")
HELLO = ("Ask about prices, insurance, opening hours, doctors and free times, or book an appointment. "
         "In Arabic or English. | اسأل عن الأسعار والتأمين والمواعيد، أو احجز كشفًا.")


class UISettings(BaseSettings):
    """The page's own settings, from the same .env. It needs only the API's address."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    CLINIC_API_URL: str = "http://localhost:8000"
    UI_TIMEOUT_SECONDS: float = 120  # the most we wait between two events (the API pings every 15 s)


@st.cache_resource  # one client for the whole app, not a new one on every rerun
def get_api() -> ClinicAPI:
    settings = UISettings()
    return ClinicAPI(settings.CLINIC_API_URL, settings.UI_TIMEOUT_SECONDS)


def text_block(text: str, small: bool = False) -> None:
    """Show text exactly as it is: escaped, so it is never read as HTML or Markdown (it's not ours to trust).
    Arabic reads right to left."""
    safe = html.escape(text).replace("\n", "<br>")
    direction = "rtl" if ARABIC.search(text) else "ltr"
    if small:
        direction = "auto"  # a document can mix both: the first letter decides
    style = "font-size: 0.85em; color: gray;" if small else ""
    st.markdown(f'<div dir="{direction}" style="{style}">{safe}</div>', unsafe_allow_html=True)


def show(message: dict) -> None:
    """One message from the history, with everything the agent sent along with it."""
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.error(message["error"])
            return
        if message.get("changed"):
            result = message["changed"]
            st.success(f"Done · {result.get('reference', '')}")
        if message.get("confirm"):
            with st.container(border=True):  # the change, from our database: not the model's words
                st.markdown("**Please confirm | من فضلك أكّد**")
                for label, value in message["confirm"]:
                    st.markdown(f"**{html.escape(label)}:** {html.escape(value)}")
        else:
            text_block(message["text"])
        if message.get("sources"):
            with st.expander(f"Sources: what the assistant read ({len(message['sources'])})"):
                for source in message["sources"]:
                    st.markdown(f"**{html.escape(source['source'])}**")
                    text_block(source["text"][:500], small=True)


def send(text: str) -> None:
    """Send one message and show the agent's events as they arrive. Then save the reply in the history."""
    state = st.session_state
    state.history.append({"role": "user", "text": text})
    show(state.history[-1])
    reply = {"role": "assistant", "text": "", "sources": [], "confirm": None, "changed": None, "error": None}
    with st.chat_message("assistant"):
        steps = st.status("Sending…")  # loading: what the agent is doing now
        answer = st.empty()  # the answer, as it is written
        written = ""
        try:
            for event in get_api().chat(state.conversation_id, text):
                if event.kind == "status":
                    steps.update(label=event.data["text"])
                    steps.write(event.data["text"])
                elif event.kind == "token":
                    written += event.data["text"]
                    answer.markdown(html.escape(written) + " ▌")
                elif event.kind == "sources":
                    reply["sources"] += event.data["sources"]
                elif event.kind == "confirm":
                    reply["confirm"] = event.data["details"]
                elif event.kind == "changed":
                    reply["changed"] = event.data["result"]
                elif event.kind == "done":
                    reply["text"] = event.data["reply"]  # the whole reply: it replaces what we streamed
                    state.conversation_id = event.data["conversation_id"]
                    state.waiting = event.data["waiting_for_confirmation"]
                elif event.kind == "error":
                    reply["error"] = event.data["message"]
        except APIError as error:
            reply["error"] = error.message
        if not reply["text"] and not reply["error"]:  # the stream ended without "done"
            reply["error"] = "The answer was cut off. Please try again."
        steps.update(label="Failed" if reply["error"] else "Done", state="error" if reply["error"] else "complete")
    state.history.append(reply)
    st.rerun()  # draw the page again from the history: the reply, its card, its sources


# ===== The page. Streamlit runs this whole file again after every click or message =====

st.set_page_config(page_title="Nile Family Clinic", page_icon="🩺")
state = st.session_state
state.setdefault("history", [])  # the messages on screen (the agent's memory is in the database)
state.setdefault("conversation_id", None)
state.setdefault("waiting", False)  # True: the last reply asks the patient to confirm a change

api_up = get_api().health()
with st.sidebar:
    st.header("Nile Family Clinic")
    if api_up:
        st.success("Connected to the clinic's server")
    else:
        st.error("The clinic's server is not running. Start it with: uv run fastapi dev")
    if st.button("New conversation", width="stretch"):
        state.history, state.conversation_id, state.waiting = [], None, False
        st.rerun()

    st.divider()
    st.subheader("Clinic documents (staff)")
    upload = st.file_uploader("PDF, TXT or MD", type=["pdf", "txt", "md"])
    if upload and st.button("Upload", disabled=not api_up):
        with st.spinner(f"Reading {upload.name}…"):
            try:
                document = get_api().upload(upload.name, upload.getvalue())
                st.success(f"{document['name']}: {document['chunks']} chunks")
            except APIError as error:
                st.error(error.message)

st.title("🩺 Clinic assistant")
if not state.history:
    st.info(HELLO)  # the empty state: say what this page can do
for message in state.history:
    show(message)

if state.waiting:  # a change waits for the patient: one click instead of typing
    arabic = bool(ARABIC.search(state.history[-2]["text"]))  # answer in the language the patient wrote in
    yes, no = st.columns(2)
    if yes.button("Yes, go ahead | نعم", type="primary", width="stretch"):
        state.waiting = False
        send("نعم" if arabic else "yes")
    if no.button("No | لا", width="stretch"):
        state.waiting = False
        send("لا" if arabic else "no")

prompt = st.chat_input("Write your message…", max_chars=1000, disabled=not api_up, submit_mode="disable")
if prompt:
    state.waiting = False
    send(prompt)
