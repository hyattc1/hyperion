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
