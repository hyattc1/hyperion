# Hybrid candidate: running log

Rival 2's decision core behind Hero's shell (`hyperion/hybrid/`, simulator name `hybrid`). A candidate measured
against Hero, not a replacement: which bot ships is the owner's decision. Measurements land here as they finish;
the summary goes to docs/decisions.md, "Hybrid candidate". Rival 3 (`holdout`) is measured once per candidate
version and never tuned on.

## 2026-11-01 01:30 ET: v1 built (commit below)

- `hyperion/hybrid/core.py`: `Rival2Core` subclasses rival 2's `Bot` (nothing in `hyperion/sim/rivals/` edited or
  copied). Its ICM curve is built from `Rules.payouts` at rival 2's own knots with Hero's exact `icm_value`, in
  hand_end (outside the clock; rival 2 built it inside the first decision of every hand: ~115 us p50, ~500 us
  p99). Sampler: `mc_max` 64 samples (rival 2: 160, cut by its 260 us clock at ~110 heads-up), 200 us wall
  budget, 450 us hard stop; soft deadline 350 us before sampling starts -> Hero's cheap path.
- `hyperion/hybrid/bot.py`: `HybridCore` routes; `Hybrid` is SafeBot around it with Hero's deadline and panic
  settings. Core: plain hold'em, any rank order (remapped first), any payouts, antes (in `pot`), pot limit
  (its all-in is the cap), 3-card hands before the discard (its best two). Hero: short deck, lowball, wild
  cards, category order, hi/lo, two boards, Omaha, fixed limit, bounties, knockout points, exposed cards,
  preflop with a straddle, postflop with 3+ hole cards; discards, swaps and buying a card are Hero's
  `variant_decide`.
- Bestiary: `hybrid`; fields `realistic_h`, `top_h`, `top2_h`, `holdout_h` (hybrid in Hero's seat, else identical,
  so seating and deals match seed for seed).
- `tests/test_hybrid.py`: 36 tests (legality over 300 deep hands, all 23 catalogue entries with no error and the
  expected routing, the rank-remap round trip on a recorded table, payouts in the curve with rival 2's globals
  untouched, the fallbacks, timing). Full suite 570 passed, 1 skipped.
- Smoke, measure mode, top2_h, 3 seeds x 8: hybrid p50 25 us, p99 226 us.

## 01:35-01:42: the sampler budget (100 seeds x 8, strict, seed 7, pinned worktree d3616b1; 2 runs at a time, load 4-8)

Hybrid's own paired deltas between sampler settings (same seeds). "built" is rival 2's own sampler: 160 samples,
260 us budget, 520 us hard stop.

| field | mc 32 | mc 64 | built | 64 - 32 | built - 32 | built - 64 |
|---|---|---|---|---|---|---|
| top2_h | 4.954 ± 0.147 | 5.058 ± 0.148 | 4.941 ± 0.145 | +0.104 ± 0.167 | -0.013 ± 0.180 | -0.117 ± 0.164 |
| realistic_h | 5.513 ± 0.151 | 5.443 ± 0.154 | 5.452 ± 0.150 | -0.070 ± 0.159 | -0.061 ± 0.168 | +0.008 ± 0.158 |

No measurable difference. Timing in the same runs (top2_h, load 4-5): mc 32 p50 27 / p99 296 us, 0.264% over
1 ms (hero_tight in the same run 0.155%); mc 64 p99 314, 0.282% (hero_tight 0.168%); built p99 492 and its 0.5 ms
overruns pushed SafeBot into panic (Hero's cheap path) for 3,901 decisions. Earlier, on a quieter host (load 3-6,
40 seeds, hybrid and Hero in one field): mc 32 p99 240 us, 0.070% over 1 ms vs Hero 0.041%; mc 64 p99 293, 0.170%
vs Hero 0.072%. **v1 ships mc_max 32.** Where the time goes (measure mode, top2_h): postflop is 17% of decisions
and ~47% of the hybrid's time (mean ~226 us at mc 64); preflop p50 22-32 us, like Hero's ~20. Timeouts follow
mean time per decision, and the core's preflop alone costs about what Hero's whole decision does, so no sampler
budget brings the hybrid's timeout rate under Hero's at the same load: it runs ~1.7x Hero's.

## 01:45-01:55: v1 (133a837) vs Hero on realistic and the holdout (200 seeds x 8, strict, seed 7, pinned worktree)

Hero is the committed `hyperion/strategy` at 133a837 (last strategy commit c38259e). Two runs at a time, load 4-7.

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, leader | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| realistic | 5.491 ± 0.099 | 5.491 ± 0.106 | **+0.001 ± 0.129** | 2 of 8; rival1 5.721 | 20/79 us, 0.05% | 26/232 us, 0.09% |
| holdout (measured once) | 5.451 ± 0.099 | 5.430 ± 0.109 | **-0.021 ± 0.133** | 2 of 8; rival3 5.876 | 20/63 us, 0.02% | 26/222 us, 0.04% |

Gaps to the field's rival on the same seeds: realistic hybrid - rival1 -0.230 ± 0.167 (Hero - rival1 -0.183 ± 0.166);
holdout hybrid - rival3 -0.446 ± 0.169 (Hero - rival3 -0.555 ± 0.153); rival 3 itself scores 5.876 against the
hybrid's table and 6.005 against Hero's (paired -0.130 ± 0.121). Routes: realistic core 248,398, soft deadline 36,
panic 200 (one table); holdout core 245,773, soft deadline 19. 0 exceptions, 0 illegal, 0 swallowed errors.

## 01:55-02:00: top and top2 (same settings)

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, next/leader | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| top | 4.497 ± 0.105 | 4.988 ± 0.099 | **+0.491 ± 0.139** | 1 of 7; rival2 4.930 | 20/113 us, 0.09% (load 6-9) | 26/292 us, 0.22% |
| top2 | 4.490 ± 0.108 | 4.983 ± 0.107 | **+0.493 ± 0.148** | 1 of 7; rival2 4.916 | 21/102 us, 0.07% (load 6-9) | 26/220 us, 0.07% |

Same seeds, gaps to the rivals: top hybrid - rival1 +0.263 ± 0.129 (Hero -0.263 ± 0.152), hybrid - rival2 +0.058
± 0.151 (Hero -0.462 ± 0.160); top2 hybrid - rival2 +0.067 ± 0.135 (Hero -0.549 ± 0.151). In the rival-heavy rooms the
hybrid is rival 2 (level with it) and half a point over Hero; on realistic and the holdout it is level with Hero.
Routes: top core 252,387, soft deadline 89, panic 799 (two tables); top2 core 255,815, soft deadline 32, panic 64.

## 02:01: strong (same settings; hybrid in Hero's seat of hero,pushfold,pushfold,tag,hero_tight,hero_loose,nit,loose_aggro)

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| strong | 5.150 ± 0.101 | 5.165 ± 0.117 | **+0.015 ± 0.143** | 1 of 7; hero_loose 4.800 | 16/58 us, 0.01% (load 5-7) | 23/182 us, 0.01% (load 4-6) |

Routes: core 254,012, nothing else.

## 02:09-02:17: payout robustness, the brief's 10/7/5/4/3/2/1/0 (uniform 4.00; same seeds; load 1.4-5.7)

`--payouts` sets `Rules.payouts`: the engine scores by it, Hero reads it, the hybrid's curve is built from it.

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, leader |
|---|---|---|---|---|
| realistic, brief payouts | 5.376 ± 0.145 | 5.492 ± 0.154 | +0.116 ± 0.197 | 2 of 8; rival1 5.965 |
| top, brief payouts | 3.929 ± 0.128 | 4.553 ± 0.157 | **+0.624 ± 0.196** | 2 of 7; rival2 4.748 |

(Linear 8..1 is the default: realistic +0.001 ± 0.129, top +0.491 ± 0.139 above.) Under the brief's table Hero is
fourth on top, 0.85 behind rival 2 and level with tag; the hybrid is second, 0.20 behind rival 2.

## 02:17-02:26: payout robustness, top_heavy 50/25/12/6/3/2/1/1 (uniform 12.5; same seeds; load 4.4-6.1)

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, leader |
|---|---|---|---|---|
| realistic, top_heavy | 19.53 ± 0.92 | 20.09 ± 0.94 | +0.57 ± 1.23 | 2 of 8; rival1 23.18 |
| top, top_heavy | 12.75 ± 0.78 | 15.36 ± 0.77 | **+2.62 ± 1.06** | 3 of 7; rival1 15.96, rival2 15.92 |

On top, Hero is 3.4-3.7 behind both rivals under top_heavy; the hybrid is level with them (-0.6). Routes: realistic
core 241,388, soft deadline 54, panic 49; top core 239,508, soft deadline 37, panic 95.

## 02:26-02:38: variant readiness, all 23 entries (tools/variant_matrix.py style: `--field realistic`, 200 tables per
entry, seed 7, strict, no rotation; the hybrid in Hero's seat of the same tables, so per-table deltas are paired;
one worker each, load 5.0-5.7)

Verdicts as variant_matrix.py (READY = top 2 with VPIP >= 10%, PLAYS = rank 3-4). "Over 1 ms" and p99 include
variant_decide calls.

| variant | axis | Hero pts, rank, verdict | hybrid pts, rank, verdict | hybrid - Hero (paired) | hybrid routes | hybrid over 1 ms (Hero) | hybrid p99 us (Hero) |
|---|---|---|---|---|---|---|---|
| permuted_ranks | ranking | 6.03 ± 0.29, 1, READY | 6.03 ± 0.29, 1, READY | -0.00 ± 0.37 | core 99% | 0.40% (0.18%) | 329 (142) |
| short_deck | ranking | 5.80 ± 0.26, 1, READY | 5.87 ± 0.26, 1, READY | +0.07 ± 0.16 | core 0%; table:deck 100% | 0.04% (0.05%) | 97 (101) |
| lowball | ranking | 7.78 ± 0.14, 1, READY | 7.77 ± 0.14, 1, READY | -0.01 ± 0.12 | core 0%; table:showdown 100% | 0.05% (0.05%) | 102 (93) |
| wild_deuces | ranking | 7.12 ± 0.27, 1, READY | 6.98 ± 0.29, 1, READY | -0.14 ± 0.17 | core 0%; table:showdown 100% | 0.06% (0.06%) | 126 (116) |
| flush_over_full_house | ranking | 5.42 ± 0.29, 2, READY | 5.67 ± 0.29, 1, READY | **+0.26 ± 0.22** | core 0%; table:showdown 100% | 0.07% (0.07%) | 93 (91) |
| toss_or_holdem | information | 6.10 ± 0.24, 1, READY | 5.65 ± 0.29, 2, READY | **-0.45 ± 0.33** | core 100% | 0.24% (0.07%) | 268 (114) |
| three_card_blind_discard | information | 6.04 ± 0.22, 1, READY | 5.69 ± 0.26, 2, READY | **-0.35 ± 0.32** | core 100% | 0.26% (0.12%) | 298 (117) |
| three_card_keep | information | 6.06 ± 0.25, 1, READY | 5.43 ± 0.27, 2, READY | **-0.63 ± 0.32** | core 63%; extra_hole 37% | 0.24% (0.24%) | 175 (186) |
| omaha_four | information | 6.74 ± 0.20, 1, READY | 6.73 ± 0.20, 1, READY | -0.01 ± 0.05 | core 0%; table:must_use 100% | 0.25% (0.23%) | 173 (148) |
| swap_holdem | information | 5.32 ± 0.29, 3, PLAYS | 5.49 ± 0.29, 2, READY | +0.17 ± 0.38 | core 100% | 0.32% (0.13%) | 289 (117) |
| swap_one_turn | information | 5.76 ± 0.29, 1, READY | 5.66 ± 0.30, 2, READY | -0.10 ± 0.36 | core 100% | 0.25% (0.11%) | 272 (106) |
| exposed_card | information | 5.49 ± 0.30, 2, READY | 5.58 ± 0.30, 2, READY | +0.09 ± 0.20 | core 0%; table:exposed 100% | 0.05% (0.05%) | 108 (98) |
| two_boards | information | 5.28 ± 0.27, 2, READY | 5.26 ± 0.26, 2, READY | -0.02 ± 0.23 | core 0%; table:showdown 100% | 0.02% (0.02%) | 96 (87) |
| bonus_card | information | 5.59 ± 0.29, 1, READY | 5.66 ± 0.30, 1, READY | +0.07 ± 0.30 | core 77%; extra_hole 23% | 0.02% (0.01%) | 97 (75) |
| bounty | payoff | 5.48 ± 0.30, 2, READY | 5.37 ± 0.31, 2, READY | -0.12 ± 0.24 | core 0%; table:bounty 100% | 0.02% (0.01%) | 84 (85) |
| knockout_bounty | payoff | 6.91 ± 0.47, 1, READY | 6.88 ± 0.48, 2, READY | -0.03 ± 0.35 | core 0%; table:bounty 100% | 0.02% (0.03%) | 84 (86) |
| top_heavy | payoff | 20.91 ± 2.63, 2, READY | 18.38 ± 2.65, 2, READY | -2.53 ± 3.16 | core 100% | 0.07% (0.01%) | 246 (92) |
| hi_lo | payoff | 5.49 ± 0.30, 2, READY | 5.65 ± 0.29, 2, READY | +0.16 ± 0.22 | core 0%; table:showdown 100% | 0.05% (0.05%) | 109 (108) |
| pot_limit | betting | 5.61 ± 0.29, 2, READY | 5.58 ± 0.30, 2, READY | -0.02 ± 0.33 | core 100% | 0.06% (0.04%) | 236 (95) |
| antes_from_level_3 | betting | 5.69 ± 0.30, 1, READY | 5.35 ± 0.32, 3, PLAYS | -0.33 ± 0.35 | core 100% | 0.07% (0.03%) | 239 (93) |
| fixed_raise | betting | 5.61 ± 0.28, 2, READY | 5.72 ± 0.28, 2, READY | +0.10 ± 0.19 | core 0%; table:fixed_limit 100% | 0.01% (0.03%) | 98 (98) |
| fast_schedule | betting | 5.39 ± 0.30, 2, READY | 5.20 ± 0.29, 3, PLAYS | -0.19 ± 0.37 | core 100% | 0.17% (0.15%) | 284 (187) |
| straddle | betting | 5.54 ± 0.32, 2, READY | 5.71 ± 0.32, 1, READY | +0.17 ± 0.31 | core 32%; straddle 67%, panic 1% | 0.55% (0.18%) | 475 (183) |


**Hybrid READY 21, PLAYS 2 (antes_from_level_3, fast_schedule), first on 8; Hero READY 22, PLAYS 1 (swap_holdem),
first on 12.** 0 exceptions, 0 illegal, 0 swallowed errors, 0 core errors for either. The 11 Hero-routed entries
play Hero's code with Hero's seed, so their deltas are a null check: strict-mode timeouts are host events, and one
different decision changes the rest of a table. They spread -0.14 to +0.26 (flush_over_full_house's +0.26 ± 0.22 is
the one outside its interval). Of the core-routed entries the three 3-card games are the real cost: toss_or_holdem
-0.45 ± 0.33, three_card_blind_discard -0.35 ± 0.32, three_card_keep -0.63 ± 0.32. There the core plays preflop from
its best two cards and Hero plays from 3-card variant tables. Antes -0.33 ± 0.35 (rival 2's push/fold solve has no
antes; the antes reach it only as dead money). Everything else is level within noise. top_heavy here is 200
unrotated tables (± 3); the 1,600-table payout runs above are the better read.

## 02:39: v1.1, three hole cards go to Hero (`hero_on_three_cards`, default on)

The brief's mechanism (the core plays a 3-card hand preflop from its best two, Hero discards) measured 0.35-0.63
worse than Hero on the three 3-card games, where Hero plays from 3-card variant tables. Mixing within a hand (Hero
preflop, the core after the discard) would leave the core parsing preflop history as if it were the flop, so the
whole table goes to Hero instead. Only tables with `Rules.hole_cards == 3` change: every 2-card result above stands
as measured. The best-two path stays available (`hero_on_three_cards` false) and tested.

## 02:39-02:50: the mirrors (200 seeds x 8, strict, seed 7, v1 at 133a837; 2 at a time, load 4.4-6.1; uniform 4.50)

| room | the lone bot | the seven | paired, the same room with Hero in the hybrid's place |
|---|---|---|---|
| hybrid + 7 rival2 | hybrid **4.551 ± 0.099** | rival2 4.493 | hero + 7 rival2: Hero 3.537 ± 0.088; hybrid - Hero **+1.014 ± 0.129** |
| rival2 + 7 hybrids | rival2 **4.430 ± 0.097** | hybrid 4.510 | rival2 + 7 Heroes: rival2 5.157 ± 0.106; rival2's change **-0.727 ± 0.148** |

The hybrid holds uniform in both mirrors (+0.05 alone among rival 2s, rival 2 -0.07 alone among hybrids); Hero is
-0.96 alone among rival 2s and gives a lone rival 2 +0.66. Timeouts: rival2 among 7 hybrids 2,249 (its usual rate),
the 7 hybrids 2,560 in 1.9 million decisions (0.13%); SafeBot panic in a few tables (746 decisions).

## 02:50-02:53: timing next to Hero in the same runs, v1.1 3-card rows

Hybrid and Hero seated in one field (hybrid, hero, rival1, rival2, pushfold, tag, hero_tight, loose_aggro), strict:

| run | load | hybrid p50 / p99 / mean, over 1 ms | Hero p50 / p99 / mean, over 1 ms | rival2 (as built) |
|---|---|---|---|---|
| 80 seeds x 8, quiet | 1.2-1.5 | 24 / 179 / 38.7 us, 1 in 100,039 | 19 / 54 / 21.5 us, 1 in 110,240 | 119 / 305 us, 5 in 99,866 |
| 200 seeds x 8 | 5.0 -> 2.0 | 24 / 192 / 39.8 us, 22 in 256,757 (0.009%) | 19 / 61 / 21.8 us, 9 in 266,690 (0.003%) | 120 / 350 us, 0.035% |

In the field runs above, against hero_tight (a Hero clone, same code path) in the same run: top_h 0.224% vs 0.127%
(load 6.5-8.9), top2_h 0.065% vs 0.044%, strong 0.009% vs 0.003%, top_h top_heavy 0.127% vs 0.063%, top_h brief
0.020% vs 0.009%: the hybrid times out 1.5-3x as often as Hero, and 4-7x less often than rival 2 as built (0.33-0.90%
in the same runs). Its p99 was 182-292 us in every run, under 300 us; Hero's 53-152 us.

hand_end / new_table (untimed by our engine; 30 tables in measure mode, load ~1.5): hybrid hand_end p50 68 / p99 226 us
(Hero 41 / 137) on linear payouts, 240 / 599 us (Hero 161 / 527) on top_heavy; new_table p50 101 us (Hero 46).

v1.1 on the 3-card games (200 tables, same seeds as Hero's matrix row, load 1.4-1.7): toss_or_holdem -0.01 ± 0.15,
three_card_blind_discard +0.02 ± 0.17, three_card_keep +0.06 ± 0.18, first on all three. v1.1 matrix: READY 21,
PLAYS 2 (antes_from_level_3, fast_schedule), first on 11.

## 02:54: Hero moved under the measurements

The aggression pass shipped f349380 (mid-depth re-shoves to 25 bb, the c-bet margin) after this log's pin
(133a837). Everything above is against the Hero before it. Re-measuring Hero at 7e51197 (the coordinator's frozen
Hero) on the same seeds, and the hybrid wherever Hero clones sit at its table (top, top2, strong: hero_tight,
hero_loose). On realistic, the holdout and the rival 2 mirrors the hybrid's opponents did not change and the core
took every decision but 0.1% (Hero's cheap path), so those hybrid runs stand and are paired with the new Hero.

## 02:54-03:05: against the frozen Hero at 7e51197 (200 seeds x 8, strict, seed 7; pinned worktree at 7e51197, which
also carries hybrid v1.1; load 0.9-3.0)

| field | Hero 7e51197 | hybrid | hybrid - Hero (paired) | hybrid's rank, next/leader | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| realistic | 5.598 ± 0.097 | 5.491 ± 0.106 (133a837 run, load 4-7) | -0.107 ± 0.132 | 2 of 8; rival1 5.721 | 19/55 us, 0.00% | 26/232 us, 0.09% |
| holdout | 5.552 ± 0.097 | 5.430 ± 0.109 (133a837 run, load 6-7; measured once) | -0.123 ± 0.128 | 2 of 8; rival3 5.876 | 19/55 us, 0.00% | 26/222 us, 0.04% |
| top | 4.668 ± 0.104 | 4.940 ± 0.108 | **+0.272 ± 0.135** | 2 of 7; rival2 5.000 | 19/56 us, 0.00% | 24/183 us, 0.00% |
| top2 | 4.511 ± 0.103 | 4.961 ± 0.103 | **+0.450 ± 0.139** | 1 of 7; rival2 4.930 | 20/59 us, 0.00% | 24/175 us, 0.00% |
| strong | 5.133 ± 0.105 | 5.123 ± 0.109 | -0.009 ± 0.139 | 1 of 7; hero_tight 4.859 | 16/57 us, 0.01% | 23/185 us, 0.01% |

Hero 7e51197 vs Hero 133a837, same seeds: realistic +0.108 ± 0.105, holdout +0.102 ± 0.084 (the aggression pass's own
400-seed numbers: +0.051, +0.109). The hybrid between its two runs (opponents hero_tight / hero_loose changed): top
-0.048 ± 0.098, top2 -0.022 ± 0.111. Gaps on the same seeds: top Hero - rival1 +0.012 ± 0.143, hybrid - rival1 +0.284
± 0.143; top2 Hero - rival2 -0.424 ± 0.139, hybrid - rival2 +0.031 ± 0.127.

## 03:05-03:16: payout robustness against the frozen Hero (7e51197; load 2.6-10.0, a spike from another session)

| field, payouts | Hero 7e51197 | hybrid | hybrid - Hero (paired) | leader |
|---|---|---|---|---|
| realistic, brief 10/7/.../0 | 5.628 ± 0.153 | 5.492 ± 0.154 (133a837 run) | -0.136 ± 0.190 | rival1 5.965 |
| realistic, top_heavy | 20.83 ± 0.89 | 20.09 ± 0.94 (133a837 run) | -0.74 ± 1.22 | rival1 23.18 |
| top, brief | 4.263 ± 0.139 | 4.541 ± 0.149 | +0.278 ± 0.188 | hybrid first; rival2 4.533 |
| top, top_heavy | 13.94 ± 0.83 | 14.74 ± 0.83 | +0.80 ± 1.03 | rival2 16.05 |

Against Hero 133a837 the same rows were +0.116, +0.57, +0.624, +2.62: the aggression pass closed most of Hero's
top_heavy weakness (Hero on realistic top_heavy 19.53 -> 20.83; the pass measured +2.39 ± 0.68 over 400 seeds).

## 03:16-03:21: the mirrors against the frozen Hero (7e51197; load 4.8-5.9)

hero + 7 rival2: Hero 3.680 ± 0.095 (133a837: 3.537); hybrid - Hero **+0.871 ± 0.136**. rival2 + 7 Heroes: rival2
5.131 ± 0.104 (133a837: 5.157); rival2 among 7 hybrids 4.430, change **-0.701 ± 0.149**. (Hybrid runs from 133a837:
the opponents are rival 2 copies, unchanged.)

## 03:21-03:41: readiness against the frozen Hero (v1.1 and Hero at 7e51197, same tables; load 5 -> 35)

Hybrid v1.1 READY 23, first on 13; Hero 7e51197 READY 21, PLAYS 2 (swap_holdem, two_boards), first on 15. 0 errors
for either. Another session took the box from load 5 to 35 during the run; from swap_holdem on, the hybrid's
timeouts reached 1.3-2.0% and its SafeBot panic share 4-18%. Only straddle (load 35, panic 18%) is outside its
interval: -0.37 ± 0.34. Full table in docs/decisions.md, "Hybrid candidate". A load-matched hybrid re-run on
realistic was started and killed at load 34.

## 03:45: written up

docs/decisions.md "Hybrid candidate" (every number above, the verdict, the recommendation); one line in HANDOFF.md.

## 04:20: rival 2's import-time tables vary with host load

At load ~30, `import hyperion.sim.rivals.rival2` computed 1,088 and 1,152 of its 1,500 import-time Monte Carlo boards
(the 2.4 s budget binds) and took 5.9-6.4 s; quiet, 1,500 boards in ~1.15 s. The core's equity tables, and so its play,
differ between processes on a loaded host. The round-trip and legality tests now switch off SafeBot panic (it reads
the wall clock) and play deep stacks, so a loaded host cannot make them flake.

# Hybrid 3: rival 3's decision core behind the same shell

## 04:42: hybrid3 built (commit below)

- `hyperion/hybrid/core3.py`: `Rival3Core` subclasses rival 3's `Bot` (rival3.py untouched). Its one ICM method,
  `_allin`, is re-implemented with `icm_points` and `Rules.payouts` (rival 3's O(n) closed form whenever the payouts
  are linear from third place down, which covers 8..1 and the brief's table; Hero's exact `icm_me` otherwise), and its
  bust value comes from the same table. hand_end gets the hand's history in the kit's shape. A soft deadline before
  its preflop/postflop logic gives Hero's cheap path. Replay errors are counted before rival 3 swallows them.
- `hyperion/hybrid/bot.py`: one router for both cores (`HybridConfig.core` "rival2" | "rival3"), through one adapter
  (setup, start_hand, decide, legalize, end). The rival 2 hybrid's play is bit-identical across the refactor (563
  decisions over 4 deterministic tables, same sha). New route `hero:core_none`: rival 3 returns nothing when the move
  it wants is not legal (a shove with only call or fold offered; as built it then folds); Hero decides those.
- Bestiary: `hybrid3`; fields `realistic_h3`, `top_h3`, `top2_h3`.
- `tests/test_hybrid3.py`: 33 tests (legality over 300 deep hands with 0 replay errors, all 23 entries with the
  expected routing, the rank-remap round trip, `icm_points` against `_icm1` and `icm_me`, payouts in `_allin` with
  rival 3's globals untouched, the hand_end history, declines, the soft deadline, timing). Full suite 656 passed.
- Smoke (strict, 10 seeds x 8, load ~3): top2_h3 p50 32 / p99 70 us, realistic_h3 p50 28 / p99 65 us.

## 05:20: the exploit layer wired in (off by default); `hybrid_x`, `hybrid3_x`

`HybridConfig.exploit` (None = off; "hero" = the params Hero's Config ships at that commit; or a dict of
ExploitParams fields) puts hyperion/strategy/exploit.py in front of every decision, core or Hero. When it is on, the
fallback Hero's own copy is switched off, so one layer sees every decision and nothing is counted twice. The layer
only replaces passive actions (a check postflop; a fold or check preflop), so it cannot double an action the core
already took; its fires are counted as `exploit:<spot>`. Bestiary: `hybrid_x`, `hybrid3_x` (the layer with Hero's
shipped params: the same as `hybrid` / `hybrid3` while Hero ships every spot off). The rival 2 hybrid stays
bit-identical (563 decisions, same sha as v1.1 at 7e51197). Full suite 661 passed.

## 04:43-05:14: round 2, all three candidates on the same seeds (200 x 8, seed 7, model mode, SafeBot panic off)

Protocol change, and why: the host swung from load 2 to 35 under other sessions. In strict mode that moves the
Monte Carlo and timeout bots' timeouts (so the field itself) and SafeBot's panic, and it did so differently for runs
made at different times. Mode "model" (the engine's deterministic timeout model, 72440a6) folds the bots that model
a cost over budget and never folds a bot on the wall clock; panic is off for every Hero, Hero clone and hybrid
(`panic_after` 10^9), as in the exploit pass's screens. Timing is measured separately, in strict mode, with all three
candidates seated at one table so they share the load. Worktree: 4973806 with `hyperion/strategy` at 7e51197.
Hero runs and the hybrid runs of a field ran side by side. Ranks are among the field's bot names.

| field | Hero 7e51197 (rank) | hybrid3 (rank) | hybrid3 - Hero | hybrid (rank) | hybrid - Hero |
|---|---|---|---|---|---|
| realistic | 5.528 ± 0.092 (2) | 5.984 ± 0.102 (1) | **+0.456 ± 0.126** | 5.526 ± 0.105 (2) | -0.002 ± 0.118 |
| top | 4.648 ± 0.102 (4) | 4.892 ± 0.100 (2) | **+0.244 ± 0.138** | 5.064 ± 0.111 (1) | **+0.415 ± 0.132** |
| top2 | 4.474 ± 0.102 (4) | 4.871 ± 0.115 (2) | **+0.397 ± 0.135** | 5.055 ± 0.105 (1) | **+0.581 ± 0.151** |
| strong | 5.132 ± 0.104 (1) | 5.458 ± 0.117 (1) | **+0.326 ± 0.143** | 5.129 ± 0.107 (1) | -0.003 ± 0.136 |
| realistic, brief 10/7/5/4/3/2/1/0 | 5.575 ± 0.144 (2) | 6.202 ± 0.170 (1) | **+0.628 ± 0.197** | 5.503 ± 0.163 (2) | -0.072 ± 0.188 |
| top, brief 10/7/5/4/3/2/1/0 | 4.281 ± 0.148 (3) | 4.448 ± 0.159 (2) | +0.167 ± 0.204 | 4.563 ± 0.147 (2) | **+0.282 ± 0.191** |
| realistic, top_heavy | 20.891 ± 0.879 (2) | 24.725 ± 1.015 (1) | **+3.834 ± 1.243** | 20.336 ± 0.925 (2) | -0.555 ± 1.116 |
| top, top_heavy | 13.600 ± 0.815 (3) | 14.724 ± 0.830 (3) | **+1.123 ± 1.097** | 14.753 ± 0.768 (3) | **+1.153 ± 1.055** |

Mirrors (same protocol; uniform 4.50):

| room | Hero 7e51197 | hybrid3 | hybrid | hybrid3 - Hero | hybrid - Hero |
|---|---|---|---|---|---|
| candidate + 7 rival3 (candidate's points) | 4.312 ± 0.111 | 4.467 ± 0.070 | 4.996 ± 0.112 | +0.155 ± 0.136 | +0.684 ± 0.158 |
| rival3 + 7 candidates (rival3's points, lower is better) | 4.833 ± 0.101 | 4.531 ± 0.077 | 4.053 ± 0.111 | -0.301 ± 0.128 | -0.780 ± 0.148 |
| candidate + 7 rival2 (candidate's points) | 3.714 ± 0.099 | 4.084 ± 0.112 | 4.585 ± 0.082 | +0.370 ± 0.138 | +0.871 ± 0.125 |
| rival2 + 7 candidates (rival2's points, lower is better) | 5.108 ± 0.095 | 4.985 ± 0.111 | 4.437 ± 0.089 | -0.124 ± 0.144 | -0.671 ± 0.127 |

Readings. hybrid3 beats Hero on every room above, by more than noise on realistic (+0.46), top2 (+0.40), strong
(+0.33) and the payout variants of realistic; it is first on realistic, strong and both realistic payout tables, and
second to the rival 2 hybrid on top and top2. The rival 2 hybrid is level with Hero on realistic and strong and ahead
in the rival rooms (top +0.42, top2 +0.58), as in round 1. Against rival 3 copies the rival 2 hybrid is the strongest
bot here (5.00 alone among seven rival 3s; rival 3 alone among seven of it, 4.05).

## 05:39-05:49: raw rival 3 in Hero's seat, the same deals as hybrid3 (round-2 protocol)

`rival3` is the bestiary bot with no shell: rival 3 as built behind the kit adapter, which already passes it the
hand's history at hand_end, pricing every all-in with the brief's 10/7/5/4/3/2/1/0, seeing displayed cards, and
folding where it declines. hybrid3 differs by the payouts in its all-in prices, the rank remap, Hero on the
declined decisions and on the tables it cannot represent, the soft deadline and SafeBot.

| field | raw rival3 in Hero's seat | hybrid3 | hybrid3 - rival3 (paired) | Hero 7e51197 | rival3 - Hero |
|---|---|---|---|---|---|
| realistic | 5.897 ± 0.109 | 5.984 ± 0.102 | **+0.087 ± 0.058** | 5.528 ± 0.092 | **+0.369 ± 0.128** |
| top | 4.824 ± 0.104 | 4.892 ± 0.100 | +0.069 ± 0.098 | 4.648 ± 0.102 | **+0.175 ± 0.145** |
| top2 | 4.728 ± 0.110 | 4.871 ± 0.115 | **+0.143 ± 0.114** | 4.474 ± 0.102 | **+0.254 ± 0.132** |
| strong | 5.324 ± 0.125 | 5.458 ± 0.117 | **+0.134 ± 0.077** | 5.132 ± 0.104 | **+0.192 ± 0.146** |
| realistic, brief | 6.207 ± 0.171 | 6.202 ± 0.170 | -0.005 ± 0.011 | 5.575 ± 0.144 | **+0.633 ± 0.198** |
| top, brief | 4.493 ± 0.152 | 4.448 ± 0.159 | -0.045 ± 0.148 | 4.281 ± 0.148 | **+0.212 ± 0.200** |
| realistic, top_heavy | 25.035 ± 1.048 | 24.725 ± 1.015 | -0.310 ± 0.699 | 20.891 ± 0.879 | **+4.144 ± 1.266** |
| top, top_heavy | 14.710 ± 0.891 | 14.724 ± 0.830 | +0.014 ± 0.865 | 13.600 ± 0.815 | +1.109 ± 1.134 |

What the shell adds on plain hold'em: +0.07 to +0.14 on the default 8..1 table (outside noise on realistic, top2,
strong), nothing on the brief's table (-0.005 ± 0.011: there rival 3's own ICM is already exact and the bots are
nearly the same), nothing measurable on top_heavy. So "rival 3 by itself" and "the rival 3 hybrid" make nearly the
same decisions on plain hold'em; the gain is the payout correction. The shell's other value is everywhere rival 3
cannot go: rank remaps, the 14 tables Hero plays, timing guards (variant matrix and timing below).

## 05:49-06:07: round 3, the exploit layer shipped (1957983): Hero HEAD, hybrid3_x, hybrid_x (worktree at 0d660dc;
model mode, panic off; load 13-50 from other sessions)

`hybrid3_x` / `hybrid_x` carry the layer with Hero's shipped params (bet when checked to by folders, the dead-seat
steal, the steal by fold reads). Paired against Hero HEAD on the same seeds; on realistic, which seats no Hero clone,
also against round 2's runs (same deals, same opponents).

| field | Hero HEAD (rank) | hybrid3_x (rank) | hybrid3_x - Hero HEAD | hybrid_x (rank) | hybrid_x - Hero HEAD | Hero HEAD - Hero 7e51197 | hybrid3_x - hybrid3 | hybrid_x - hybrid |
|---|---|---|---|---|---|---|---|---|
| realistic | 5.967 (1) | 6.141 (1) | **+0.174 ± 0.128** | 5.790 (1) | **-0.177 ± 0.122** | **+0.439 ± 0.073** | **+0.157 ± 0.078** | **+0.265 ± 0.086** |
| top | 4.765 (3) | 4.949 (2) | **+0.183 ± 0.135** | 5.124 (1) | **+0.358 ± 0.143** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |
| top2 | 4.653 (3) | 4.870 (2) | **+0.217 ± 0.136** | 5.160 (1) | **+0.507 ± 0.167** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |
| strong | 5.299 (2) | 5.363 (1) | +0.064 ± 0.145 | 5.560 (1) | **+0.262 ± 0.142** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |

The layer's fires per table (counted at the hybrid): realistic, hybrid3_x bet_checked 3.1, steal_fold 1.6, steal 0.1;
hybrid_x 3.1, 6.7, 0.7. Top: 2.4 / 1.1 / 0.0 against 2.5 / 4.8 / 0.2. Strong: 2.6 / 1.8 / 0.1 against 2.8 / 8.0 / 0.8.
This is where rival 3's own dead-seat logic overlaps the layer. Rival 3 already steals against folders, so the
layer's fold-read steal fires a quarter as often on top of it, and the layer adds +0.16 to hybrid3 on realistic,
against +0.27 to the rival 2 hybrid and +0.44 to Hero. Betting when checked to fires equally for every core. The
layer only replaces passive actions, so nothing is done twice; it is worth less on a core that already takes those pots.

## 06:07-06:25: the judge, measured once per candidate (rival 4, 0d660dc; 200 x 8, seed 7, model mode, panic off;
load 27-49)

Six candidates, each run once on each judge field, never tuned on: Hero 7e51197 (Hero HEAD with the three shipped
layer keys off, which the exploit pass gives as 7e51197's behaviour), Hero HEAD (the layer shipped), hybrid,
hybrid_x, hybrid3, hybrid3_x. The no-layer hybrids also run with their fallback Hero's layer off. `judge` = holdout
with rival 4 in rival 3's seat; `judge_top` = hero, rival1-4, pushfold, tag, loose_aggro. Same deals for all six.

`judge`:

| candidate | points (rank) | - Hero 7e51197 | - Hero HEAD | candidate - rival4 | rival4 | load |
|---|---|---|---|---|---|---|
| Hero 7e51197 (no layer) | 5.707 ± 0.104 (1) | - | **-0.327 ± 0.078** | +0.032 ± 0.145 | 5.675 | 37-41 |
| Hero HEAD (layer) | 6.034 ± 0.111 (1) | **+0.327 ± 0.078** | - | **+0.379 ± 0.153** | 5.655 | 41-35 |
| hybrid | 5.505 ± 0.108 (2) | **-0.202 ± 0.126** | **-0.529 ± 0.133** | **-0.362 ± 0.144** | 5.867 | 27-34 |
| hybrid_x | 5.657 ± 0.111 (2) | -0.050 ± 0.134 | **-0.377 ± 0.138** | -0.125 ± 0.152 | 5.781 | 27-41 |
| hybrid3 | 6.094 ± 0.101 (1) | **+0.387 ± 0.133** | +0.060 ± 0.137 | **+0.501 ± 0.145** | 5.593 | 41-27 |
| hybrid3_x | 6.210 ± 0.096 (1) | **+0.503 ± 0.124** | **+0.176 ± 0.133** | **+0.657 ± 0.138** | 5.553 | 35-27 |

`judge_top`:

| candidate | points (rank) | - Hero 7e51197 | - Hero HEAD | candidate - rival4 | rival4 | load |
|---|---|---|---|---|---|---|
| Hero 7e51197 (no layer) | 4.599 ± 0.111 (5) | - | **-0.215 ± 0.111** | -0.052 ± 0.156 | 4.651 | 34-49 |
| Hero HEAD (layer) | 4.814 ± 0.111 (2) | **+0.215 ± 0.111** | - | **+0.165 ± 0.156** | 4.649 | 41-46 |
| hybrid | 4.933 ± 0.103 (1) | **+0.334 ± 0.140** | +0.119 ± 0.142 | **+0.298 ± 0.149** | 4.635 | 47-47 |
| hybrid_x | 5.128 ± 0.103 (1) | **+0.529 ± 0.134** | **+0.314 ± 0.128** | **+0.581 ± 0.144** | 4.548 | 47-44 |
| hybrid3 | 4.869 ± 0.106 (3) | **+0.270 ± 0.138** | +0.055 ± 0.138 | **+0.289 ± 0.159** | 4.580 | 49-47 |
| hybrid3_x | 4.927 ± 0.108 (2) | **+0.328 ± 0.134** | +0.113 ± 0.131 | **+0.404 ± 0.150** | 4.523 | 46-47 |

Rival 2's sampler is on the wall clock, so at load 30-50 it, and the rival 2 hybrids, sampled less than on a quiet
host in these runs. Model mode removes every other load effect.
