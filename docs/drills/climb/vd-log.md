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

## 3. Setup time on a new variant

`python -m hyperion.sim.generic --prepare NAME|file.py:factory --workers 2` (default budget 45 s of sampling per
worker). Measured at load 18-20 of 8 cores, nice 10, two workers:

- **A variant the catalog does not have, written as a file** (hyperion/drills/variant_file_example.py: MIT 2021's
  three boards, pot split three ways; table deleted first): **23.5 s wall, 30 MB RSS** (169 classes stratified, 4,000
  hands each from the deal through its hooks; score 4.2 us, runout 12.4 / 21.8 us).
- The 26 catalog entries (`--prepare all`, timed one by one; all committed under tables/generic/, 460 KB): 0.1 s for
  the ten with hold'em cards and no card hooks (they reuse tables/preflop_equity.json), 6-20 s for two-card twists
  (bounty 15 s, hi_lo 14 s, river_of_blood 20 s, two_boards 18 s), 29 s lowball, 42 s wild_deuces (its showdown
  averages 122 us), about 40 s for the 3- to 5-hole-card entries (toss, blind discard, three_card_keep, omaha 659
  labels from 321,400 hands, deal5_keep2 884 labels).
- So a new twist costs at most the sampling budget, about 45 s at two workers on this loaded host, well inside the
  2-minute target; a catalog twist costs nothing (the table is in the repo). Without a prepared table a bot builds a
  4-second table at its first table start and caches it under scratch/generic/ (climb_accept and aware_board prepare
  the table first, so workers never do).

## 4. Validation against the hand-built aware bots and the plain archetypes

Mixed tables: each generic bot at the same table as the bot it should match, all eight rotations, paired per seed
(seeds 10000-10099 x 8, model mode; `tools/aware_board.py --fields generic_vs_<twist>`; paired difference of the two
bots' per-seed points, 95% interval). Run on the working tree between 08:49 and 08:57 (the last edits before commit
7a2ae19 only trimmed the variant decisions' budget and fixed a crash at table start on rules with no variant).

| table | gen_mc - its match | gen_tag - its match | gen_pushfold - its match | F (hero seat) |
|---|---|---|---|---|
| hold'em: aware_mc, tag, pushfold | +0.057 ± 0.163 | +0.206 ± 0.150 | +0.107 ± 0.180 | 6.83 |
| toss_or_holdem: toss_mc, toss_tag, toss_pushfold | **+0.785 ± 0.203** | **+0.417 ± 0.173** | **+0.523 ± 0.226** | 6.19 |
| bounty: bounty_mc, bounty_tag, bounty_pushfold | -0.166 ± 0.193 | +0.126 ± 0.179 | +0.029 ± 0.201 | 6.67 |
| short_deck: short_mc, short_tag, short_pushfold | -0.064 ± 0.206 | -0.039 ± 0.176 | +0.168 ± 0.200 | 6.14 |
| river_of_blood: rob_mc, rob_tag, rob_pushfold | -0.076 ± 0.197 | -0.011 ± 0.174 | -0.110 ± 0.216 | 6.86 |

- **About as strong everywhere, stronger on toss.** No generic bot is beyond noise below its hand-built match; on
  toss_or_holdem all three are beyond noise above (the hand-built toss bots pick the Chen-best two preflop and toss by a
  made-hand-then-outs rule; the generic ones price the three-card hand from a table dealt through the toss hook and
  toss by runouts with every face-up toss dead).
- **Where they fall short:** gen_mc on bounty (-0.17, inside noise) prices the bounty into every call through the
  payoff hook; the hand-built BountyMC found that pricing it into calls loses (aware.py: -0.07) and only bets a hit
  bounty. gen_pushfold on river_of_blood (-0.11, noise) reads the made hand now, without the hand-built rob bots' draw
  calls while a red card means another street (gen_mc's runouts do deal the run).
- **Hold'em: they play like their archetypes.** Decision agreement with the archetype on the same observations
  (realistic field, seeds 10000-10005 x 8): preflop 100% for all three (the twin is the class itself); postflop
  gen_tag 84.5% (498 decisions), gen_pushfold 85.9% (872), gen_mc 86.8% (615; two Monte Carlo bots with different
  samples). Points level with each archetype (table above).

## 5. Legality and speed on every catalog entry

`generic_aware` field, seeds 10000-10001 x 8 per entry, model mode, CPU time per decision (thread_time; the wall
clock at load 18 adds 8-12 ms preemptions to every bot). Zero exceptions and zero illegal actions for all three bots
on all 26 entries (also in tests/test_generic_aware.py, 40 hands per entry, and on the board below at 200 x 8).

| variant | gen_mc act p50 / p99 / max us | gen_tag | gen_pushfold | exc | illegal |
|---|---|---|---|---|---|
| permuted_ranks | 8 / 328 / 1585 | 10 / 145 / 1488 | 9 / 142 / 1182 | 0 | 0 |
| short_deck | 8 / 314 / 859 | 9 / 174 / 539 | 9 / 169 / 1518 | 0 | 0 |
| lowball | 7 / 272 / 1041 | 8 / 44 / 1185 | 8 / 41 / 490 | 0 | 0 |
| wild_deuces | 7 / 189 / 5857 | 8 / 271 / 5309 | 8 / 313 / 460 | 0 | 0 |
| flush_over_full_house | 8 / 292 / 781 | 9 / 128 / 1046 | 9 / 133 / 1703 | 0 | 0 |
| toss_or_holdem | 13 / 406 / 2272 | 15 / 143 / 1263 | 13 / 138 / 627 | 0 | 0 |
| three_card_blind_discard | 12 / 314 / 1259 | 14 / 122 / 2749 | 13 / 115 / 783 | 0 | 0 |
| three_card_keep | 12 / 296 / 926 | 14 / 135 / 470 | 13 / 164 / 3001 | 0 | 0 |
| omaha_four | 13 / 92 / 1441 | 14 / 76 / 1825 | 14 / 93 / 2123 | 0 | 0 |
| swap_holdem | 8 / 267 / 1148 | 10 / 112 / 528 | 9 / 108 / 1458 | 0 | 0 |
| swap_one_turn | 8 / 290 / 1900 | 9 / 97 / 2218 | 9 / 101 / 191 | 0 | 0 |
| exposed_card | 8 / 303 / 21887 | 9 / 127 / 385 | 9 / 139 / 11279 | 0 | 0 |
| two_boards | 8 / 343 / 3565 | 10 / 139 / 681 | 9 / 149 / 564 | 0 | 0 |
| bonus_card | 9 / 350 / 737 | 11 / 138 / 356 | 10 / 159 / 1423 | 0 | 0 |
| auction | 9 / 341 / 1877 | 10 / 108 / 267 | 10 / 127 / 864 | 0 | 0 |
| deal5_keep2 | 16 / 309 / 940 | 19 / 121 / 652 | 19 / 139 / 657 | 0 | 0 |
| bounty | 16 / 269 / 828 | 17 / 107 / 1191 | 16 / 112 / 670 | 0 | 0 |
| knockout_bounty | 8 / 233 / 811 | 8 / 84 / 2083 | 9 / 90 / 396 | 0 | 0 |
| top_heavy | 8 / 236 / 1597 | 10 / 87 / 288 | 9 / 93 / 2796 | 0 | 0 |
| hi_lo | 8 / 332 / 2824 | 9 / 125 / 1696 | 9 / 137 / 1174 | 0 | 0 |
| pot_limit | 8 / 237 / 724 | 9 / 97 / 1005 | 9 / 104 / 994 | 0 | 0 |
| antes_from_level_3 | 8 / 217 / 2694 | 9 / 98 / 653 | 9 / 96 / 266 | 0 | 0 |
| fixed_raise | 9 / 279 / 2838 | 11 / 104 / 679 | 10 / 101 / 741 | 0 | 0 |
| fast_schedule | 8 / 239 / 1634 | 10 / 94 / 287 | 9 / 101 / 610 | 0 | 0 |
| straddle | 11 / 274 / 2902 | 12 / 97 / 1937 | 12 / 106 / 839 | 0 | 0 |
| river_of_blood | 8 / 469 / 2353 | 9 / 118 / 376 | 9 / 116 / 745 | 0 | 0 |

- act(): p99 at most 469 us (gen_mc, river_of_blood), 92-406 us for gen_mc elsewhere, under 320 us for the other two;
  medians 7-19 us (preflop is a table lookup). The rare multi-millisecond maxima are a garbage collection inside the
  call (exposed_card 21.9 ms once) and wild_deuces' showdown when two or three deuces are out (one score costs 1-15
  ms; the engine's own showdown pays it too).
- Variant decisions (discard, keep, swap, buy_card, bid), after the last trim (one shared spare deck, 4+ runouts an
  option, 120 us budget): mean 180-265 us; p99 0.44-1.6 ms on this host (toss_or_holdem, deal5_keep2, auction,
  bonus_card; 70-135 decisions each). Standalone, unloaded: the toss decision averages 155 us. A team's real bot would
  want them cheaper; in model mode they cost nothing in points (the engine models no variant decision's time).
