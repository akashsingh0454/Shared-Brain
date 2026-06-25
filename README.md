# BrainGraph: Contextual Multi-Agent Handoff & Impact Analysis System

![BrainGraph Architecture](braingraph_architecture.png)

**BrainGraph** is a unified handoff, process monitoring, and code graph impact analysis system. It enables seamless task and context resumption across multiple AI coding agents, including **Claude Code**, **Windsurf (Cascade)**, **Cursor**, **Antigravity**, **GitHub Copilot**, **Aider**, **Roo Code/Cline**, and more.

It is designed to solve **context drift**, **billing limit exhaustion**, and **multi-device synchronization** by capturing active intents, uncommitted diffs, and traversing your AST dependency call graph.

---

## Architecture Overview

BrainGraph operates on three distinct layers:
1. **Structural Code Graph**: Parses AST and regex relationships natively to map file and symbol dependencies across multiple languages (Python, JS/TS, Go, Rust, C++, Java) with zero external dependencies and no node limits.
2. **Workspace Modifications Tracker**: Detects staged/unstaged changes, untracked files, and recent WIP commits.
3. **Intent & History Log**: Maintains a single source of truth for task goals (`active_task.md`) and a synced cross-device turn-based history (`temp_chat_history.md`).

---

## Key Features

### 1. Downstream Impact Profiling
On task resumption, BrainGraph dynamically parses the codebase to build a local, in-memory dependency graph. If you edited `auth.py`, it traverses caller symbols in reverse and warns the incoming agent:
> *The following downstream symbols depend on your changes: `run_app` (in `main.py`). Be careful when verifying.*
It also automatically compiles a Mermaid diagram of the affected callflow in `.braingraph/active_graph.md`.

### 2. The Process Watchdog (Limit Exhaustion Protection)
When an agent starts, it registers its Process ID (PID). A background watchdog monitors the process:
- If the agent terminates abruptly (e.g. runs out of LLM API credits or crashes) and leaves uncommitted work:
  - It scans local transcripts for credit-exhaustion keywords (`429`, `limit`, `quota`, `billing`).
  - It auto-commits the work as `WIP: Auto-checkpoint (Agent terminated abruptly due to limit error)` and pushes it to GitHub.
  - It marks the agent as **Exhausted** in `agents.json`.

### 3. Interactive Agent Usage Console (`agents`)
Displays an interactive CLI dashboard showing:
- Available vs. Exhausted agents.
- Turn-based usage counts dynamically parsed from `temp_chat_history.md`.
- Options to toggle availability, set targets, or add manual offsets.

---

## Commands Reference

Run the control CLI inside your project:

```bash
# Initialize BrainGraph rules and folder structures
python .braingraph/scripts/braingraph.py init

# Start a new task (automatically launches the watchdog)
python .braingraph/scripts/braingraph.py start "Your Task Description"

# Compile context for the next agent, analyzing git edits & native AST/regex dependencies
python .braingraph/scripts/braingraph.py resume

# Manage agent availability and view Task Usage statistics
python .braingraph/scripts/braingraph.py agents

# Stop the watchdog, archive chat history, and write a handoff report
python .braingraph/scripts/braingraph.py handoff
```
