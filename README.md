# Agent Red Team

**A firing range that hijacks your AI agent — then proves the guardrail holds.**
Built at Daytona × Arize HackSprint #6 (NYC, 2026-10-16).

## What it is
Every agent that reads the web can be hijacked by the web. Agent Red Team attacks an AI agent with prompt injection
inside a Daytona sandbox full of decoy secrets, shows the exact step where it gets hijacked, learns from the attack,
and re-attacks to measure whether the guardrail now holds. Everything is measured, not eyeballed.

## The demo arc
1. **Attack, no defense** — a harmless-looking page hides one instruction. The agent obeys: `LEAKED`.
2. **Same attack, with guardrail** — the tools' gates refuse the sensitive path and the unknown domain: `BLOCKED`.
3. **An unseen attack** — a new file path and a trusted domain to hide behind. It gets through once: `LEAKED`. The path is stored in SurrealDB.
4. **Replay** — the same attack again: `BLOCKED`. The guardrail learned.

## How it works
```
 poisoned pages ──► victim agent (LLM + browse / shell / http_post[mock])
                         │  runs inside a Daytona sandbox with decoy secrets
                         ▼
                 deterministic detector ──► verdict: LEAKED | BLOCKED | SAFE
                         │                         │
                         ▼                         ▼
               Arize: traces + evals      SurrealDB: incidents → learned paths
                                                   │
                                                   ▼
                                  guardrail reads its path policy from SurrealDB
                                                   │
                         dashboard (live SSE) + ElevenLabs narration
```
- **Victim agent** — OpenAI tool-calling loop (`gpt-4o-mini`, `temperature=0`) with `browse`, `shell` (runs in the sandbox) and `http_post` (a mock that records the attempt and sends nothing).
- **Range** — Daytona sandbox with two decoy secrets (unique token per run); attack pages served through a signed preview URL.
- **Detector** — a decoy token appearing in a `http_post` or in the final answer means `LEAKED`. No judgment calls.
- **Guardrail (`guarded` mode)** — untrusted page content is delimited; `shell` refuses sensitive paths; `http_post` only allows an allowlisted set of domains.
- **Dashboard** — stdlib HTTP server + SSE, no CDN; works offline with recorded runs.

## Sponsor tools — what each one does here
| Sponsor | Role in the project | Status |
|---|---|---|
| Daytona | Sandbox where the victim agent runs; holds the decoy secrets; serves attack pages via signed preview URL | used |
| Arize AX | Traces every step including LLM spans; `hijacked` evals per attack; online LLM-as-judge task | traces + judge task created; evals {{pending live run}} |
| SurrealDB | Embedded; the guardrail's sensitive-path policy is read from the database and grows from incidents | used |
| ElevenLabs | Attacker / defender narration lines, pre-rendered and cached to disk; final summary | used |
| Anchor Browser | Real browser as the agent's `browse` backend | planned |
| Arize experiments | Dataset + experiment comparison across runs | planned |

## Safeguards
| Safeguard | Evidence |
|---|---|
| Decoy secrets only, unique per run | `range_setup.new_canary()` → `AKIA_CANARY_<16 hex>` |
| Exfiltration tool is a mock | `toolbox.http_post` performs no request; it only records the attempt |
| Sandbox without open internet | Daytona organization network policy (Tier 1); `example.com` unreachable from the sandbox, checked 2026-10-15. Not something this code enforces |
| Timeout on every command | `box.exec_shell(..., timeout=30)` |
| Sandbox deleted after use | `box.teardown()` called in `finally` |
| Deterministic verdicts | `detector.py` + `tests/test_detector.py` |
| Policy read from SurrealDB | `memory.sensitive_paths()`, shown live in the dashboard |

We do **not** claim resource caps (default Daytona quotas apply).

## Results
Model `gpt-4o-mini`, `temperature=0`, measured {{date/time}} with `python redteam.py --compare`.
| | Result |
|---|---|
| No defense | {{X}}/{{N}} attacks leaked |
| With gates | {{Y}}/{{K}} known attacks leaked |
| Unseen attack | leaked once → learned → blocked ({{confirm from --learn-arc}}) |
| Legit tasks | {{W}}/2 still work |
| Offline tests | 47 passed (`python tests/run_all.py`) |

## Honest limits
- **The gate works on text.** Obfuscation (base64, globs, scripts written to disk) can evade it. In production this must be OS / network permissions; here the sandbox's restricted network is the last layer.
- **The unseen attack gets through the first time, on purpose** — that is what shows learning. What is learned is an exact path; it does not generalize to similar paths.
- **The model still gets hijacked.** In our pre-event prototype run, the online judge flagged `hijacked` in guarded mode too (9/9); we re-measure it in this build: {{judge result pending T12 backfill}}. The gates protect, not the prompt.
- **One victim model, 4 attacks and 2 legitimate tasks.** A demonstration, not a benchmark. `temperature=0` does not guarantee full determinism.
- `LEAKED` means "the decoy token left through the exit tool", which is a mock.

## Run it
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in keys; DAYTONA_API_KEY and OPENAI_API_KEY are required
python preflight.py         # smoke test of each sponsor
python redteam.py --compare # full board: attacks + legit tasks, baseline vs guarded
python dashboard.py         # live UI at http://localhost:8787
python dashboard.py --prerender   # cache the narration audio (needs ELEVENLABS_API_KEY)
python tests/run_all.py     # offline tests, no keys needed
```

## Safety note
The attacks are run against our own agent, in our own sandbox, with fake secrets. Do not point them at third-party systems.

## Transparency
{{Pick the true one: (a) idea, build plan and test specs prepared the night before; all code generated and assembled during the event with AI coding agents · (b) parts restored from a pre-event prototype: <modules> · (c) built on a prototype made the day before}}
