# S17: one size for the exploit layer's stab (running log)

Branch climb/s17-stab-size, from main bb1569f. Brief (coordinator, 2026-11-03): item 2 of "Edges against strong
opponents" (docs/research/). The layer's `bet_checked` stab bets 0.33 pot and is mostly air, while Hero's own bets on
hold'em tables are one balanced size since batch 5 (`hero.postflop.balance_sizes`, 0.5 pot): the stab's size says
"air". Exploiter 2 raises small bets with any hand (S11: -750 bb in 120 heads-up tables), and adapt1 reads F's small
bets as weak (R6). Add `exploit.stab_size` (off by default): the stab bets Hero's balanced size where Hero has one.
Not this task: exploiter 3's edge (F folding after it checks) is S15's.

Rules kept: no H1-H18 (20000-38399), no judge set (30000-30399), no judge bot, judge field or held-out variant run,
read or tuned on. Decisions on screen seeds (10000-10199) through tools/climb_accept.py; the size survey on fresh
diagnostic seeds 8200-8239 (under 10000). Model mode, F as hyperion.ship builds it. Host shared: at most 3 worker
processes, nice 5.

Scratch tools (session scratchpad `goal/s17/`, measuring devices, never shipped):
- `survey.py`: every F decision with the simulator's cards. Source of each decision from the composite's counts
  before and after the act ("layer:bet_checked", "layer:steal", "layer:steal_fold", or the member that decided:
  hero, base = rival 3's core, elite1 = the strong route). Postflop bets with nothing to call: size of the pot
  before the bet, Hero's tier read (0-1 air ... 5+ two pair or better), adapt1's own showdown strength (made + draw,
  what its size counter averages), the answers (fold / call / raise) and F's answer to a raise. Preflop first-in
  raises: size in bb, the hand's percentile (top x of 1,326 combos by Hero's tables.rank), the answers.

## Findings

1. **F's two postflop sizes name the hand** (survey of F's bets by source, seeds 8200-8239, all 12 exploit cells,
   the five strong tables and night; run 1). The layer's stab is 32-54% of F's heads-up bets, always 0.33 pot, mean
   tier 1.1-1.4, 48-64% air, never two pair or better (adapt1's own strength measure 0.28-0.32). Hero's bets are one
   0.5 size, tier 3.0-4.6, 0-28% air, 20-40% two pair or better (0.52-0.69). Exploiter 2 raises 93% of the stabs
   heads-up and 34% three-handed, exploiter 1 46% heads-up; F folds 71-99% of those raises. Rival 3's core bets only
   preflop in F (postflop is Hero's).
2. **The steal's 2.0 bb is not read** (run 3). It always carries a hand rival 3's core folds (mean percentile
   0.77-0.94), against rival 3's 2.2 / 2.4 / 2.45 bb opens. But the same steals at 2.4 bb meet the same re-raise rates
   in every spot (strong tables 0.17 / 0.17 small blind, 0.21 / 0.20 button, 0.22 / 0.23 heads-up; adapt1 0.18 /
   0.18; exploiter 1 0.35 / 0.35): the size only trades calls for folds. Left as it is.
3. **One size at every table (C1, `exploit.stab_size`) closes the tell and fails a guard** (run 7, screen). With it,
   97-100% of F's heads-up bets are one size; raises of the stab drop from 93% to 1% (exploiter 2 heads-up), 46% to
   3% (exploiter 1), 9% to 3% (adapt1); the larger stab is folded to more by price-reading seats (night 0.54 -> 0.61,
   mirror 0.47 -> 0.67). Screen: exploit2_hu +0.247 ± 0.125, exploit2_3 +0.117 ± 0.107, adapt_hu +0.203 ± 0.126 (all
   up), exploiter 1 level, night +0.043 ± 0.064, but **realistic -0.078 ± 0.059 (down): REJECT**. realistic's Monte
   Carlo, loose and push/fold seats fold as often to 0.5 as to 0.33 (run 8), so there the larger stab only costs more.
4. **The one size at three players or fewer (C3: `exploit.stab_size` + `exploit.stab_alive` 3) keeps the gains and
   passes** (runs 10-11). A dev set (9000-9199) chose it over a higher fold bar for the larger stab (C2,
   `stab_min_fold` 0.48, which lost the gains). Screen: exploit2_hu **+0.247 ± 0.125**, exploit2_3 **+0.117 ± 0.107**,
   adapt_hu **+0.203 ± 0.126** (up, C1's numbers seed for seed); exploit_hu +0.045, exploit_3 +0.017, exploit +0.004
   (exploiter 1 level); exploit3_hu +0.068; adapt_3 +0.030; night -0.003 ± 0.014; realistic +0.006 ± 0.011; every
   guard, elite and variant cell level. **ACCEPT** under `--aim exploit`. Recommended for held-out confirmation:
   `{"dials": {"exploit.stab_size": true, "exploit.stab_alive": 3}}`.
5. **No value stab** (run 2): the layer only replaces Hero's checks, and Hero bets every value hand at the same 0.5
   first, so the one size already carries value and air (24-48% air, 9-23% two pair or better).
6. **F is bit-identical with the dials off**: 14 of 14 confirm and guard chunks (10000-10039) equal main's, at both
   codes (runs 5, 10). Latency of C3: hand end p99 141.7 µs, act p99 108.3 µs (per-call minimum; F 146.7 / 115.8 at
   the same load).
7. What C3 leaves: at a full table the stab is still 0.33 and still air, so a reader there can still use it (the
   8-max exploit cells were level with C1 as well, -0.111 to +0.127). Exploiter 3's edge (F folding after checking)
   is untouched here; it is S15's.

## Runs, as they happened

### 1. The size survey on main (bb1569f), 02:47-02:51

`WT=wt_s17_main survey.py --fields <the 12 exploit cells, elite, elite_night, mirror, elite_b, mirror_b, night>
--lo 8200 --hi 8240 --workers 3` (F as main ships it, from a detached worktree of bb1569f; 40 seeds x rotations,
211 s, load 9). Heads-up pots (multiway is 5-10% of F's bets and tells the same story). "Raised" is the share of the
answers to the bet that were raises; "F folds" counts F's answers to those raises.

| cell | stab: share of F's HU bets, size | tier / air / 2pr+ / adapt1 str | raised / F folds | Hero 0.45-0.58: share | tier / air / 2pr+ / adapt1 str | raised / F folds |
|---|---|---|---|---|---|---|
| exploit_hu | 32%, 0.33 | 1.11 / 62% / 0% / 0.29 | 46% / 56 of 79 | 66% | 4.52 / 1% / 40% / 0.69 | 3% / 1 of 12 |
| exploit_3 | 37%, 0.33 | 1.26 / 56% / 0% / 0.30 | 11% / 49 of 53 | 61% | 3.77 / 15% / 31% / 0.61 | 3% / 5 of 21 |
| exploit | 39%, 0.33 | 1.18 / 61% / 0% / 0.29 | 6% / 79 of 86 | 58% | 3.41 / 19% / 22% / 0.57 | 5% / 29 of 108 |
| exploit2_hu | 32%, 0.33 | 1.41 / 48% / 0% / 0.32 | 93% / 141 of 162 | 66% | 4.55 / 0% / 38% / 0.69 | 1% / 0 of 4 |
| exploit2_3 | 36%, 0.33 | 1.16 / 60% / 0% / 0.29 | 34% / 168 of 170 | 61% | 3.58 / 17% / 27% / 0.58 | 17% / 92 of 142 |
| exploit2 | 39%, 0.33 | 1.16 / 62% / 0% / 0.29 | 13% / 207 of 219 | 58% | 3.24 / 22% / 21% / 0.56 | 8% / 102 of 218 |
| exploit3_hu | 49%, 0.33 | 1.10 / 64% / 0% / 0.29 | 2% / 14 of 18 | 51% | 3.32 / 24% / 27% / 0.56 | 1% / 2 of 10 |
| exploit3_3 | 42%, 0.33 | 1.20 / 59% / 0% / 0.29 | 4% / 25 of 29 | 56% | 3.37 / 21% / 25% / 0.56 | 3% / 9 of 29 |
| exploit3 | 39%, 0.33 | 1.16 / 61% / 0% / 0.29 | 4% / 68 of 73 | 59% | 3.24 / 23% / 22% / 0.55 | 5% / 31 of 119 |
| adapt_hu | 54%, 0.33 | 1.11 / 61% / 0% / 0.28 | 9% / 50 of 66 | 46% | 3.00 / 28% / 22% / 0.52 | 1% / 0 of 6 |
| adapt_3 | 47%, 0.33 | 1.15 / 61% / 0% / 0.28 | 5% / 37 of 44 | 52% | 3.24 / 23% / 23% / 0.54 | 3% / 10 of 26 |
| adapt | 40%, 0.33 | 1.15 / 62% / 0% / 0.28 | 4% / 64 of 70 | 57% | 3.13 / 24% / 20% / 0.55 | 5% / 36 of 111 |
| elite | 42%, 0.33 | 1.17 / 60% / 0% / 0.29 | 4% / 54 of 58 | 56% | 3.42 / 19% / 21% / 0.58 | 6% / 24 of 115 |
| elite_night | 41%, 0.33 | 1.17 / 60% / 0% / 0.29 | 5% / 91 of 95 | 56% | 3.29 / 22% / 20% / 0.56 | 7% / 50 of 156 |
| mirror | 44%, 0.33 | 1.19 / 59% / 0% / 0.30 | 4% / 48 of 49 | 55% | 3.57 / 15% / 22% / 0.60 | 6% / 27 of 96 |
| elite_b | 43%, 0.33 | 1.20 / 60% / 0% / 0.29 | 6% / 81 of 84 | 55% | 3.43 / 17% / 20% / 0.59 | 7% / 37 of 122 |
| mirror_b | 44%, 0.33 | 1.24 / 59% / 0% / 0.30 | 5% / 61 of 66 | 54% | 3.53 / 16% / 21% / 0.60 | 5% / 28 of 80 |
| night | 41%, 0.33 | 1.11 / 64% / 0% / 0.28 | 4% / 80 of 82 | 57% | 3.13 / 25% / 20% / 0.54 | 7% / 58 of 187 |

Read:
- **F has two postflop sizes, and the size is the hand.** Every seat at every table sees the same split: the layer's
  stab is 32-54% of F's heads-up bets, always 0.33 pot, mean tier 1.1-1.4, 48-64% air, never two pair or better;
  Hero's bets are one 0.5 size (batch 5's one size; the other sizes are under 3% of F's bets: stations, all-ins),
  mean tier 3.0-4.6, 0-28% air, 20-40% two pair or better. adapt1's own strength measure reads 0.28-0.32 against
  0.52-0.69 (R6 saw 0.28-0.32 against 0.75-0.78; its "large" bucket is 0.6 pot and up, which F rarely bets now).
- Against exploiter 1 heads-up and exploiter 2 the tell is played: exploiter 2 raises 93% of the stabs heads-up and
  34% three-handed, exploiter 1 46% heads-up; F folds 71-99% of those raises. Hero's 0.5 bets are raised 1-3%
  heads-up. Against exploiter 2 heads-up Hero's bets are pure value (0% air): the layer takes every bluff, so the
  two sizes split value from air exactly.
- Nobody else raises the stab much (2-9%), but it is called 33-54% of the time almost everywhere, and folded to by
  F after any raise (87-100%).
- Rival 3's core never bets postflop in F (postflop is Hero's); its sizes are preflop only (below).

### 2. The dial (8fbead6) and the same survey with it on, 02:55-03:03

`exploit.stab_size` (hyperion/strategy/exploit.py, off by default): at each table start the host hands the layer its
postflop's params (`Exploit.size_from`): where `balance_sizes` is on for this table (Hero picks its params per table:
with `s11_holdem_only`, hold'em tables only), the stab bets `balance_size` (0.5) of the pot, else `bet_frac` (0.33).
The composite passes its hero member's postflop (the member that plays postflop in F; the base's fallback Hero when
no hero member is routed); Hero with its own layer passes its own. Everything else about the stab (who is bluffable,
the 0.4 fold product, the quarter-of-my-chips cap, the big-blind minimum) is unchanged. tests/test_s17_stab_size.py:
the size per table (hold'em 0.5; a bounty table and `balance_sizes` off keep 0.33; the dial off keeps 0.33), Hero's
own layer, and that the dial reaches heads-up decisions against exploiter 2 and replays exactly.

`run_surveys2.sh`: the survey again on main (wt_s17_main; identical counts, float sums aside) and with
`{"exploit.stab_size": true}` (wt_s17_meas, a detached worktree of 8fbead6), seeds 8200-8239.

The stab's answers, per answer (heads-up pots; multiway the same direction):

| cell | stabs main / C1 | fold / call / raise at 0.33 | at 0.5 |
|---|---|---|---|
| exploit_hu | 172 / 244 | 0.14 / 0.40 / **0.46** | 0.41 / 0.56 / 0.03 |
| exploit_3 | 466 / 487 | 0.43 / 0.46 / 0.11 | 0.52 / 0.45 / 0.03 |
| exploit | 1429 / 1414 | 0.52 / 0.42 / 0.06 | 0.59 / 0.37 / 0.04 |
| exploit2_hu | 174 / 347 | 0.03 / 0.03 / **0.93** | 0.55 / 0.44 / 0.01 |
| exploit2_3 | 496 / 558 | 0.35 / 0.30 / **0.34** | 0.56 / 0.36 / 0.08 |
| exploit2 | 1736 / 1678 | 0.49 / 0.38 / 0.13 | 0.60 / 0.35 / 0.04 |
| exploit3_hu | 759 / 811 | 0.48 / 0.50 / 0.02 | 0.55 / 0.42 / 0.03 |
| exploit3_3 | 826 / 824 | 0.42 / 0.54 / 0.04 | 0.52 / 0.44 / 0.04 |
| exploit3 | 1672 / 1616 | 0.53 / 0.43 / 0.04 | 0.60 / 0.36 / 0.04 |
| adapt_hu | 775 / 876 | 0.58 / 0.33 / 0.09 | 0.70 / 0.27 / 0.03 |
| adapt_3 | 805 / 802 | 0.58 / 0.37 / 0.05 | 0.65 / 0.32 / 0.03 |
| adapt | 1658 / 1557 | 0.55 / 0.40 / 0.04 | 0.64 / 0.32 / 0.04 |
| elite | 1385 / 1303 | 0.46 / 0.50 / 0.04 | 0.56 / 0.40 / 0.04 |
| elite_night | 1769 / 1588 | 0.51 / 0.44 / 0.05 | 0.59 / 0.36 / 0.05 |
| mirror | 1325 / 1219 | 0.47 / 0.50 / 0.04 | 0.67 / 0.29 / 0.04 |
| elite_b | 1347 / 1181 | 0.52 / 0.42 / 0.06 | 0.60 / 0.34 / 0.06 |
| mirror_b | 1248 / 1134 | 0.50 / 0.45 / 0.05 | 0.69 / 0.26 / 0.05 |
| night | 2053 / 1926 | 0.54 / 0.42 / 0.04 | 0.61 / 0.35 / 0.04 |

F's whole heads-up 0.45-0.58 range, main -> C1 (with C1 it is 97-100% of F's heads-up bets):

| cell | tier / air / 2pr+ / adapt1 str, main | C1 | raised, F folds to the raise: main | C1 |
|---|---|---|---|---|
| exploit_hu | 4.52 / 1% / 40% / 0.69 | 3.06 / 28% / 23% / 0.52 | 3%, 1 of 12 | 3%, 7 of 20 |
| exploit2_hu | 4.52 / 1% / 38% / 0.69 | 3.01 / 24% / 20% / 0.51 | 1%, 0 of 4 | 1%, 4 of 10 |
| exploit2_3 | 3.54 / 17% / 27% / 0.58 | 2.57 / 35% / 16% / 0.46 | 17%, 93 of 143 | 14%, 134 of 188 |
| exploit3_hu | 3.32 / 24% / 27% / 0.56 | 2.13 / 45% / 13% / 0.41 | 1%, 2 of 10 | 2%, 18 of 30 |
| adapt_hu | 3.00 / 28% / 22% / 0.52 | 1.89 / 48% / 9% / 0.38 | 1%, 0 of 6 | 2%, 23 of 32 |
| adapt_3 | 3.23 / 23% / 23% / 0.54 | 2.21 / 42% / 11% / 0.42 | 3%, 10 of 26 | 3%, 28 of 51 |
| adapt | 3.12 / 24% / 20% / 0.54 | 2.31 / 40% / 11% / 0.44 | 5%, 37 of 112 | 4%, 91 of 165 |
| elite | 3.42 / 19% / 21% / 0.58 | 2.43 / 38% / 12% / 0.46 | 6%, 24 of 115 | 5%, 73 of 161 |
| mirror | 3.57 / 15% / 22% / 0.60 | 2.51 / 36% / 12% / 0.47 | 6%, 27 of 96 | 5%, 74 of 138 |
| night | 3.11 / 25% / 20% / 0.54 | 2.31 / 41% / 12% / 0.44 | 7%, 59 of 188 | 5%, 128 of 260 |

F's points on these 40 seeds (diagnostic only, too few seeds to decide anything): exploit2_hu 7.787 -> 8.088,
exploit2_3 7.483 -> 7.675, adapt_hu 8.800 -> 9.062, adapt_3 7.975 -> 8.033, exploit_hu 9.400 -> 9.512, exploit_3
8.775 -> 8.525, exploit3_hu 8.200 -> 8.350, night 5.956 -> 6.091, elite 4.725 -> 4.774, elite_b 4.710 -> 4.588,
mirror_b 4.565 -> 4.494.

Read:
- **The raises of the stab go away**: exploiter 2 heads-up from 93% of its answers to 1%, three-handed 34% to 8%;
  exploiter 1 heads-up 46% to 3%; adapt1 9% to 3%. Exploiter 2 reads 0.5 as "medium" (it raises those only as a
  flop c-bet by the preflop raiser while its count of our folds to its raises stays high), and adapt1's size counter
  has no small bucket left to read (small is 0.45 pot or less, large 0.6 or more).
- **The larger stab is folded to more, everywhere** (night 0.54 -> 0.61, elite 0.46 -> 0.56, mirror 0.47 -> 0.67):
  the opponents call by price. With the stab's hand as air (tier about 1.1), its value per stab heads-up is roughly
  fold x pot - call x bet: night 0.39 -> 0.42 pot, elite 0.28 -> 0.34, mirror 0.29 -> 0.51. The S2 caveat (a 0.5 stab
  needs 33% folds, not 25%) does not bite: the 0.4 fold product still gates it and the folds rose.
- **The size carries both without a value stab.** The layer only ever replaces Hero's checks, and Hero bets every
  value hand (value tier and up) at the same 0.5 first, so in the spots the layer stabs, F's 0.5 range is Hero's value
  plus the layer's air: 24-48% air, 9-23% two pair or better, one size for 97-100% of F's heads-up bets. A value stab
  would have nothing to take: there is no value hand left in the checks it replaces (Hero's only value checks are the
  ICM commit gate, where the layer's quarter-of-my-chips cap refuses too). Not built.

### 3. The steal's 2.0 bb against rival 3's opens, 02:55-03:08

From the run 1 survey (main): F's first-in raises by source. Rival 3's core opens 2.2 bb heads-up, 2.4 three-handed,
2.45 at four or more; elite1 (the strong route, 10-20 bb) 2.33; the layer's steals are 2.0 bb every time, with the
hands rival 3's core folds (mean percentile 0.77-0.94, 0-5% in the top 20%, 85-100% outside the top half). So 2.0 bb
names a hand from the bottom of the deck. Does anyone read it? The same survey with `{"exploit.steal_bb": 2.4}`
(wt_s17_meas, seeds 8200-8239; a measuring device, not a candidate): the steals fire in the same spots, so the answers
to the same steals at 2.0 and at 2.4 bb say whether the size moves anyone. Answers per answering seat, fold / call /
re-raise, beside rival 3's own opens from the same seat (strong = elite, mirror, elite_b, mirror_b, elite_night):

| tables | spot | steal at 2.0 | the same steals at 2.4 | rival 3's opens there |
|---|---|---|---|---|
| strong | 4+ alive, button (n 284 / 288) | 0.66 / 0.13 / 0.21 | 0.70 / 0.10 / 0.20 | 0.69 / 0.20 / 0.11 |
| strong | 4+, small blind (453 / 453) | 0.55 / 0.28 / 0.17 | 0.60 / 0.23 / 0.17 | 0.57 / 0.29 / 0.14 |
| strong | 3-handed, small blind (112 / 128) | 0.56 / 0.20 / 0.24 | 0.57 / 0.16 / 0.27 | 0.53 / 0.23 / 0.24 |
| strong | heads-up (142 / 150) | 0.46 / 0.32 / 0.22 | 0.57 / 0.20 / 0.23 | 0.47 / 0.27 / 0.26 |
| adapt cells | 4+, small blind (129 / 129) | 0.51 / 0.36 / 0.12 | 0.57 / 0.29 / 0.13 | 0.67 / 0.23 / 0.10 |
| adapt cells | heads-up (159 / 153) | 0.60 / 0.22 / 0.18 | 0.61 / 0.21 / 0.18 | 0.53 / 0.33 / 0.14 |
| exploiter 1 cells | heads-up (283 / 274) | 0.58 / 0.07 / 0.35 | 0.59 / 0.05 / 0.35 | 0.54 / 0.12 / 0.34 |
| exploiter 2 cells | 4+, small blind (155 / 147) | 0.43 / 0.36 / 0.21 | 0.47 / 0.33 / 0.20 | 0.56 / 0.30 / 0.15 |
| exploiter 2 cells | heads-up (128 / 132) | 0.69 / 0.18 / 0.13 | 0.71 / 0.16 / 0.13 | 0.42 / 0.38 / 0.20 |
| exploiter 3 cells | 4+, small blind (134 / 132) | 0.52 / 0.34 / 0.14 | 0.58 / 0.27 / 0.15 | 0.55 / 0.27 / 0.18 |
| night | heads-up (89 / 94) | 0.70 / 0.24 / 0.07 | 0.78 / 0.16 / 0.06 | 0.65 / 0.23 / 0.12 |

Read: **no size read separates the steal.** In every spot the re-raise rate against the same steals is the same at
2.0 and 2.4 bb (0.17 / 0.17, 0.21 / 0.20, 0.22 / 0.23, 0.18 / 0.18, 0.35 / 0.35 ...); the larger size only trades
calls for folds, which is price, not a read. Where the steals meet more re-raises than rival 3's opens (strong tables,
button: 0.21 against 0.11) they do so at either size: that is the spot the steal fires in (seats behind that read
as folders), not its size. F's points with the 2.4 steal on these seeds are level everywhere (-0.13 to +0.16, 40
seeds). **The steal stays as it is**; no dial added.

### 4. The candidate, fixed before the screen (03:10)

**C1 = `{"dials": {"exploit.stab_size": true}}`** on top of F: the layer's stab bets Hero's one size (0.5) on hold'em
tables, 0.33 elsewhere as now. Nothing else: no value stab (run 2: Hero already bets every value hand at that size in
the spots the layer stabs), no steal change (run 3: nobody reads the steal's size), no heads-up-only form (multiway
stabs at 0.5 are folded to more too: night 0.69 -> 0.73, elite_night 0.59 -> 0.69). One candidate.

### 5. Identity with the dial off (03:10-03:12)

From wt_s17_meas (8fbead6, code cc3e60d954): `climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages
confirm,guards --workers 3 --out s17/ca_ident` (2.3 min). Compared chunk for chunk (scratch `cmp_id.py`: samples, call
counts) with main's cache of the same command at code 4b28a28819 (bb1569f's hyperion tree, run from a detached
worktree of main: `goal/idchk18/post/f582563b88a4`): **14 of 14 chunks identical**. night 5.965, night_hard 5.638,
realistic 6.269, top 5.023, night @10/7/5/4/3/2/1/0 6.218, night @50/25/12/6/3/2/1/1 24.589, night +double 5.853:
R6's main baseline to the third decimal.

### 6. Latency (03:13-03:16)

From wt_s17_meas: `tools/latency.py --hand-end --reps 3 --p99-us 200 --dials '{}'` and `--dials '{"exploit.stab_size":
true}'` (realistic, 20 tables, seed 2026, load 10.5). Per-call minimum of 3:

| | hand_end p50 / p99 / max | act p50 / p99 / max | first act p99 |
|---|---|---|---|
| F | 56.4 / 136.3 / 186.7 µs | 50.9 / 99.0 / 138.0 µs | 126.1 µs |
| C1 | 56.2 / 137.2 / 182.2 µs | 52.2 / 100.8 / 146.7 µs | 133.2 µs |

Both under 200 µs (OK, exit 0). The dial costs one attribute read per stab and one at each table start.

### 7. The screen of C1 (03:17-05:26)

From wt_s17_meas (8fbead6, code cc3e60d954): `climb_accept --cand '{"dials": {"exploit.stab_size": true}}' --base
'{"dials": {}}' --aim exploit --set screen --stages exploit,confirm,guards,elite,variants --workers 3 --out s17/ca
--json s17/res/screen_c1.json` (133.9 min, load 9-14). No timeouts or errors in any cell.

| stage | cell | F | C1 | C1 - F | |
|---|---|---|---|---|---|
| exploit | exploit @10/7/5/4/3/2/1/0 | 5.839 | 5.829 | -0.010 ± 0.156 | level (exploiter1 4.608 -> 4.748) |
| | exploit_hu | 9.227 | 9.273 | +0.045 ± 0.106 | level (7.772 -> 7.728) |
| | exploit_3 | 8.458 | 8.475 | +0.017 ± 0.128 | level (6.900 -> 6.898) |
| | exploit2 @10/7/5/4/3/2/1/0 | 5.844 | 5.972 | +0.127 ± 0.129 | level (exploiter2 5.086 -> 4.827) |
| | exploit2_hu | 7.848 | 8.095 | **+0.247 ± 0.125** | **UP** (9.152 -> 8.905) |
| | exploit2_3 | 7.378 | 7.495 | **+0.117 ± 0.107** | **UP** (8.165 -> 7.990) |
| | exploit3 @10/7/5/4/3/2/1/0 | 5.471 | 5.481 | +0.010 ± 0.105 | level |
| | exploit3_hu | 8.268 | 8.335 | +0.068 ± 0.129 | level |
| | exploit3_3 | 7.528 | 7.538 | +0.010 ± 0.114 | level |
| | adapt @10/7/5/4/3/2/1/0 | 5.889 | 5.778 | -0.111 ± 0.114 | level (adapt1 5.106 -> 5.138) |
| | adapt_hu | 8.605 | 8.807 | **+0.203 ± 0.126** | **UP** (8.395 -> 8.193) |
| | adapt_3 | 8.007 | 8.037 | +0.030 ± 0.123 | level (7.657 -> 7.577) |
| confirm | night | 5.972 | 6.015 | +0.043 ± 0.064 | level |
| guards | night_hard | 5.499 | 5.481 | -0.017 ± 0.075 | level |
| | realistic | 6.370 | 6.292 | **-0.078 ± 0.059** | **DOWN** |
| | top | 5.058 | 5.074 | +0.016 ± 0.079 | level |
| | night @10/7/5/4/3/2/1/0 | 6.199 | 6.177 | -0.023 ± 0.114 | level |
| | night @50/25/12/6/3/2/1/1 | 24.699 | 25.168 | +0.468 ± 0.758 | level |
| | night +double | 5.848 | 5.862 | +0.014 ± 0.061 | level |
| elite | elite | 4.865 | 4.829 | -0.036 ± 0.074 | level |
| | elite_night | 5.422 | 5.384 | -0.038 ± 0.070 | level |
| | mirror | 4.498 | 4.558 | +0.061 ± 0.081 | level |
| | elite_b | 4.638 | 4.683 | +0.045 ± 0.076 | level |
| | mirror_b | 4.466 | 4.548 | +0.082 ± 0.090 | level |
| variants | 22 twist entries | | | +0.000 ± 0.000 | identical (the one size is hold'em only) |
| | top_heavy | 28.654 | 28.292 | -0.362 ± 0.755 | level |
| | antes_from_level_3 | 6.496 | 6.462 | -0.034 ± 0.053 | level |
| | fast_schedule | 6.122 | 6.072 | -0.050 ± 0.057 | level |
| | straddle | 6.412 | 6.410 | -0.002 ± 0.056 | level |

Verdict: **REJECT** on one guard. The exploit rule is met (exploit2_hu, exploit2_3, adapt_hu up; none down;
exploiter 1 not down; night level, +0.043), elite and variants none down, but realistic is down (-0.078 ± 0.059),
and the four hold'em-shaped variants, all played on realistic, lean the same way (level each).

### 8. Why realistic loses (05:27-05:35)

`survey.py` (now also counting who answers each stab) on realistic, adapt and night, seeds 8200-8279, main
(wt_s17_main) and C1 (wt_s17_meas). Answers to the stab per answering bot, fold / call / raise, 0.33 -> 0.5:

| bot (realistic) | answers | at 0.33 | at 0.5 |
|---|---|---|---|
| rival1 | 1412 / 1258 | 0.47 / 0.50 / 0.03 | 0.57 / 0.39 / 0.03 |
| montecarlo | 823 / 764 | 0.64 / 0.29 / 0.08 | 0.64 / 0.27 / 0.09 |
| montecarlo30 | 496 / 464 | 0.38 / 0.51 / 0.11 | 0.39 / 0.50 / 0.11 |
| loose_aggro | 760 / 769 | 0.86 / 0.07 / 0.07 | 0.85 / 0.08 / 0.07 |
| pushfold | 309 / 296 | 0.77 / 0.10 / 0.13 | 0.77 / 0.12 / 0.11 |
| tag | 135 / 148 | 0.73 / 0.15 / 0.12 | 0.76 / 0.12 / 0.12 |
| night pool seats (night) | 4293 / 4080 | 0.54 / 0.41 / 0.04 | 0.62 / 0.34 / 0.04 |
| adapt1 (adapt, 8-max) | 535 / 535 | 0.58 / 0.35 / 0.07 | 0.64 / 0.32 / 0.04 |

F's points on these 80 seeds: realistic 6.292 -> 6.231, adapt 5.595 -> 5.708, night 5.890 -> 6.008.

Read: night's pool, the strong bots, rival 1 and adapt1 call by price, so a larger stab is folded to more and pays.
realistic's Monte Carlo seats, the loose student and the push/fold bot fold exactly as often to 0.5 as to 0.33: against
them the larger stab only costs more when it is called or raised (against montecarlo30, roughly 0.17 of the pot per
stab at 0.33 and 0.09 at 0.5). The research note's risk ("a few stabs that were thin at 0.33 lose at 0.5") is this.

### 9. Two narrower forms (4bd9a3c), both off by default

- `exploit.stab_alive` N: the one size only while at most N players have chips (or are all in this hand); above that,
  bet_frac. The tell is played in short-handed pots against the same seat (exploiter 2 and adapt1 gained heads-up
  and three-handed; the 8-max exploit cells were level), while a full table holds the equity callers.
- `exploit.stab_min_fold` x: the one-size stab needs the fold product to be at least x (0 = bet_min_fold). 0.48 keeps
  bet_min_fold's margin (0.4 against a 0.25 break-even at 0.33) over the 0.5 bet's 0.33 break-even.

Tests: tests/test_s17_stab_size.py (both gates; neither touches the stab without the one size).

### 10. Identity again, and the three forms on a dev set (05:36-06:12)

Identity at 4bd9a3c (code bf168db5ac), same command as run 5 (`--out s17/ca_ident2`): **14 of 14 chunks identical**
to main's.

Scratch `quick.py` (climb_accept's own run_cells / gather / paired on chosen cells, code bf168db5ac), dev seeds
9000-9199 (not a screen, held-out or judge seed), F and three forms:
C1 = `{"exploit.stab_size": true}`, C2 = C1 + `"exploit.stab_min_fold": 0.48`, C3 = C1 + `"exploit.stab_alive": 3`.

| cell | F | C1 - F | C2 - F | C3 - F |
|---|---|---|---|---|
| realistic | 6.374 | -0.021 ± 0.056 | -0.031 ± 0.061 | +0.000 ± 0.010 |
| night | 6.096 | -0.050 ± 0.065 | -0.022 ± 0.066 | -0.012 ± 0.014 |
| exploit2_hu | 7.848 | **+0.172 ± 0.100 UP** | +0.098 ± 0.102 | **+0.172 ± 0.100 UP** |
| exploit2_3 | 7.348 | **+0.237 ± 0.113 UP** | **+0.260 ± 0.117 UP** | **+0.237 ± 0.113 UP** |
| adapt_hu | 8.672 | +0.105 ± 0.115 | +0.075 ± 0.130 | +0.105 ± 0.115 |
| adapt_3 | 7.993 | +0.123 ± 0.142 | -0.098 ± 0.141 | +0.123 ± 0.142 |
| exploit_hu | 9.250 | +0.007 ± 0.097 | +0.015 ± 0.098 | +0.007 ± 0.097 |

Read: C1's gains repeat on fresh seeds (exploit2 heads-up and three-handed up again; adapt1 up a little). C2's
higher fold bar costs the gains (it drops stabs against exploiter 2 heads-up and adapt1 three-handed, which fold
0.55-0.65 to the larger stab) and does not help realistic. C3 plays C1 exactly in every heads-up and three-handed cell
(at most three players have chips there) and stays within a hundredth of F at full tables: it keeps the gain where the
tell is read and leaves the 8-max play where the callers are.

**Final candidate, fixed here: C3 = `{"dials": {"exploit.stab_size": true, "exploit.stab_alive": 3}}`.**

### 11. The screen of C3 (from 06:14)

From wt_s17_meas (4bd9a3c, code bf168db5ac): `climb_accept --cand '{"dials": {"exploit.stab_size": true,
"exploit.stab_alive": 3}}' --base '{"dials": {}}' --aim exploit --set screen --stages
exploit,confirm,guards,elite,variants --workers 3 --out s17/ca --json s17/res/screen_c3.json`, launched detached.
F's 400 screen chunks are pinned: copied from run 7's cache (code cc3e60d954) under F's key at bf168db5ac, since F
plays bit-identically at both codes (runs 5 and 10) and the code between them only adds branches behind `stab_size`.

Partial at 07:23 (exploit, confirm, guards, elite done; variants running; load 23-28):

| stage | cell | F | C3 | C3 - F | |
|---|---|---|---|---|---|
| exploit | exploit @10/7/5/4/3/2/1/0 | 5.839 | 5.843 | +0.004 ± 0.031 | level (exploiter1 4.608 -> 4.612) |
| | exploit_hu | 9.227 | 9.273 | +0.045 ± 0.106 | level (7.772 -> 7.728) |
| | exploit_3 | 8.458 | 8.475 | +0.017 ± 0.128 | level (6.900 -> 6.898) |
| | exploit2 @10/7/5/4/3/2/1/0 | 5.844 | 5.871 | +0.026 ± 0.039 | level (5.086 -> 5.057) |
| | exploit2_hu | 7.848 | 8.095 | **+0.247 ± 0.125** | **UP** (9.152 -> 8.905) |
| | exploit2_3 | 7.378 | 7.495 | **+0.117 ± 0.107** | **UP** (8.165 -> 7.990) |
| | exploit3 @10/7/5/4/3/2/1/0 | 5.471 | 5.476 | +0.005 ± 0.032 | level |
| | exploit3_hu | 8.268 | 8.335 | +0.068 ± 0.129 | level |
| | exploit3_3 | 7.528 | 7.538 | +0.010 ± 0.114 | level |
| | adapt @10/7/5/4/3/2/1/0 | 5.889 | 5.901 | +0.013 ± 0.035 | level (adapt1 5.106 -> 5.111) |
| | adapt_hu | 8.605 | 8.807 | **+0.203 ± 0.126** | **UP** (8.395 -> 8.193) |
| | adapt_3 | 8.007 | 8.037 | +0.030 ± 0.123 | level (7.657 -> 7.577) |
| confirm | night | 5.972 | 5.969 | -0.003 ± 0.014 | level |
| guards | night_hard | 5.499 | 5.495 | -0.004 ± 0.013 | level |
| | realistic | 6.370 | 6.375 | +0.006 ± 0.011 | level |
| | top | 5.058 | 5.059 | +0.001 ± 0.010 | level |
| | night @10/7/5/4/3/2/1/0 | 6.199 | 6.191 | -0.008 ± 0.034 | level |
| | night @50/25/12/6/3/2/1/1 | 24.699 | 24.844 | +0.144 ± 0.274 | level |
| | night +double | 5.848 | 5.856 | +0.008 ± 0.011 | level |
| elite | elite | 4.865 | 4.870 | +0.004 ± 0.011 | level |
| | elite_night | 5.422 | 5.430 | +0.009 ± 0.015 | level |
| | mirror | 4.498 | 4.498 | +0.000 ± 0.008 | level |
| | elite_b | 4.638 | 4.637 | -0.001 ± 0.013 | level |
| | mirror_b | 4.466 | 4.475 | +0.009 ± 0.010 | level |

The heads-up and three-handed exploit cells are C1's to the last seed (at most three players have chips there).

Complete at 08:27 (133.8 min, load 23-59). Variants: the 22 twist entries identical (+0.000 ± 0.000); top_heavy
28.654 -> 28.828 (+0.174 ± 0.213), antes_from_level_3 -0.005 ± 0.011, fast_schedule -0.001 ± 0.009, straddle +0.006 ±
0.011, all level. No timeouts or errors in any cell. (The p99 column of this run's output reads 8,000-10,000 µs for C3
against about 400-4,100 for F: F's chunks ran in run 7 at load 11, C3's at load 55-59; the p50 is 85 against 88 µs,
and run 12's per-call minimum is what measures the bot.)

**Verdict: ACCEPT** (`--aim exploit`): exploit2_hu, exploit2_3 and adapt_hu up; no exploit cell down (exploiter 1
level in all three); night level (-0.003 ± 0.014); no guard, elite or variant cell down.

### 12. Latency of C3, and the tests (08:27-08:35)

`tools/latency.py --hand-end --reps 3 --p99-us 200 --dials '{"exploit.stab_size": true, "exploit.stab_alive": 3}'`
from wt_s17_meas, load 23.6: hand_end per-call minimum p50 57.1 / p99 141.7 / max 206.3 µs, act p99 108.3 µs, first
act p99 145.4 µs: OK. F beside it (load 22.9): hand_end p99 146.7 µs, act p99 115.8 µs.
`pytest tests/test_s17_stab_size.py tests/test_strategy_exploit_layer.py tests/test_strategy_exploit.py
tests/test_s11_dials.py tests/test_compose.py tests/test_ship.py tests/test_compose_levels.py
tests/test_compose_sections.py`: 106 passed.
