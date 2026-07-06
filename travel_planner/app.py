import streamlit as st
import uuid

from config import (
    APP_TITLE, APP_ICON, APP_LAYOUT, SIDEBAR_TITLE, NEW_TRIP_LABEL,
    HOW_IT_WORKS, EXAMPLE_QUERIES, THREAD_ID_LEN,
    TRIP_STYLES, TRAVEL_GROUPS, BUDGETS, PACES, ACCOMMODATION_TYPES,
)
from graph import plan, resume, get_history
from logs import load_past_runs

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout=APP_LAYOUT)


# ── Session state helpers ─────────────────────────────────────────────────────

def trip_state(thread_id: str) -> dict:
    """Per-trip HITL state stored in st.session_state."""
    key = f"trip_state_{thread_id}"
    if key not in st.session_state:
        st.session_state[key] = {"stage": None, "data": None, "metrics": None}
    return st.session_state[key]

def set_trip_state(thread_id: str, **kwargs):
    s = trip_state(thread_id)
    s.update(kwargs)


# ── Metrics renderer ──────────────────────────────────────────────────────────

def render_metrics(traces, summary):
    with st.expander("📊 Run Metrics — Tokens · Latency · Cost · Searches", expanded=False):
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Tokens",  f"{summary['total_tokens']:,}")
        m2.metric("Prompt Tokens", f"{summary['prompt_tokens']:,}")
        m3.metric("Output Tokens", f"{summary['completion_tokens']:,}")
        m4.metric("Est. Cost",     f"${summary['total_cost_usd']:.5f}")
        m5.metric("Total Latency", f"{summary['total_latency_ms'] / 1000:.1f}s")
        st.divider()
        st.markdown("**Per-Agent Breakdown**")
        st.table([
            {
                "Agent":           t.agent,
                "Latency (ms)":    f"{t.latency_ms:.0f}",
                "Prompt Tokens":   t.prompt_tokens,
                "Output Tokens":   t.completion_tokens,
                "Total Tokens":    t.total_tokens,
                "Tavily Searches": t.search_calls,
                "Est. Cost ($)":   f"{t.cost_usd:.6f}",
            }
            for t in traces
        ])
        st.caption(
            "⚠️ Estimates based on DeepSeek-V3.2 pricing "
            "(input $0.27/M · output $1.10/M). Actual Azure billing may differ."
        )


# ── HITL checkpoint renderers ─────────────────────────────────────────────────

def render_supervisor_review(thread_id: str, data: dict):
    """Checkpoint 1 — user confirms/edits destination, duration, interests."""
    st.info("✋ **Checkpoint 1 of 3** — Review what the supervisor extracted from your query.")

    with st.form("supervisor_form"):
        st.markdown("#### 🧠 Supervisor Extracted")
        col1, col2 = st.columns(2)
        with col1:
            destination = st.text_input("Destination",  value=data.get("destination", ""))
            duration    = st.text_input("Duration",      value=data.get("duration",    ""))
        with col2:
            interests = st.text_input(
                "Interests / Focus areas",
                value=data.get("interests", ""),
                help="Comma-separated list of themes, e.g. food, history, nature",
            )

        submitted = st.form_submit_button("✅ Confirm & Search Places →", type="primary", use_container_width=True)

    if submitted:
        with st.spinner("🔍 Searching places, attractions & dining…"):
            status = resume(thread_id, {
                "destination": destination,
                "duration":    duration,
                "interests":   interests,
            })
        set_trip_state(thread_id, stage=status["stage"], data=status.get("data"))
        st.rerun()


def render_places_review(thread_id: str, data: dict):
    """Checkpoint 2 — user selects which place categories to include."""
    st.info("✋ **Checkpoint 2 of 3** — Choose what to include in your itinerary.")

    places_found = data.get("places_found", "")

    # Split into sections by ### heading
    sections: dict[str, str] = {}
    current_title = None
    current_lines = []
    for line in places_found.splitlines():
        if line.startswith("### "):
            if current_title:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title:
        sections[current_title] = "\n".join(current_lines).strip()

    st.markdown("#### 🗺️ Places Found — toggle sections to include/exclude")

    included_sections = []
    for title, content in sections.items():
        with st.expander(title, expanded=True):
            include = st.checkbox(f"Include this section", value=True, key=f"chk_{title}")
            st.markdown(content)
            if include:
                included_sections.append(f"### {title}\n{content}")

    st.divider()
    extra_prefs = st.text_area(
        "📝 Any extra preferences or places to exclude?",
        placeholder="e.g. Skip sushi restaurants, prefer smaller museums, avoid tourist traps…",
        height=80,
    )

    if st.button("✅ Confirm Places & Build Itinerary →", type="primary", use_container_width=True):
        selected = "\n\n".join(included_sections)
        if extra_prefs.strip():
            selected += f"\n\n📝 User preferences:\n{extra_prefs.strip()}"
        with st.spinner("📅 Building your day-by-day itinerary…"):
            status = resume(thread_id, {"selected_places": selected})
        set_trip_state(thread_id, stage=status["stage"], data=status.get("data"))
        st.rerun()


def render_itinerary_review(thread_id: str, data: dict):
    """Checkpoint 3 — user reviews the itinerary and optionally adds revision notes."""
    st.info("✋ **Checkpoint 3 of 3** — Review your itinerary before we add tips and polish it.")

    itinerary = data.get("itinerary", "")

    with st.expander("📅 Your Draft Itinerary", expanded=True):
        st.markdown(itinerary)

    st.divider()

    col1, col2 = st.columns([3, 1])
    with col1:
        feedback = st.text_area(
            "✏️ Revision note (optional)",
            placeholder=(
                "e.g. Swap Day 2 and Day 3, make Day 1 more relaxed, "
                "add more food stops on Day 3…"
            ),
            height=90,
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        approve = st.button("✅ Approve & Finalise →", type="primary", use_container_width=True)
        skip    = st.button("⏩ Approve as-is",         use_container_width=True)

    if approve or skip:
        note = feedback.strip() if approve else ""
        with st.spinner("💡 Fetching tips & polishing your travel guide…"):
            status = resume(thread_id, {"feedback": note})
        if status["stage"] == "done":
            set_trip_state(
                thread_id,
                stage="done",
                data=None,
                metrics={"traces": status["traces"], "summary": status["summary"]},
            )
            st.session_state.trips[thread_id] = (
                st.session_state.get(f"pending_query_{thread_id}", "Trip")[:35] + "…"
            )
        st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header(SIDEBAR_TITLE)

    if "trips" not in st.session_state:
        st.session_state.trips = {}
    if "active_trip" not in st.session_state:
        st.session_state.active_trip = None

    if st.button(NEW_TRIP_LABEL, use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())[:THREAD_ID_LEN]
        st.session_state.trips[new_id] = f"Trip {len(st.session_state.trips) + 1}"
        st.session_state.active_trip   = new_id
        st.session_state.pop("query_prefill", None)
        st.rerun()

    st.divider()
    for tid, label in st.session_state.trips.items():
        ts = trip_state(tid)
        stage = ts.get("stage")
        badge = {"supervisor_review": " 🟡", "places_review": " 🟡", "itinerary_review": " 🟡", "done": " ✅"}.get(stage, "")
        prefix = "▶  " if tid == st.session_state.active_trip else "   "
        if st.button(f"{prefix}{label}{badge}", key=f"trip_{tid}", use_container_width=True):
            st.session_state.active_trip = tid
            st.rerun()

    if st.session_state.trips:
        st.divider()
        st.caption(f"Thread: `{st.session_state.active_trip}`")

    st.divider()
    st.markdown("### How it works")
    st.markdown(HOW_IT_WORKS)


# ── Tabs ──────────────────────────────────────────────────────────────────────

st.title(f"{APP_ICON} {APP_TITLE}")
tab_plan, tab_history = st.tabs(["✈️  Plan a Trip", "📋  Run History"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Plan a Trip
# ═══════════════════════════════════════════════════════════════════════════════

with tab_plan:
    if st.session_state.active_trip is None:
        st.info("👈 Click **➕ Plan a New Trip** in the sidebar to begin.")
        st.stop()

    thread_id = st.session_state.active_trip
    ts = trip_state(thread_id)
    stage = ts.get("stage")

    # ── HITL checkpoint: supervisor review ────────────────────────────────────
    if stage == "supervisor_review":
        st.caption("Tell us where you want to go — our AI agents handle the rest.")
        render_supervisor_review(thread_id, ts["data"])
        st.stop()

    # ── HITL checkpoint: places review ───────────────────────────────────────
    if stage == "places_review":
        st.caption("Tell us where you want to go — our AI agents handle the rest.")
        render_places_review(thread_id, ts["data"])
        st.stop()

    # ── HITL checkpoint: itinerary review ────────────────────────────────────
    if stage == "itinerary_review":
        st.caption("Tell us where you want to go — our AI agents handle the rest.")
        render_itinerary_review(thread_id, ts["data"])
        st.stop()

    # ── Done — show the final plan ────────────────────────────────────────────
    if stage == "done":
        history = get_history(thread_id)
        for msg in history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            elif msg["role"] == "assistant" and msg is history[-1]:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
        metrics = ts.get("metrics")
        if metrics:
            render_metrics(metrics["traces"], metrics["summary"])
        st.stop()

    # ── Initial form (no stage yet) ───────────────────────────────────────────
    st.caption("Tell us where you want to go — our AI agents handle the rest.")

    st.subheader("🎯 Customise Your Trip")
    col1, col2 = st.columns(2)
    with col1:
        trip_style   = st.selectbox("Trip style",       TRIP_STYLES,             help="What kind of experience?")
        travel_group = st.selectbox("Travelling as",    TRAVEL_GROUPS,           help="Who are you going with?")
        budget       = st.selectbox("Budget level",     BUDGETS,      index=1,   help="Shapes hotel tier, restaurants & activities.")
    with col2:
        pace          = st.selectbox("Trip pace",          PACES,        index=1, help="How much to pack into each day?")
        accommodation = st.selectbox("Accommodation type", ACCOMMODATION_TYPES,   help="Where would you prefer to stay?")

    st.divider()

    st.subheader("📍 Where do you want to go?")
    st.caption("Click an example or type your own.")

    prefill = st.session_state.get("query_prefill", "")
    ex_cols = st.columns(len(EXAMPLE_QUERIES))
    for col, ex in zip(ex_cols, EXAMPLE_QUERIES):
        if col.button(ex, use_container_width=True):
            st.session_state["query_prefill"] = ex
            st.rerun()

    user_query = st.text_input(
        label="query",
        value=prefill,
        placeholder="e.g. 5 days in Tokyo, Weekend in Barcelona…",
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("✈️  Start Planning", type="primary", use_container_width=True):
        if not user_query.strip():
            st.warning("Please enter a destination or trip query first.")
            st.stop()

        # Save the query label for the sidebar
        st.session_state[f"pending_query_{thread_id}"] = user_query

        with st.spinner("🧠 Supervisor is analysing your query…"):
            status = plan(
                user_query=user_query,
                thread_id=thread_id,
                trip_style=trip_style,
                travel_group=travel_group,
                budget=budget,
                pace=pace,
                accommodation=accommodation,
            )

        set_trip_state(thread_id, stage=status["stage"], data=status.get("data"))
        st.session_state["query_prefill"] = ""
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Run History
# ═══════════════════════════════════════════════════════════════════════════════

with tab_history:
    st.subheader("📋 Past Runs")

    if st.button("🔄 Refresh"):
        st.rerun()

    past_runs = load_past_runs(limit=100)

    if not past_runs:
        st.info("No runs logged yet. Complete a travel plan to see logs here.")
    else:
        overview = [
            {
                "Run ID":        r.get("run_id", "—"),
                "Timestamp":     r.get("timestamp", "")[:19].replace("T", " "),
                "Query":         r.get("query", "")[:55],
                "Total Tokens":  r.get("summary", {}).get("total_tokens", 0),
                "Searches":      r.get("summary", {}).get("total_searches", 0),
                "Latency (s)":   f"{r.get('summary', {}).get('total_latency_ms', 0) / 1000:.1f}",
                "Est. Cost ($)": f"{r.get('summary', {}).get('total_cost_usd', 0):.5f}",
            }
            for r in past_runs
        ]
        st.dataframe(overview, use_container_width=True)

        st.divider()
        st.markdown("**Drill into a run**")
        run_ids   = [r.get("run_id", "") for r in past_runs]
        chosen_id = st.selectbox("Select run", run_ids, label_visibility="collapsed")
        chosen    = next((r for r in past_runs if r.get("run_id") == chosen_id), None)

        if chosen:
            s = chosen.get("summary", {})
            st.markdown(
                f"**Query:** {chosen.get('query')}  \n"
                f"**Thread:** `{chosen.get('thread_id')}` | "
                f"**Timestamp:** {chosen.get('timestamp', '')[:19].replace('T', ' ')}"
            )
            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("Total Tokens",  f"{s.get('total_tokens', 0):,}")
            d2.metric("Prompt Tokens", f"{s.get('prompt_tokens', 0):,}")
            d3.metric("Output Tokens", f"{s.get('completion_tokens', 0):,}")
            d4.metric("Est. Cost",     f"${s.get('total_cost_usd', 0):.5f}")
            d5.metric("Latency",       f"{s.get('total_latency_ms', 0) / 1000:.1f}s")

            st.table([
                {
                    "Agent":           a["agent"],
                    "Latency (ms)":    f"{a['latency_ms']:.0f}",
                    "Prompt Tokens":   a["prompt_tokens"],
                    "Output Tokens":   a["completion_tokens"],
                    "Total Tokens":    a["total_tokens"],
                    "Tavily Searches": a["search_calls"],
                    "Cost ($)":        f"{a['cost_usd']:.6f}",
                }
                for a in chosen.get("agents", [])
            ])

        st.divider()
        st.caption("Logs stored at: `run_logs/traces.jsonl` · `run_logs/app.log`")
