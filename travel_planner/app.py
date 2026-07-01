import streamlit as st
import uuid

from config import (
    APP_TITLE, APP_ICON, APP_LAYOUT, SIDEBAR_TITLE, NEW_TRIP_LABEL,
    HOW_IT_WORKS, EXAMPLE_QUERIES, THREAD_ID_LEN,
    TRIP_STYLES, TRAVEL_GROUPS, BUDGETS, PACES, ACCOMMODATION_TYPES,
)
from graph import plan, get_history
from logs import load_past_runs

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout=APP_LAYOUT)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
        rows = [
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
        ]
        st.table(rows)
        st.caption(
            "⚠️ Estimates based on DeepSeek-V3.2 pricing "
            "(input $0.27/M · output $1.10/M). Actual Azure billing may differ."
        )


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
        prefix = "▶  " if tid == st.session_state.active_trip else "   "
        if st.button(f"{prefix}{label}", key=f"trip_{tid}", use_container_width=True):
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
    st.caption("Tell us where you want to go — our AI agents handle the rest.")

    if st.session_state.active_trip is None:
        st.info("👈 Click **➕ Plan a New Trip** in the sidebar to begin.")
        st.stop()

    thread_id = st.session_state.active_trip

    # Show existing plan if thread already ran
    history = get_history(thread_id)
    if history:
        for msg in history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            elif msg["role"] == "assistant" and msg is history[-1]:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
        saved = st.session_state.get(f"metrics_{thread_id}")
        if saved:
            render_metrics(saved["traces"], saved["summary"])
        st.stop()

    # ── Preferences form ──────────────────────────────────────────────────────
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

    # ── Query input ───────────────────────────────────────────────────────────
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

    # ── Generate ──────────────────────────────────────────────────────────────
    if st.button("✈️  Generate My Travel Plan", type="primary", use_container_width=True):
        if not user_query.strip():
            st.warning("Please enter a destination or trip query first.")
            st.stop()

        with st.chat_message("user"):
            st.markdown(
                f"**{user_query}**  \n"
                f"_{trip_style} · {travel_group} · {budget} · {pace} · {accommodation}_"
            )

        with st.chat_message("assistant"):
            with st.status("Our agents are planning your trip…", expanded=True) as status:
                st.write("🧠 **Supervisor** — understanding your query & preferences…")
                st.write("🔍 **Places Agent** — searching attractions, food & hidden gems…")
                st.write("📅 **Itinerary Agent** — building your day-by-day plan…")
                st.write("💡 **Recommendations Agent** — visa, weather & safety tips…")
                st.write("✍️  **Formatter** — polishing your personalised travel guide…")

                result, traces, summary = plan(
                    user_query=user_query,
                    thread_id=thread_id,
                    trip_style=trip_style,
                    travel_group=travel_group,
                    budget=budget,
                    pace=pace,
                    accommodation=accommodation,
                )
                status.update(label="Your travel plan is ready! 🎉", state="complete")

            st.markdown(result)

        st.session_state[f"metrics_{thread_id}"] = {"traces": traces, "summary": summary}
        render_metrics(traces, summary)

        st.session_state.trips[thread_id] = user_query[:35] + ("…" if len(user_query) > 35 else "")
        st.session_state["query_prefill"] = ""
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Run History  (reads from run_logs/traces.jsonl)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_history:
    st.subheader("📋 Past Runs")

    col_refresh, col_info = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh"):
            st.rerun()

    past_runs = load_past_runs(limit=100)

    if not past_runs:
        st.info("No runs logged yet. Generate a travel plan to see logs here.")
    else:
        # Overview table
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

        # Drill-down
        st.markdown("**Drill into a run**")
        run_ids = [r.get("run_id", "") for r in past_runs]
        chosen_id = st.selectbox("Select run", run_ids, label_visibility="collapsed")
        chosen = next((r for r in past_runs if r.get("run_id") == chosen_id), None)

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

            agent_rows = [
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
            ]
            st.table(agent_rows)

        st.divider()
        st.caption(f"Logs stored at: `run_logs/traces.jsonl` · `run_logs/app.log`")
