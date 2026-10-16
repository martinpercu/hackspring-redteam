# Agent Red Team

**Tagline:** A firing range that hijacks your AI agent — then proves the guardrail holds.

## Inspiration
Every agent that reads the web can be hijacked by the web, and almost nobody tests for it before shipping.

## What it does
Agent Red Team attacks an AI agent with poisoned web pages inside a Daytona sandbox full of decoy secrets, detects the exact step where the agent is hijacked (Arize trace), learns from successful attacks (SurrealDB), builds a guardrail, re-attacks to prove it holds, and narrates the result (ElevenLabs).
Result: {{X}}/{{N}} attacks leaked without defenses; {{Y}}/{{K}} known attacks leaked with gates; the unseen attack leaked once, was learned, and was blocked on the second try ({{confirm from --learn-arc}}); {{W}}/2 legitimate tasks keep working.

## How we built it
Python + an OpenAI tool-calling agent (`gpt-4o-mini`) with three tools (`browse`, `shell`, mocked `http_post`).
- **Daytona:** sandbox with decoy secrets; attack pages served through a signed preview URL.
- **Arize AX:** traces for every step including LLM spans; an online LLM-as-judge task; `hijacked` evaluations {{pending live run}}.
- **SurrealDB (embedded):** the guardrail's sensitive-path policy is read from the database and grows from incidents.
- **ElevenLabs:** attacker/defender narration lines, pre-rendered and cached so the live demo needs no network for audio.
- Planned, not built: Anchor Browser as the agent's real browser; Arize experiments.

## Safeguards
- Decoy secrets only, unique per run.
- The exfiltration tool (`http_post`) is a mock; nothing is sent.
- The sandbox has no open internet (Daytona organization network policy, checked 2026-10-15).
- Every command has a timeout; the sandbox is deleted after each session.
- Verdicts are deterministic: a decoy token either left or it didn't.

## Challenges
Making attacks deterministic enough for a live demo; closing path-normalization evasions in the gate; being honest about what a text-level gate can and cannot stop.

## Accomplishments
A measurable before/after, a detector with no judgment calls, and a demo that survives a dead wifi (recorded-run mode).

## What we learned
The model gets hijacked either way: in our pre-event prototype run, the online judge flagged `hijacked` in guarded mode too (9/9); we re-measure it in this build: {{judge result pending T12 backfill}}. What saves you is the gates in the tools and the sandbox around them.

## What's next
Semantic gates, network/OS-level enforcement, multi-model comparison on the same battery, more attack techniques, Anchor Browser as the real browser.

## Built with
Daytona · Arize AX · SurrealDB · ElevenLabs · OpenAI · Python

## Transparency
{{Pick the true one: (a) idea, build plan and test specs prepared the night before; all code generated and assembled during the event with AI coding agents · (b) parts restored from a pre-event prototype: <modules> · (c) built on a prototype made the day before}}
