# STATUS — Agent Red Team (live)

> Tablero compartido. **Cada agente edita solo su fila.** Estados: `TODO` · `DOING` · `DONE` · `STUBBED` (funciona degradado, ver nota) · `BLOCKED`.
> Última actualización del tablero: ____:____

## Tarjetas
| Tarjeta | Carril | Dueño | Estado | Verificado con (comando exacto) | Nota |
|---|---|---|---|---|---|
| T00 scaffold | FUNDACIÓN | líder | DONE | `python tests/run_all.py` | venv + tests + repo GitHub |
| T01 preflight | FUNDACIÓN | Plataforma | DONE | `python preflight.py` → PREFLIGHT OK | todos PASS; sin keys → SKIP + exit 1 |
| T02 config+events+fixtures | ENGINE | líder | DONE (copiado de reference) | `python tests/run_all.py fixtures` → 6 passed | 11:00 |
| T03 gate+detector | ENGINE | líder | DONE (copiado de reference) | gate 6 · detector 4 passed | 11:00 |
| T04 tracing+memory | ENGINE | líder | DONE (copiado de reference) | events 3 · memory 4 passed | 11:00 |
| T05 toolbox+victim | ENGINE | engine | DONE | `python tests/run_all.py toolbox` → 7 passed, 0 failed | |
| T06 runner | ENGINE | engine | DONE | `python tests/run_all.py runner` → 8 passed, 0 failed; run_all → 38 passed, 5 failed (esperado) | |
| T07 box+range (Daytona) | PLATAFORMA | Plataforma | DONE | `python box.py --selftest`; `python range_setup.py --selftest` → SELFTEST OK | 6 URLs ok, teardown ok |
| T08 CLI redteam.py | ENGINE | | TODO | | |
| T09 calibración | ENGINE | | TODO | | |
| T10 Arize trazas | ARIZE | | TODO | | |
| T11 Arize evals | ARIZE | Plataforma | STUBBED | `python tests/run_all.py` (38/5, fallos = módulos ajenos); mock de DataFrame ok | falta aceptación live: requiere redteam.py --compare (T08/T10) |
| T12 Arize judge online | ARIZE | Plataforma | DONE | `python arize_task.py --list` / `python arize_task.py` → tarea injection_judge_redteam-live creada | backfill pendiente (paso 3, espera spans reales) |
| T13 Arize experiments (stretch) | ARIZE | Plataforma | STUBBED | `python -c "import arize_experiment"` ok | escrito, NO ejecutado (falta T08 runner/redteam) |
| T20 replay+narrator+scenarios | DEMO | demo+pitch | DONE | `python tests/run_all.py replay_narrator` → 5 passed; `... scenarios` → 3 passed | |
| T21 dashboard server | DEMO | demo+pitch | DONE | `python tests/run_all.py` → 47 passed, 0 failed | `--prerender` en vivo pendiente (T23) |
| T22 UI index.html | DEMO | demo+pitch | DONE | dev_fake_dashboard.py + Playwright 1500x900: battery 4/4·1/4·2/2, unseen BLOCKED, 0 errores de consola | no probado: Offline, 800px, audio |
| T23 voice | DEMO | demo+pitch | DONE | `python dashboard.py --prerender` → "10/10 lineas de narracion listas"; `ls web/audio | wc -l` → 11; `run_all.py` → 47 passed | segunda voz: no verifiqué ELEVENLABS_VOICE_ID_2 (no leo .env) |
| T30 Anchor (stretch) | SPONSORS | | TODO | | |
| T31 hardening (stretch) | SPONSORS | Plataforma | DONE | `python preflight.py --only harden` PASS; `SANDBOX_HARDEN=1 python box.py --selftest` OK | falta que el humano ponga SANDBOX_HARDEN=1 en .env (no toco .env) |
| T40 slides | PITCH | demo+pitch | DONE | `grep -c "https\?://" slides/index.html` → 0; 4 slides <=25 palabras (contador); `{{X}}/{{N}}/{{Y}}/{{K}}/{{W}}` pendientes | placeholders hasta Resultados finales; sin Anchor; slide 4 recortada a 25 palabras |
| T41 README + Devpost | PITCH | demo+pitch | DOING | esqueleto escrito: `grep -c "{{" README.md DEVPOST.md` → 7 y 3 (líneas) | faltan números reales + transparencia |
| T42 grabación offline + video | PITCH | | TODO | | |
| T43 ensayo ×2 | PITCH | | TODO | | |
| T50 freeze + submit | ENTREGA | | TODO | | |

## Sponsors vivos (de `python preflight.py`, T01)
| Sponsor | Estado | Nota |
|---|---|---|
| Daytona | PASS | sandbox 0.7s, preview URL ok |
| OpenAI | PASS | gpt-4o-mini |
| Arize | PASS | injection_judge EXISTE |
| ElevenLabs | PASS | mp3 ok |
| SurrealDB (embebido) | PASS | mem:// |
| Anchor | PASS (billing) | créditos: 0 → BROWSE_BACKEND=direct |

## Resultados finales (los únicos números que se pueden usar en slides/README/Devpost)
| Dato | Valor | Cómo se midió (comando) | Fecha/hora |
|---|---|---|---|
| Calibración baseline (T09) | ×/3 por ataque | `python redteam.py --calibrate --runs 3` | |
| Baseline (compare) | X/N LEAKED | `python redteam.py --compare --no-voice --reset-memory` | |
| Guarded (compare) | X/N LEAKED · conocidos X/3 · no visto X/1 | idem | |
| Controles | X/2 OK → X/2 OK | idem | |
| Learn arc | LEAKED → BLOCKED | `python redteam.py --learn-arc` | |
| Judge `injection_judge` | hijacked N/N (baseline) · N/N (guarded) | UI de Arize | |
| Tests offline | N passed | `python tests/run_all.py` | |

## Links de la demo
- Traza Arize LEAKED (baseline, hidden-docs): 
- Traza Arize BLOCKED (guarded, hidden-docs): 
- Dashboard: http://localhost:8787 · Slides: `slides/index.html` · Video de respaldo: `backup/demo.mp4`

## Pedidos (agentes → humano). Formato: `BLOQUEADO: <qué> | INTENTÉ: <qué> | NECESITO: <qué>`
- 

## Decisiones del humano (rescates, recortes, cambios de plan)
- 
