# app.py
import os
import json
import time
import uuid
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st

from services.voice import tts_gtts, transcribe_audio_bytes
from services.db import init_db, insert_message, upsert_user, log_event  # keep db.py as you sent
from services.router import deep_link_for_intent
from services.llm import chat_complete
from services.rag import VectorStore, pdf_to_chunks, rag_answer
from services.intent import detect_lang, rule_intent
from services.recommender import load_jobs_csv, make_recs
from services.utils import init_session

# ---------- App Config ----------
st.set_page_config(page_title="PGRKAM AI Assistant", page_icon="🌐", layout="wide")

# ---------- Init DB / Session ----------
init_db()
init_session()

# ---------- Secrets / env ----------
if "GROQ_API_KEY" not in os.environ and "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
if "MODEL_NAME" in st.secrets:
    os.environ["MODEL_NAME"] = st.secrets["MODEL_NAME"]

# ---------- Simple account store (JSON file) ----------
ACCOUNTS_PATH = Path("users.json")

def _load_accounts() -> dict:
    if ACCOUNTS_PATH.exists():
        try:
            return json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_accounts(data: dict):
    ACCOUNTS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def _user_id_from_email(email: str) -> str:
    return f"user-{hashlib.md5(email.encode()).hexdigest()[:10]}"

def ensure_session_user():
    """Ensure an anonymous key exists (used before login)."""
    if "user_key" not in st.session_state or not st.session_state.get("user_key"):
        st.session_state.user_key = f"anon-{uuid.uuid4().hex[:12]}"

def set_logged_in(user_id: str, email: str, name: str = ""):
    st.session_state.auth_user = {"user_id": user_id, "email": email, "name": name or email.split("@")[0]}
    st.session_state.user_key = user_id  # tie all logs/messages to this user_id
    log_event(user_id, "auth_login", 1.0, json.dumps({"email": email}))

def logout():
    if "auth_user" in st.session_state:
        log_event(st.session_state["auth_user"]["user_id"], "auth_logout", 1.0, "{}")
    st.session_state.pop("auth_user", None)
    ensure_session_user()
    st.rerun()

def _default_prefs():
    return {
        "roles": ["clerk", "web developer"],
        "sectors": ["government", "private"],
        "locations": ["Chandigarh", "Ludhiana", "Mohali"],
        "degree": "B.Com",
        "experience": "0",
    }

def load_user_prefs():
    if "prefs" not in st.session_state:
        st.session_state.prefs = _default_prefs()

# --------------- Language guard ---------------
GREET_FIX = {"hi", "hello", "hey", "yo", "sup", "hai", "hola", "namaste", "sat sri akal"}

def safe_detect_lang(text: str) -> str:
    t = (text or "").strip().lower()
    # short greetings → English
    if t in GREET_FIX or len(t) <= 2:
        return "en"
    try:
        code = detect_lang(text)
        # accept only pa/hi/en; default to en otherwise
        if code not in {"pa", "hi", "en"}:
            return "en"
        return code
    except Exception:
        return "en"

# ---------- Auth UI ----------
def render_auth():
    st.title("🌐 PGRKAM AI Assistant")

    tab_login, tab_signup = st.tabs(["🔐 Log in", "🆕 Sign up"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                accounts = _load_accounts()
                entry = accounts.get(email)
                if not entry:
                    st.error("No account found. Please sign up first.")
                else:
                    if entry["pass_hash"] != _hash_password(password):
                        st.error("Incorrect password.")
                    else:
                        user_id = entry["user_id"]
                        name = entry.get("name") or email.split("@")[0]
                        # Ensure a row exists in DB users (db.py has minimal schema)
                        upsert_user(user_key=user_id)
                        set_logged_in(user_id, email, name)
                        st.success("Logged in successfully.")
                        st.rerun()

    with tab_signup:
        with st.form("signup_form", clear_on_submit=True):
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            if not (name and email and password and confirm):
                st.error("Please fill all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                accounts = _load_accounts()
                if email in accounts:
                    st.error("This email is already registered. Please log in.")
                else:
                    user_id = _user_id_from_email(email)
                    accounts[email] = {
                        "user_id": user_id,
                        "name": name,
                        "pass_hash": _hash_password(password),
                        "created_at": int(time.time()),
                    }
                    _save_accounts(accounts)
                    # Minimal users row in SQLite (compatible with your db.py)
                    upsert_user(user_key=user_id)
                    log_event(user_id, "auth_signup", 1.0, json.dumps({"email": email}))
                    set_logged_in(user_id, email, name)
                    st.success("Account created and logged in.")
                    st.rerun()

# ---------- Main App (after login) ----------
def render_app():
    st.title("🌐 PGRKAM AI Assistant")
    user = st.session_state.get("auth_user", {})
    st.caption(f"Welcome to PGRKAM AI Assistant (Prototype),  {user.get('name','User')}")

    # Initialize voice queue to keep audio after reruns
    if "voice_queue" not in st.session_state:
        st.session_state.voice_queue = []  # list of dicts: {"bytes": mp3bytes, "ts": int}

    # Logout & History controls
    left_sb, right_sb = st.sidebar.columns([0.55, 0.55])
    left_sb.button("🚪 Log out", use_container_width=True, on_click=logout)
    with right_sb:
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.pop("history", None)
            st.session_state.voice_queue = []
            st.success("Chat cleared.")
            st.rerun()

    # ---- Sidebar: Knowledge base upload (optional) ----
    st.sidebar.header("📚 Knowledge Base")
    uploaded = st.sidebar.file_uploader("Upload PDFs (FAQs, schemes, notices)", type=["pdf"], accept_multiple_files=True)

    # ---- Sidebar: Preferences (persist only if not empty) ----
    st.sidebar.header("🎯 Preferences")
    load_user_prefs()
    roles_in = st.sidebar.text_input("Preferred roles", value=", ".join(st.session_state.prefs.get("roles", [])))
    sectors_in = st.sidebar.text_input("Sectors", value=", ".join(st.session_state.prefs.get("sectors", [])))
    locations_in = st.sidebar.text_input("Locations", value=", ".join(st.session_state.prefs.get("locations", [])))
    degree_in = st.sidebar.text_input("Highest qualification", value=st.session_state.prefs.get("degree", ""))
    experience_in = st.sidebar.text_input("Experience (years)", value=st.session_state.prefs.get("experience", "0"))

    if st.sidebar.button("💾 Save Preferences"):
        roles = [r.strip() for r in roles_in.split(",") if r.strip()]
        sectors = [s.strip() for s in sectors_in.split(",") if s.strip()]
        locations = [l.strip() for l in locations_in.split(",") if l.strip()]
        degree = degree_in.strip()
        experience = experience_in.strip()

        # Validate not empty
        if not (roles and sectors and locations and degree and experience):
            st.sidebar.error("Please fill all preference fields (none can be empty).")
        else:
            st.session_state.prefs = {
                "roles": roles,
                "sectors": sectors,
                "locations": locations,
                "degree": degree,
                "experience": experience,
            }
            try:
                # db.py signature: upsert_user(user_key, lang="", district="", prefs_json="")
                upsert_user(
                    user_key=st.session_state.user_key,
                    prefs_json=json.dumps(st.session_state.prefs),
                )
                log_event(st.session_state.user_key, "prefs_saved", 1.0, json.dumps(st.session_state.prefs))
                st.sidebar.success("Preferences saved.")
            except Exception as e:
                st.sidebar.error(f"Failed to save preferences: {e}")

    # ---- Sidebar: Chat history preview ----
    st.sidebar.header("🗂️ Recent Chat")
    hist = st.session_state.get("history", [])
    if not hist:
        st.sidebar.info("No chats yet.")
    else:
        for role, msg in hist[-6:]:
            prefix = "👤" if role == "user" else "🤖"
            st.sidebar.write(f"{prefix} {msg[:60]}{'…' if len(msg) > 60 else ''}")

    # ---- Tabs
    tab_chat, tab_admin = st.tabs(["💬 Chat", "👤 Admin & Analytics"])

    # ----------------------- CHAT TAB -----------------------
    with tab_chat:
        col1, col2 = st.columns([0.62, 0.38])

        # Left: chat area
        with col1:
            st.subheader("Ask")

            # --- Pre-widget state adjustments (avoid StreamlitAPIException) ---
            # Clear after send:
            if st.session_state.get("_clear_chat"):
                st.session_state.chat_input = ""
                st.session_state._clear_chat = False
            # Prefill from ASR:
            if st.session_state.get("_prefill_text"):
                st.session_state.chat_input = st.session_state.pop("_prefill_text")

            from streamlit_mic_recorder import mic_recorder
            # FORM so ENTER submits
            with st.form("chat_form", clear_on_submit=False):
                cc1, cc2, cc3 = st.columns([0.15, 0.65, 0.20])

                with cc1:
                    audio = mic_recorder(
                        key="mic",
                        start_prompt="🎤",
                        stop_prompt="⏹",
                        just_once=True
                    )

                with cc2:
                    user_query = st.text_input(
                        "Ask here",
                        placeholder="Speak or type your question… (English / Punjabi / Hindi)",
                        label_visibility="collapsed",
                        key="chat_input"
                    )

                with cc3:
                    send = st.form_submit_button("➤", use_container_width=True)

            # If voice recorded → ASR → prefill textbox safely on next run
            if audio and "bytes" in audio:
                try:
                    transcribed_text = transcribe_audio_bytes(audio["bytes"], lang_hint="en")
                    if transcribed_text:
                        st.session_state._prefill_text = transcribed_text
                        st.rerun()
                except Exception as e:
                    st.warning(f"Voice transcription failed: {e}")

            # Toggle for RAG; voice reply is always ON per your request
            ask_rag = st.toggle("📚 Use Knowledge Base", value=True, help="If ON, answers cite your uploaded PDFs.")

            # Process send (works on Enter because it's a form)
            if send and st.session_state.chat_input.strip():
                query = st.session_state.chat_input.strip()
                lang = safe_detect_lang(query)
                intent = rule_intent(query)
                vs = st.session_state.get("vector_store") if ask_rag else None

                if vs is not None:
                    answer = rag_answer(vs, query, lang, chat_complete)
                else:
                    answer = chat_complete(
                        "You are a helpful assistant for the PGRKAM portal.",
                        f"User language: {lang}\nUser query: {query}\nAnswer briefly with steps if relevant."
                    )

                # persist messages
                insert_message(st.session_state.user_key, "user", query, intent=intent)
                insert_message(st.session_state.user_key, "assistant", answer, intent=intent)

                if "history" not in st.session_state:
                    st.session_state.history = []
                st.session_state.history.append(("user", query))
                st.session_state.history.append(("assistant", answer))

                log_event(st.session_state.user_key, "ask", 1.0, json.dumps({"intent": intent, "rag": ask_rag}))

                # ---- ALWAYS SPEAK REPLY (store bytes so they persist after rerun) ----
                try:
                    tts_bytes = tts_gtts(answer, lang_hint=lang)
                    if tts_bytes:
                        st.session_state.voice_queue.append({"bytes": tts_bytes, "ts": int(time.time())})
                except Exception as e:
                    st.warning(f"Voice reply issue: {e}")

                # Signal to clear input on next run (avoids StreamlitAPIException)
                st.session_state._clear_chat = True
                st.rerun()

            # Display history
            if "history" in st.session_state:
                for role, msg in st.session_state.history[-12:]:
                    if role == "user":
                        st.chat_message("user").write(msg)
                    else:
                        st.chat_message("assistant").write(msg)

            # Render latest voice reply player (persisted)
            if st.session_state.voice_queue:
                last = st.session_state.voice_queue[-1]
                st.audio(last["bytes"], format="audio/mp3")

        # Right: routing + recs
        with col2:
            st.subheader("🧭 Smart Routing")
            last_user = ""
            if "history" in st.session_state:
                last_user = next((m for r, m in reversed(st.session_state.history) if r == "user"), "")
            pred_intent = rule_intent(last_user) if last_user else "GeneralFAQ"
            st.metric("Intent", pred_intent, help="Predicted from your latest query.")
            st.link_button("Open Section", deep_link_for_intent(pred_intent))

            st.divider()
            st.subheader("🔎 Job Recommendations")
            jobs_path = "data/pgrkam_jobs.csv"  # keep if you have one; else handle exception
            try:
                df = load_jobs_csv(jobs_path)
                recs = make_recs(df, st.session_state.prefs, top_k=5)
                for _, row in recs.iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['title']}** — {row['location']} · {row['sector']}")
                        st.write(row["description"])
                        st.write(f"Deadline: {row['deadline']}")
                        st.link_button("View / Apply", row["url"])
            except Exception as e:
                st.info("Recommendations unavailable (no CSV found).")
                # st.error(f"Recommender error: {e}")

    # ----------------------- ADMIN TAB -----------------------
    with tab_admin:
        st.subheader("Admin • Upload & Analytics")
        st.caption("Restrict access or auth on this tab.")

        # Upload tracker
        if uploaded:
            st.info("Your uploaded PDFs will be re-indexed on 'Build/Update Index'.")
            try:
                rows = [{"file": f.name} for f in uploaded]
                st.dataframe(pd.DataFrame(rows))
            except Exception:
                pass

        # Basic analytics from DB
        try:
            import plotly.express as px
            from sqlalchemy import text as sqltext
            from services.db import engine

            with engine.begin() as con:
                intents = list(con.execute(sqltext("""
                    SELECT intent, COUNT(*) cnt
                    FROM messages
                    WHERE intent IS NOT NULL AND intent!=''
                    GROUP BY intent
                    ORDER BY cnt DESC
                """)))
                hourly = list(con.execute(sqltext("""
                    SELECT strftime('%Y-%m-%d %H:00', ts, 'unixepoch') h, COUNT(*) c
                    FROM messages
                    GROUP BY h
                    ORDER BY h
                """)))

            c1, c2 = st.columns(2)
            with c1:
                if intents:
                    df_int = pd.DataFrame(intents, columns=["intent","count"])
                    st.plotly_chart(px.bar(df_int, x="intent", y="count"), use_container_width=True)
                else:
                    st.info("No messages yet to chart intents.")
            with c2:
                if hourly:
                    df_h = pd.DataFrame(hourly, columns=["hour","count"])
                    st.plotly_chart(px.line(df_h, x="hour", y="count"), use_container_width=True)
                else:
                    st.info("No messages yet to chart over time.")
        except Exception as e:
            st.warning(f"Analytics unavailable: {e}")

# ---------- Entry Point ----------
if "auth_user" not in st.session_state:
    ensure_session_user()
    render_auth()
else:
    render_app()
