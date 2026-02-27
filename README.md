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

By default, tables show the compact columns (`Rank`..`Days`) for better terminal fit.
Use `--show-raw` to append `ImpRaw`, `InhRaw`, and `FatRaw`.

## Output glossary (every printed column)

The table below includes both the technical definition and what each field means in everyday baseball terms.

| Column | Technical meaning | In plain English, this tells you... |
|---|---|---|
| `Rank` | Position in final ascending BVI ranking (1 = least volatile). | Where that bullpen sits from most predictable (`1`) to most erratic (`30`). |
| `Team` | Team abbreviation from MLB API (e.g., `LAD`, `NYY`). | Quick scoreboard-style team code. |
| `Team Name` | Team full name from MLB API. | The full club name for readability. |
| `BVI` | Final composite Bullpen Volatility Index on 0–100 scale (lower = more stable). | The headline volatility score: lower means "this bullpen behaves more consistently," higher means "more up-and-down outcomes." |
| `ImpN` | Normalized impact-proxy volatility component (0–100 after robust clipping + min-max). | How swingy the bullpen is in pressure moments: high values mean relief outings in tense spots vary a lot from calm to damaging. |
| `InhN` | Normalized inherited-runner instability component (0–100 after robust clipping + min-max). | How inconsistent the bullpen is at handling runners left by previous pitchers: high values mean sometimes they strand them, sometimes many score. |
| `FatN` | Normalized fatigue volatility component (0–100 after robust clipping + min-max). | How uneven bullpen workload is day-to-day: high values mean big spikes and dips in usage. |
| `ImpRaw` | Raw (pre-normalization) sample stddev of impact proxy across relief appearances for the team. | The unscaled "how wild were the game-impact outcomes" number before converting to 0–100. Useful for deeper analysis, but less easy to compare quickly. |
| `InhRaw` | Raw (pre-normalization) inherited-runner instability = weighted stddev(inherited scored rate, weighted by inherited runners) × smoothing factor. | The unscaled "how unpredictable were inherited runner results" number before normalization. |
| `FatRaw` | Raw (pre-normalization) coefficient of variation of daily bullpen pitch totals (sample stddev / mean). | The unscaled "how jumpy was bullpen usage by day" number before normalization. |
| `Apps` | Number of extracted relief appearances for the team. | Sample size: how many relief outings went into this team's score. |
| `InhApps` | Number of extracted relief appearances where inherited runners > 0. | How often this bullpen had to clean up someone else's mess. |
| `Days` | Number of game dates with bullpen pitch totals recorded for the team. | How many game-days were used for workload/fatigue calculations. |

## How to read the output quickly

- Start with **`BVI`** for the overall stability ranking.
- Use **`ImpN` / `InhN` / `FatN`** to see *why* a team is volatile.
  - High `ImpN` → volatile results in high-pressure situations.
  - High `InhN` → inherited runners are handled inconsistently.
  - High `FatN` → bullpen workload is uneven across days.
- Use **`Apps` / `InhApps` / `Days`** to judge confidence in the signal (more rows generally means more stable estimates).

## Composite definition

The prototype uses:

- `BVI = 0.50 * ImpN + 0.30 * InhN + 0.20 * FatN`

See `MODEL.md` for formula details and approximation notes.

## Notes / limitations

- Entry game-state (inning/outs/runners/score differential) is inferred from the first play where each reliever appears in play-by-play.
- If exact entry state is unavailable, conservative defaults are used.
- Requires internet access to `statsapi.mlb.com` on first run; subsequent runs benefit from local cache.
