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
