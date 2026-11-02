# S11: closing exploiter 2's leaks (running log)

Brief (coordinator, 2026-11-02): a second counter-strategy agent played F with FIN (r3.v3_defend, half-pot dry c-bet)
as a black box for two hours and beat it short-handed (docs/drills/exploiter2/FINDINGS.md). Freeze it as a test
opponent, then fix F's leaks behind dials that are off by default. Every measurement is `tools/climb_accept.py` (or
scratch `quick.py`, which runs climb_accept's own cells and cache on a subset of cells) on the screen seeds
10000-10199 (200 seeds, every rotation), model mode at fixed speed. Base = FIN = `{"dials": {"r3.v3_defend": true,
"hero.postflop.cbet_size_dry": 0.5}}` on top of SHIP_DIALS; candidates = FIN plus their dials. Deltas are candidate
minus base in our seat's points; ± is the 95% interval of the per-seed paired difference. Workers 2, nice 10, host
load 10-14 (other measurements running). The coordinator runs the held-out confirmation and the judges.

Another worker (S9, climb/s9-strong-tables) works on strong tables and first-place conversion; everything here is
behind its own dials (`r3.v3_bvb_*`, `hero.postflop.probe_*` / `cbet_from` / `raiser_*` / `balance_sizes`,
`exploit.raise_guard`).

## 05:50 ET: exploiter 2 as a frozen test opponent (08ede84)

- `hyperion/sim/field/exploiter2/`: the six modules of docs/drills/exploiter2/ (exploit_bot.py, md5 d77551bc; base, trk,
  ev, pre_table, mat_table), each below an origin header and otherwise byte for byte (tests/test_sim_exploiter.py checks
  every md5 and copy).
- They import each other by bare name (`from base import Base`) and put their directory on sys.path, as the arena ran
  them. `hyperion.sim.field.load_flat` imports them as one package (`hyperion.sim.field.exploiter2.<part>`): each bare
  name points at the package's module only while the bundle imports, and afterwards sys.path and sys.modules are as
  they were (tested), so no other bot's `base` or `ev` ever meets these. Its `EXPP` experiment override (an environment
  variable read at import) is unset while it imports.
- `bestiary.Exploiter2Bot` (registry `exploiter2`): the PersonaBot kit adapter its arena used (payouts in the rules
  dict, the history at hand_end). No clock. Its one RNG (base.py) seeds itself from the seat number at new_table; the
  adapter reseeds it per table from the seat seed (`seed * 1_000_003 + 0xE2`), so tables draw their own streams and
  runs replay exactly (tested). Never in a night pool (tested).
- Fields: `exploit2` = hero, exploiter2, `night.1`..`night.6` (the arena's 8-max seating; payouts 10/7/5/4/3/2/1/0 in
  climb_accept), `exploit2_hu` = hero, exploiter2 (rules hu.json), `exploit2_3` = hero, exploiter2, `night.1`
  (three.json). climb_accept's EXPLOIT list has all six cells; the exploiter column prints whichever exploiter sits in
  the cell.

**Both exploiters against F and F with FIN, screen seeds (code 08ede84; 1,600 / 400 / 600 tables per cell):**

| field | F | its exploiter | FIN | its exploiter | the arena (exploiter 2's FINDINGS, FIN) |
|---|---|---|---|---|---|
| exploit (8-max, 10/7/5/4/3/2/1/0) | 4.999 | 5.369 | 5.711 | 4.684 | - |
| exploit_hu (10/7) | 8.005 | 8.995 | 9.107 | 7.893 | - |
| exploit_3 (10/7/5) | 7.027 | 8.330 | 8.359 | 6.985 | - |
| exploit2 (8-max, 10/7/5/4/3/2/1/0) | 5.747 | 5.175 | (below) | | F 5.65-5.76, exploiter 5.15-5.44 |
| exploit2_hu (10/7) | 7.555 | 9.445 | (below) | | F 7.48-7.52, exploiter 9.48-9.52 |
| exploit2_3 (10/7/5) | 7.118 | 8.598 | (below) | | F 7.21, exploiter 8.61-8.65 |

The exploiter-1 cells reproduce S2's numbers exactly. (The FIN half of this run was lost at 82 of 96 chunks: the
process died without output; FIN's exploiter-2 cells are re-measured at f74ec92 below, where FIN plays identically.)

**Where F with FIN loses heads-up** (scratch `spots.py`: F's decisions and its chips by spot, 40 seeds x 2 rotations
heads-up against exploiter 2, 4,900 hands, F -0.63 bb a hand):
- preflop, small blind: opens 2.2 bb with 73% of hands at 30+ bb (65% at 15-30); facing the 3x 3-bet it folds 87%
  (220 of 254: -2.2 bb each, -480 bb), calls 13% (+11 bb a call). Rival 3's core prices every 3-bet as an all-in
  against its tight read, and `r3.v3_defend` never plays: exploiter 2 3-bets 18%, under the defence's 0.2 floor with
  its prior of 0.08 worth 20 chances (t3 tends to 0.18 from below).
- preflop, big blind: against the 2 bb min-raise folds 47%, calls 37% (-1.1 to -1.35 bb a call: worse than folding,
  because of the postflop below), 3-bets 16% (+0.4 to +1.8 bb).
- postflop, small blind (F raised preflop): the big blind leads 0.4 pot into it on almost every flop; F folds 60% (539
  of 903: -1,194 bb), calls 39% (+1.3 bb a call), raises 1%.
- postflop, big blind (F called): F checks, the exploiter bets 0.6 pot (a c-bet); F folds 70% (393 of 565: -801 bb).
- the exploit layer's bet_checked (0.33 pot, the "0.30 / 0.35" sizes of the findings) fires into it as bluffable
  (it checks a lot) and is raised: F folds (-258, -179 bb on the flop, -418 on the turn).
- value bets win small pots: it folds to 0.7 and 0.8 pot.

## 06:05: the fixes, each a dial off by default (f74ec92; tests/test_s11_dials.py; test_ship / test_compose replay)

Measured from a detached worktree at the commit (`wt_s11_meas`), so edits never reach a running measurement.

- **Blind against blind, the 3-bet's cold start** (`r3.v3_bvb_prior`, `r3.v3_bvb_min_rate` 0.12, `r3.v3_bvb_f4_cap`;
  hyperion/hybrid/core3.py `_vs3bet`): when the big blind 3-bets our small-blind open (heads-up: the button's) with
  nobody else in, the 3-bet defence reads the 3-bettor from its own prior (e.g. 0.15 worth the usual 20 chances) and
  floor, so it plays from the first 3-bet: a wide open meets a wide 3-bet there. The other spots keep S2's guarded
  prior (0.08) and floor (0.2), which read nits correctly on night. `v3_bvb_f4_cap` caps the modelled fold to a 4-bet
  there (0.45: no bluff 4-bets until the 3-bettor is seen folding to one), the over-adjustment the findings name (a
  2.2x 4-bet that then faces a jam).
- **Floats and check-raises against wide bettors** (`hero.postflop.probe_from`, `cbet_from`, `probe_raise_tier`,
  `probe_trap`; hyperion/strategy/postflop.py, new Profiler reads). Two reads per seat in heads-up pots with me, flop
  and turn: a probe chance (it has nothing to call and the initiative is not its own: a lead into me, a stab after my
  check) and an aggressor's chance (a c-bet or a barrel); each counts the bets. Facing the street's first bet from a
  seat over the threshold for its kind of bet, my equity moves from the tier's proxy (TIER_EQUITY: against a betting
  range) toward WIDE_EQUITY (the tier against a whole range) by (rate - from) / (1 - from): a seat that bets every
  chance bets its whole range. probe_raise_tier lowers the tier that raises it (a check-raise, a raise of the lead);
  probe_trap checks a value hand first to act against such a seat, to call or raise its bet.
- **A raiser of my bets** (`hero.postflop.raiser_from`): facing a raise of my heads-up flop or turn bet from a seat that
  raises my bets above the threshold (prior 0.12 worth 5), call down wider (the call-down dial, 1 + 2 x excess).
- **The exploit layer's small bluff** (`exploit.raise_guard`): bet_checked (0.33 pot into a seat that checks and folds)
  skips a seat that raises my postflop bets above the threshold (its own read in the layer, prior 0.1 worth 4).
- **Bet sizes that name the hand** (`hero.postflop.balance_sizes`; `balance_from` for the read-based form): every bet
  with nothing to call that is not against a station or a dead table (big value, value, c-bet, semi-bluff) takes the
  c-bet size of the board's texture (FIN: 0.5 dry; 0.5 wet as shipped, 0.7 with `cbet_size_wet` 0.7), so a size no
  longer separates air from value. `balance_from`: the same only heads-up against a seat that raises my bets (the
  reader shows itself by raising the small sizes).
- Already there and re-tried here: `r3.bb_defend` (S2: the big blind defends by price), `hero.postflop.cbet_ftc_read`
  (c-bet bluffs scale with the caller's fold-to-c-bet).

## 06:20-06:55: dev batch 1, exploiter 2 heads-up and three-handed (quick.py, screen seeds, code f74ec92 + nothing)

FIN at f74ec92 replays FIN at 08ede84 chunk for chunk (identical samples on every exploit2_hu and exploit2_3 seed:
the new dials are off). **F with FIN against exploiter 2: heads-up 7.540 (exploiter 9.460), three-handed 7.135
(exploiter 8.573)**; 8-max below. Δ against FIN:

| candidate (FIN +) | exploit2_hu | exploit2_3 |
|---|---|---|
| `r3.v3_bvb_prior` 0.15 | +0.060 ± 0.125 | -0.053 ± 0.095 |
| ... + `r3.v3_bvb_f4_cap` 0.45 | **+0.135 ± 0.115** | +0.053 ± 0.064 |
| `probe_from` 0.6 | +0.030 ± 0.098 | -0.012 ± 0.055 |
| ... + `cbet_from` 0.75 | +0.052 ± 0.103 | -0.025 ± 0.058 |
| ... + `probe_raise_tier` 5 | +0.068 ± 0.105 | -0.028 ± 0.060 |
| `exploit.raise_guard` 0.3 | +0.007 ± 0.068 | -0.003 ± 0.047 |
| `balance_sizes` (one size, 0.5) | **+0.180 ± 0.105** | **+0.163 ± 0.101** |
| `balance_sizes` + `cbet_size_wet` 0.7 (0.5 dry / 0.7 wet) | **+0.052 ± 0.048** | +0.047 ± 0.077 |
| bvb + f4 cap + probe + cbet + raise tier 5 + guard | **+0.240 ± 0.134** | **+0.105 ± 0.092** |

Read (spot diagnostics, 40-60 seeds heads-up):
- The bvb defence plays from the first 3-bet now; its calling line wants equity about 0.40 against the top 18-20%,
  so it continues with the top ~25-30% of hands (40% of a 73% open). Without the 4-bet cap it 4-bets light and folds
  to the jam 54 times in 80 tables (-14.5 bb each): exploiter 2 jams every 3-bet hand over a 4-bet. The cap takes the
  bluff 4-bets out.
- The probe and c-bet reads barely moved the folds (SB against the lead 60% -> 50%, BB against the c-bet 70% -> 63%):
  each kind alone learns over a table (prior worth 6 chances, threshold 0.6-0.75: ten chances to a weight of one half)
  and heads-up tables are short; and the call margin (0.2 in SHIP_DIALS) still folds tier 0-1 hands even at their
  whole-range equity. Fixes (8a0ee53): `wide_from` on both kinds together (prior 0.5 worth 2: four bets in four
  chances already weigh one half), `probe_margin` (the margin moves to 0.03 by the weight), `probe_bluff` (air or a
  strong draw raises the bet). With wide_from 0.65 + margin + raise tier 5 (60 seeds): BB folds 41% to its c-bet, SB
  folds 41% to its lead, and raising the lead wins +5 to +9.5 bb a time.
- The guard at 0.3 needs two raises with its prior (1.4 / 5 = 0.28 after one): 0.2 stops after the first.
- One size, 0.5 pot everywhere, is the best single fix in both formats: exploiter 2 raises small bets with any hand
  and folds to big ones, so value at 0.5 gets raised and stacks in; at 0.7 wet the old tell survives on wet boards.

## 06:30-07:00: dev batch 2, both exploiters heads-up and three-handed (code 8a0ee53)

X0 = FIN + `r3.v3_bvb_prior` 0.15, `r3.v3_bvb_f4_cap` 0.45, `hero.postflop.wide_from` 0.65, `probe_margin` 0.03,
`probe_raise_tier` 5, `exploit.raise_guard` 0.2. Base FIN: exploit2_hu 7.540 (exploiter 9.460), exploit2_3 7.135
(8.573), exploit_hu 9.107 (7.893), exploit_3 8.359 (6.985).

| candidate | exploit2_hu | exploit2_3 | exploit_hu | exploit_3 |
|---|---|---|---|---|
| X0 | **+0.510 ± 0.145** | **+0.235 ± 0.127** | **-0.525 ± 0.153** | **-0.282 ± 0.163** |
| X1 = X0 + `balance_sizes` | **+0.660 ± 0.150** | **+0.448 ± 0.140** | **-0.405 ± 0.166** | **-0.225 ± 0.172** |
| X1 + `probe_bluff` 0.4 | **+0.720 ± 0.157** | **+0.373 ± 0.153** | **-0.608 ± 0.164** | -0.167 ± 0.179 |
| X1 + `r3.bb_defend` | **+0.690 ± 0.163** | **+0.498 ± 0.147** | **-0.608 ± 0.156** | **-0.309 ± 0.179** |
| X1 + `cbet_ftc_read` | **+0.645 ± 0.150** | **+0.480 ± 0.149** | **-0.405 ± 0.166** | **-0.230 ± 0.179** |
| X1 + `raiser_from` 0.3 | = X1 (never fires) | +0.472 ± 0.141 | = X1 | = X1 |
| X0 + `balance_from` 0.3 | = X0 (never fires) | +0.332 ± 0.133 | = X0 | -0.277 ± 0.163 |
| `wide_from` 0.65 + margin + raise tier 5 | **+0.240 ± 0.133** | +0.095 ± 0.108 | **-0.172 ± 0.118** | -0.063 ± 0.126 |

Against exploiter 2 the gains are real (X1 + bb_defend: 8.23 against 8.77 heads-up); against exploiter 1 every one
of them loses, and that is disqualifying. Two causes:
- **the wide read fires on exploiter 1** (and on an elite bot). Reads measured over 30 heads-up tables each and 12
  night tables (scratch `reads2.py`, F with FIN in the hero seat):

  | seat | probe (no initiative) | c-bet / barrel | both | raises my bets |
  |---|---|---|---|---|
  | exploiter 2 | **0.99** | 0.71 | 0.84 | 0.33 |
  | exploiter 1 | 0.61 | 0.88 | 0.86 | 0.21 |
  | elite2 | 0.72 | 0.84 | 0.76 | 0.10 |
  | elite1 | 0.54 | 0.60 | 0.56 | 0.03 |
  | rival3 | 0.34 | 0.63 | 0.43 | 0.02 |
  | rival1 | 0.12 | 0.52 | 0.18 | 0.02 |
  | night pool seats | 0.25 | 0.57 | 0.34 | 0.06 |

  Both kinds together do not separate exploiter 2 from exploiter 1 or elite2, and c-bet frequency is not what makes
  exploiter 2 different (exploiter 1 barrels more, with Monte Carlo equity behind its bets, so calling it wider
  loses). The probe read alone does: exploiter 2 leads and stabs every chance. Next: `probe_from` 0.75-0.8 with a
  prior worth 2 chances (learns in a few hands), no wide_from.
- **the blind-against-blind 4-bet cap** (`v3_bvb_f4_cap` 0.45) takes out the light 4-bets that S2's defence won with
  against exploiter 1 (it folds to 4-bets; exploiter 2 jams over them). With the cap at S2's 0.6 the model learns in
  one hand (one jam: (0 + 4 x 0.6) / 5 = 0.48, under the 0.58 a 2.2x 4-bet needs), so the cap is dropped.
- raise_guard: nothing against exploiter 2 alone (+0.007); exploiter 1 raises 21% of my bets, so at 0.2 it would
  block bet_checked there too. Dropped. raiser_from and balance_from never fire (no seat raises my bets above 0.3
  after the prior).

## 07:05-07:30: dev batch 3, the probe read alone (code 8a0ee53)

P = FIN + `probe_from` 0.75, `probe_n` 2 (prior 0.45 worth 2 chances), `probe_margin` 0.03, `probe_raise_tier` 5,
`balance_sizes`. No wide_from, no 4-bet cap, no guard.

| candidate | exploit2_hu | exploit2_3 | exploit_hu | exploit_3 |
|---|---|---|---|---|
| P | **+0.285 ± 0.122** | **+0.215 ± 0.118** | +0.007 ± 0.117 | +0.065 ± 0.106 |
| **Y1 = P + `r3.v3_bvb_prior` 0.15** | **+0.315 ± 0.142** | **+0.167 ± 0.129** | +0.120 ± 0.140 | +0.086 ± 0.136 |
| Y1 + `probe_bluff` 0.4 | **+0.307 ± 0.149** | **+0.243 ± 0.129** | +0.120 ± 0.140 | +0.100 ± 0.137 |
| Y1 + `r3.bb_defend` | **+0.292 ± 0.145** | **+0.153 ± 0.142** | +0.068 ± 0.142 | -0.024 ± 0.154 |
| Y1 with `probe_from` 0.8 | **+0.263** | **+0.175** | +0.113 | +0.086 |
| `r3.v3_bvb_prior` 0.15 alone | +0.060 ± 0.125 | -0.053 ± 0.095 | **+0.142 ± 0.131** | +0.047 ± 0.117 |
| `balance_sizes` alone | **+0.180 ± 0.105** | **+0.163 ± 0.101** | +0.007 ± 0.117 | +0.065 ± 0.106 |

The probe read never fires on exploiter 1 (P and balance_sizes alone give identical samples there), and the bvb prior
helps against it (+0.14 heads-up: its min 3-bets meet the defence from the first one). Y1 holds up against exploiter
1 in both formats (point estimates up) and gains against exploiter 2 in both. bb_defend costs again (as in S2).
Y1 goes to confirm, guards and elite (07:15); its night cell is already in: -0.039 ± 0.060, night_hard -0.016 ± 0.066.

X1's guards before it was stopped (it fails exploiter 1 anyway): night -0.061 ± 0.071, night_hard -0.014 ± 0.075,
realistic +0.013 ± 0.059, top +0.040 ± 0.095 (150 seeds). FIN's screen means: night 5.996, night_hard 5.463,
realistic 6.348, top 5.024, night 10/7/5/4/3/2/1/0 6.203, night 50/25/12/6/3/2/1/1 24.973, doubling blinds 5.856.

## 07:15-08:02: Y1 on confirm, guards and elite (screen seeds, code 8a0ee53, 46.7 min)

Y1 = `{"dials": {"r3.v3_defend": true, "hero.postflop.cbet_size_dry": 0.5, "r3.v3_bvb_prior": 0.15,
"hero.postflop.probe_from": 0.75, "hero.postflop.probe_n": 2, "hero.postflop.probe_margin": 0.03,
"hero.postflop.probe_raise_tier": 5, "hero.postflop.balance_sizes": true}}` against FIN.

| cell | FIN | Y1 | Y1 - FIN | |
|---|---|---|---|---|
| night (confirm) | 5.996 | 5.957 | -0.039 ± 0.060 | level |
| night_hard | 5.463 | 5.447 | -0.016 ± 0.066 | level |
| realistic | 6.348 | 6.352 | +0.004 ± 0.045 | level |
| top | 5.024 | 5.024 | -0.000 ± 0.067 | level |
| night @10/7/5/4/3/2/1/0 | 6.203 | 6.191 | -0.012 ± 0.110 | level |
| night @50/25/12/6/3/2/1/1 | 24.973 | 24.672 | -0.301 ± 0.621 | level |
| night, doubling blinds | 5.856 | 5.856 | -0.001 ± 0.048 | level |
| elite | 4.708 | 4.765 | +0.056 ± 0.069 | level |
| elite_night | 5.346 | 5.391 | +0.045 ± 0.059 | level |

No guard and no elite cell down; 0 timeouts, 0 errors. (climb_accept prints REJECT for its confirm line, night beyond
noise up, which an exploit fix does not claim: addendum 6 asks for up on an exploit field and down on nothing.)
Night's point estimate is the lowest (-0.04): balanced sizes give up some value against callers there; see the
read-based balance below.

## 07:30-08:10: dev batch 4, the Y1 family on all six exploit cells (code 8a0ee53)

FIN on the 8-max cells: exploit 5.711 (exploiter 1 4.684), **exploit2 5.642 (exploiter 2 5.246)**. So F with FIN
against exploiter 2 on the screen seeds: 8-max 5.642 / 5.246, heads-up 7.540 / 9.460, three-handed 7.135 / 8.573
(the arena: 5.65-5.76 / 5.15-5.44, 7.48-7.52 / 9.48-9.52, 7.21 / 8.61-8.65): the frozen copy reproduces its result.

| candidate | exploit | exploit_hu | exploit_3 | exploit2 | exploit2_hu | exploit2_3 |
|---|---|---|---|---|---|---|
| Y1 | +0.003 ± 0.124 | +0.120 ± 0.140 | +0.086 ± 0.136 | **+0.153 ± 0.091** | **+0.315 ± 0.142** | **+0.167 ± 0.129** |
| Y3 = Y1 + `probe_bluff` 0.4 | +0.001 ± 0.125 | +0.120 ± 0.140 | +0.100 ± 0.137 | **+0.192 ± 0.092** | **+0.307 ± 0.149** | **+0.243 ± 0.129** |
| Y1 with `balance_from` 0.2 for balance_sizes | -0.030 ± 0.056 | +0.120 ± 0.132 | +0.008 ± 0.118 | +0.036 ± 0.043 | **+0.188 ± 0.144** | +0.063 ± 0.123 |

Exploiter points with Y1 / Y3: exploiter 2 at 8-max 5.132 / 5.103, heads-up 9.145 / 9.152, three-handed 8.243 /
8.165; exploiter 1 4.780 / 4.786, 7.772 / 7.772, 6.905 / 6.900. The read-based balance (sizes balanced only against
a seat that raises my bets) keeps most of the heads-up gain but little elsewhere: the read takes a table to cross 0.2,
and exploiter 2's raises are partly of the layer's small bets. Y3's bluff raise fires only against probers (never on
exploiter 1: identical samples there). Y3 goes to the exploit, confirm, guards and elite stages; Y1's variants run
meanwhile (100 seeds a cell, from 08:05).

## 08:15-08:30: where Y3 still loses heads-up; the 4-bet that folds to the jam

Spot diagnostic, Y3 against exploiter 2 heads-up (60 seeds x 2, F 8.15 against 8.85 here):
- the biggest single leak left is preflop: our blind-against-blind 4-bet (2.2x the 3-bet) that folds to its jam,
  -14.5 bb each, about 1.4 a table (scratch `fourbet.py`: our 4-bets and its answers by their order at the table).
  Exploiter 2 folds to 30-50% of them (deeper than 60 bb it folds its non-premium 3-bets) and jams the rest, so the
  model's fold rate stays near 0.5 and the light 4-bets keep coming; against exploiter 1 it folds 95% of them, which is
  where S2's defence wins.
- tried, not kept: `r3.v3_follow` (answer the jam from the defence's own model instead of rival 3's re-raise read, so a
  4-bet priced as 4-bet / call is played that way). It folded more (68 against 60 first 4-bets folded in 120 tables):
  the model's jam range (the top w3 x (1 - fo4), ~8%) is tighter than the 18% exploiter 2 jams, so the model's own
  answer is fold. Removed.
- next, in the dev tree only: `r3.v3_bvb_cont` (blind against blind, the share of all hands a 3-bettor continues with
  against a 4-bet; S2's v3_cont is 0.04, QQ+ / AK). At 0.08 a seat 3-betting 18% folds 56% in the model, under the
  0.58 a 2.2x 4-bet needs, so no light 4-bets against it; a seat 3-betting 40% (exploiter 1's rate) still reads 80%,
  capped at 0.6, so the light 4-bets that win there stay.
- the BB against its c-bet: still folds 67% (444 of 657 flops), -913 bb in 120 tables, and its turn barrel -477 bb.
  Exploiter 2 c-bets less often than exploiter 1 or elite2 (0.71 against 0.88 / 0.84), so no frequency read separates
  it; exploiter 2 shows down air after barrelling and never bluffs the river, which a showdown read could learn, but not
  in this round.
- the layer's 0.33-pot bet_checked into it, raised, folded: -750 bb in 120 tables (exploiter 2 raises 0.30 / 0.35
  bets with any hand). The raise guard that stops it also fires on exploiter 1 (21% of my bets raised).

Full test suite at 8a0ee53 + the dev tree (08:13-08:28, host load 17-19): 1,013 passed, 19 failed, 9 skipped. The
failures are wall-clock budgets (test_sim_bestiary under-budget, test_nightof_latency, test_gate timeouts 0.33%,
test_slowbox) and the model-mode replay tests of the exploit and outside fields, whose hero seat diverged between two
runs under that load; all of those pass alone (test_sim_exploiter, test_slowbox: 24 passed). One real one:
test_apicard, docs/packet/CONTRACTS.md was stale since f74ec92 (the new dials): regenerated.

## 08:15-09:03: Y3 on every stage but variants (screen seeds, code 8a0ee53, base FIN, 47.7 min)

Y3 = Y1 + `hero.postflop.probe_bluff` 0.4.

| cell | FIN | Y3 | Y3 - FIN | | exploiter FIN / Y3 |
|---|---|---|---|---|---|
| exploit (8-max, 10/7/5/4/3/2/1/0) | 5.711 | 5.713 | +0.001 ± 0.125 | level | 4.684 / 4.786 |
| exploit_hu | 9.107 | 9.227 | +0.120 ± 0.140 | level | 7.893 / 7.772 |
| exploit_3 | 8.359 | 8.458 | +0.100 ± 0.137 | level | 6.985 / 6.900 |
| exploit2 (8-max, 10/7/5/4/3/2/1/0) | 5.642 | 5.834 | **+0.192 ± 0.092** | UP | 5.246 / 5.103 |
| exploit2_hu | 7.540 | 7.848 | **+0.307 ± 0.149** | UP | 9.460 / 9.152 |
| exploit2_3 | 7.135 | 7.378 | **+0.243 ± 0.129** | UP | 8.573 / 8.165 |
| night (confirm) | 5.996 | 5.953 | -0.043 ± 0.060 | level | |
| night_hard | 5.463 | 5.448 | -0.016 ± 0.066 | level | |
| realistic | 6.348 | 6.352 | +0.004 ± 0.045 | level | |
| top | 5.024 | 5.021 | -0.004 ± 0.066 | level | |
| night @10/7/5/4/3/2/1/0 | 6.203 | 6.190 | -0.012 ± 0.111 | level | |
| night @50/25/12/6/3/2/1/1 | 24.973 | 24.644 | -0.328 ± 0.626 | level | |
| night, doubling blinds | 5.856 | 5.852 | -0.004 ± 0.048 | level | |
| elite | 4.708 | 4.764 | +0.055 ± 0.069 | level | |
| elite_night | 5.346 | 5.392 | +0.046 ± 0.059 | level | |

## 09:03: the base changes (coordinator): FIN's dry c-bet does not ship

Batch 4 ships `r3.v3_defend` alone; `hero.postflop.cbet_size_dry` 0.5 does not (it lost on bonus_card, pooled H2 + H3
-0.030 ± 0.025, and it is exploiter 2's 78%-fold-to-check-raise leak). From here the base is `{"dials":
{"r3.v3_defend": true}}`, the candidates that plus their dials. Everything above was measured on FIN; the Y1 variants
run (base 82 of 100 chunks done, Y1 none) was stopped as moot.

Consequence for `balance_sizes`: it took the c-bet sizes for every bet, so on the new base it would bet dry value at
0.33. It now has its own size (9cb5e36): `hero.postflop.balance_size` 0.5, one size for every bet with nothing to call
(c-bets included), not against stations or dead tables. On the new base that includes a dry c-bet at 0.5, so it is a
dry-board sizing change and goes to the variants stage with bonus_card at 200 seeds.

Z = `{"dials": {"r3.v3_defend": true, "r3.v3_bvb_prior": 0.15, "hero.postflop.probe_from": 0.75,
"hero.postflop.probe_n": 2, "hero.postflop.probe_margin": 0.03, "hero.postflop.probe_raise_tier": 5,
"hero.postflop.probe_bluff": 0.4, "hero.postflop.balance_sizes": true}}` (Y3's dials on the new base; same sizes
as Y3 played). Runs from 09:08 (code 9cb5e36): exploit, confirm, guards, elite; and bonus_card at 200 seeds, then
every variant at 50.

## 09:08-09:15: Z on bonus_card (realistic, 200 seeds, code 9cb5e36), and latency

- bonus_card: base 5.967, Z 5.935, **-0.032 ± 0.060**, level on the screen set. The point estimate is the size of the
  held-out loss that sank the dry c-bet (pooled H2 + H3 -0.030 ± 0.025), and Z's one size bets dry c-bets at 0.5 too,
  so the coordinator's held-out check of bonus_card decides `balance_sizes`. Z0 (Z without balance_sizes) is the
  fallback below.
- latency (tools/latency.py --bot composite, 20,000 calls, two runs each, interleaved, host load 13-17):

  | dials | p50 us | p99 us | max us | over 1 ms |
  |---|---|---|---|---|
  | base `{"r3.v3_defend": true}` | 48.7 / 49.6 | 353.1 / 260.5 | 6,782 / 11,704 | 0.27% / 0.09% |
  | Z | 49.7 / 49.1 | 259.3 / 258.5 | 5,350 / 6,494 | 0.10% / 0.14% |

  Z's p99 is the base's on this host; both are over the 200 us line only because of the load (S2 measured the base at
  144-163 us at load 7-10). The new work per decision is a few counter updates in the profiler and, facing a bet, two
  smoothed reads.

## 09:35: Z plays exactly as Y3; its cells reuse Y3's chunks

With `balance_sizes` on, every bet that would read `cbet_size_dry` (the c-bet branch, the only reader in hyperion/)
takes `balance_size` instead, so FIN's dry c-bet changes nothing under it: Z (new base + Y3's dials) and Y3 (FIN +
the same dials) make the same decisions. Checked: Z's eight night chunks at 9cb5e36 equal Y3's at 8a0ee53 sample for
sample (all 200 seeds), and the code between them changes no default and no decision (balance_size 0.5 = the sizes Y3
bet; _v3_model is _vs3bet's own lines). So Z's exploit, guard and elite chunks are Y3's (copied into Z's cache key);
only the new base's chunks are new. The combined run was stopped at that point (it was recomputing Z's half); the
base runs in two pieces (exploit stage now, then confirm/guards/elite), and Z's variants (not run for Y3) run in full.

## 09:40-09:55: Z's exploit stage against the new base (code 9cb5e36; base computed, Z = Y3's chunks)

| cell | base `{"r3.v3_defend": true}` | Z | Z - base | | exploiter base / Z |
|---|---|---|---|---|---|
| exploit (8-max, 10/7/5/4/3/2/1/0) | 5.619 | 5.713 | +0.094 ± 0.139 | level | 4.727 / 4.786 |
| exploit_hu (10/7) | 9.115 | 9.227 | +0.113 ± 0.140 | level | 7.885 / 7.772 |
| exploit_3 (10/7/5) | 8.354 | 8.458 | +0.105 ± 0.143 | level | 6.993 / 6.900 |
| exploit2 (8-max, 10/7/5/4/3/2/1/0) | 5.754 | 5.834 | +0.079 ± 0.117 | level | 5.175 / 5.103 |
| exploit2_hu (10/7) | 7.540 | 7.848 | **+0.307 ± 0.149** | UP | 9.460 / 9.152 |
| exploit2_3 (10/7/5) | 7.142 | 7.378 | **+0.237 ± 0.143** | UP | 8.573 / 8.165 |

F as it will ship (v3_defend, no dry c-bet change) against exploiter 2 on the screen seeds: 8-max 5.754 / 5.175,
heads-up 7.540 / 9.460, three-handed 7.142 / 8.573: the same picture as FIN (FIN's dry c-bet moved only the 8-max
cell, 5.642 there). Z: up beyond noise on both short-handed exploiter-2 fields, every other exploit cell up in point
estimate, against exploiter 1 too.

## 09:15-10:03: Z's variants (realistic, the screen set's first 50 seeds a cell; bonus_card also at 200)

None beyond noise down (25 cells, 0 timeouts, 0 errors). Lowest: permuted_ranks -0.054 ± 0.112, bounty -0.050 ±
0.120, swap_holdem -0.047 ± 0.146, short_deck -0.035 ± 0.097, deal5_keep2 -0.030 ± 0.036, wild_deuces -0.025 ± 0.111;
three_card_blind_discard **+0.081 ± 0.078** (UP); flush_over_full_house +0.119 ± 0.133, exposed_card +0.106 ± 0.116,
knockout_bounty +0.100 ± 0.210. bonus_card +0.027 ± 0.131 at 50 seeds, -0.032 ± 0.060 at 200 (above). 50 seeds a
cell is a quarter of the protocol's 200: a screen, not a verdict; the coordinator's held-out variants decide, bonus_card
first.

## 09:58-10:12: Z on confirm, guards and elite against the new base (code 9cb5e36)

| cell | base `{"r3.v3_defend": true}` | Z | Z - base | |
|---|---|---|---|---|
| night (confirm) | 5.968 | 5.953 | -0.015 ± 0.072 | level |
| night_hard | 5.486 | 5.448 | -0.039 ± 0.074 | level |
| realistic | 6.346 | 6.352 | +0.005 ± 0.057 | level |
| top | 5.035 | 5.021 | -0.014 ± 0.073 | level |
| night @10/7/5/4/3/2/1/0 | 6.149 | 6.190 | +0.042 ± 0.129 | level |
| night @50/25/12/6/3/2/1/1 | 24.406 | 24.644 | +0.238 ± 0.757 | level |
| night, doubling blinds | 5.830 | 5.852 | +0.022 ± 0.065 | level |
| elite | 4.681 | 4.764 | +0.082 ± 0.086 | level |
| elite_night | 5.328 | 5.392 | +0.064 ± 0.068 | level |

No guard and no elite cell down. Against the new base the night estimate is -0.015 (against FIN it was -0.043: FIN's
dry c-bet was worth +0.028 there, and Z's one size keeps it).
