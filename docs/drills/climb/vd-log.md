# V-d: generic variant-aware opponents (any twist, no per-twist code) and the honest variant board

Branch climb/vd-generic-aware, from main c73a229. Opponent and tooling work: F's play does not change (section 6).
Screen seeds only (10000-10199, `--set screen`) and fresh diagnostics under 10000; no held-out seeds, no judge bot or
field, no held-out variant run, read or tuned on. Host shared (load 17-20 of 8 cores the whole session): every
measurement `nice -n 10`, two workers, at most two measurement processes at once. Latency is reported as CPU time per
decision (thread_time) next to the engine's wall-clock p50/p99, because at this load the wall clock shows the
scheduler (8-12 ms preemptions hit every bot at the table, F and the trivial ones included).

## 1. The problem and the design

On the night every bot knows the twist. Our variant numbers were F against opponents whose strategy ignores the twist
for 22 of 26 catalog entries (aware.py has hand-built aware bots for toss_or_holdem, bounty, short_deck,
river_of_blood; bestiary has aware bidders/keepers for auction and deal5_keep2), and for every unseen twist.

hyperion/sim/generic.py: three archetypes that derive their play from the table's Rules and the variant's own hooks.

- **One simulator for everything** (`Sim`): rolls the rest of a hand out through a private copy of the variant's hooks:
  on_street (discards, swaps, bought or auctioned cards, a second board), next_card (boards of any length), the
  showdown (score_hand or score_splits: rank orders, short decks, wild cards, lowball, must-use, split pots), and
  on_payout (bounties: a win can be worth more than the pot). Public per-hand state comes back from Observation.extras
  (hooks.restore when defined, else extras keys that name hook attributes: bounties, discards, revealed, exposed);
  cards in extras are dead (discards, reveals, boards, shown) or held by their seat (exposed, face-up).
- **The variant's preflop table** (`prepare`, `python -m hyperion.sim.generic --prepare NAME|all`): the value share of
  every hole class against one random hand, dealt from the deal through the same hooks (169 classes stratified, or
  best2+tags labels sampled for 3+ hole cards, shrunk to their best-two class), plus the measured CPU cost of a
  showdown score, of a runout (1 and 3 opponents) and of a hand from the deal (these fix every sample count, so play is
  deterministic once the file exists), and score quantiles per board length. Hold'em-shaped card rules with no card
  hooks reuse tables/preflop_equity.json. Committed for the 26 entries under tables/generic/ (not packed: pack.py takes
  tables/*.json and tables/variants/<name>/ only).
- **The hold'em twin**: a variant class maps to the hold'em class at the same combo percentile of its own table. The
  TAG and push/fold charts are applied to the twin, so they open the same share of hands, the variant's best ones; on
  hold'em the twin is the class itself.
- **gen_mc**: AwareMC's policy (bet 0.6, raise 0.75, call at price + 0.05 + up to 0.15 by bet size) on the value share
  after the call from runouts against min(opponents, 3) random holdings; preflop AwareMC's Chen thresholds on the
  twin's Chen score.
- **gen_tag / gen_pushfold**: ChartTAG / PushFoldBot preflop on the twin; postflop "top pair or better" and "two pair or
  better" become made shares (the share of random holdings the hand beats on this board under the variant's
  showdown) at the thresholds that agree best with those reads in hold'em (section 2).
- **Levers any twist can pull, derived, not written per twist**: winning the pot now pays >= 1.1 x the pot (on_payout)
  -> one notch wider preflop (gen_mc +2 Chen), and a half-pot bet when checked to in a pot of three or fewer; antes
  making the forced bets >= 2 bb -> one notch wider; a live straddle is the big blind preflop.
- **Variant decisions by type** (discard, keep, swap, buy_card, bid), each option priced by the same value share with
  common random numbers; an unknown decision gets None (the hook's default).
- **Budgets** (CPU ns of the measured cost): runouts 240 us, made shares 80 us, a variant decision's options 120 us (at least 4 runouts an option, one shuffled spare deck shared by the options); a
  bot that cannot afford 10 samples of its read falls back: runouts against every opponent -> heads-up runouts to the
  power of the opponents -> made share -> the score's quantile at this board length. Who falls back: wild_deuces
  (showdown ~120 us mean, heavy tail: two or three deuces cost 1-15 ms) and omaha_four (~30 us, 60 evaluations) read
  by quantile; lowball's made share (9 us a score) too; lowball and omaha_four's gen_mc multiway runouts go heads-up.
- `generic_aware` field = hero, montecarlo30, gen_mc, gen_pushfold, loose_aggro, rival1, gen_tag, timeout_then_recover
  (the aware fields' shape), playable under any `--variant`, including a file (`variants.get("path.py:factory")`
  registers it by name so the generic bots find its hooks).

Not modelled (said plainly): knockout_bounty's on_bust points (points, not chips; nothing prices them), payout tables
(the archetypes ignore ICM, as the hand-built aware bots do), the engine's hand-shape hooks that need the table object
(settle, after_forced); opponents' future variant decisions inside a runout use the hook's default.

## 2. Calibration: the hold'em thresholds (scratch script, seed 20261102)

Random two-card hands and boards, made share against every opponent holding (exact enumeration), threshold that
maximises agreement with the archetype's read:

| board | top pair or better: share, h, agreement | two pair or better: share, h, agreement |
|---|---|---|
| flop | 0.173, 0.850, 0.975 | 0.081, 0.970, 0.956 |
| turn | 0.261, 0.815, 0.912 | 0.193, 0.925, 0.876 |
| river | 0.434, 0.550, 0.848 | 0.393, 0.560, 0.814 |

(10,000 spots each; 3,000 gave the same thresholds within 0.01.) On the river the archetypes' own reads are loose
(category >= 2 counts any board pair plus a pair), so the best-agreeing made share is low there.
