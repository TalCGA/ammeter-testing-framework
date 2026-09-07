# Ammeter Testing Framework

QA harness for three TCP ammeter emulators (Greenlee, ENTES, CIRCUTOR). Emulators stay the instrument under test; `src/` only samples, analyzes, archives, and plots over localhost sockets.

## Quick start

Python 3.9+. Run from the repo root.

```sh
python3 -m pip install -r requirements.txt   # pyyaml, matplotlib, pytest
python3 main.py                              # smoke test: one reading per meter
python3 examples/run_tests.py                # full session → JSON + PNG
python3 examples/run_tests.py --no-plot      # skip matplotlib
python3 -m pytest                            # unit tests (mocked I/O)
```

| Flag | Effect |
| --- | --- |
| `--config PATH` | YAML for ports, commands, sampling (default `config/config.yaml`) |
| `--no-plot` | Skip PNG on `run_tests.py` (no-op on `main.py` smoke test) |

Default plan: **10 samples @ 2 Hz / 5 s** per device.

## Architecture

```
config.yaml → AmmeterTestFramework
                ├─ AmmeterClient
                ├─ SamplingEngine
                ├─ AnalysisEngine
                ├─ visualization (optional PNG)
                └─ ResultArchiver (one session JSON)
```

| Layer | Module | Role |
| --- | --- | --- |
| Client | `src/testing/ammeter_client.py` | Unified `measure() → float` |
| Sampling | `src/testing/sampling.py` | `perf_counter` loop: count / duration / frequency |
| Analysis | `src/testing/analysis.py` | Stats + cross-ammeter comparison |
| Archive | `src/testing/archive.py` | One JSON per session |
| Visualization | `src/testing/visualization.py` | Two-panel matplotlib PNG |
| Orchestration | `src/testing/test_framework.py` | Isolate per-device failures |
| Emulators | `Ammeters/` | TCP servers; synthetic current only |
| Runner | `examples/run_tests.py` | Start emulators, run session, print summary |

## Protocol

Exact command bytes. Server uses `==`; a truncated string returns empty data.

| Ammeter | Port | Command | Physics |
| --- | --- | --- | --- |
| Greenlee | **5000** | `MEASURE_GREENLEE -get_measurement` | `I = V / R` |
| ENTES | **5001** | `MEASURE_ENTES -get_data` | `I = B × K` |
| CIRCUTOR | **5002** | `MEASURE_CIRCUTOR -get_measurement` | `I ≈ Σ V Δt` |

Defined in `config/config.yaml`; must match each emulator’s `get_current_command`.

## Baseline socket fixes

`main.py` did not return currents until these were aligned:

| Issue | Fix |
| --- | --- |
| Ports 5001–5003 vs documented 5000–5002 | **5000 / 5001 / 5002** everywhere |
| Truncated client commands; CIRCUTOR extra `-current` | Full README command strings |
| `localhost` → IPv6 vs `AF_INET` | Bind/connect **`127.0.0.1`** |
| Restart `TIME_WAIT` bind errors | **`SO_REUSEADDR`** |
| Hang on connect/recv | **5 s** socket timeouts |

## Artifacts

One `run_tests.py` process → **one** session (`{UTC timestamp}_{UUID}`). Generated files are gitignored (keep `.gitkeep`).

```
results/runs/YYYY-MM-DD/<session_id>.json
results/logs/YYYY-MM-DD/<timestamp>_ammeter_test.log
results/plots/YYYY-MM-DD/run_<timestamp>_plot.png
```

JSON: metadata, sampling plan, `execution_summary`, `comparison`, `plot_path`, per-device `metrics` + `samples`.

PNG (`Agg`, headless): shared time axis

- **Log-scale current** — ENTES (~tens of A) vs Greenlee/CIRCUTOR (≪ 1 A)
- **Normalized trace** — each series / its mean; `y = 1` is the device mean

## Robustness

- **Retries:** two extra attempts on timeout, empty payload, or non-float body
- **Skip sample:** failed `measure()` is logged and dropped; all-fail → device `error`, other meters continue
- **Sampling fallback:** any two of `{count, duration, frequency}` derive the third
- **CV:** `std_dev / |mean|` ranks relative stability (not absolute accuracy — emulators do not share a reference current)

## CI and production scale

**GitHub Actions** (`.github/workflows/test.yml`): on `push` / `pull_request` → Python 3.12 → `pip install -r requirements.txt` → `python -m pytest` (no live emulators).

Local `YYYY-MM-DD` folders map to object storage:

```
s3://<bucket>/ammeter-qa/dt=YYYY-MM-DD/session=<session_id>/report.json
s3://<bucket>/ammeter-qa/dt=YYYY-MM-DD/session=<session_id>/run_<timestamp>_plot.png
```

`dt=` keeps prefix listing and lifecycle rules cheap; `session_id` is the retry idempotency key. Swap filesystem for S3 in the archiver without changing sampling or analysis.

## Layout

```
main.py                 # smoke test + --config / --no-plot
Ammeters/               # TCP emulators
config/config.yaml
examples/run_tests.py   # full session
src/testing/            # client, sampling, analysis, archive, viz
src/utils/              # config, logging, paths
tests/                  # pytest
.github/workflows/      # CI
results/                # dated artifacts (gitignored)
Exam/                   # original spec
```
