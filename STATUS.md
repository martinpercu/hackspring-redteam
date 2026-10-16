# STATUS — Agent Red Team (live)

> Tablero compartido. **Cada agente edita solo su fila.** Estados: `TODO` · `DOING` · `DONE` · `STUBBED` (funciona degradado, ver nota) · `BLOCKED`.
> Última actualización del tablero: ____:____

## Tarjetas
| Tarjeta | Carril | Dueño | Estado | Verificado con (comando exacto) | Nota |
|---|---|---|---|---|---|
| T00 scaffold | FUNDACIÓN | | TODO | | |
| T01 preflight | FUNDACIÓN | | TODO | | |
| T02 config+events+fixtures | ENGINE | | TODO | | |
| T03 gate+detector | ENGINE | | TODO | | |
| T04 tracing+memory | ENGINE | | TODO | | |
| T05 toolbox+victim | ENGINE | | TODO | | |
| T06 runner | ENGINE | | TODO | | |
| T07 box+range (Daytona) | PLATAFORMA | | TODO | | |
| T08 CLI redteam.py | ENGINE | | TODO | | |
| T09 calibración | ENGINE | | TODO | | |
| T10 Arize trazas | ARIZE | | TODO | | |
| T11 Arize evals | ARIZE | | TODO | | |
| T12 Arize judge online | ARIZE | | TODO | | |
| T13 Arize experiments (stretch) | ARIZE | | TODO | | |
| T20 replay+narrator+scenarios | DEMO | | TODO | | |
| T21 dashboard server | DEMO | | TODO | | |
| T22 UI index.html | DEMO | | TODO | | |
| T23 voice | DEMO | | TODO | | |
| T30 Anchor (stretch) | SPONSORS | | TODO | | |
| T31 hardening (stretch) | SPONSORS | | TODO | | |
| T40 slides | PITCH | | TODO | | |
| T41 README + Devpost | PITCH | | TODO | | |
| T42 grabación offline + video | PITCH | | TODO | | |
| T43 ensayo ×2 | PITCH | | TODO | | |
| T50 freeze + submit | ENTREGA | | TODO | | |

## Sponsors vivos (de `python preflight.py`, T01)
| Sponsor | Estado | Nota |
|---|---|---|
| Daytona | | |
| OpenAI | | |
| Arize | | |
| ElevenLabs | | |
| SurrealDB (embebido) | | |
| Anchor | | créditos: |

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
