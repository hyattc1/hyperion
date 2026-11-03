# V-j: payoff by street (Tranche Hold'em) in our engine, a twist-aware field, and F's play there (2026-11-03)

Branch climb/vj-tranche, from main 8310cc0 (batch 6). Drill 11's unseen twist (kit I, Tranche Hold'em) moved a hand's
payoff by street and our simulator could not play it, so the drill's only measurement was the kit's own simulator.
This branch makes the engine play street-settled pots and no-runout all-ins, puts the twist in the catalog with
twist-aware test opponents, and gives F dials for it (off by default). Seeds: screen 10000-10199 and diagnostics
12000-12199 only; no held-out set, judge seed, judge bot or held-out variant was run, read or tuned on. Host shared
(8 cores, load 17-19): `nice -n 10`, at most two heavy processes, long runs detached with a done-file. Scratch
scripts: the session scratchpad, `goal/vj_work/`.

This log is written as the work goes; each run's command, seeds and numbers are appended when it finishes.

## Decisions (taken without asking; noted here)

- **Rules.extras keys, not new Rules fields.** `settle: "street"` and `no_runout: True`, each usable alone. A new
  dataclass field would change `tablegen.rules_to_dict` for every Rules, so every prepared generic table's key
  (`generic.table_key` hashes the whole dict) and every cache would move; extras keys leave every existing table,
  key and cell as they are (the precedent: `cap_places`, `removed_ranks`, `run_until_black`).
- **Hands under five cards** (a preflop tranche, an all-in before the flop): `core.eval.evaluate_short`, ranks only,
  suits never count: quads > trips > two pair > pair > no pair, then the ranks by count and height. On two cards that
  is kit I's rule: a pair over any non-pair, the higher pair, then the high card, then the kicker.
- **Payouts and schedule of the entry**: our default table (8..1, ICM at the cap, the default blinds), as every other
  catalog entry carries except top_heavy (whose twist is its payouts). Kit I's own points (16/10/6/3/1/0/-1/-3, places
  by chips at hand 200) and schedule are `docs/drills/drill11/rules_tonight.json`, for `--rules`.
- **What a folded seat put in above every contender** joins the top contender's layer (kit I: "a layer with no bot
  still in the hand that paid up to it joins the layer below"); the same rule the hand-level award already had.
- **The earlier tranches reach the bots** as `Observation.extras["tranches"]` (the earlier streets' totals; this
  street's chips are obs.bets): a bot needs them to price a fold (it forfeits them). On the night the adapter fills it
  (kit I: `v.tranches[:v.street]`). HandResult.extras carries "tranches" and "awards" per street.
- **The runout term** (`tools/runout_term.py`, unchanged) has no events on the entry: with `no_runout` no card comes
  after the last decision of a hand that is shown down, so its corrected samples are the raw ones there. A rule set
  with street settlement and a runout would need the term taught about tranches (not done; no entry has it).

## 1. The engine and the entry

- `hyperion/core/eval.py`: `evaluate_short` (above).
- `hyperion/sim/engine.py`: `Table.by_street` / `Table.no_runout` from the Rules; per-street contribution marks and
  the board each round was bet on (`HandState.marks`, `.boards`) only when settling by street; `_award_streets`
  (layers per tranche, `_settle_pot` for ties and the odd chip clockwise from the button, dead money as before);
  `_betting_over` ends the deal once at most one seat in the hand has chips behind; `_scores` evaluates hands of
  fewer than five cards with `evaluate_short`. Default play reaches none of it (two flag checks per street).
- `hyperion/drills/variants.py`: `tranche_holdem` (axis payoff, after hi_lo), Rules extras `{"variant":
  "tranche_holdem", "settle": "street", "no_runout": True}`, no hooks; `validate` accepts an engine rule as the
  "documented engine rule" a hookless needs_engine entry must have.
- `tests/test_vj_tranche.py` (14 tests): the handout's worked example (settlement alone and through the engine, the
  tranches in each observation, the hand's report), side pots within a tranche with an all-in seat that has no stake
  later, ties and the odd chip (by button), a tie on the river board, folded chips as dead money and the layer nobody
  still in reached, a fold forfeiting every tranche paid into, a preflop all-in with no board (2-2 over A-K), an
  all-in on the flop that deals no turn or river, `no_runout` alone (2-2 over A-K with no board; with a runout the
  kings on the board win), `settle` alone (the runout is dealt; only tranche 0 has chips), an unknown settle rule,
  the entry itself, and 200 tables of seven bestiary archetypes with every chip kept.

Runs:
- smoke, 50 tables of bestiary bots under the entry (`goal/vj_work/smoke.py 50`): 9,656 hands, 690 showdowns, 343 of
  them with no board (a preflop all-in), chips conserved every hand, 0 exceptions; 2.9 s.
- `pytest tests/test_vj_tranche.py`: 14 passed (14 s). Engine and catalog suites (test_sim_engine, test_variant_catalog,
  test_drills_variants, test_eval, test_runout_term, test_s12_reads, test_vf_twists): 171 passed.

## 2. Twist-aware opponents and the wiring

- `hyperion/strategy/tranche.py` (new, stdlib + core): the two rules, two-card keys and their exact share against one
  random hand (with card removal; the organiser notes' numbers to 0.005, theirs count a tie as no win), the twin map
  (two-card rank -> the hold'em class at the same combo percentile: 22 -> ATs, 66 -> 77, AK -> AKo, A2 -> QJo, KQ ->
  A3s, 72 -> 54o, as the drill's adapter found), and `now_share` (the hand as it is now against n random holdings).
- `hyperion/sim/aware.py`: `tranche_tag`, `tranche_pushfold`, `tranche_mc` and the field `tranche_holdem_aware`
  (the other aware fields' shape: hero, montecarlo30, tranche_mc, tranche_pushfold, loose_aggro, rival1, tranche_tag,
  timeout_then_recover); `AWARE_VARIANT` maps it to the entry, so `climb_accept --stages aware` runs it by default.
  Built from the handout's rules only (the kit's tranche_bot was never opened).
- `hyperion/sim/generic.py`: under `settle: "street"` the generic opponents score the showdown on the board as it
  stands (no runout; two cards alone preflop), so their preflop table is the two-card order and their postflop value
  share is the street's own tranche; `holdem_cards()` is False there. Gated on the key: every other table is as before.
  `tables/generic/tranche_holdem-d65b70f5.json` (10.6 KB; 16.5 s to build): AA 0.999, 22 0.939, AKo 0.935, 87s 0.237.
- The weighted score (addendum 11): tranche_holdem is not added to `tools/accept_weights.json`'s probability table, so
  every saved review's weighted score reproduces; a run that includes it weighs it as an unlisted twist (1).
  tests/test_climb_accept.py's hand-made case now counts the 27th entry and fifth aware field at that weight.

Calibration of the aware bots (diagnostic seeds 12000-12099, eight rotations each, model mode; scratch scripts
`goal/vj_work/aware_parts.py`, `aware_mc.py`; two copies each of four variants of the bot in one field):

| bot | first version (claim on every street, weak 0.25) | final (claim only where a call ends the betting, weak 0.15) |
|---|---|---|
| tranche_tag / twin preflop only / claim only / ChartTAG | 4.297 / 4.693 / 4.360 / 4.650 | 4.632 / 4.573 / 4.408 / 4.387 |
| tranche_pushfold / twin only / claim only / PushFoldBot | 4.233 / 4.879 / 4.053 / 4.835 | 4.539 / 4.539 / 4.460 / 4.462 |
| tranche_mc vs AwareMC played blind (4 + 4) | | 4.551 vs 4.449 |

The first claim call (keep calling while the earlier tranches times their chance cover the price) cost 0.3 to 0.8:
on the flop and turn a call keeps the claim only if it also pays every later bet, so the formula overpays there. It
now applies where a call ends the betting (the river, an all-in); the Monte Carlo bot takes half the claim before.
Each aware bot now beats its blind archetype (+0.25, +0.08, +0.10), smaller than the organiser's 2.6 points on kit
I's 19-point scale (about 1 on our 7-point one): our archetypes already play made hands only after the flop.

Tests: `tests/test_vj_aware.py` (8): the shares and twins, now_share, the field's wiring, the claim only where the
betting ends, both aware fields (tranche_holdem_aware, generic_aware) playing the entry clean, the generic read.
test_aware, test_generic_aware (every catalog entry has a prepared table and plays clean), test_climb_accept: pass.

## 3. F's dials (off by default; SHIP_DIALS unchanged)

Who plays what on a tranche_holdem table: the extras keys are not a showdown key the base's core refuses
(`hybrid.bot.table_reason` is None), so F plays it as hold'em is played: rival 3's core preflop (the base), Hero after
the flop (route `post=hero`) and in `pre_raised_short`. So the preflop patch has to reach every member, and the
postflop one is Hero's.

- `tranche_twin` (ComposeConfig, a flat dial; "" off, "all", "allin"): on a street-settled table every preflop
  decision is shown, to every member, the hold'em class at our two-card rank's percentile of Hero's own tables
  (`tranche.twin_cards_map(tables.load().rank)`, a copy of the observation; the engine's is untouched). On a table
  that only settles all-ins on the cards out (`no_runout` alone), and with "allin" on either, only the all-in
  decisions (effective stack 20 bb or less, or a call of 40% of our stack or more: the drill's TWIN_BB 20 /
  TWIN_CALL_FRAC 0.4). The drill's adapter `twin_hole`, keyed on the Rules instead of the kit.
- `hero.tranche` (Config.tranche; comma parts, "" off), each part only where its rule is on, two hole cards and
  hold'em's showdown:
  - `now` (street settlement): the postflop read without draws (`Postflop.read(..., now=True)`: no draw outs, no
    draw tier bumps) and no cards to come, as on a river: this street's pot is decided on these cards.
  - `sunk` (street settlement): facing a bet the price is (call - claim) / (this street's chips + call) instead of
    the whole pot's; claim = sum over earlier streets of T_k x q_k^n (q_0 the two-card share against one random hand,
    q_k the tier's equity on street k's board, n the opponents in), counted in full where the call ends the betting
    (the river, an all-in either side: `tranche.closes_betting`) and x `hero.tranche_claim_early` (0.5) before, x
    `hero.tranche_claim_scale` (1.0). The aware bots' calibration above is why the early claim is discounted.
  - `allin` (no runout): a call that ends the betting is read as the hand is now (no draws).
  - `hero.tranche_value_shift`, `hero.tranche_call_shift` (int, 0): value/raise thresholds and the facing-a-bet read
    moved on street-settled tables (for candidates without a code change; every hyperion edit misses the cache).
- Tests: `tests/test_vj_dials.py` (6): off in the ship and in the defaults; the twin only on street-settled or
  no-runout tables (22 shown as A-T suited; no other catalog entry, no hold'em table; no-runout alone only short);
  Hero's parts only where the rule is (none on the 26 other entries); the now-read gives a nut flush draw ace high and
  no outs; a flush draw that calls a half-pot flop bet in hold'em folds; a pair of deuces holding a 1000-chip
  preflop tranche calls a river bet it folds without `sunk`, and the same on the turn calls at claim_early 1.0 and
  folds at 0.

## 4. Screen runs (our sim)

Every run: `tools/climb_accept.py --base '{"dials": {}}' --cand <spec> --set screen --stages variants,aware --variants
tranche_holdem --aware tranche_holdem_aware,generic:tranche_holdem --runout-term`, seeds 10000-10199 (200 seeds, eight
rotations each, model mode, paired by seed), out `goal/vj_work/ca`, code version b3ae54d3e7 (branch c1ccbdd). The
cells: tranche_holdem on `realistic` (twist-blind opponents), `tranche_holdem_aware` and `generic_aware` under the
entry. The runout term has no events on the entry (no_runout), so corrected = raw throughout. F (base) scores 6.475
(realistic), 6.331 (aware), 6.345 (generic aware) on the 8..1 table.

| candidate | realistic | tranche_holdem_aware | generic_aware | verdict |
|---|---|---|---|---|
| c1 `{"tranche_twin": "all"}` | +0.027 ± 0.095 | -0.019 ± 0.106 | +0.014 ± 0.102 | level (25.2 min with base, 2 workers) |
| c3 `{"tranche_twin": "all", "hero.tranche": "now,sunk"}` (claim_early 0.5) | +0.045 ± 0.100 | -0.025 ± 0.110 | +0.024 ± 0.108 | level |

How often the parts change Hero's decision (`goal/vj_work/flips.py`: F + dials in tranche_holdem_aware, diagnostic
seeds 12000-12019 x 8; at each tranche-path decision the plain read is asked too, from the same rng state):

| dials (with the twin) | tranche-path decisions | changed | the main changes |
|---|---|---|---|
| now | 5,149 | 4.2% | turn bets checked (100: semi-bluffs gone), flop bets checked (58), flop calls folded (47: draws) |
| now,sunk (claim_early 0.5) | 5,237 | 9.9% | flop folds called (229: half the preflop claim makes a flop call cheap), turn/flop bets checked (180), river folds called (42) |
| now,sunk (claim_early 0.0) | 4,804 | 9.3% | flop calls folded (239: this street's pot alone prices the call), bets checked (149), river folds called (29) |
| c2 `{"tranche_twin": "all", "hero.tranche": "now"}` | +0.040 ± 0.098 | -0.007 ± 0.103 | +0.005 ± 0.104 | level |
