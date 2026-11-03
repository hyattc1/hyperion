# NOTEBOOK — rival_bot (trained bot, blind build)

T0 = 1793700158 (see T0.txt). Machine load ~14 on 8 cores, so per-decision work must be table lookups only.

## Plan
- numpy (system python3) for offline precompute only; bot is pure stdlib.
- Offline: vectorised 7-card evaluator -> 169x169 HU preflop equity matrix.
- Push/fold: CFR on n-player jam/call game (n=2..8, depth 1.5..25 BB) with ICM utility over 10/7/5/4/3/2/1/0.
- Deep preflop: CFR on open/3bet/4bet-jam game, ICM utility, equity-realisation model postflop.
- Postflop: hand-feature -> equity table (MC), equity buckets, batched chance-sampled CFR on a HU bucket game
  (check / bet 0.66 pot / all-in; raise 3x / all-in), imperfect-recall keys (street, SPR bucket, local line, bucket).
- Simulator: 8-max SNG with simple opponents + self-play; harness for latency.

## E1 equity tables
`python3 pre_equity.py 8e6 {1,2}` + `3e7 {3,4}`: stratified MC, 76M HU deals total, min 330+ samples per cell; equity vs k=1..7 random.
Checks: AA v KK .823, AKs v QQ .468, AKo v 22 .474, 72o v AA .111; EK1 AA .853, 72o .343. Evaluator matches brute force (3000 hands), category freqs match theory.

## E2 push/fold CFR+ sanity
n=2 S=10: SB jam 58.2%, BB call 37.3% (matches known HU Nash; 2-player ICM is linear). S=20: 39.7/21.7.
n=8 S=10 ICM: jam by pos UTG..SB 15.8,19.1,25.7,36.0,48.3,69.3,100; BB calls UTG 2.8%, SB 8.6% (strong ICM pressure, flat payouts).
## E3 deep preflop CFR+ (`deep_solve.py 2..8 300`), ICM equal stacks, realised share eq±0.15·eq(1-eq)
HU 20BB: SB fold/open/jam 43.6/49.4/7.0; BB vs open f/c/3b/j 16.6/54.6/0/28.8. HU 100BB: SB opens 76.5%, BB f/c/3b 8/74/18.
8-max 100BB opens by pos: 26,27,28,30,35,48(BTN),53(SB); no deep jams. (UTG wide vs real GTO: one-responder model.)

## E4 postflop CFR (post_cfr.py), 600k HU deals from 'played' range, 8 equity buckets/street, 6 SPR buckets
200-iter probe: river SPR~1 IP after check: jam bucket0 89% (bluff), mid buckets check, bucket7 jam 100% -> polarised, as expected.
Facing river jam: calls only buckets 6-7. Latency of bot: CPU min-of-3 max 51us; wall spikes to 8-35 ms are machine contention (load 17 on 8 cores), not code.
## E5 first SNG sims (sim.py, 8 distinct bots, 2x500 tables, seeds 11/12)
Field: rival_bot(6000-it postflop CFR), rival_v0 (same, 200-it), tag, solid, nit, random, maniac, station.
rival_bot 5.857 / 5.949 | tag 5.48/5.46 | rival_v0 5.45/5.34 | nit 5.29/5.30 | solid 5.17/5.27 | random 1.95/1.82 | maniac 1.57/1.51 | station 1.22/1.36
(SE ~0.13 per 500 tables.) More CFR iterations -> +0.5 pts vs the 200-it policy. 0 exceptions, 0 illegal. Wall max ~12-38 ms for EVERY bot incl. station: machine contention.
## E6 ICM vs chip-EV push/fold tables (`CHIPEV=1 pf_solve.py`), + wild-opponent detection (>=2 big preflop raises)
chip-EV 8-max 10BB: UTG jam 10.9% (ICM 15.8%), calls 5.9% (ICM 2.8%): ICM jams wider, calls much tighter.
simC field (rival_bot, rival_chip, tag, solid, nit, random, maniac, station) 800 tables seed 21:
  rival_chip 5.738, rival_bot 5.692, tag 5.377, solid 5.262, nit 5.117, random 1.98, maniac 1.54, station 1.29
simD field (rival_bot, rival_chip, rival_old, rival_v0, tag, solid, nit, random) 800 tables seed 22:
  rival_chip 4.768, rival_bot 4.619, nit 4.540, rival_old 4.524, rival_v0 4.406, tag 4.351, solid 3.975, random 0.82
-> chip vs ICM within noise (SE~0.1) but chip ahead in both. wild detection (rival_bot vs rival_old) +0.1.
## E7 PF utility blend (ALPHA=0.5 ICM/chip) — 2000 tables seed 31, field rival_bot(ICM), rival_chip, rival_half, tag, solid, nit, random, maniac
rival_half 5.162, rival_bot 5.065, nit 5.041, rival_chip 4.981, tag 4.825, solid 4.508, random 1.27, maniac 1.15 (SE~0.07): no clear winner; half best.
## E8 bust analysis (dist.py/dist2.py, 600 tables): median bust hand 25, 25% by hand 9.
Early busts (hand<=50): preflop call 53, preflop jam 39, then postflop stack-offs with middle pair / overcards (mc 1,2,4).
-> (a) raise wild-call threshold deep (EK1>=.64 >40BB, .60 18-40BB, .56 short). (b) train risk-averse postflop CFR:
   losses weighted v*(1+tau*fraction_of_stack_lost), tau=0.6 (post_cfr_risk.py), a crude ICM concavity.
## E9 wild-call thresholds raised: rival_bot(new) 5.172 vs rival_half(old) 5.038, rival_chip 4.908, nit 4.989, tag 4.826 (2000 tables seed 51) -> keep.
## E10 self-play 8x rival_bot, 300 tables: seat avgs 3.85-4.19, sum 32.0/table, 316,664 decisions, 0 exc, 0 illegal, mean 26.6us.
## E11 exploiters, one seat vs 7x rival_bot (300 tables each, seed 71): break-even = 4.0
jam 0.83 | minraise 0.47 | potbet 0.68 | station 0.40 | random 0.79 | tag 4.06 | nit 4.49  <- nit profits by sitting out while copies of us
trade stacks: our play is too high-variance for a flat payout. Next: risk-averse postflop CFR; tighter deep preflop (flop-pot tax).
## E12 tighter deep preflop: `TAX=0.9 deep_solve.py` (flop pots worth 0.9x to both players -> 8-max 100BB opens 12.7,15.4,18.5,22.4,28.1,38(BTN),41.6(SB))
1500 tables seed 81: rival_tax 5.299 vs rival_base 5.084, rival_chip 5.003, nit 4.901, tag 4.801, solid 4.472.
## E13 risk-averse postflop CFR (TAU=0.6, 8000 it x 4096 deals) x deep tax, 2x1200 tables seeds 91/92:
rival_both (tax+risk) 5.224/5.218 | rival_tax 5.247/5.160 | rival_risk 4.855/5.057 | rival_base 4.878/4.924 | nit 4.81/4.86 | tag 4.59/4.38
-> tax +0.3 (clear), risk postflop +0.0..0.06 (noise level, but it lowers bust variance; keep both).
## E14 exploiters vs 7x rival_both (400 tables, seed 72): nit 3.746 (was 4.49 vs base), tag 3.581 (was 4.06), jam 0.866, potbet 0.842 -> none above 4.0.
## E15 TAX=0.8 deep preflop (opens 16.5..42.6 at 8-max: BB folds more so stealing pays) vs tax 0.9:
seed 101: rival_t8 5.166, rival_both 5.164, rival_tax 5.088, chip 4.79, nit 4.73, tag 4.70
seed 102 (+solid): rival_both 5.027, rival_t8 4.763, rival_tax 4.604, chip 4.43, nit 4.34, tag 4.19, solid 3.86 -> keep tax 0.9 (rival_both).
## E16 fuzz.py (odd obs shapes: posts in history, legal as list, tuples, None history/hand_no, dead button, min=max raise): 0 illegal, 0 internal exceptions (DEBUG on and off).
## E17 weak field (rival_both + random, maniac, station, nit, tag, solid, potbet) 1000 tables seed 111: rival_both 6.216, tag 5.911, solid 5.700, nit 5.346, potbet 3.26, random 2.24, maniac 1.79, station 1.54
## E18 loose-opponent exploits (rival_x): vs players with fold rate <12% over >=15 actions -> no bluffs, value-bet buckets>=5 at 0.75-1 pot, call more;
   vs wild raisers (aggr>.4 or >=2 big raises) deep: continue with EK1>=.55 instead of folding.
   weak field seed 112: rival_x 6.173, rival_both 6.026, tag 5.608, nit 5.272 ... ; strong field seed 113 (5 rival variants, tag, nit, solid): rival_x 4.465, rival_both 4.458, t8 4.254, tax 4.226, nit 3.86, chip 3.76, tag 3.72, solid 3.25
## E19 TAU=1.0 risk postflop (rival_x10 = x + tau 1.0) and repeat comparisons
seed 131: x10 5.288, both 5.223, x 5.154 | seed 132: both 4.852, x10 4.801, x 4.738 | seed 141: both 5.181, x10 5.122, x 5.089 | seed 142: x 5.293, x10 5.223, both 5.184
sums over 4 runs: x10 20.43, both 20.44, x 20.27 -> all within noise. Pick x10: same strength, most risk-averse postflop (flat payout), keeps the station/wild exploits.
## FINAL = rival_x10 build: PF tables ALPHA=0.5 (ICM/chip blend), deep preflop TAX=0.9, postflop risk CFR TAU=1.0 (8000 it), exploits on.
Build: `PFGLOB='pfa0.5_*.json' DPGLOB='deeptax0.9_*.json' python3 build_bot.py post_risk1.0_1.json` -> rival_bot.py 1,493,214 bytes, import 0.04-0.15 s.
harness (n=2000 and 20000, seeds 1-4): 0 exceptions, 0 illegal, 0 fold-when-check; median ~20us, p99 120-390us; wall max 9-44 ms.
null_bot (returns instantly) in the same harness: max 4-8 ms -> the wall spikes are scheduler stalls (load 17-18 on 8 cores, nice 5).
Intrinsic cost (min-of-3 CPU per obs, 20k obs): p99 24us, max 64us.
fuzz.py: 0 illegal / 0 internal exceptions. self-play 300 tables: 346,708 decisions, 0 exc, 0 illegal, seat avgs 3.84-4.42 (sum 32).
exploiters vs 7x final (300 tables, seed 151): nit 3.443, tag 3.392, jam 0.887, potbet 0.861, station 0.207, random 0.677, minraise 0.747.
weak field (1500 tables, seed 153): rival_bot 6.250, tag 5.806, solid 5.622, nit 5.510, potbet 3.227, random 2.165, maniac 1.910, station 1.511.
md5 23e6881818195b0d110e2b79ecbaa861  elapsed 59 min
