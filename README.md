# Agent Red Team

HackSprint #6 (Daytona × Arize AI, NYC, 2026-10-16).

A firing range for AI agents: we attack an agent with prompt injection inside a Daytona sandbox full of decoy secrets,
trace the exact step where it gets hijacked (Arize), learn from the attacks (SurrealDB), build a guardrail,
re-attack to prove it holds, and narrate the result (ElevenLabs).

Work in progress — built during the event.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys
```
