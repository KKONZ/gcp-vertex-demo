"""Streamlit frontend -- stands in for "the mobile app" (see docs/architecture.md
for why that's the right scope call here). Talks to the agent service only over
HTTP, never reads data files directly: in Kubernetes this runs in its own pod
with no shared filesystem.
"""

import os
import random

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")

CATEGORIES = [
    "Outerwear & Coats",
    "Jeans",
    "Dresses",
    "Sweaters",
    "Swim",
    "Tops & Tees",
    "Accessories",
]

st.set_page_config(page_title="gcp-vertex-demo", page_icon="🛍️")
st.title("Shopping assistant")
st.caption("Demo project -- not a real retailer. See docs/architecture.md for the design.")


@st.cache_data(ttl=60)
def fetch_personas() -> list[dict]:
    resp = requests.get(f"{AGENT_URL}/personas", timeout=10)
    resp.raise_for_status()
    return resp.json()


personas = fetch_personas()
if not personas:
    st.error(
        "No personas available -- run `python data/scripts/sample_personas.py` "
        "first, then restart the agent service."
    )
    st.stop()

if "persona" not in st.session_state:
    st.session_state.persona = random.choice(personas)

col1, col2 = st.columns([3, 1])
with col1:
    st.info(f"Shopping as: {st.session_state.persona['summary']}")
with col2:
    if st.button("New customer"):
        st.session_state.persona = random.choice(personas)
        st.rerun()

category = st.selectbox("Category", CATEGORIES)
message = st.text_area(
    "What's on your mind?",
    placeholder="I'm thinking about getting this wool coat, but I run cold -- will it work for me?",
)

if st.button("Ask", type="primary", disabled=not message.strip()):
    with st.spinner("Thinking..."):
        resp = requests.post(
            f"{AGENT_URL}/assess",
            json={
                "user_id": st.session_state.persona["user_id"],
                "category": category,
                "message": message,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

    st.subheader("Response")
    st.write(result["draft"])

    decision = result["decision"]
    st.subheader("Confidence")
    badge = {"low": "🔴", "medium": "🟡", "high": "🟢"}.get(decision["risk_category"], "⚪")
    st.metric("Keep confidence", f"{decision['keep_confidence_pct']}%")
    st.write(f"{badge} Risk category: **{decision['risk_category']}**")
    st.caption(decision["rationale"])

    with st.expander("Sources"):
        for source in result["sources"]:
            st.write(f"- {source}")
