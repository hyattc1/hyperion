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
- **Budgets** (CPU ns of the measured cost): runouts 240 us, made shares 80 us, a variant decision's options 120 us
  (at least 4 runouts an option, one shuffled spare deck shared by the options); a bot that cannot afford 10 samples
  of its read falls back: runouts against every opponent -> heads-up runouts to the power of the opponents -> made
  share -> the score's quantile at this board length. Who falls back: wild_deuces (showdown ~120 us mean, heavy tail:
  two or three deuces cost 1-15 ms) and omaha_four (~30 us, 60 evaluations) read by quantile; lowball's made share (9
  us a score) too; lowball and omaha_four's gen_mc multiway runouts go heads-up.
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

## 6. One command for any variant, rehearsed; F unchanged

- `python tools/climb_accept.py --stages aware --aware generic:<variant> --base '' --cand '<dials>' --set
  10000:10100 --workers 2`; `<variant>` is a catalog name, `all` (every entry), or a file (`path.py:factory`; the
  cache names it by content). `--aware generic:...` maps to the `generic_aware` field and builds missing tables first.
  Before this branch the aware stage imported hyperion/sim/aware.py before the bestiary, which with the generic module
  imported from the bestiary's end was an ImportError: fixed in fd4a40d (imported from aware.py's end; a test runs each
  import order in a fresh process).
- **Rehearsal on a twist the catalog lacks** (hyperion/drills/variant_file_example.py, three boards; its table deleted
  first), F against the `survival` recipe, seeds 10000-10099 x 8, two workers, load ~12: **142.6 s wall end to end**,
  table 13.7 s; F 5.988, survival 5.967 (-0.021 ± 0.037, level), 0 errors. PLAYBOOK Stage 5 and prompt 05 now run it
  after the realistic sim; the freeze warms the twist's table.
- **F's play is unchanged.** `tools/climb_accept.py --cand '' --base '' --set 10000:10040 --stages confirm` (night,
  40 seeds x 8) at base c73a229 (detached worktree) and at fd4a40d (separate cache dirs, so both ran): the 40 per-seed
  samples are identical, mean 6.00103 both. The branch adds bots, fields, tables and tools; F's code
  (hyperion/strategy, compose, hybrid, ship) is untouched and never imports the variants module. Because of that, the
  board's twist-blind `realistic` cells were played once, from the base worktree (`--field-version realistic=c73a229`).

## 7. The honest variant board: F against the generic aware field, every catalog entry

`tools/aware_board.py --set screen --fields generic_aware,realistic` (F as shipped; seeds 10000-10199 x 8, model mode,
two workers, nice 10). generic_aware cells from commit 7a2ae19 (code a33cfb0442, 208 chunks, 08:57-10:05); realistic
cells from the base worktree c73a229 (F identical, section 6). Margins are F minus the bot with the best mean, paired
per seed; **shrink** = F's margin over its best opponent on realistic minus the same on generic_aware, paired on the
same 200 seeds (positive: F's lead shrinks once the seats read the twist). top_heavy is on its 50/25/12/... scale;
knockout_bounty's points include the knockout bonus.

| variant | F generic | rank | margin over best generic bot | margin over best opponent | F realistic | rank | margin over best opponent | shrink (paired seeds) |
|---|---|---|---|---|---|---|---|---|
| lowball | 6.883 | 1 | +0.863 ± 0.128 (gen_mc) | +0.863 ± 0.128 (gen_mc) | 7.785 | 1 | +3.134 ± 0.106 (tag) | +2.271 ± 0.154 (n 200) |
| wild_deuces | 6.056 | 1 | +0.200 ± 0.160 (gen_tag) | +0.200 ± 0.160 (gen_tag) | 6.962 | 1 | +1.726 ± 0.144 (tag) | +1.525 ± 0.213 (n 200) |
| short_deck | 5.810 | 1 | +0.280 ± 0.127 (gen_tag) | +0.280 ± 0.127 (gen_tag) | 6.164 | 1 | +0.781 ± 0.134 (tag) | +0.501 ± 0.166 (n 200) |
| omaha_four | 6.081 | 1 | +0.453 ± 0.138 (gen_tag) | +0.453 ± 0.138 (gen_tag) | 6.665 | 1 | +0.546 ± 0.096 (rival1) | +0.093 ± 0.167 (n 200) |
| fixed_raise | 6.113 | 1 | +1.404 ± 0.132 (gen_tag) | +0.078 ± 0.161 (rival1) | 6.307 | 1 | +0.137 ± 0.153 (rival1) | +0.058 ± 0.156 (n 200) |
| pot_limit | 6.270 | 1 | +1.389 ± 0.131 (gen_tag) | +0.828 ± 0.152 (rival1) | 6.387 | 1 | +0.850 ± 0.157 (rival1) | +0.022 ± 0.192 (n 200) |
| auction | 6.387 | 1 | +1.437 ± 0.139 (gen_tag) | +1.437 ± 0.139 (gen_tag) | 6.534 | 1 | +1.446 ± 0.140 (tag) | +0.009 ± 0.183 (n 200) |
| antes_from_level_3 | 6.386 | 1 | +1.530 ± 0.123 (gen_tag) | +1.025 ± 0.159 (rival1) | 6.494 | 1 | +1.022 ± 0.157 (rival1) | -0.002 ± 0.202 (n 200) |
| hi_lo | 6.046 | 1 | +1.236 ± 0.135 (gen_tag) | +0.501 ± 0.184 (rival1) | 6.126 | 1 | +0.482 ± 0.150 (rival1) | -0.018 ± 0.230 (n 200) |
| bounty | 6.318 | 1 | +1.396 ± 0.139 (gen_tag) | +1.007 ± 0.150 (rival1) | 6.389 | 1 | +0.970 ± 0.151 (rival1) | -0.037 ± 0.181 (n 200) |
| river_of_blood | 6.297 | 1 | +1.421 ± 0.146 (gen_tag) | +1.043 ± 0.169 (rival1) | 6.319 | 1 | +1.006 ± 0.169 (rival1) | -0.037 ± 0.216 (n 200) |
| three_card_keep | 5.874 | 1 | +0.501 ± 0.136 (gen_tag) | +0.501 ± 0.136 (gen_tag) | 6.168 | 1 | +0.450 ± 0.125 (rival1) | -0.051 ± 0.181 (n 200) |
| flush_over_full_house | 6.103 | 1 | +1.305 ± 0.145 (gen_pushfold) | +0.616 ± 0.165 (rival1) | 6.140 | 1 | +0.531 ± 0.147 (rival1) | -0.085 ± 0.217 (n 200) |
| fast_schedule | 6.119 | 1 | +1.249 ± 0.131 (gen_tag) | +0.735 ± 0.157 (rival1) | 6.114 | 1 | +0.600 ± 0.160 (rival1) | -0.135 ± 0.176 (n 200) |
| straddle | 6.284 | 1 | +1.366 ± 0.139 (gen_tag) | +0.831 ± 0.164 (rival1) | 6.380 | 1 | +0.696 ± 0.173 (rival1) | -0.135 ± 0.203 (n 200) |
| deal5_keep2 | 6.121 | 1 | +0.654 ± 0.133 (gen_tag) | +0.654 ± 0.133 (gen_tag) | 6.667 | 1 | +0.510 ± 0.101 (rival1) | -0.144 ± 0.159 (n 200) |
| exposed_card | 6.134 | 1 | +1.344 ± 0.147 (gen_tag) | +0.731 ± 0.158 (rival1) | 6.167 | 1 | +0.575 ± 0.147 (rival1) | -0.155 ± 0.189 (n 200) |
| two_boards | 6.092 | 1 | +1.338 ± 0.132 (gen_tag) | +0.508 ± 0.162 (rival1) | 6.127 | 1 | +0.351 ± 0.154 (rival1) | -0.157 ± 0.199 (n 200) |
| swap_holdem | 6.336 | 1 | +1.402 ± 0.139 (gen_tag) | +0.913 ± 0.157 (rival1) | 6.343 | 1 | +0.731 ± 0.158 (rival1) | -0.182 ± 0.222 (n 200) |
| three_card_blind_discard | 6.185 | 1 | +1.033 ± 0.136 (gen_tag) | +0.815 ± 0.159 (rival1) | 6.326 | 1 | +0.586 ± 0.118 (rival1) | -0.229 ± 0.187 (n 200) |
| bonus_card | 6.066 | 1 | +1.106 ± 0.148 (gen_tag) | +1.047 ± 0.167 (rival1) | 5.973 | 1 | +0.807 ± 0.138 (tag) | -0.240 ± 0.187 (n 200) |
| swap_one_turn | 6.484 | 1 | +1.642 ± 0.133 (gen_tag) | +1.158 ± 0.170 (rival1) | 6.445 | 1 | +0.917 ± 0.143 (rival1) | -0.241 ± 0.212 (n 200) |
| permuted_ranks | 6.715 | 1 | +1.598 ± 0.127 (gen_tag) | +1.598 ± 0.127 (gen_tag) | 6.693 | 1 | +1.329 ± 0.127 (tag) | -0.269 ± 0.164 (n 200) |
| toss_or_holdem | 6.284 | 1 | +1.031 ± 0.124 (gen_tag) | +1.026 ± 0.149 (rival1) | 6.409 | 1 | +0.688 ± 0.121 (rival1) | -0.338 ± 0.177 (n 200) |
| knockout_bounty | 8.252 | 1 | +2.802 ± 0.209 (gen_pushfold) | +1.778 ± 0.257 (rival1) | 8.102 | 1 | +1.414 ± 0.254 (rival1) | -0.364 ± 0.343 (n 200) |
| top_heavy | 29.170 | 1 | +17.625 ± 1.192 (gen_pushfold) | +10.042 ± 1.452 (rival1) | 28.629 | 1 | +8.995 ± 1.616 (rival1) | -1.047 ± 2.064 (n 200) |

Generic bots on the same 200 x 8 (points / exceptions / illegal / engine wall-clock p50 / p99 us; the wall p99 at load
12-16 includes scheduler preemptions and the variant decisions: CPU time is in section 5): **zero exceptions and zero
illegal actions for all three bots on all 26 entries.**

| variant | gen_mc | gen_tag | gen_pushfold |
|---|---|---|---|
| permuted_ranks | 4.82 / 0 / 0 / 8 / 566 | 5.12 / 0 / 0 / 10 / 114 | 5.04 / 0 / 0 / 9 / 131 |
| short_deck | 5.06 / 0 / 0 / 7 / 4254 | 5.53 / 0 / 0 / 9 / 190 | 5.35 / 0 / 0 / 9 / 235 |
| lowball | 6.02 / 0 / 0 / 7 / 457 | 5.75 / 0 / 0 / 9 / 48 | 5.70 / 0 / 0 / 8 / 46 |
| wild_deuces | 5.69 / 0 / 0 / 7 / 322 | 5.86 / 0 / 0 / 8 / 338 | 5.81 / 0 / 0 / 8 / 349 |
| flush_over_full_house | 4.48 / 0 / 0 / 7 / 2121 | 4.78 / 0 / 0 / 10 / 225 | 4.80 / 0 / 0 / 9 / 326 |
| toss_or_holdem | 4.72 / 0 / 0 / 13 / 8111 | 5.25 / 0 / 0 / 16 / 803 | 5.05 / 0 / 0 / 15 / 4035 |
| three_card_blind_discard | 4.81 / 0 / 0 / 13 / 8060 | 5.15 / 0 / 0 / 16 / 1381 | 4.97 / 0 / 0 / 15 / 4405 |
| three_card_keep | 5.02 / 0 / 0 / 12 / 2047 | 5.37 / 0 / 0 / 14 / 415 | 5.31 / 0 / 0 / 14 / 427 |
| omaha_four | 5.36 / 0 / 0 / 12 / 202 | 5.63 / 0 / 0 / 15 / 241 | 5.40 / 0 / 0 / 14 / 220 |
| swap_holdem | 4.45 / 0 / 0 / 8 / 795 | 4.93 / 0 / 0 / 10 / 233 | 4.67 / 0 / 0 / 10 / 251 |
| swap_one_turn | 4.47 / 0 / 0 / 8 / 1192 | 4.84 / 0 / 0 / 11 / 402 | 4.75 / 0 / 0 / 10 / 513 |
| exposed_card | 4.70 / 0 / 0 / 8 / 754 | 4.79 / 0 / 0 / 10 / 255 | 4.67 / 0 / 0 / 9 / 300 |
| two_boards | 4.70 / 0 / 0 / 8 / 1435 | 4.75 / 0 / 0 / 10 / 326 | 4.70 / 0 / 0 / 9 / 365 |
| bonus_card | 4.18 / 0 / 0 / 9 / 4452 | 4.96 / 0 / 0 / 11 / 820 | 4.56 / 0 / 0 / 11 / 1571 |
| auction | 4.32 / 0 / 0 / 8 / 4313 | 4.95 / 0 / 0 / 11 / 612 | 4.72 / 0 / 0 / 10 / 1420 |
| deal5_keep2 | 5.30 / 0 / 0 / 15 / 5166 | 5.47 / 0 / 0 / 17 / 957 | 5.26 / 0 / 0 / 17 / 4030 |
| bounty | 4.36 / 0 / 0 / 17 / 4043 | 4.92 / 0 / 0 / 20 / 589 | 4.76 / 0 / 0 / 18 / 627 |
| knockout_bounty | 4.99 / 0 / 0 / 8 / 661 | 5.37 / 0 / 0 / 10 / 244 | 5.45 / 0 / 0 / 9 / 262 |
| top_heavy | 9.11 / 0 / 0 / 8 / 670 | 10.91 / 0 / 0 / 11 / 231 | 11.54 / 0 / 0 / 10 / 280 |
| hi_lo | 4.53 / 0 / 0 / 7 / 1051 | 4.81 / 0 / 0 / 10 / 297 | 4.56 / 0 / 0 / 9 / 334 |
| pot_limit | 4.51 / 0 / 0 / 8 / 505 | 4.88 / 0 / 0 / 10 / 178 | 4.72 / 0 / 0 / 9 / 271 |
| antes_from_level_3 | 4.43 / 0 / 0 / 8 / 481 | 4.86 / 0 / 0 / 10 / 167 | 4.76 / 0 / 0 / 9 / 190 |
| fixed_raise | 4.56 / 0 / 0 / 8 / 4025 | 4.71 / 0 / 0 / 11 / 234 | 4.34 / 0 / 0 / 10 / 259 |
| fast_schedule | 4.53 / 0 / 0 / 8 / 444 | 4.87 / 0 / 0 / 10 / 153 | 4.86 / 0 / 0 / 9 / 167 |
| straddle | 4.28 / 0 / 0 / 10 / 1009 | 4.92 / 0 / 0 / 13 / 248 | 4.81 / 0 / 0 / 12 / 310 |
| river_of_blood | 4.54 / 0 / 0 / 8 / 4209 | 4.88 / 0 / 0 / 11 / 345 | 4.73 / 0 / 0 / 10 / 459 |

What the board says:

- **F is first on all 26 entries against the generic aware field** too, but its lead shrinks beyond noise on three:
  **lowball** +3.13 -> +0.86 (shrink +2.27 ± 0.15; F 7.79 -> 6.88; gen_mc 6.02 is the best opponent), **wild_deuces**
  +1.73 -> +0.20 (shrink +1.53 ± 0.21; F 6.96 -> 6.06; gen_tag 5.86), **short_deck** +0.78 -> +0.28 (shrink +0.50 ±
  0.17; F 6.16 -> 5.81; gen_tag 5.53). On those, `realistic`'s tag, pushfold and Monte Carlo seats play hold'em's
  hand values (high cards in lowball, deuces as deuces, hold'em ranges in a 36-card deck), so the twist-blind field
  overstated F by 0.5 to 2.3 points a table.
- Everywhere else the shrink is inside noise or negative: F's margin grows on toss_or_holdem (-0.34 ± 0.18),
  permuted_ranks (-0.27 ± 0.16), swap_one_turn, bonus_card and three_card_blind_discard (-0.23 to -0.24, at the noise
  edge): the generic seats take points from rival 1 (the best opponent there in both fields) more than from F.
- **Smallest leads against twist-reading seats** (the margin, not the shrink): fixed_raise +0.08 ± 0.16 (rival 1; the
  same on realistic, +0.14: not a twist-reading problem), wild_deuces +0.20, short_deck +0.28, omaha_four +0.45 (F
  6.67 -> 6.08), three_card_keep +0.50, hi_lo +0.50, two_boards +0.51; F's points also drop most on deal5_keep2 (6.67
  -> 6.12) and omaha_four.
- **The generic field against the hand-built ones** (F's margin over its best opponent, the same 200 seeds,
  `--fields <twist>_aware`): toss_or_holdem +0.67 (toss_rival1; rival 1 with the aware toss) vs +1.03 generic (rival1
  blind there; gen_tag 5.25 vs toss_tag 5.18); bounty +0.95 vs +1.01 (rival1; bounty_tag 4.94, gen_tag 4.92);
  short_deck +0.53 (short_tag 5.42) vs +0.28 (gen_tag 5.53); river_of_blood +0.95 vs +1.04 (rival1; rob_tag 4.90,
  gen_tag 4.88). The generic field is as tough as the hand-built ones except on toss, where the hand-built field
  also seats an aware rival 1 (the generic field keeps the realistic seats blind: rival 1 is not ours to rewrite).

## 8. Targets for the variants track

1. **lowball** (shrink +2.27): F's lead falls from 3.1 to 0.9 points when the TAG, push/fold and Monte Carlo seats
   read 2-7. Hero plays it whole (score hook); its preflop and postflop were only ever measured against seats that
   value high cards.
2. **wild_deuces** (+1.53): F's lead is +0.20 ± 0.16 over gen_tag, at the noise edge. A deuce is the best card in the
   deck; F's charts and push/fold know it only through the score hook.
3. **short_deck** (+0.50): +0.28 over gen_tag (the hand-built field showed +0.53 over short_tag: the generic TAG,
   with ranges re-cut from the short-deck table and made-share reads, is the stronger opponent).
4. Then the small leads that are not shrinks: omaha_four (+0.45), three_card_keep, hi_lo, two_boards (about +0.5),
   and fixed_raise (+0.08 on both fields: F against rival 1 at fixed limit).

## 9. Runs (all screen seeds or fresh diagnostics; no held-out seed, judge or held-out variant)

| time | run | seeds | result |
|---|---|---|---|
| 08:2x | scratch thresholds.py (hold'em made-share thresholds) | 3,000 then 10,000 random spots, seed 20261102 | section 2 |
| 08:3x | lat.py / lat_all.py (CPU per decision) | 10000-10001 x 8 per entry | section 5 |
| 08:4x | agree.py (decision agreement on hold'em) | 10000-10005 x 8 | section 4 |
| 08:38-08:46 | `--prepare all` (26 tables; one stale copy killed, one crashed at bounty on a variable-shadowing bug, fixed, rerun for the missing ten) | - | section 3 |
| 08:39-08:41 | climb_accept confirm at c73a229 | night 10000-10039 x 8 | F 6.00103 |
| 08:43-10:41 | aware_board realistic (base worktree) | 10000-10199 x 8 | section 7 |
| 08:49-08:57 | aware_board generic_vs_{holdem,toss,bounty,short,rob} | 10000-10099 x 8 | section 4 |
| 08:57-10:05 | aware_board generic_aware (7a2ae19) | 10000-10199 x 8 | section 7 |
| 09:37-09:47 | aware_board <twist>_aware, four hand-built fields | 10000-10199 x 8 | section 7 |
| 09:37 | climb_accept rehearsal, first try | - | ImportError (circular import), fixed in fd4a40d |
| 10:06-10:09 | climb_accept rehearsal, three_boards file vs survival | 10000-10099 x 8 | 142.6 s, level |
| 10:09-10:12 | climb_accept confirm at fd4a40d | night 10000-10039 x 8 | identical samples |
| 10:10-10:24 | full suite | - | 1069 passed, 11 failed (section 10) |

## 10. Tests

- tests/test_generic_aware.py (57 tests): the field and no night pool; a committed table for every catalog entry; the
  hold'em twins are the classes themselves; the rollout prices lowball, wild cards and bounties as the variant does;
  public cards dead or held; every variant decision type answers legally; every catalog entry plays 40 hands with zero
  exceptions and illegal actions; a variant written as a file registers and the generic bots find its hooks; every
  import order registers everything. The registry-wide tests in tests/test_sim_bestiary.py cover the new bots too.
- hyperion/sim/runner.py `--list` printed the first line of every registered bot's docstring and crashed on a seat
  without one (compose's `register` creates such seats; test_cli_runs failed when it ran after them in the full suite):
  now prints an empty line for those. No play changes.
- Full suite on the final code, host load 13-16: **1080 passed, 12 failed, 10 skipped** (10 min). Rerun alone:
  test_drills_run toss-c, test_gate history, and the budget tests for aware_mc, rival3 and out_quants pass or skip for
  host load. Still failing, all on the wall clock or a replay that follows it: test_nightof_latency kit B/C (p99 544 us
  over the 500 us gate), the budget test for rob_mc (wall p99 8.7 ms), test_slowbox det_run_pairs (fails at base
  c73a229 too, its value moves run to run: 8.0, 5.0 vs 6.0), and the model-mode replay tests in test_sim_exploiter and
  test_sim_outside (fail at base c73a229 too under this load: Hero runs with its wall-clock deadlines there because
  those tests do not set the model-mode config). None involves a generic bot.
