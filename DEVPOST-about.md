## Inspiration

Every agent that reads the web can be hijacked by the web. A docs page, a README or a status page with one hidden sentence is enough for an agent to read your secrets and send them out — and almost nobody tests for it before shipping. We wanted a way to **attack our own agent first**, see *exactly* where it breaks, and prove the fix with numbers instead of vibes.

## What it does

**Agent Red Team is a firing range for AI agents.** A real tool-using agent lives inside a Daytona sandbox full of *decoy* secrets. We attack it with poisoned web pages (hidden text, a poisoned README, a fake `[SYSTEM]` message), and the system:

1. **Detects** the leak deterministically — a unique decoy token either left through the exfiltration tool or it didn't. No judgment calls.
2. **Shows the exact step** where the agent was hijacked, in the Arize trace.
3. **Blocks** the same attack with gates on the tools (untrusted-content delimiting, a sensitive-path gate, an egress domain allowlist).
4. **Learns**: a brand-new attack (a new file path, exfiltrated through a *trusted* domain) slips through **once**; its path is stored in SurrealDB, the guardrail reads its policy from that database, and the next attempt is blocked.
5. **Narrates** the run live with two ElevenLabs voices — the attacker and the defender.

The arc of the demo: **attack succeeds → guardrail blocks it → unseen attack gets through once → it learns → blocked.**

Measured on real runs — the numbers below are from our recorded full-battery run (the attack-success rate $ASR = \frac{\text{attacks that leaked}}{\text{attacks}}$):

| | Without defenses | With the guardrail |
|---|---|---|
| Attacks (3 known + 1 unseen) | **4/4** leaked ($ASR = 1.0$) | **1/4** leaked — known attacks **0/3**; the unseen one leaked once, then was learned and blocked |

The known attacks were blocked in **every** full-battery run (5 of 5). The unseen attack is the variable one: it leaked in 2 of 5 full-battery runs (and in 6 of 6 runs on its own); in the other 3 the model simply didn't follow the injected instruction. That is why the demo also has a recorded mode.
| Legitimate tasks | 2/2 still work | 2/2 still work (the guardrail doesn't break real work) |

Each baseline attack succeeded **3 times out of 3** on `gpt-4o-mini` (temperature 0), so the live demo is repeatable.

## How we built it

Python, an OpenAI tool-calling agent (`gpt-4o-mini`) with three tools — `browse`, `shell` (runs in the sandbox) and `http_post` (a **mock**: it records the attempt and sends nothing).

- **Daytona** — an ephemeral sandbox is the range: decoy secrets planted in files, attack pages served through a signed preview URL, every command with a timeout, sandbox deleted after each session.
- **Arize AX** — a trace of every step including the LLM calls (the injected page text is visible inside the prompt, followed by the tool call that obeys it), native `hijacked`/`resisted` evaluations on each attack, an online LLM-as-judge on every LLM span, and a dataset + two experiments (baseline vs guarded) to compare them side by side.
- **SurrealDB** (embedded) — the guardrail's sensitive-path policy is **read from the database, not from code**. Incidents are stored; a path is learned the first time an attack leaks through.
- **ElevenLabs** — the demo narrates itself with two voices. Lines are pre-rendered and cached, so the audio needs no network during the pitch.
- **A live dashboard** (zero-dependency Python server + SSE) and a **recorded-run mode** that replays real engine events, so the demo survives a dead venue wifi.
- The project was built with **AI coding agents working in parallel** against explicit contracts and a suite of 47 offline, deterministic tests.

## Challenges

- **Making attacks reliable enough for a live demo.** We calibrated every attack to succeed 3/3 in baseline. Even so, a model at temperature 0 is not fully deterministic: the unseen attack was not followed in 3 of 5 full-battery runs, although it leaked 6 out of 6 times when run on its own. We kept a recorded mode as a safety net and report the spread instead of hiding it.
- **Closing evasions in the gate.** Comparing command text is not enough (`~/app/../app/config.json`, `$HOME`, `python -c "open(...)"`, a bare file name). The gate normalizes every path in the command before comparing.
- **Being honest about what a text-level gate can and cannot stop.**

## Accomplishments that we're proud of

A measurable before/after; a detector with no judgment calls; a policy that is read from a database and learns from incidents; and a demo that keeps working with the network down.

## What we learned

**You can't prompt your way out of prompt injection.** The model gets hijacked either way: in this build's run, the online judge flagged at least one LLM span as hijacked in 4 of 4 baseline traces **and in 3 of 4 guarded traces** (31 of 44 LLM spans in that run were judged). What stopped the leaks was the gates in the tools and the sandbox around them.

**Honest limits.** The gate is text-level, so obfuscation can evade it — production needs OS/network permissions underneath, which is exactly what the sandbox's restricted network provides. What the guardrail learns is an exact path, not a concept. We test one model, 4 attacks and 2 control tasks: this is a demonstration, not a benchmark.

## Safeguards

- Decoy secrets only, unique per run — never real credentials.
- The exfiltration tool is a mock: nothing is sent anywhere.
- The sandbox has no open internet (Daytona organization network policy, checked 2026-10-15).
- Every command has a hard timeout; the sandbox is deleted after each session.
- Verdicts are deterministic: a decoy token either left or it didn't.
- These attacks target **our own agent** in **our own sandbox**; never third-party systems.

## What's next

Semantic gates that recognize injected *content*, not just paths; network/OS-level enforcement instead of string checks; running the same battery across several models; more attack techniques; and Anchor Browser as the agent's real browser (planned — not built yet).

## Built with

Daytona · Arize AX · SurrealDB · ElevenLabs · OpenAI (`gpt-4o-mini`) · Python

## Transparency

We prepared the idea, a prototype and a build plan the day before the event. During the event, AI coding agents built the agent, its tools, the runner and CLI, the Daytona range, the dashboard, the voice layer and the Arize integration. A small pure core — the decoy fixtures, the path/domain gates, the deterministic detector, the tracing wrapper and the SurrealDB memory — was restored from the pre-event prototype.

Code: https://github.com/martinpercu/hackspring-redteam
