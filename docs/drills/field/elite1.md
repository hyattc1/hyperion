# rival_bot build log

## What was built (all in this folder, standard library only, written from scratch)
- `ev.py` — 7-card evaluator (prime-product dictionary for non-flush rank multisets + 8192-entry flush/straight table, ~2.7 us/eval), the 169-class preflop index, and the postflop feature classifier (made-hand class x draw class x board texture).
- `precompute.py` → `tables.json` — (a) 169x169 heads-up preflop equity matrix (400 Monte Carlo deals per class pair), (b) postflop bucket equities: for every (street, made class, draw, texture) key, equity vs a random hand and vs opponents whose own bucket equity is >= 0.45 / 0.60 / 0.75 (700k deals per street, two-pass), with coarser fallback keys.
- `build.py` — turns the tables into embedded literals: range-equity table EQR[169][20] (hand vs top-x% for 20 widths), hand percentiles, and the postflop dict (shrunk toward coarse keys when sparse). `bot_src.py` + tables → `vN.py` / `rival_bot.py` (~100 KB, imports in ~0.03 s).
- `engine.py` — full 8-max NLHE SNG simulator: blinds schedule, button/blind rules incl. heads-up, min-raise and short all-in reopening rules, side pots, odd chips, bust ordering, 200-hand cap with exact Malmuth-Harville ICM over 10/7/5/4/3/2/1/0; duplicate deals (cards fixed per seed/hand/seat, 8 cyclic seat rotations); options for blind posts in history (as post/raise/call/blind) and hand_end(None/partial).
- `opps.py` — test opponents: RandomBot (random legal), Station, Maniac, Nit, TAG (MC equity), PushFold (Chen-threshold shover), Exploiter (adaptive: tracks fold-to-raise and aggression per seat; steals/barrels vs folders), Solver (near-Nash push/fold by position + tight-aggressive deep + MC postflop), Aggro (exploits predictable checkers/folders: stabs 70% when checked to, 3bets 20%, shoves 45% short). Plus every earlier version of my own bot (v1..v10) and parameter variants of it (LAG, nit, wide-jam) as opponents.
- Measurement: `run_match.py` (fields x heroes on identical seeds, mean, 95% CI, paired differences), `endgame.py` (low-variance targeted tests: heads-up from 15-35bb, 4-handed from 20bb, first-60-hands ICM), `fieldstats.py`, `places.py`, `bustlog.py`, `probe.py` (prints jam/call ranges), `robust.py` + `fuzz.py` (format robustness), `slowcheck.py`/`gccheck.py` (latency).

## Approach (why)
The format rewards survival and placing more than chip accumulation: payouts 10/7/5/4/3/2/1/0 are nearly linear below 2nd, busting 8th scores 0, and the 200-hand cap scores survivors by ICM. Blinds reach 200/400 while total chips are 16,000, so the second half of every table is a short-stack, ICM-driven push/fold game, and heads-up conversion (10 vs 7) is worth 3 points whenever it is reached (about a third of tables in tough fields). So the bot is built around:
1. **ICM everywhere it matters.** A fast O(n) Malmuth-Harville valuation (others treated as equal stacks) gives the points value of any stack. Every all-in-sized decision (preflop jam, call of a jam, re-jam, postflop call of 35%+ of our stack) compares V(fold) with equity-weighted V(win)/V(lose) — required equity = (Vf - Vl)/(Vw - Vl). Early with 8 alive this demands ~60% to stack off, which is what keeps the bot alive while weak bots bust.
2. **Preflop as range-vs-range arithmetic on precomputed tables.** Hand vs top-x% equity comes from the embedded 169x20 table. Jam EV sums, over each player still to act, P(call) x [equity x V(win) + (1-equity) x V(lose)] plus P(all fold) x V(steal), where each caller's range width is the set of hands with enough equity vs our perceived jam range at their pot odds (precomputed call-width table), widened/narrowed by that seat's observed looseness and by their *observed* calls of our jams. Facing a raise or shove, the raiser's range width is a Bayesian frequency estimate (their PFR, their shove rate with a depth- and position-dependent prior, their 3-bet stats), so a 100bb shove from a bot that shoves 1% of hands is read as premium and a shove from a random bot as any two.
3. **Postflop: bucketed equity vs modelled ranges, no Monte Carlo.** classify() (~5 us) maps hole+board to a made-hand/draw/texture key; the table gives equity vs random, vs continuing, betting and raising ranges. The bettor's range is a mixture whose bluff share comes from that seat's postflop aggression frequency; multiway pots raise equity to a power. Value bets are sized by strength (thin = small, strong = big, jam only when SPR is low), bluffs and c-bets are taken in proportion to the opponents' measured fold-to-bet rate (zero vs stations), draws semi-bluff, all randomised.
4. **Per-seat opponent model that does not lie.** VPIP, PFR, 3-bet, shove rate, postflop aggression, fold-to-our-raise (preflop and postflop separately) and call-our-jam rates, all with Bayesian priors. A key fix: folds to our bets that end the hand are never shown to us (no further act() call), so the bot records who still had to respond to its last raise and settles their response from hand_end stacks or the next hand's stacks (unchanged chips = fold). Without this, everybody looks like a calling station.
5. **Never crash, never time out.** act() wraps everything and legalises the result (clamped raises; raise→call→check→fold fallbacks); history parsing tolerates posts as any action name, triple/str actions, None; p99 ≈ 50–100 us on this loaded host, import 0.03 s, ~100 KB file.

## Timeline (minutes from T0)
- 0–6: read brief/kit/harness; evaluator + classifier (verified 7-card category frequencies against known values); precompute launched (61 s).
- 6–13: simulator, opponents, bot v1 (preflop ranges + push/fold EV + ICM, postflop buckets, stats); harness clean. snap_m13_v1.py.
- 13–25: first fields: v1 7.4 pts/table vs weak heuristic fields, but only 4.1 in a self-play "pro" field where a trivial PushFold bot scored 4.8. Bust log: 22% of tables busted before hand 50. v2 Bayesian shove ranges; v3 strength-scaled value sizing (both within noise).
- 25–30: probe.py showed v1–v4 jammed **any two cards at <=15bb**: the callers' required equity used risk/(dead+x) instead of risk/(dead+x+risk), so callers were modelled as never calling. Fixed in v5 (jam range at 10bb 8-handed UTG 100% → ~2–4%, SB ~13%+); positional shove priors. snap_m30.py = v5.
- 30–45: v6: inferred folds-to-our-raise and calls-of-our-jam from stack changes (hand_end or next hand), split preflop/postflop fold stats; posts-in-history robustness. v6 − v5: −0.07/+0.17/+0.13 across pro/tough/mixed2 (±0.2 each).
- 45–60: full-table A/B tests were stuck at ±0.15–0.25 noise, so I built low-variance targeted tests (endgame.py). HU conversion was 75% → v7 positional raiser ranges + wider HU opening (0.85) → 89% (n≈130 HUs); HU test +0.10 ± 0.036, 4-handed +0.17 ± 0.10. v8 3-bet frequency tracking (kept, off). v9 defaults; snap_m60.py.
- 60–80: early-game (first 60 hands, ICM-scored) tests for open width, value-bet threshold, bluff frequency, pot control, frequency-based bettor ranges, ICM on all calls, slowplay: all within ±0.12. jam_bb 11/12/20, HU iso-raise, caller-ICM models: 20 is significantly worse (−0.057 ± 0.030 HU), others neutral. v10 tolerant history parsing + guard found by harness (seat count changing between observations). v11 ICM stack-off gate for postflop jams: −0.05/−0.11/+0.05, left off. shove_mult 1.5 confirmed as local optimum (1.2 and 2.0 both −0.08 ± 0.065 in 4-handed).
- 80–107: final validation of v11 showed it **losing to v6 in the tough field (−0.43 ± 0.29)**. Isolation test (200 seeds x 8 rotations per hero, tough and mixed2): the positional raiser-range widening (pos_r) was the culprit (v11 − v6 = −0.27 ± 0.20 in tough; with pos_r off +0.08 ± 0.20 tough, +0.02 ± 0.18 mixed2), while the wider heads-up opening helps (+0.11 tough with pos_r off). Final = v12: pos_r off, HU open 0.85. One run stalled 17.8 s inside a single (v6) decision — host scheduling, not code (replays of slow decisions take <300 us; gc callbacks show only one gen-0 collection in 150 tables).
- 107: froze rival_bot.py (= v12 build), harness clean, md5 in FROZEN.md5. snap_m110_final.py is a copy.

## Test results (points per table; average is 4.0 in an 8-bot field; 95% CIs)
Unless stated, each figure is n seeds x 8 cyclic seat rotations with identical deals per seed, every hero on the same seeds; "diff" is the paired per-seed difference. Per-table SD is ~3.3 points; the rotations only partly correlate, so 1,600 tables give about ±0.17 on a mean and ±0.2 on a paired diff. That noise floor is why late tuning used the targeted tests.

Fields (7 opponents each):
- weak: RandomBot x2, Station x2, Maniac(0.15), Maniac(0.4), Nit
- mixed: RandomBot, Station, Maniac, Nit, TAG, PushFold, Exploiter
- mixed2: RandomBot, Station, Solver, Aggro, Exploiter, PushFold, v1 (my bugged early bot, a wide jammer)
- tough: Solver, Solver(tight 1.3), Aggro, Exploiter, TAG, PushFold, v5
- pro: v5, v5-LAG (wide opens, 2x bluffs, 3x light 3-bets, loose jams), v5-nit, v5 (jam<=20bb, caller-ICM), Solver, Exploiter, PushFold
- league: v1, v5, v6, v9 (earlier versions of this bot), Solver, Aggro, Exploiter

Key measured results:
| test | result |
|---|---|
| v1 vs mixed / "strong" heuristic fields (100x8) | 7.37 ± 0.23 / 7.45 ± 0.24 |
| v1 vs its own variants (pro, v1-based) | 4.12; trivial PushFold scored 4.77, which exposed the jam bug |
| v5 (bug fixed) pro / tough / mixed2 (100x8) | 4.38 ± 0.22 / 5.41 ± 0.23 / 5.93 ± 0.19 |
| v6 − v5 (opponent-model inference) pro / tough / mixed2 (150x8) | −0.07 ± 0.19 / +0.17 ± 0.25 / +0.13 ± 0.22 |
| heads-up conversion, tough field | 75% (v6) → 89% (v7 HU opening), n≈130 HUs each |
| HU endgame test (16 matches per seed x 250 seeds, 8 opponent types): HU open 0.85 | +0.10 ± 0.036 over v8 base; jam threshold 20bb −0.057 ± 0.030 |
| 4-handed endgame test (100 seeds x 4 rotations x 8 opponent types) | HU-open variant +0.17 ± 0.10; shove_mult 1.2 / 2.0: −0.08 ± 0.065 each (1.5 kept) |
| early game (first 60 hands, ICM-scored; 40 seeds x 8 rot x 8 opp) | every postflop tweak within ±0.09–0.12 (none adopted) |
| final isolation (200x8): v12 settings − v6 | tough +0.08 ± 0.20, mixed2 +0.02 ± 0.18; v11 (pos_r on) − v6 tough −0.27 ± 0.20 |

Typical absolute level of the final bot: ~5.5 in tough, ~6.1 in mixed2, 7+ against weak/mixed fields; 9.25 of 10 heads-up against the 8-opponent HU panel (8.5 = break-even); 7.6 of the 10/7/5/4 4-handed panel (6.5 = break-even).

Latency (pure Python, this shared host, load avg 7–11): harness p99 57–59 us, max 180–240 us; in-engine p99 45–110 us. Occasional multi-ms outliers in simulations come from OS scheduling (nice 15 on an oversubscribed host): replaying those exact decisions takes <300 us. Import 0.01 s cold, file 104 KB.

Robustness: harness 0 exceptions / 0 illegal over 2,000 + 5,000 + 15,000 observations; fuzz (20,000 odd observations: triple/str history entries, None history, posts in history, blinds (0,0), 'fold' legal alongside 'check', new_table(None, seat, None), hand_end(None/'x'/partial)) 0 bad and 0 internal errors; engine runs with posts recorded as post/raise/call/blind and hand_end None/partial: 0 errors.

### Final validation of the frozen file (80 seeds x 8 rotations = 640 tables per hero per field; after freezing)
| field | rival_bot (frozen) | v6 | v1 | v1 − frozen (paired) |
|---|---|---|---|---|
| weak | 7.75 ± 0.21 | 7.90 ± 0.16 | 7.71 ± 0.22 | −0.04 ± 0.25 |
| league | 4.60 ± 0.21 | 4.70 ± 0.21 | 4.82 ± 0.24 | +0.22 ± 0.28 |
| pro | 4.49 ± 0.22 | 4.36 ± 0.22 | 4.62 ± 0.24 | +0.13 ± 0.28 |
| tough | 5.69 ± 0.26 | 5.42 ± 0.22 | 5.15 ± 0.24 | −0.54 ± 0.33 |
| mixed2 | 6.45 ± 0.22 | 6.43 ± 0.25 | 5.82 ± 0.27 | −0.63 ± 0.31 |
Read: the frozen bot clearly beats v1 where the field has real push/fold opponents and weak bots (tough, mixed2). It is level with v6 everywhere (all differences inside ±0.3). In the two fields made mostly of my own ICM-tight bots (league, pro), v1's any-two jamming does about as well or slightly better (not significant): ICM-tight callers are exploitable by wide jams. Strong prepared opponents may also exploit that, and it is the first thing I would test next (an adaptive jam-width that widens when the caller model's measured call rate is low).

## Honest limits
- The test opponents are mine. Solver/Aggro/Exploiter approximate prepared teams but are not real solvers, and self-play fields share my blind spots.
- ICM treats the other stacks as equal (fast); exact ICM is used only for scoring in the simulator.
- Postflop has no multi-street planning or balanced check-raise range; buckets ignore kicker detail beyond top pair and the nut-ness of straights.
- Most late parameter changes were within noise in full tables. Adopted changes have a measured effect (bug fix, inference, HU opening); the rest stayed off by default.

## Files
- rival_bot.py (frozen, md5 in FROZEN.md5), harness_final.txt
- bot_src.py + build.py + tables.json (rebuild with `python3 build.py bot_src.py rival_bot.py`)
- snapshots: snap_m13_v1.py, snap_m30.py (v5), snap_m60.py (v9), snap_m90.py (v11), snap_m110_final.py (= frozen)
- versions v1..v12, experiment outputs exp1..exp10.txt, final_eval.txt
