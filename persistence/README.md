# LangGraph Persistence — Runnable Examples (Level 1 → 4)

No LLM / API key required — every node is a plain Python function so you can
run these immediately and see persistence behavior with your own eyes.

## Setup
```bash
pip install langgraph langgraph-checkpoint-sqlite
```

## Level 1 — In-memory checkpointer (`level1_inmemory.py`)
```bash
python3 level1_inmemory.py
```
Shows: same `thread_id` → state carries over between calls.
Different `thread_id` → totally isolated conversation.
Everything is in RAM — gone once the script exits.

## Level 2 — Durable checkpointer / SQLite (`level2_sqlite.py`)
```bash
python3 level2_sqlite.py   # run 1
python3 level2_sqlite.py   # run 2 — fresh process, but it remembers run 1!
python3 level2_sqlite.py   # run 3 — keeps growing
```
Shows: state survives across separate process runs because it's written to
`checkpoints.db` on disk instead of RAM. Delete that file to reset.

## Level 3 — Cross-thread memory / Store (`level3_store.py`)
```bash
python3 level3_store.py
```
Shows the checkpointer vs. store distinction directly:
- Thread A and Thread B share no checkpoint history at all (different `thread_id`).
- But because both are tagged with the same `user_id`, Thread B still recalls
  a "preference" that was saved into the Store during Thread A.
- A different user (`user-99`) gets nothing — Store data is scoped per-key,
  not global.

## Level 4 — Time travel (`level4_timetravel.py`)
```bash
python3 level4_timetravel.py
```
Shows: every step creates a new checkpoint (old ones are never overwritten).
`get_state_history()` lists them all. Re-invoking the graph with an *older*
checkpoint's config forks a new branch from that point in history — print
the history list first to see exactly which index to rewind to.

## Quick mental model recap
| | Checkpointer | Store |
|---|---|---|
| Scope | One `thread_id` | Whatever key you choose (e.g. `user_id`) |
| Who manages it | LangGraph, automatically | You, explicitly, inside node code |
| Use case | Conversation continuity, time travel, crash recovery | User preferences, facts that outlive any single conversation |
| Local/dev backend | `InMemorySaver` | `InMemoryStore` |
| Production backend | `SqliteSaver`, `PostgresSaver`, Redis | `PostgresStore`, Redis, AgentCore |
