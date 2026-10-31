# Tooling, libraries and language choices for a one-hour poker bot build (as of 2026-10-31)

Scope note: all dates and versions below were checked on 2026-10-31 via the GitHub REST API (`pushed_at`), PyPI, crates.io and npm registries unless a different source is cited. "pushed" = date of last push to the default branch.

## Key question 1: Hand evaluators — speed, card-count support, variants, maturity, license, install friction

### Takeaway
For C++/Rust the solved problem is OMPEval (ISC, ~270–775M evals/s, 0–7 cards) or PHEvaluator (Apache-2.0, 56–72M evals/s, 5/6/7 cards plus PLO4/5/6, still actively pushed Oct 2026). For Python the pragmatic picks are `phevaluator` (C extension with wheels for CPython 3.10–3.14, released Jul 2026) or `eval7` (Cython, wheels through 3.15, released Jul 2026, includes equity and range parsing); pure-Python `treys` tops out around 3.2M evals/s and has not been pushed since 2023. Node has one fast maintained option (`@pokertools/evaluator`, ~17.9M 7-card hands/s, released Oct 2026); `pokersolver` is ~70k hands/s and dormant since 2020–2022. Go and Java have no well-maintained fast 7-card library.

### Cited Findings

**C++**
- OMPEval: evaluates 0–7 card hands, returns a 16-bit rank; perfect hashing shrinks the main lookup table from 36 MB to ~200 kB; init ~10 ms. Single-thread benchmark on an Intel 3770k (millions of evals/s): sequential 775 (OMP) vs 223 (SKPokerEval) vs 1588 (2+2) vs 80 (ACE); random 7×uint8 hands 272 (OMP) vs 146 (SKPE) vs 19 (2+2) vs 43 (ACE); random Hand objects 520 (OMP). License ISC (bundled libdivide has its own license). Build: `make` on Unix → `lib/ompeval.a`; `make SSE4=1` for SSE4.1; no Windows build files. Equity calculator included (Monte Carlo + enumeration, multithreaded), claimed "roughly 2–10x faster (per thread)" than free EquiLab except heads-up enumeration where EquiLab uses precalculated results — [OMPEval README](https://github.com/zekyll/OMPEval)
- OMPEval last pushed 2020-06-30, 232 stars, ISC, not archived — [GitHub API](https://api.github.com/repos/zekyll/OMPEval)
- SKPokerEval last pushed 2026-09-26, 250 stars, license not SPDX-detectable (NOASSERTION) — [GitHub API](https://api.github.com/repos/kennethshackleton/SKPokerEval)
- PHEvaluator (HenryRLee/PokerHandEvaluator), C/C++ core with Google Benchmark results dated 2023-09-02 on a 12×2.6 GHz CPU: random 5-card 72M/s, 6-card 64M/s, 7-card 56M/s, PLO4 32M/s, PLO5 30M/s, PLO6 29M/s; full enumeration of all 7-card hands 60M/s. Memory: 7-card tables 144 kB; PLO4 ~30.5 MB, PLO5 ~112 MB, PLO6 ~353 MB. Official bindings: C/C++ and Python; community ports listed for JavaScript, Dart, Haskell, Go, TypeScript, C#, Rust, CUDA. Java not mentioned. Short-deck not mentioned. License Apache-2.0. 526 stars — [PokerHandEvaluator README](https://github.com/HenryRLee/PokerHandEvaluator)
- PHEvaluator last pushed 2026-10-26 (actively maintained) — [GitHub API](https://api.github.com/repos/HenryRLee/PokerHandEvaluator)
- Two Plus Two evaluator: the generated `HandRanks.dat` lookup table is ~124 MB and "takes a while" to generate; MD5 of the canonical file is 5003cf3e6d5c9b8ee77094e168bfe73f; evaluates 5/6/7 cards — [pokerlookup-rs README via search](https://docs.rs/crate/pokerlookup/latest); the original mirror's `generate_table.cpp` builds it — [TwoPlusTwoHandEvaluator mirror](https://uithub.com/tangentforks/TwoPlusTwoHandEvaluator); overview write-up — [Blazing Fast 7-card Poker Hand Evaluator](https://bostik.iki.fi/aivoituksia/projects/twoplustwo-hand-evaluator.html)
- The 2+2 evaluator is fastest only for sequential evaluation (1588M/s) and collapses to 19M/s on random hands in OMPEval's table (cache misses on the 124 MB table) — [OMPEval README](https://github.com/zekyll/OMPEval)
- Cactus Kev-derived code (christophschmalhofer/poker) last pushed 2011-01-23, no license file — [GitHub API](https://api.github.com/repos/christophschmalhofer/poker)

**Python**
- `phevaluator` 0.6.0 released 2026-07-11; requires Python ≥3.10 <4.0; prebuilt binary wheels (C extension) for CPython 3.10–3.14 on Windows x86-64, Linux glibc x86-64, macOS x86-64 and arm64; also an 8 MB sdist needing a C compiler. Returns rank 1 (best) to 7462 (worst), Cactus Kev-compatible; supports Omaha; PLO5/PLO6 opt-in at build time because tables are very large; ~100 kB memory for 7-card eval. Apache-2.0 — [PyPI phevaluator](https://pypi.org/project/phevaluator/)
- `eval7` 0.1.11 released 2026-07-29; wheels for CPython 3.9–3.15 incl. free-threaded 3.14t/3.15t on Linux x86-64, Windows, macOS universal2; MIT; single maintainer (JulianAndrews); dev status "3 - Alpha" and README says "only the functionality needed by Flop Ferret has been fully implemented". Evaluator based on Keith Rule's evaluator. `HandRange` parses weighted PokerStove-style strings (e.g. `"AQs+, 0.4(AsKs)"`). Equity functions `py_hand_vs_range_exact`, `py_hand_vs_range_monte_carlo`, `py_all_hands_vs_range` do not yet support weighted ranges and "could benefit from optimization". The `Deck` class is pure Python and described as too slow for full range-vs-range work — [PyPI eval7](https://pypi.org/project/eval7/)
- The GitHub repo `JulianAndrews/eval7` returned 404 from the GitHub API on 2026-10-31 (repo may have moved/renamed); PyPI remains the authoritative source — [GitHub API](https://api.github.com/repos/JulianAndrews/eval7)
- `treys`: Python 3 port of Deuces; handles 5, 6 and 7 card lookups (6/7 by evaluating 5-card combinations); "bit arithmetic and dictionary lookups"; MIT; `pip install treys`; README says it won't beat a C implementation; no Omaha documented (repo contains `plo_go.py`/`plo_perf.py` but unexplained) — [treys README](https://github.com/ihendley/treys)
- treys last pushed 2023-07-15, 181 stars, MIT; deuces last pushed 2024-07-08, 625 stars, no SPDX license detected — [GitHub API treys](https://api.github.com/repos/ihendley/treys), [GitHub API deuces](https://api.github.com/repos/worldveil/deuces)
- PokerKit's own benchmark (single core i7-1255U, Python 3.11.5): PokerKit 1,016,740 hands/s vs Treys 3,230,966 hands/s for standard high hands; docs recommend C++ (OMPEval) if speed is critical. Hand types: standard high, Greek, Omaha, standard low, 8-or-better, Omaha 8-or-better, short-deck, regular low, badugi, standard badugi, Kuhn, Rhode Island — [PokerKit evaluation docs](https://pokerkit.readthedocs.io/en/latest/evaluation.html)
- pokerkit last pushed 2026-10-12, 517 stars, MIT — [GitHub API](https://api.github.com/repos/uoftcprg/pokerkit)
- MIT Pokerbots' own evaluator `pkrbot` 1.1.0 on PyPI: "Fast poker hand evaluation library with eval7-compatible API", MIT; releases 1.0.3, 1.0.4, 1.1.0 — [PyPI pkrbot JSON](https://pypi.org/pypi/pkrbot/json)

**Rust**
- `rs_poker` 5.1.0 published 2026-08-13, 102k downloads; repo pushed 2026-08-13, 185 stars, Apache-2.0 — [crates.io](https://crates.io/api/v1/crates/rs_poker), [GitHub API](https://api.github.com/repos/elliottneilclark/rs-poker)
- rs-poker README claims ~20 ns per 5-card evaluation (~50M hands/s) and <25 ns per 7-card evaluation, fuzz-validated; older releases claimed ~16 ns; self-reported with no hardware stated — [crates.io README mirror (2.0.0)](https://crates-io.ganymede-static.progval.net/crates/rs_poker/2.0.0)
- rs_poker modules: `core` (cards, hand values), `holdem` (range parsing via `RangeParser` for strings like "KQo+", `MonteCarloGame` for equity vs a set of hands), `arena` (agent-trait game simulator, "most experimental", "most likely to change") — [docs.rs rs_poker](https://docs.rs/rs_poker/latest/rs_poker/)
- `aya_poker` 0.1.0 (2023-10-31), 10k downloads; port of OMPEval to Rust; no_std by default; supports standard, A-5 lowball, 2-7 lowball, six-or-better (short-deck), Omaha, Omaha Hi/Lo, Badugi, Baduci; 0–7 cards; compile-time perfect-hash tables; license "Zlib OR Apache-2.0 OR MIT"; no benchmark figures on docs.rs — [docs.rs aya-poker](https://docs.rs/aya-poker), [crates.io](https://crates.io/api/v1/crates/aya-poker); repo pushed 2023-11-24, 9 stars — [GitHub API](https://api.github.com/repos/dtrifuno/aya-poker)
- `rust_poker` 0.1.14 (2021-03-04): "rust rewrite of zekyll's C++ equity calculator, OMPEval"; repo pushed 2021-03-04, MIT, 22 stars — [crates.io](https://crates.io/api/v1/crates/rust_poker), [GitHub API](https://api.github.com/repos/kmurf1999/rust_poker)
- `poker` crate 0.7.0 published 2025-06-15, 23k downloads — [crates.io](https://crates.io/api/v1/crates/poker)
- A crate named `holdem-hand-evaluator` was not found on crates.io on 2026-10-31 — [crates.io API](https://crates.io/api/v1/crates/holdem-hand-evaluator)

**Go**
- `chehsunliu/poker`: port of deuces; 5/6/7 cards; author benchmark (darwin/amd64, 4 cores) 253 ns/op 5-card, 16,357 ns/op 7-card (7-card is combinatorial, not a 7-card table); last pushed 2023-04-17, MIT, 83 stars — [pkg.go.dev](https://pkg.go.dev/github.com/chehsunliu/poker), [GitHub API](https://api.github.com/repos/chehsunliu/poker)
- Nerdmaster/poker reports (Go 1.17.1, 16 threads) 141 ns/op 5-card, 10,406 ns/op 7-card — [Nerdmaster/poker](https://github.com/nerdmaster/poker)

**Java**
- No widely used, maintained fast 7-card Java library surfaced. Candidates: Klaatu `FastEval` (table-driven, 5/6/7 cards, source survives only in third-party archives) — [javatips archive](https://www.javatips.net/api/opentestbed-master/src/main/java/common/handeval/klaatu/FastEval.java); jmp/poker-hand-evaluator is 5-card only, MIT — [ecosyste.ms listing](https://awesome.ecosyste.ms/projects/github.com%2Fjmp%2Fpoker-hand-evaluator)

**TypeScript / Node**
- `@pokertools/evaluator` 2.1.0 published 2026-10-13, MIT; its docs report ~17.9M 7-card hands/s with integer input vs pokersolver ~71k hands/s with string input — [npm registry](https://registry.npmjs.org/@pokertools/evaluator), [yarn package page](https://classic.yarnpkg.com/en/package/@pokertools/evaluator)
- `poker-evaluator` (chenosaurus) 2.1.1 published 2025-08-18, ISC; README claims ~22M hands/s on a 2.7 GHz quad-core MacBook Pro; a third-party benchmark measured ~1.4M/s with string input; repo last pushed 2020-02-16 — [npm registry](https://registry.npmjs.org/poker-evaluator), [npm page](https://www.npmjs.com/package/poker-evaluator), [GitHub API](https://api.github.com/repos/chenosaurus/poker-evaluator)
- `pokersolver` 2.1.4 published 2020-07-20, MIT; repo last pushed 2022-02-21, 442 stars — [npm registry](https://registry.npmjs.org/pokersolver), [GitHub API](https://api.github.com/repos/goldfire/pokersolver)
- `phe` (JS port of PHEvaluator) 0.6.0 published 2018-03-22, MIT — [npm registry](https://registry.npmjs.org/phe)

### Inferences
- Evaluator speed is not the bottleneck in any compiled language; in Python the evaluator call overhead (~0.3 µs for treys, less for a C extension) is dwarfed by pure-Python dealing/shuffling loops, which is why eval7's own README warns its `Deck` is too slow for range-vs-range work.
- If the competition engine is multiway or short-deck, PHEvaluator (Omaha) / aya-poker and pokerkit (short-deck) are the only options above that document variant support; OMPEval, treys, eval7 and the Node libraries are Hold'em-only.
- OMPEval's 2020 last push is not a practical risk: it is a header+static-lib C++ project with no dependencies and ports (aya-poker, rust_poker) exist; but Windows users must compile by hand.

### Gaps
- No single benchmark runs all evaluators on the same hardware; numbers above are self-reported on different machines (3770k from 2012 for OMPEval; 2023 12-core for PHEvaluator; i7-1255U for pokerkit/treys). Run a 60-second local microbenchmark before the event.
- No benchmark figures found for `phevaluator`'s Python binding or `eval7` specifically (only the C core of PHEvaluator).
- No maintained Java fast evaluator found; a Java-only skeleton would require vendoring a 2+2 or Cactus-Kev port.

## Key question 2: Equity calculation — Monte Carlo vs exhaustive, range-vs-range libraries, samples needed for ±1%

### Takeaway
A worst-case 95% margin of ±1% needs ~9,600 Monte Carlo samples (±2% needs ~2,400; ±0.5% needs ~38,400); at compiled-evaluator speeds that is sub-millisecond, in pure Python it is tens to hundreds of milliseconds unless the sampling loop is vectorised or in C. OMPEval (C++) remains the reference range-vs-range calculator; in Python, eval7 and pokerkit give range-aware Monte Carlo with modest speed; rs_poker gives it in Rust.

### Cited Findings
- Wald interval: p ≈ p̂ ± z·sqrt(p̂(1−p̂)/n), z = 1.96 at 95%; the Wikipedia article notes Wald performs poorly for small n or p near 0/1 and recommends Wilson — [Wikipedia: Binomial proportion confidence interval](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval)
- OMPEval `EquityCalculator`: `eq.start({"AK","QQ"}); eq.wait(); eq.getResults().equity[i]`; Monte Carlo uses a random-walk that avoids full resampling after hole-card collisions; supports enumeration and Monte Carlo, multithreaded; claimed 2–10x per-thread faster than free EquiLab — [OMPEval README](https://github.com/zekyll/OMPEval)
- eval7 range-vs-hand functions exist (`py_hand_vs_range_exact`, `py_hand_vs_range_monte_carlo`, `py_all_hands_vs_range`) but unweighted and unoptimised per the author — [PyPI eval7](https://pypi.org/project/eval7/)
- pokerkit `calculate_equities(ranges, board, hole_dealing_count, board_dealing_count, deck, hand_types, sample_count=..., executor=...)` and `calculate_hand_strength(player_count, ...)` are Monte Carlo, accept `parse_range(...)` inputs, support 2- and 3-player examples, and can use a `ProcessPoolExecutor`; examples use `sample_count` 1,000 and 10,000; no timing figures published — [PokerKit analysis docs](https://pokerkit.readthedocs.io/en/latest/analysis.html)
- rs_poker `holdem::MonteCarloGame` simulates equity vs a set of hands; `RangeParser` parses range strings — [docs.rs rs_poker](https://docs.rs/rs_poker/latest/rs_poker/)
- A forum post on EquiLab's preflop speed notes that precomputing all 28,561 (=169×169) preflop hand-class matchups makes heads-up preflop lookup instantaneous — [pokerstrategy.com forum](https://www.pokerstrategy.com/forum/poker-tools-1361/how-does-equilab-calculate-preflop-range-vs-range-equity-so-fast-523836/)
- PHEvaluator full enumeration of all 7-card hands runs at 60M/s in C — [PokerHandEvaluator README](https://github.com/HenryRLee/PokerHandEvaluator)

### Inferences
- Sample sizes (derived from the Wald formula above, worst case p=0.5): n = 0.96/E² → ±1% ≈ 9,604; ±2% ≈ 2,401; ±0.5% ≈ 38,416; ±3% ≈ 1,068.
- Latency estimate: 10k samples × 2 seven-card evaluations = 20k evals. At OMPEval's ~270M/s random-hand rate the evaluation cost is ~0.07 ms; dealing dominates, so expect ~1 ms per 10k-sample heads-up equity in C++/Rust. In pure Python with treys (3.2M evals/s) the evaluations alone are ~6 ms and the Python dealing loop realistically pushes a 10k-sample estimate to 50–300 ms. These are derived from the cited evaluator rates, not measured.
- Exhaustive is cheap post-flop heads-up with a known opponent hand (river: 0 outcomes; turn: 44 rivers; flop: 990 turn+river combos) and expensive preflop (all 5-card boards) or vs ranges; the practical split is: enumerate on turn/river, Monte Carlo on flop vs ranges, lookup table preflop.
- In Python, the safe route under time pressure is to precompute preflop (169×169 heads-up, 169×N-opponent random) offline with OMPEval or a numpy/numba loop, and keep decision-time Monte Carlo to ≤2,000 samples (±2%) unless a C extension handles dealing.

### Gaps
- No published wall-clock figures for pokerkit or eval7 Monte Carlo equity at a given sample count; must be benchmarked locally.
- Could not verify a maintained, downloadable 169×169 all-in equity matrix from a reputable source (see Q4).

## Key question 3: CFR / game-solving libraries — can they yield a usable HUNL strategy on a laptop in hours, and can a bot load it?

### Takeaway
Nothing off-the-shelf produces a full-game HUNL blueprint on a laptop in hours. What is realistic: (a) OpenSpiel `universal_poker` with `bettingAbstraction=fcpa`/`fchpa` and tabular CFR/MCCFR on a reduced game (small stacks, fewer ranks/rounds) exported as a policy dict; (b) b-inary's `postflop-solver` (Rust, AGPL, suspended since Oct 2023) or TexasSolver (C++, AGPL, pushed Oct 2026, JSON export) to pre-solve a handful of common flop subtrees; (c) HoldemResources' heads-up push/fold Nash tables for short stacks. PokerRL, Deep-CFR, DeepStack-Leduc and fedden/poker_ai are research code, stale or archived, and do not ship usable NLHE strategies.

### Cited Findings
- OpenSpiel last pushed 2026-10-30, 5,567 stars, Apache-2.0 — [GitHub API](https://api.github.com/repos/google-deepmind/open_spiel)
- `universal_poker` wraps the ACPC environment (ethansbrown/acpc), contributed Nov 2019, "has not been extensively reviewed or tested by the DeepMind OpenSpiel team"; it is an optional dependency — [universal_poker README](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/games/universal_poker/README.md)
- The build flag is `OPEN_SPIEL_BUILD_WITH_ACPC`, defaulting to `$DEFAULT_OPTIONAL_DEPENDENCY` in `global_variables.sh` — [open_spiel/scripts/global_variables.sh](https://raw.githubusercontent.com/google-deepmind/open_spiel/master/open_spiel/scripts/global_variables.sh)
- `universal_poker` parameters and defaults: numPlayers=2, betting="nolimit" (or "limit"), stack="1200 1200", blind="100 100", raiseSize (limit only), numRounds=2, firstPlayer="1 1", maxRaises unset (ACPC default UINT8_MAX), numSuits=4 (must be 4), numRanks=6, numHoleCards=1, numBoardCards="0 1", bettingAbstraction="fcpa", calcOddsNumSims=0, potSize/boardCards/handReaches for subgames. Abstractions: `fc` (fold/check-call), `fcpa` (+pot bet, all-in), `fchpa` (+half-pot), `fullgame` (action N = raise to N chips). Max 10 players. Can also load an ACPC gamedef string via `LoadUniversalPokerGameFromACPCGamedef` — [universal_poker.cc](https://raw.githubusercontent.com/google-deepmind/open_spiel/master/open_spiel/games/universal_poker/universal_poker.cc)
- OpenSpiel algorithms table lists tabular CFR, CFR-BR, external- and outcome-sampling MCCFR, Deep CFR, XFP, NFSP, RCFR — [docs/algorithms.md](https://raw.githubusercontent.com/google-deepmind/open_spiel/master/docs/algorithms.md)
- OpenSpiel install: pip binary wheels are x86_64 only (new in 1.0.0); Linux/macOS supported, Windows separate; Python version statements in install.md are inconsistent (tests on 3.7–3.10, rest supports 3.11, JAX parts need ≥3.12); install.md does not say whether pip wheels include universal_poker — [docs/install.md](https://raw.githubusercontent.com/google-deepmind/open_spiel/master/docs/install.md)
- A student project reports training on OpenSpiel universal_poker only in a simplified limit-style variant, not full HUNL — [Group-9 final report](https://whygukin.github.io/Group-9/final.html)
- The unabstracted HUNL game has on the order of 10^160–10^161 decision points, so full solving requires abstraction — [arXiv 2509.23747](https://arxiv.org/pdf/2509.23747)
- rlcard: envs `limit-holdem` (~10^14 infosets), `no-limit-holdem` (~10^162 infosets, action size 10^4), `leduc-holdem`; algorithms DMC, DQN, NFSP, CFR (`examples/run_cfr.py`); the only pretrained poker model is `leduc-holdem-cfr`; rule models for leduc and limit holdem only; `pip3 install rlcard[torch]`; MIT; Python 3.6+ — [rlcard README](https://github.com/datamllab/rlcard); last pushed 2024-06-26, 3,586 stars — [GitHub API](https://api.github.com/repos/datamllab/rlcard)
- PokerRL last pushed 2023-03-31 (MIT, 547 stars); Deep-CFR last pushed 2020-05-06 (MIT, 335 stars) — [GitHub API PokerRL](https://api.github.com/repos/EricSteinberger/PokerRL), [GitHub API Deep-CFR](https://api.github.com/repos/EricSteinberger/Deep-CFR)
- DeepStack-Leduc: Lua, last pushed 2018-01-06, no license detected — [GitHub API](https://api.github.com/repos/lifrordi/DeepStack-Leduc)
- fedden/poker_ai: archived 2024-07-16 (read-only); MCCFR with clustering (`poker_ai cluster` → `card_info_lut.joblib`); "Currently we only support a 20 card deck without modification"; GPL-3; does not confirm a shipped usable strategy; training compute not stated — [poker_ai README](https://github.com/fedden/poker_ai), [GitHub API](https://api.github.com/repos/fedden/poker_ai)
- b-inary/postflop-solver: Rust, Discounted CFR (γ=3.0), no card abstraction but isomorphic turn/river chances merged, multithreaded, SIMD; bunching effect up to four folded players; serialisation via `bincode` (default) and optional `zstd`; postflop only; git dependency only (`postflop-solver = { git = "https://github.com/b-inary/postflop-solver" }`), breaking changes without version bumps; AGPL-3.0; "As of October 2023 ... suspend development" — [postflop-solver README](https://github.com/b-inary/postflop-solver); last pushed 2024-07-09, 378 stars — [GitHub API](https://api.github.com/repos/b-inary/postflop-solver); wasm-postflop and desktop-postflop also suspended — [search summary](https://www.github.com/b-inary/wasm-postflop)
- TexasSolver (bupticybee): C++ port of TexasHoldemSolverJava ("5x faster than the java version, <1/3 memory"); Hold'em and short deck; benchmark same flop spot spr=10, 6 threads: PioSolver 1.0 492 MB / 0.29% / 242 s vs TexasSolver 0.1.0 1600 MB / 0.275% / 172 s; dumps strategy to JSON; console branch builds with CMake/MinGW; GPU version claimed >20x faster; AGPL-3 with personal use free, embedding the solver code or offering as a service requires a commercial license; 2.6k stars — [TexasSolver README](https://github.com/bupticybee/TexasSolver); last pushed 2026-10-08 — [GitHub API](https://api.github.com/repos/bupticybee/TexasSolver)
- Slumbot's own CFR code (slumbot2019: CFR+, MCCFR, endgame resolving, abstraction tools) is MIT, C++, last pushed 2023-09-18; the repo has no API client or API docs — [slumbot2019 README](https://github.com/ericgjackson/slumbot2019), [GitHub API](https://api.github.com/repos/ericgjackson/slumbot2019), [repo root listing](https://api.github.com/repos/ericgjackson/slumbot2019/contents/)
- HoldemResources heads-up push/fold Nash charts (pusher/caller max stack in bb, No Ante and Ante 10% variants, "20+" cap) are publicly viewable and a raw data zip covering 1–200 bb in 0.05 bb steps is downloadable; page notes push/fold is "generally only advisable up to about 10bb" — [holdemresources.net/hune](https://www.holdemresources.net/hune)
- An open-source C++ heads-up all-in-or-fold Nash solver exists (rt500/Heads-Up-Push-or-Fold) — [GitHub](https://www.github.com/rt500/Heads-Up-Push-or-Fold)
- Open-source HoldemSolver (88-degrees) exports strategies to JSON — [GitHub](https://github.com/88-degrees/HoldemSolver)

### Inferences
- A one-hour window cannot absorb solver integration; anything solver-derived must be precomputed into flat lookup tables (JSON/npz) before the event, keyed by abstracted state (position, street, pot/stack bucket, hand bucket). TexasSolver's JSON dump and postflop-solver's bincode are both loadable, but only TexasSolver has a maintained build in 2026.
- OpenSpiel is the only ready CFR stack that runs end-to-end in Python, but its value is limited to toy/abstracted games; a `fcpa` 2-round small-stack game is solvable in minutes, full 4-round 200bb HUNL is not. Treat it as a way to generate preflop/short-stack heuristics, not a blueprint.
- AGPL on postflop-solver and TexasSolver matters only if the bot code is distributed; using precomputed tables they emit is fine for a hackathon, but do not vendor their source into a repo you will publish under a permissive license.

### Gaps
- No source gives measured laptop solve times for OpenSpiel universal_poker CFR at any abstraction; "minutes vs hours" above is inference.
- Could not fetch Slumbot's API documentation (slumbot.com is a JS app; the slumbot2019 repo has no client). The GTO Wizard paper confirms only that a public API exists since 2021. Protocol details (endpoints, token flow) must be read from slumbot.com's "API" link in a browser.
- Did not find any free, redistributable full-game HUNL blueprint strategy file.

## Key question 4: Precomputable assets — preflop equity tables, push/fold charts, opening ranges, flop buckets, E[HS²]

### Takeaway
The highest-value precomputes are (1) a 169-class heads-up all-in equity matrix plus 169×N-opponents random-hand equity (compute locally with OMPEval or phevaluator; no trustworthy downloadable matrix found), (2) HoldemResources' Nash push/fold raw data (free zip, 1–200 bb), and (3) small E[HS]/E[HS²] tables for flop hand bucketing. No free, redistributable GTO-Wizard-style 100bb heads-up opening/3-bet range set in machine-readable form was found.

### Cited Findings
- 169 strategically distinct starting-hand classes = 13 pairs + 78 suited + 78 offsuit, reducing 1,326 combos — [pokerstrategy forum (citing Wikipedia)](https://www.pokerstrategy.com/forum/poker-tools-1361/how-does-equilab-calculate-preflop-range-vs-range-equity-so-fast-523836/)
- Precomputing all 28,561 class-vs-class matchups makes preflop lookup instantaneous — same source
- Deuces Cracked publishes exact all-in equity for only 25 common heads-up confrontations, not a full grid — [deucescracked.com](https://www.deucescracked.com/blog/preflop-poker-equity-matchups-exact-data)
- A PDF titled "Preflop Hand Equity By Number Of Players" (2026-03) exists but provenance is unverified — [pokerrailbird.com PDF](https://pokerrailbird.com/wp-content/uploads/2026/03/Preflop_Hand_Equity_By_Number_Of_Players.pdf)
- HoldemResources heads-up Nash push/fold: raw data zip for 1–200 bb at 0.05 bb steps; charts simplified from exact solution; No Ante / Ante 10% variants — [holdemresources.net/hune](https://www.holdemresources.net/hune)
- E[HS²] is the average of the squared hand-strength value over all rollouts of the remaining cards; it rewards hands that are very strong on some rivers and weak on others; buckets are formed by percentile bucketing or k-means on E[HS]/E[HS²] — [arXiv 1807.00900](https://arxiv.org/pdf/1807.00900); Effective Hand Strength (HS plus positive/negative potential) background — [Wikipedia: Effective hand strength algorithm](https://en.wikipedia.org/wiki/Effective_hand_strength_algorithm)
- PHEvaluator enumerates all 7-card hands at 60M/s and OMPEval evaluates random hands at ~270M/s single-thread (used below to size compute) — [PokerHandEvaluator README](https://github.com/HenryRLee/PokerHandEvaluator), [OMPEval README](https://github.com/zekyll/OMPEval)
- OMPEval's README says EquiLab uses precalculated results for heads-up enumeration (i.e. the standard practice is a precomputed heads-up preflop table) — [OMPEval README](https://github.com/zekyll/OMPEval)
- libregto (MIT) ships GTO opening ranges in a `ranges.js` file (coverage/format not verified) — [GitHub rdpharr/libregto](https://github.com/rdpharr/libregto); a hosted "pokerdata" MCP serves preflop ranges with 6-max NL free but no NLHE heads-up 100bb option listed — [glama.ai listing](https://glama.ai/mcp/connectors/io.github.hft-studio/pokerdata)
- Pokertrainer.se ranges are 6-max 100bb simplified pure-strategy, not heads-up — [pokertrainer.se](https://pokertrainer.se/preflop-introduction/)

### Inferences
- Sizes: a 169×169 float32 heads-up matrix is 114 KB; a 169×{1..8 opponents} table is 5 KB; both fit in source as a literal. A per-flop E[HS²] table over 1,755 strategically distinct flops × 169 classes (float16) is ~0.6 MB; a full per-flop × per-hand-combo table is larger but still single-digit MB.
- Compute time (derived from cited evaluator rates): heads-up 169×169 by Monte Carlo at 100k samples per matchup = 2.9×10^9 matchups × 2 evals ≈ 20–40 s per core with OMPEval; exact enumeration is also feasible in minutes in C++ (OMPEval's enumerator does it natively). In pure Python the same job is hours; use numba/numpy or the C++ tool and ship the result.
- A "free GTO-Wizard-style" heads-up 100bb range set does not exist as a verified download; the honest substitute is: HoldemResources Nash for ≤20 bb, a hand-written heads-up opening range (e.g. SB opens ~70–85% of hands, which the agent can justify from the equity table), and solver-free 3-bet/4-bet thresholds by equity rank. This is inference; no cited source gives those percentages.

### Gaps
- No reputable, verifiable downloadable 169×169 all-in equity matrix located (hits were low-quality mirror sites); plan to compute it.
- Did not confirm the contents of HoldemResources' raw zip (format, columns) — download and inspect before the event.
- No free machine-readable heads-up 100bb opening/3-bet GTO ranges found; GTO Wizard's own terms for reuse were not checked.
- No source for precise flop-texture bucket counts or recommended bucket numbers for a hackathon-scale bot.

## Key question 5: Language recommendation given agent-written code in a one-hour window

### Takeaway
Default to Python for the bot shell (what competition skeletons almost always provide, what the engine protocol examples are in, and where Claude Code is most fluent), with the heavy numeric path either (a) pre-tabled, or (b) delegated to a C-extension evaluator (`phevaluator`/`eval7`/`pkrbot`) and a numpy-vectorised Monte Carlo loop. Keep a Rust (`rs_poker`) or C++ (OMPEval) fallback pre-built only as an offline precompute tool, not as the submission language, unless the skeleton is C++/Java only.

### Cited Findings
- MIT Pokerbots 2026 ships skeletons in Python, Java and C++; Python needs ≥3.8 via `uv` with deps `cython 3.2.3` and `pkrbot 1.0.4`; C++ needs C++17, CMake ≥3.8 and Boost (for socket I/O), WSL on Windows; Java ≥8 (17 recommended) — [engine-2026 README](https://github.com/mitpokerbots/engine-2026)
- MIT engine 2026 config: `STARTING_GAME_CLOCK = 60.0` s total per bot across `NUM_ROUNDS = 1000` hands, `STARTING_STACK = 400`, blinds 1/2, `BUILD_TIMEOUT = 10` s, `CONNECT_TIMEOUT = 10` s, `PLAYER_TIMEOUT = 120`, `ENFORCE_GAME_CLOCK = True`, player log cap 512 KB — [engine-2026 config.py](https://raw.githubusercontent.com/mitpokerbots/engine-2026/master/config.py)
- MIT engine protocol: the engine binds a TCP socket on an ephemeral port, launches the bot as a subprocess, and exchanges newline-delimited text; per-round messages start `T<clock>`, `P<seat>`, `H<cards>`, `G`; final `A<delta>`; `Q` to quit; action codes `F` fold, `C` call, `K` check, `R` raise, `D<card>` discard — [engine-2026 engine.py](https://raw.githubusercontent.com/mitpokerbots/engine-2026/master/engine.py)
- ACPC dealer protocol (used by OpenSpiel universal_poker and the GTO Wizard benchmark): dealer is a TCP server, clients connect; messages are CRLF-terminated; lines starting `#` or `;` can be ignored; `MATCHSTATE:<position>:<hand#>:<betting>:<cards>` and the client replies with the same string plus `:<action>` (e.g. `r250`) — [DeepWiki acpc-server protocol summary (secondary)](https://deepwiki.com/crissilvaeng/acpc-server/3.2-acpc-protocol)
- GTO Wizard Benchmark: public RESTful API with example code at gtowizard-ai/researcher-api-client; HUNL under ACPC rules, blinds 50/100, 200 bb (20,000 chip) stacks reset every hand; AIVAT variance reduction cuts standard deviation ~3x — [arXiv 2603.23660](https://arxiv.org/html/2603.23660)
- Python evaluator availability: phevaluator wheels CPython 3.10–3.14 (Jul 2026), eval7 wheels CPython 3.9–3.15 (Jul 2026), pkrbot 1.1.0 eval7-compatible API — [PyPI phevaluator](https://pypi.org/project/phevaluator/), [PyPI eval7](https://pypi.org/project/eval7/), [PyPI pkrbot](https://pypi.org/pypi/pkrbot/json)
- Rust `rs_poker` 5.1.0 (Aug 2026) bundles evaluator, range parser, Monte Carlo and an arena simulator in one Apache-2.0 crate — [crates.io](https://crates.io/api/v1/crates/rs_poker), [docs.rs](https://docs.rs/rs_poker/latest/rs_poker/)
- Node's fast evaluator `@pokertools/evaluator` was released 2026-10-13 (MIT) — [npm registry](https://registry.npmjs.org/@pokertools/evaluator)
- Go and Java lack maintained fast 7-card libraries (see Q1 findings) — [pkg.go.dev chehsunliu/poker](https://pkg.go.dev/github.com/chehsunliu/poker), [Java search summary](https://www.javatips.net/api/opentestbed-master/src/main/java/common/handeval/klaatu/FastEval.java)
- OpenSpiel pip wheels are x86_64 only and it is unclear whether they include universal_poker — [docs/install.md](https://raw.githubusercontent.com/google-deepmind/open_spiel/master/docs/install.md)

### Inferences
- Budget arithmetic: MIT's 60 s clock over 1,000 hands with ~3–4 decisions per hand gives ~15–20 ms per decision. In Python that allows roughly 1–2k Monte Carlo samples per decision with a C-extension evaluator (±2–3%), or unlimited table lookups. If the Sequoia engine has a similar per-game clock, Monte Carlo at decision time must be capped and the preflop table is mandatory.
- Risk ranking for a 60-minute agent-written build: Python < TypeScript < Rust < C++ < Go/Java. Python wins on skeleton availability, install (one `pip install` of a wheel), and agent fluency; TypeScript is viable only if the engine speaks a simple socket/JSON protocol and `@pokertools/evaluator` is pre-installed; Rust is the best "fast and safe" choice but costs compile cycles and cargo network access; C++ carries Boost/CMake friction (MIT's own skeleton needs Boost); Go/Java lack a drop-in evaluator.
- Pre-build for both worlds: a Python package (evaluator + tables + Monte Carlo + protocol adapters for socket, stdin, and class-skeleton), plus a single statically linked Rust/C++ CLI (`equity <hero> <board> <range> <n>`) that Python can shell out to if the engine gives generous time. Pre-download wheels (`pip download phevaluator eval7 numpy`) so an offline or slow venue network cannot block install.

### Gaps
- The Sequoia event's engine, protocol, time limit and permitted languages are unknown; the MIT numbers are the only concrete reference point found.
- No measured numba vs numpy vs C-extension Monte Carlo timings were found; the per-decision sample budget above is inference from evaluator rates.

## Key question 6: Testing harness — local engines/simulators and strong-bot benchmarks

### Takeaway
For local bot-vs-bot play use the MIT engine-2026 (Python, socket protocol, logs, 1,000-hand matches, game clock) or pokerkit (maintained, Oct 2026, full NLHE state machine with equity tools); PyPokerEngine and rlcard still install but are dormant (2024) and Python-2-era in PyPokerEngine's case. For a strong external benchmark, Slumbot's public API (HUNL 200 bb) is the historical standard and the GTO Wizard Benchmark API (March 2026, AIVAT-adjusted) is the stronger, better-instrumented alternative.

### Cited Findings
- MIT engine-2026: Python engine, runs two bots configured in `config.py` (`PLAYER_1_PATH`, `PLAYER_2_PATH`), writes `gamelog`, enforces a 60 s game clock over 1,000 rounds, 400-chip stacks, 1/2 blinds; 2026 variant deals 3 hole cards and discards one face-up after the flop; last pushed 2026-01-16; the org also hosts reference bots, a scrimmage server and an online playground — [engine-2026 README](https://github.com/mitpokerbots/engine-2026), [config.py](https://raw.githubusercontent.com/mitpokerbots/engine-2026/master/config.py), [GitHub API](https://api.github.com/repos/mitpokerbots/engine-2026), [mitpokerbots org](https://github.com/mitpokerbots)
- pokerkit: hand-type coverage incl. short-deck and Omaha, Monte Carlo equity with optional multiprocessing; last pushed 2026-10-12, MIT — [PokerKit evaluation docs](https://pokerkit.readthedocs.io/en/latest/evaluation.html), [PokerKit analysis docs](https://pokerkit.readthedocs.io/en/latest/analysis.html), [GitHub API](https://api.github.com/repos/uoftcprg/pokerkit)
- PyPokerEngine: `BasePokerPlayer` subclass with `declare_action` and `receive_*` callbacks; `Emulator` class for RL; PyPokerGUI for browser play; README claims Python 2.7 and 3.5 support; MIT; no speed figures; last pushed 2024-04-10, 726 stars — [PyPokerEngine README](https://github.com/ishikota/PyPokerEngine), [GitHub API](https://api.github.com/repos/ishikota/PyPokerEngine)
- rlcard: `no-limit-holdem` env with DMC/DQN/NFSP/CFR example scripts; only Leduc has a pretrained CFR model; last pushed 2024-06-26 — [rlcard README](https://github.com/datamllab/rlcard), [GitHub API](https://api.github.com/repos/datamllab/rlcard)
- rs_poker `arena` module: implement an `Agent` trait and simulate Hold'em games in Rust (experimental) — [docs.rs rs_poker](https://docs.rs/rs_poker/latest/rs_poker/)
- OpenSpiel `universal_poker` gives an ACPC-rules HUNL/limit environment with configurable stacks/blinds/abstraction for self-play evaluation — [universal_poker.cc](https://raw.githubusercontent.com/google-deepmind/open_spiel/master/open_spiel/games/universal_poker/universal_poker.cc)
- Slumbot: 2018 ACPC champion; public API released 2021 by Eric Jackson for benchmarking; abstraction-based so "vulnerable to potential exploits"; lacks strong variance reduction so significant results are expensive — [arXiv 2603.23660](https://arxiv.org/html/2603.23660); heads-up cash, constant 200 bb stacks — [arXiv 2509.22387 (SpinGPT)](https://arxiv.org/pdf/2509.22387)
- Reported results vs Slumbot: GTO Wizard AI +19.4 ± 4.1 bb/100 over 150k hands (2022) — [arXiv 2603.23660](https://arxiv.org/html/2603.23660); a Sept-2025 leaderboard snapshot lists PokerGPT 15.8 bb/100 (10k hands), SpinGPT-SFT 13.4 ± 12.9 (30k), AlphaHoldem 11.2 (100k), ReBeL 4.5 — [wizwand SOTA page (secondary)](https://www.wizwand.com/sota/heads-up-no-limit-hold-em-poker-on-slumbot-benchmark-agent)
- GTO Wizard Benchmark: public REST API (example client gtowizard-ai/researcher-api-client), HUNL ACPC rules, 50/100 blinds, 20,000-chip stacks reset each hand, AIVAT; LLM agents at 5,000 hands each all lose heavily (best GPT-5.3 Extra High −16 ± 3 bb/100; Claude Opus 4.6 −20.4 ± 8.6; check/call −241; random −285; all-in −381; always-fold −64.6 ± 3.3) — [arXiv 2603.23660](https://arxiv.org/html/2603.23660)

### Inferences
- Throughput: none of the Python engines publish hands/s. The MIT engine spawns bots as subprocesses and round-trips over a socket per action, so it is bounded by bot latency, not the engine; with trivial bots thousands of hands per minute is plausible, but measure it. For statistical power, AIVAT-free self-play needs on the order of 10^5 hands to resolve a few bb/100, so local A/B tests in the hour should use duplicate-style seeding (same cards, swapped seats) rather than raw hand counts.
- The always-fold baseline (−64.6 bb/100 under 50/100 blinds) is a useful sanity floor: any bot losing more than that to a strong opponent is worse than folding every hand.
- Slumbot remains the practical "is my bot not embarrassing" benchmark; the GTO Wizard API is better instrumented but its access terms were not confirmed.

### Gaps
- Slumbot API protocol details (endpoints, auth token, hands per session, rate limits) were not retrievable from fetched sources; slumbot.com renders client-side. Verify in a browser before relying on it.
- GTO Wizard Benchmark API cost, rate limits and signup requirements not stated in the paper.
- No measured hands-per-second numbers found for MIT engine, pokerkit, PyPokerEngine or rlcard environments.
- The deepwiki ACPC protocol page is a secondary summary; the official `project_acpc_server` protocol PDF was not fetched (rate-limited).
