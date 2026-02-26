# MLB Bullpen Volatility Index (BVI) Prototype

A local Python prototype that computes a **team-level Bullpen Volatility Index (BVI)** for MLB using only the public MLB Stats API (`statsapi.mlb.com`).

The tool analyzes relief appearances for all MLB teams in a target season (default: 2025), computes three volatility components, normalizes them to 0–100, and outputs a ranking from **least volatile** to **most volatile** bullpen.

## Quick start

```bash
python -m pip install -r requirements.txt
python main.py --season 2025
```

Optional:

```bash
python main.py --season 2025 --workers 6
```

- `--workers` controls parallel fetches for game feeds.
- Responses are cached under `./cache/` to speed reruns.

## Project structure

- `main.py` — CLI entrypoint, orchestration, printing ranked outputs.
- `mlb_api.py` — MLB API client with retry/backoff and disk cache.
- `extract.py` — Parses game feed/boxscore into relief appearance records.
- `metrics.py` — BVI component math, normalization, and composite score.
- `MODEL.md` — Model notes and formulas.

## Output sections

`main.py` prints:
1. Top 10 least volatile bullpens
2. Top 10 most volatile bullpens
3. Full ranked list (all MLB teams)
4. Sanity check line for zero-appearance extraction cases

## Output glossary (every printed column)

| Column | Meaning |
|---|---|
| `Rank` | Position in final ascending BVI ranking (1 = least volatile). |
| `Team` | Team abbreviation from MLB API (e.g., `LAD`, `NYY`). |
| `Team Name` | Team full name from MLB API. |
| `BVI` | Final composite Bullpen Volatility Index on 0–100 scale (lower = more stable). |
| `ImpN` | Normalized impact-proxy volatility component (0–100 after robust clipping + min-max). |
| `InhN` | Normalized inherited-runner instability component (0–100 after robust clipping + min-max). |
| `FatN` | Normalized fatigue volatility component (0–100 after robust clipping + min-max). |
| `ImpRaw` | Raw (pre-normalization) stddev of impact proxy across relief appearances for the team. |
| `InhRaw` | Raw (pre-normalization) inherited-runner instability = stddev(inherited scored rate) × stabilization factor. |
| `FatRaw` | Raw (pre-normalization) stddev of daily bullpen pitch totals. |
| `Apps` | Number of extracted relief appearances for the team. |
| `InhApps` | Number of extracted relief appearances where inherited runners > 0. |
| `Days` | Number of game dates with bullpen pitch totals recorded for the team. |

## Composite definition

The prototype uses:

- `BVI = 0.50 * ImpN + 0.30 * InhN + 0.20 * FatN`

See `MODEL.md` for formula details and approximation notes.

## Notes / limitations

- Entry game-state (inning/outs/runners/score differential) is inferred from the first play where each reliever appears in play-by-play.
- If exact entry state is unavailable, conservative defaults are used.
- Requires internet access to `statsapi.mlb.com` on first run; subsequent runs benefit from local cache.
