# Edges against strong opponents: what to test next in F, and in what order

Written 2026-11-03 from the four research notes in `docs/research/notes/Edges against strong opponents/`
(`pro_sng_strategy.md`, `poker_ai_literature.md`, `opponent_modelling.md`, `competitions.md`) and from F's own record:
HANDOFF.md, `docs/drills/goal-leaderboard.md`, the "The climb" entries in `docs/decisions.md`, the climb logs (S9, S11,
S12, S13, V-d to V-g), the module docs of `compose/bot.py`, `strategy/hero.py`, `strategy/exploit.py` and
`strategy/profiler.py`, and the earlier report `docs/research/Sequoia poker bot competition prep.md`. Nothing was run
and no code was changed. "F" is batch 5 (3aac34d). In flight while this was written: S14 (strong bots' play by section
at strong tables), S15 (exploiter 3's postflop counter), S6 on H16 (the gated short-handed specialist), V-h (known
cards), the start-vs-now run on H17.

## Findings

1. **Most of what the notes rank first is already in F, or was tried and lost.**
   - Exact ICM against the named opponent on preflop all-ins is in. Rival 3's core plays F's preflop and prices every
     all-in with `_allin` (fold, steal, win and lose, this table's payouts; `hyperion/hybrid/core3.py`). The literature
     note's "largest available gain" was read from Hero's `pushfold.py`. In F, Hero's push/fold plays only re-shoves
     facing a raise under 20 bb (`pre_raised_short`) on hold'em tables, not calls of all-ins.
   - One bet size for value and bluffs is in since batch 5 (`balance_sizes`, 0.5 pot). It was the largest single fix
     against exploiter 2.
   - Reading an opponent's bet size as its strength is in (batch 5's size read).
   - Zero timeouts, a twist-correct equity table built in the first minutes, a legal bot first, and a paired harness
     with held-out seeds are all in.
   - Shoving wider against tight callers, a first-in shove zone at 10-15 bb, an exploitative re-shove price, isolating,
     and steals from fold reads were all tried in Hero. Each lost between 0.02 and 0.19 points on top, top2,
     realistic or the strong field.
2. **Our largest measured gap against strong bots is still short-handed preflop.** In S9, at the elite table, F won
   +0.018 bb a decision three-handed preflop against +0.24 to +0.36 for rival 2 and the elite builds, and +0.07 heads-up
   against +0.20 to +0.32. Routing those two sections to elite1 (with `pre_open_10`) gained about +0.09 more at elite
   and mirror than `pre_open_10` alone. The literature agrees: heads-up "experts" grafted onto a multiplayer strategy
   beat the base. S14 is on this. Its candidate list should include `pre_3way` and `pre_hu`.
3. **F's preflop exploitation looks too strong at strong tables.** Perfect reads from hand 0 lost -0.24 ± 0.16 at
   elite (S12). The `dead_seats` recipe lost -0.16 at elite and -0.12 on top (F1). Isolating (-0.12) and an
   exploitative re-shove price (-0.14) lost on the strong field in Hero's time. The literature says the same:
   exploiting entries lost to every strong bot in the ACPC, and the robust methods give a read no weight below about
   10 observations. Test a trust weight on the preflop reads that widen our risk, at tables that read strong. Keep the
   defensive reads that measured well.
4. **We cannot yet measure "bots that adapt to us".** Exploiters 1-3 are fixed counter-strategies. Each was built with
   one to two hours of black-box play against F. No team has that on the night: the rules reset bot state every table
   and anonymise opponents (§3.8). The real threat is a bot that learns F inside one table. We need one in the field
   before we tune against it.
5. **One measured size tell remains: the exploit layer's 0.33-pot stab.** It bets only air, by design. Exploiter 2
   raises 0.30-0.35 pot bets with any hand, and F folds (-750 bb in 120 heads-up tables, S11). S2 measured a 0.5-pot
   stab as level. This is cheap to fix.
6. **The cap pays ICM, so `cap_vol_bb` is the wrong model and should stay off.** It assumes survivors are ranked by
   chips at the cap (kit F's rule). The official rule and our engine pay ICM on the survivors' stacks. The pro note
   suggests sweeping it; that conflicts with the rule. What ICM still misses near the cap is the blinds each stack
   must still post. That is a small, cheap correction.
7. **Evaluation can get cheaper.** The literature's biggest evaluation tool (AIVAT) suits our sim, because we know
   every card. An all-in runout term is unbiased for any value function we fix in advance. It may cut the seeds each
   test needs. It must be measured: on 6-max cash data the chance-only term gave almost nothing (1.07x).
8. **Many of the notes' format-specific numbers are the researchers' own arithmetic.** The bubble-factor tables, the
   +0.070 points for an any-two jam by the covering stack, "tight callers pay 3x more", the cost of folding to the cap,
   the probe sizes and the blind correction are computed in the notes, mostly in two-player, jam-or-fold models
   without card removal. Human-pool leaks (river under-bluffing) need not hold for bots. ACPC and Pluribus numbers are
   100-200 bb cash. Each item below says which kind its evidence is.
9. **Not worth testing now.** "Call less, raise or fold": our data say F over-folds to strong bettors (72-75% to bets
   of 0.4 pot or less that are 50-65% air from five strong seats, S12; 70% to exploiter 2's c-bet, S11). Probing for
   bet-size translation errors with odd sizes: the field is equity bots, and odd sizes undo our one size. Bandits over
   strategy portfolios: the evidence is 3,000-hand matches, and we get 200. Reads kept across tables: the rules forbid
   it. Real-time search, value nets and full range tracking: far over 1 ms.
10. **The cheapest field information comes from the other regionals.** Menlo Park (Nov 6) and Cambridge (Nov 9) play
    before Pittsburgh. Whatever becomes public (the twist, the kit's shape, whether logs are given, how the field
    plays) is worth more than any sim field: V-g found our measured gains hold when the field is the same and shrink
    to nothing against a different field.

## The ranking at a glance

Rank is by expected gain against strong bots and bots that adapt to us, times the chance it passes `climb_accept`.
"Strong" and "exploit" mean the `--aim` rules (addenda 8 and 6).

| rank | technique | status in F | measured by | expected |
|---|---|---|---|---|
| 1 | Short-handed preflop at strong tables from a strong build | partly in (`pre_open_10` only); S14 running | `--aim strong`, all five elite cells, exploit | +0.03 to +0.08 at strong tables |
| 2 | One size for the layer's stab | partly in (Hero's bets only) | `--aim exploit`, exploiter 2 and 3 cells | +0.05 to +0.2 in heads-up and 3-handed exploit cells |
| 3 | Trust weight on risk-taking preflop reads at strong tables | partly in (weak priors, no floor, no gate) | `--aim strong`; night not down | +0.02 to +0.06 at strong tables; uncertain |
| 4 | An online adaptive exploiter in the field | new (tool) | new `adapt` cells | none by itself; measures 3, 7, 9 |
| 5 | Horizon-aware ICM (blinds still owed) | new; `cap_vol_bb` is the wrong model | confirm, guards, new late-table report | +0.01 to +0.03; more top-heavy |
| 6 | All-in runout term in `climb_accept` | new (tool) | A/A check, interval ratio | fewer seeds per test, if it works |
| 7 | Counter-exploitation alarm and forgetting | partly in (layer decay only) | `adapt` cells | unknown; only against adapters |
| 8 | 3-5 handed ICM push/fold tables, fuller tree | partly in (S13's `short_3`, off) | `--aim strong`, 3-handed exploit cells | only if item 1 leaves a gap |
| 9 | Cover-and-jam at 10-16 bb against tight jam-callers | partly in; tried and rejected in Hero | guards (realistic first), new jam-EV report | small and fragile |
| 10 | Field reader between tournaments | partly in (window recipes) | window stage on a rehearsal kit | depends on the field |
| 11 | Opponent-specific postflop ICM, covered/covering play | partly in (pro-rata curve) | diagnostic, then guards | small |
| 12 | Light 3-bets against openers who over-fold | built, off; oracle level | 400 seeds, confirm, guards, elite | +0.02 to +0.05; under-powered |
| 13 | Off-size robustness (probing test bots, pseudo-harmonic mapping) | partly in | new `probe` field | insurance |
| 14 | Twist decisions priced as value of information | partly in | aware (generic), variants | small per twist |
| 15 | Card bunching on first-in shoves | new | confirm, guards | tiny |
| 16 | Bandit over a portfolio of strategies | partly in (gated routes) | exploit, elite | small at 200 hands |
| 17 | Multiway mode | partly in | confirm, guards | small (2-4% of decisions) |
| 18 | Probing translation errors with odd sizes | new | `probe` field | near zero against this field |

Techniques that are already in, or that do not fit 1 ms and 200 hands, are in the table after the details.

## The techniques in detail

Each item: (a) what it is; (b) evidence and expected edge, with the note's citation; (c) status in F; (d) how to
measure; (e) cost and risk; (f) rank. Latency now: act p99 about 100 µs and hand end p99 about 137 µs on plain
hold'em (batch 5, per-call minimum, load 9), under SafeBot's 0.8 ms deadline.

### 1. Short-handed preflop at strong tables from a strong build

- (a) At tables that read strong, play three-handed and heads-up preflop (`pre_3way`, `pre_hu`) with a strong
  build's code (elite1x, elite2x, r2x or a new elite4x), as batch 5 already does for 10-20 bb opens.
- (b) Evidence and size.
  - Ours (S9, diagnostic seeds): `pre_3way` F +0.018 bb a decision against rival 2 +0.238, elite2 +0.272, elite1 +0.356;
    `pre_hu` F +0.072 against +0.196 to +0.319. F folds a third of these raises to a re-raise (34% / 32%; the strong
    builds 16-22%). On the mirror, from three-handed, F wins 23%, elite1 61%, elite2 51% (F holds 30% of the chips
    there, they 39-42%). The elite builds take first place 19-24% of the time against F's 12-18% (leaderboard).
  - Ours (S9 screen, ungated): the three sections to elite1 (E1) gave elite +0.192 ± 0.084, mirror +0.258 ± 0.088,
    night -0.117 ± 0.074. `pre_open_10` alone (U2) gave +0.099, +0.165 and -0.056. So the two short-handed sections
    carried about +0.09 at both strong tables before any gate. Under top-heavy payouts the gated route's gain was four
    times larger relative to a seat's average (S10).
  - Notes: heads-up "experts" grafted on after folds beat the base strategy, +3.06 ± 0.70 against -6.09 (strategy
    stitching, NIPS 2011; poker_ai_literature §4). Spin specialists call preflop "the most underestimated street"
    (pro_sng §2.4; coach opinion).
  - Expected: +0.03 to +0.08 at strong tables once gated (our judgement). Since S9, batch 5's S11 fixes changed
    blind-against-blind and heads-up play, and S6 may ship, so re-profile before trusting the S9 split.
- (c) Partly in. The strong route covers `pre_open_10` only (`strong_route` elite1x, `strong_rr` 0.2). S9's split was
  never run after the scope change. S14 is running and routes by section to r2x, elite2x and elite4x.
- (d) `--aim strong`. Stages confirm, guards, elite (elite, elite_night, mirror, elite_b, mirror_b), exploit (all nine
  cells: exploiters 2 and 3 still win heads-up and three-handed, and S6 also plays `pre_hu`), variants (only the
  hold'em-shaped entries the route can reach: top_heavy, antes_from_level_3, fast_schedule, straddle), judges at batch
  end (elite_judge and elite_judge_b first). Needs one new rule: which route wins `pre_hu` when both `strong_route` and
  `short_route` are open.
- (e) A light shadow per donor costs about 8-10 µs a decision (elite1, measured). Rival 2's core needs a light shadow
  first (its full shadow is about 260 µs, S9). On ordinary tables the gate stays shut: night re-raises 14% of our
  opens, strong tables 24-26% (49% three-handed on mirror). If the gate leaks, the cost is night: ungated E1 was
  -0.12. S5's lesson applies too: taking short-handed spots from F against ordinary bots lost -0.25 under top-heavy
  payouts.
- (f) Rank 1.

### 2. One size for the exploit layer's stab

- (a) When `balance_sizes` is on, the layer's `bet_checked` bets the same 0.5 pot as every other bet with nothing to
  call, so a size no longer says "air". Check the layer's 2.0 bb steal against rival 3's 2.2-2.5 bb opens for the
  same reason.
- (b) Evidence and size.
  - Ours: exploiter 2 raises 0.30-0.35 pot bets with any hand and F folds: -750 bb in 120 heads-up tables (S11). The
    guard that skipped the stab against raisers (`exploit.raise_guard`) also fired on exploiter 1 (21% of our bets
    raised) and was dropped. Before batch 5, F's 0.33 bets were 57% of its bets and 61% air (S12 survey). One size for
    Hero's bets was the largest single fix: +0.180 ± 0.105 heads-up and +0.163 ± 0.101 three-handed against exploiter
    2 (S11 dev screen). S2 measured the stab at 0.5 pot as level (`exploit.py`, `bet_frac`).
  - Notes: "if we bet one size with a weak hand and a different size with a strong hand, it would be very easy for the
    opponent to exploit us" (Ganzfried & Yusuf; poker_ai_literature §7); MIT 2025 winners read hidden cards from bet
    sizes (opponent_modelling §3b); Galfond's example (pro_sng §5.7).
  - Expected: +0.05 to +0.2 in the exploiter heads-up and three-handed cells, level on night (our judgement). The
    steal size is speculative: no test has shown a reader using it.
- (c) Partly in: Hero's bets use one size on hold'em since batch 5; the layer's stab does not.
- (d) `--aim exploit`. Exploit stage: exploit2_hu, exploit2_3, exploit3, exploit3_hu, exploit3_3 should rise;
  exploiter 1's cells must not fall. Confirm (night: the stab earns there), guards, elite, variants (all 26, with
  addendum 7: the layer acts on twist tables too). Coordinate with S15: exploiter 3's postflop counter may be this tell.
- (e) No latency. A 0.5-pot stab needs 33% folds where 0.33 needed 25%; the layer already requires a 0.4 product of
  fold rates, and dead seats fold anyway. Risk: a few stabs that were thin at 0.33 lose at 0.5.
- (f) Rank 2.

### 3. A trust weight on risk-taking preflop reads at strong tables

- (a) Shrink the preflop reads that widen F's risk toward their priors, with weight n / (n + s) and zero weight below
  10 chances in that cell, while the table reads strong. These are rival 3's core's fold reads in its steal price and
  open clauses, and the layer's `steal_min_fold`. Leave the defensive reads alone (the 3-bet defence, the size read,
  the probe read): they measured up at strong tables.
- (b) Evidence and size.
  - Ours: all of F's reads known from hand 0 lost -0.236 ± 0.161 at elite and gained +0.181 ± 0.148 on realistic
    (S12). By store, inside noise each: rival 3's core -0.112 ± 0.169, the layer -0.054 ± 0.119, Hero's profilers
    +0.022. `dead_seats` lost -0.16 ± 0.08 at elite and -0.12 ± 0.08 on top (F1). In Hero's time, isolating lost -0.12
    and an exploitative re-shove price -0.14 on the strong field, and exploitative first-in shoves 0.05-0.10 on top and
    top2 (decisions).
  - Notes: Alberta's exploiting entries lost 8-37 mbb/g to every strong limit bot and 105-184 to strong no-limit bots,
    while their equilibrium twins mostly won (Bard thesis; opponent_modelling §2, §3b). Data-biased response with no
    trust below 10 observations did not overfit (Johanson & Bowling 2009; opponent_modelling §1). DBBR's authors:
    "might actually become significantly exploitable to strong opponents" (pro_sng §7.4). The Fullhouse winner
    reportedly played pure baseline below 20 observed actions and full weight from 60 (competitions §2; second-hand).
  - Expected: +0.02 to +0.06 at strong tables (our judgement). The case is thin in one place: S12's warm reads were
    long-run rates from tables where the elite builds had already adapted to F. That is not the same as F's cold reads.
- (c) Partly in: weak Beta priors (profiler `prior_n` 2), decayed layer reads, the 3-bet defence's slow prior (0.08
  worth 20). No trust floor and no strong-table gate on read-driven steals.
- (d) First a diagnostic: S12's warm-store split on elite_b and mirror_b at 200 seeds, to see whether the preflop
  reads really carry the loss. Then `--aim strong`: the five elite cells; confirm (night must not fall: reads pay
  against weak seats); guards (realistic, top); exploit (exploiter 1's cells rest on the 3-bet defence, which this must
  not touch). Later, the adaptive exploiter's cells (item 4).
- (e) No latency (one multiply per read). Risk: the strong-table signal was on at only about a fifth of the size read's
  spots at elite and mirror (S12b), so a gate on it alone may do
  little. A per-seat evidence gate is the fallback, fixed before screening.
- (f) Rank 3.

### 4. An online adaptive exploiter in the field

- (a) A test opponent that starts sound and learns F inside one table. It counts F's pooled stats (fold to a bet, fold
  to a raise, fold to a 3-bet, c-bet rate, our bet sizes against the strength shown, jam-call rate) and switches to
  fixed counters after about 30 hands.
- (b) Evidence and size.
  - Notes: the opponent-modelling note's suggested harness includes exactly this bot (opponent_modelling, "Testable").
    Against an opponent that switches to best-responding after 100 hands, risking only what has been won scored
    -0.020 against -0.121 for an unsafe best response (Ganzfried & Sandholm 2015; opponent_modelling §2). A model that
    assumed a stationary opponent lost money against one that switched (Bard & Bowling 2007).
  - Ours: no field holds such a bot. Elite 5 (reads-minded) is a held-out judge. Rival 3 reads, but was not built to
    beat F. The mirror's F copies read F only through F's own reads.
  - Expected: no points by itself. It is the measurement for items 3, 7 and 9, and the honest test of "bots that adapt
    to us".
- (c) New.
- (d) New bot(s) and cells: `adapt` (8-max, with six night seats), `adapt_hu`, `adapt_3`, in `climb_accept`'s exploit
  stage. Fix the roles in a decisions addendum before any result: one tuning copy, and one built by a fresh agent with
  no repo access, held out as a judge. Check it adapts: its chips per hand against F should rise from hands 1-30 to
  hands 100-200, and should not rise against a field without F.
- (e) Test-only; `--slim` already leaves test bots out of the zip. It must replay exactly in model mode (seeded per
  table). Risk: tuning F to one adapter (a single-opponent agent "can not be generalised", DeepBot; competitions §3);
  the held-out copy guards against it.
- (f) Rank 4.

### 5. Horizon-aware ICM: the blinds each stack still owes

- (a) Before each ICM evaluation, take from every stack the blinds it must still post before the cap or before its
  next button, whichever comes first. Apply it in Hero's `IcmCurve` and in rival 3's core's `icm_points`. Keep
  `cap_vol_bb` off.
- (b) Evidence and size.
  - Notes: against the 3-player jam/fold equilibrium, ICM's mean error is $0.37 per $100, and its worst is $2.99, for a
    big blind about to post most of his stack (Ganzfried & Sandholm 2008; poker_ai_literature §8, competitions §3).
    Future-game simulation reverses UTG's and the SB's push ranges at 6 or fewer alive and under 10 bb (ICMIZER;
    pro_sng §1.8). HRC's author claims +0.3% ROI for it, self-reported, with no interval. The blind correction itself
    is the researcher's own rule, not from the literature (poker_ai_literature §8 says so). The cost of folding to the
    cap is the pro note's arithmetic (§0). The note says about half our tables end at the cap with two or three alive;
    not re-measured here.
  - Expected: +0.01 to +0.03 on night, more under top-heavy payouts and a doubling schedule (our judgement).
- (c) New. `cap_vol_bb` (built, off, never swept) blends ICM with a chip-rank model of the cap. That is kit F's rule
  (`cap_places: chips`); the official rule and our engine pay ICM at the cap. Rival 1's own cap mode was worth nothing
  to it (5.698 with, 5.759 without, 60 seeds: thin).
- (d) Confirm; guards (all three payout tables and the doubling schedule); variants (fast_schedule,
  antes_from_level_3, top_heavy); elite. New: a report of points and bust rate on tables that reach hand 150 with
  three or more alive, and a guard rules file with a 150-hand cap.
- (e) No per-decision cost: the curve is built at hand end. Risk: it lowers short stacks' values far from the cap,
  which changes calls. Test one form fixed in advance, with no sweep.
- (f) Rank 5.

### 6. An all-in runout term in `climb_accept`

- (a) When a hand goes all-in before the river, score each bot's points minus (V of the actual runout minus the
  average V over all runouts), with V the ICM points of the post-hand stacks. The term has mean zero for any V fixed in
  advance, so the estimate stays unbiased.
- (b) Evidence and size.
  - Notes: AIVAT cut the standard deviation about 3x heads-up (ten times fewer hands) and Pluribus' variance about 9x.
    But the chance-only part alone gave about 1.07x on Pluribus' 6-max data, and duplicate deals already remove much
    of what chance terms remove (poker_ai_literature §11). Fix V before looking; optional stopping breaks the stated
    intervals (2026 preprints, same section).
  - Ours: one all-in often decides a short-stacked table, so the term may do more here than in deep cash. Unknown
    until measured.
- (c) New.
- (d) A `climb_accept` option. Check that the term averages zero: over 400 seeds, each spec's corrected mean must match
  its raw mean within noise, and two known batch-5 comparisons must give the same verdicts. Report the interval ratio
  per cell. Write a protocol addendum before any verdict uses it.
- (e) Sim time per all-in (enumerate or sample about 50 runouts with a fixed seed); no cost to the bot. Risk: a bug
  that biases verdicts. Keep the raw estimate as the verdict until the checks pass.
- (f) Rank 6. No points by itself; it multiplies every later test.

### 7. A counter-exploitation alarm, and forgetting

- (a) When an exploit starts against a seat, record that seat's rate in the stat the exploit leans on (for example its
  raise rate against our c-bets). If the rate moves by 2 standard errors or more, with at least 10 observations,
  return that seat to baseline. Decay counts about 1% a hand.
- (b) Evidence and size.
  - Notes: the safe-against-switchers result in item 4. Bard & Bowling's best fixed setting was a 0.01 switch rate per
    hand. Seeing a 1 bb a hand loss from raw results needs about 278 hands (opponent_modelling §2, the note's own
    arithmetic), so result-based alarms cannot work inside a table. The behaviour-based alarm is the note's own design;
    nobody measured it.
  - Expected: unknown; it only matters against adapters.
- (c) Partly in: the layer's reads decay (a memory of about seven spots, S12). The profiler's counts do not. No alarm.
- (d) The `adapt` cells (item 4) should rise; exploit stage; confirm and guards must not fall. Needs item 4.
- (e) A few µs. Risk: false alarms on noise turn off exploits that earn on night.
- (f) Rank 7.

### 8. Three-to-five-handed ICM push/fold tables with a fuller tree

- (a) Extend S13's three-handed ICM solve (`tables/short_3.json`) with a small-blind flat, a big-blind 4-bet and two
  3-bet sizes. Add jam/fold tables for four and five alive at this format's payouts, with card bunching from the seats
  that folded.
- (b) Evidence and size.
  - Notes: under ICM, first-in jams barely move but calls shrink 2-9x; the big blind overcalls two jams 2.1% of the
    time against 19.7% in a single hand (Ganzfried & Sandholm 2008; poker_ai_literature §8, competitions §3). Policy
    iteration with fictitious play gives an equilibrium whenever it converges (IJCAI 2009). Card bunching moved a
    9-max SB jam from 77.3% to 69.3% after seven folds (HRC, with antes; pro_sng §3.2); with no ante it is smaller.
  - Ours: S13's three-handed tables lost to both exploiters because the tree has no SB flat and no BB 4-bet and maps
    small 3-bets onto 3.5x.
  - Expected: if S14 routes `pre_3way` well, little is left. Otherwise +0.02 to +0.05 at strong tables (our judgement).
- (c) Partly in: built and off (`short.three`); it loses to the exploiters.
- (d) `--aim strong`, plus the three-handed exploit cells; guards with top_heavy (first place is decided short-handed).
- (e) An offline solve (about 14 minutes with numpy for 512 configurations); 1-2 MB of tables in the zip; lookups in
  µs. Risk: the tree's gaps, already measured.
- (f) Rank 8. Run only if item 1 leaves `pre_3way` behind.

### 9. Cover-and-jam at 10-16 bb against seats that call jams tightly

- (a) Extend rival 3's ICM jam, now only at 10 bb or less, to 10-16 bb when we cover the likely caller and its observed
  jam-call rate is low.
- (b) Evidence and size.
  - Notes: in a two-player jam-or-fold model of this format, the covering SB jams any two against a 3% caller for
    +0.070 points per SB hand, and loses 0.057 jamming any two into a 21% caller (pro_sng §0, the researchers' own
    computation, no card removal). At 10 bb heads-up the best response to a top-15% caller gains +0.29 bb a hand, about
    3x what loose callers give (poker_ai_literature §8, the researcher's own fictitious play on our `hu_matrix`).
    Removing one hand from a caller's range widened a correct push from 17.5% to 27% (ICMIZER; pro_sng §1.6).
    ICM-aware strong bots should call jams tightly.
  - Ours, against: exploitative first-in shoves lost 0.05-0.10 on top and top2; a first-in shove zone lost 0.12-0.19 on
    realistic, where Monte Carlo bots call wide; adding `pre_open_short` to the strong route bought nothing (S9, G3).
    Jam-call reads settle slowly: off by 0.10-0.17 at hand 199 (S12).
  - Expected: small and fragile.
- (c) Partly in: rival 3 jams at 10 bb or less by exact ICM against the loosest seat behind, its call width taken from
  VPIP rather than observed jam calls. Elite1 jams up to 14 bb at strong tables through the route. Tried and rejected in
  Hero.
- (d) Confirm; guards (realistic first); elite; exploit 8-max; the `adapt` cells (an adapter learns to call wider).
  New: a report of jam EV by the caller's observed jam-call bucket.
- (e) µs. Risk: the realistic loss, twice measured.
- (f) Rank 9.

### 10. A field reader between tournaments (the hour)

- (a) In each 20-minute window, read whatever the kit gives about the last tournament (logs, hand histories,
  standings) and choose a window recipe by a rule fixed in advance.
- (b) Evidence and size.
  - Notes: Alberta's static response to pooled field data won three-player limit by 84.3% and 40.1% in 1,000-hand
    matches (Bard thesis; opponent_modelling §4). Every MIT winning approach "used scrimmage logs" (competitions §1).
    The rules do not say logs are provided.
  - Ours: V-g found our deltas hold when the field is the same and shrink to zero against another. F's recipes exist
    (survival, passive, dead_seats, strong_field), and `dead_seats` helps only for its own signal (-0.12 on top).
  - Expected: depends on the field. The main value is not picking the wrong recipe.
- (c) Partly in: recipes, the `window` stage and prompt 06. No log reader.
- (d) The window stage on a rehearsal kit's field; a drill with a kit that writes the previous tournament's logs;
  minutes from logs to a chosen recipe.
- (e) No runtime cost. Risk: fitting a recipe to one tournament (a Fullhouse finalist's per-opponent table was right
  46% of the time on held-out data; competitions §2).
- (f) Rank 10.

### 11. Opponent-specific postflop ICM, and covered/covering play

- (a) Price postflop stack-offs with exact ICM against the specific opponent (Hero's curve moves chips to the field pro
  rata). When an opponent in the pot covers us and our bubble factor against it is 1.3 or more, c-bet less and check
  back marginal hands; when we cover, lead more.
- (b) Evidence and size.
  - Notes: single solver spots (GTO Wizard, written up by Carter; pro_sng §1.7): the covered player c-bets under half as
    often; the covering big blind leads 9-24%. Carter's ≈2 bb/100 for the covered player's chip-EV overbets is an
    author's estimate. The bubble factor depends on whom we play: 2.24 against the cover, 1.17 against a short stack
    (poker_ai_literature §8, computed).
  - Expected: small. F is not chip-EV postflop (the curve and the 0.2 call margin already price stack-offs), and pots
    with a real cover gap and heavy ICM pressure are a few percent of decisions.
- (c) Partly in.
- (d) First a diagnostic on S12's recordings: count postflop stack-offs where opponent-specific ICM and the curve
  disagree. Then a dial: guards (night under 50/25/12/... and top_heavy first), elite, confirm.
- (e) The hero-only exact ICM is about 44 µs at eight alive (the researcher's timing, under load); compute it only on
  stack-off decisions, or cache per opponent at hand end. Risk: checking more when covered gives probing bots more
  free stabs (S11's leads).
- (f) Rank 11.

### 12. Light 3-bets against openers who over-fold

- (a) Turn on the learned version of `r3.l3_on`: with deep stacks, 3-bet a wider range when the opener's observed
  fold-to-3-bet is high.
- (b) Evidence and size.
  - Ours: openers fold 67-89% to a 3-bet (elite1 43%); F 3-bets 7%, for value only (S12 survey). The oracle (true fold
    rates) gave +0.058 ± 0.093 night, +0.084 ± 0.141 top, +0.023 ± 0.121 elite at 100 seeds, never beyond noise. The
    learned version was never measured.
  - Notes: light 3-bets in position against regs became common once SNG fields filled with regs (Moshman; pro_sng
    §2.4). GTO Wizard says its mass data show big blinds 3-bet too little (no sample size; human pools).
  - Expected: +0.02 to +0.05 on night and top; it needs 400 seeds to see.
- (c) Built, off; the oracle was level.
- (d) 400 seeds; confirm, guards, elite; exploit (interplay with the 3-bet defence and exploiter 1's light 4-bets).
- (e) µs. Risk: 4-bet jams from strong bots.
- (f) Rank 12.

### 13. Off-size robustness

- (a) Add test opponents that min-bet into big pots, overbet-bluff at 2-10x pot, and bet sizes between the common ones
  (0.2, 0.71, 1.4 pot). Fix only what loses. In S13's specialist, map off-tree raises with the randomized
  pseudo-harmonic mapping; its log-scale split is geometric and never maps a bet down.
- (b) Evidence and size.
  - Notes: in the clairvoyance game the randomized pseudo-harmonic mapping is unexploitable (0.00), against 1.00 for
    randomized geometric and 12.37 for deterministic arithmetic (poker_ai_literature §7). Claudico's biggest leak was
    misreading the pot after translation. A min-bet on a large pot broke MIT CFR bots (competitions §4). These hurt
    table bots with fixed size menus.
  - Ours: Hero and rival 3 price bets continuously by pot odds, so most of this does not apply to F (the note says near
    zero against equity bots). The specialist is the exception.
  - Expected: insurance.
- (c) Partly in.
- (d) A new `probe` field (the probing bots plus night seats); confirm unchanged. For the kit side: a fixed menu of
  pot-fraction tokens, as drill 9's kit used.
- (e) Test-only bots; µs in F.
- (f) Rank 13.

### 14. Twist decisions priced as value of information (variants)

- (a) Price each twist decision (bid, buy, swap, discard, keep) as the difference in value between the options by quick
  simulation, include what denying the card to others is worth, then scale by one multiplier tuned on aware fields.
  Add V-g's showdown-tax read: the prepared table's mean value share against one hand (0.501 in hold'em) as a shift in
  call and value thresholds.
- (b) Evidence and size.
  - Notes: GTO Wizard's MIT 2024 auction entry used an equity difference times 1.8, the best of 0.5-2.5x; Notato
    priced bids as offensive plus defensive value fitted from logs (competitions §5).
  - Ours: F bids from a precomputed table (auction +1.44 over the best generic bot, V-d) and keeps or discards by value
    share. The Ghost's mean value share was 0.342 (V-g).
  - Expected: small per twist. The decision-bearing families are about a third of the twist mass by V-f's weights.
- (c) Partly in.
- (d) The aware stage with `generic:<entry>` for auction, bonus_card, swap_holdem, swap_one_turn, toss_or_holdem,
  three_card_blind_discard and deal5_keep2; the variants stage with addendum 7; a held-out set. Three multiplier values
  fixed in advance, no sweep beyond them.
- (e) Precomputed; µs. Risk: tuning a multiplier on screen seeds that does not hold out.
- (f) Rank 14.

### 15-18. Lower in the order

| # | (a) what | (b) evidence and size | (c) status | (d) measure | (e) cost and risk | (f) |
|---|---|---|---|---|---|---|
| 15 | Card bunching: after several folds, assume the folders held weaker hands when pricing a first-in jam | HRC: 9-max 7.5 bb with antes, SB jam 77.3% → 69.3%, BB call 62.3% → 52.5%; about 24% of standard SB combos lose, worst 0.5 bb (pro_sng §3.2). Smaller with no ante. Tiny | new (rival 3 multiplies independent fold reads) | confirm, guards, elite | an offline table; tiny gain; bundle with item 8 or 9 | 15 |
| 16 | A bandit (Exp3/Exp4) over 3-4 strategy variants per seat, scored off-policy | Implicit modelling would have won the 2011 total bankroll, 317 vs 224 (Bard et al. 2013), in 3,000-hand matches; at 200 hands the notes expect a smaller edge (opponent_modelling §4) | partly in: the composite already routes by table reads (strong route, short route) | exploit, elite | off-policy weights over our actions; complex; learns little in 200 hands | 16 |
| 17 | Multiway mode: exploit only in pots heads-up with the target; no pure bluffs multiway; squeeze linear | "Pure bluffs are ineffective multiway" (GTO Wizard); a chump-farming 3-player agent was exploited once the chumps were gone (Abou Risk; opponent_modelling §5) | partly in: the layer's stab needs every opponent left bluffable | confirm, guards | multiway is 2-4% of decisions | 17 |
| 18 | Probing translating bots with odd sizes (0.2, 0.714, 1.4 pot; tiny bluffs) | Hyperborean 2009 won with a card-blind boundary prober; naïvePA beat hard translation by about 13.5 bb a hand (poker_ai_literature §7). Near zero against equity bots, which treat sizes continuously | new | `probe` field | undoes one size, our best fix against exploiter 2 | 18 |

## Already in, or ruled out

Numbers in parentheses are the notes' own "Testable" item numbers.

| technique (notes) | (b) evidence | (c) status in F | (d) measure | (e) cost / risk | (f) |
|---|---|---|---|---|---|
| Exact ICM on every all-in call and shove (pro 1, literature 1, competitions 6) | calls shrink 2-9x under ICM; bad calls cost about 4-10x bad shoves | in for preflop all-ins (rival 3's `_allin`); re-shoves and postflop use Hero's pro-rata curve (item 11) | regression only | none | in |
| One size per node, no size tells (pro 10, literature 5, modelling 2) | one river size keeps 99.7% of EV; a one-size bot won 19.4 vs 13.1 bb/100 against Slumbot (self-reported) | in for Hero's bets (`balance_sizes`); the layer's stab is item 2. Size jitter is not built; the notes expect near zero from it against rule bots | — | — | in |
| Reading opponents' size against strength (pro 12, literature 8) | no paper measures it in bots | in (batch 5's size read: night +0.032, mirror +0.158 held out) | — | — | in |
| Re-steal jams at 10-25 bb (pro 6) | re-jam break-even folds 72-87% (pro §0) | in (`reshove_mid_bb` 25 in Hero, `pre_raised_short`); the exploitative re-shove price lost -0.14 strong | — | — | in |
| Gift detectors with hard counters (modelling 1) | degenerate bots identified in about 5 hands (modelling §1, computed) | in (the layer's dead and timeout reads, the profiler's flags, archetype dials) | — | — | in |
| Raise-or-fold, call less, stack-off discipline, bluff-catcher discipline (competitions 4-5, pro 9) | top MIT bots call far less, but partly from end-of-match check-folding; Fullhouse scores chips with a bust penalty, not ICM points | in (call margin 0.2; risk-of-ruin margin swept within noise); our data say F over-folds to strong bettors | do not test | conflicts with S11 and S12 | — |
| Zero forfeited decisions; twist-correct equity first; simple bot first; a paired harness (competitions 1, 2, 9, 10) | the biggest single fix for a Fullhouse finalist; the HPI champion's main work | in (governor, gate, generic tables, drills 7-9, `climb_accept`) | — | — | in |
| No-ante preflop calibration (pro 5) | MTT charts with antes are too loose here | in (rival 3 was built for this brief; S13's tables have no ante) | — | — | in |
| Cap-aware laddering, "check-fold the last 100 hands" (pro 4, competitions 3, modelling 11) | MIT and HPI winners did it under chip-lead scoring | mostly priced already: the ICM split is the cap's payoff; what is missing is the blinds still owed (item 5) | — | — | see 5 |
| Exploratory play in the first 25 hands; multi-street bluff planning by line EV (modelling 12, pro 14) | Kuhn poker; one worked solver example | not built | — | small, speculative | skip |
| An 8-max preflop solved offline with ICM leaves; fold-biased purification of solver tables; an offline self-improver for size menus (literature 6, 10, 12) | +71 vs +20 mbb/h for purification (heads-up cash); Libratus' self-improver | F has no blueprint; S13's tables are the only solver tables | — | high build cost for little | skip |
| Real-time search, value nets, full range tracking, reads kept across tables | search was the decisive part of every superhuman bot | ruled out: 1 ms in Python; the rules reset state per table (V-g's +0.45 came from a kit that does not) | — | — | out |

## The next two rounds

Before round 1, two messages to running workers, not new workers:
- **S14:** put `pre_3way` and `pre_hu` in the candidate sections (item 1), each behind the strong-table gate, and
  propose a precedence rule with S6's `short_route` for `pre_hu`.
- **S15:** check whether exploiter 3's postflop counter leans on the layer's 0.33 stab. If it does, hand that part to
  S17.

### Round 1 (now): six workers, tracks strength, robustness and variants

Listed in the order of expected gain against strong and adapting bots.

1. **S17 (strength): one size for the layer's stab.** Dial `exploit.stab_size`, 0.5 on hold'em tables when
   `balance_sizes` is on; report the layer's 2.0 bb steal size against the base's opens, and change it only if a size
   read separates it. Screen, then held out, `--aim exploit`: exploiter 2 and 3 cells up, exploiter 1 cells not down,
   night, guards, elite and all 26 variants not down. About half a day.
2. **S16 (strength): a trust weight on risk-taking preflop reads at strong tables.** First the diagnostic: S12's
   warm-store split on elite_b and mirror_b, 200 seeds. Then dials `r3.read_trust` and `exploit.read_trust`: weight
   n / (n + 10), zero below 10 chances, only while `Profiler.strong_table` reads strong; the fallback (a per-seat
   evidence gate) is fixed before screening. The 3-bet defence, size read and probe read are untouched. `--aim strong`:
   elite stage up, night and realistic not down, exploiter 1 cells unchanged.
3. **R6 (robustness): an online adaptive exploiter.** A test bot that learns F's pooled stats and switches to fixed
   counters after 30 hands; cells `adapt`, `adapt_hu`, `adapt_3` in the exploit stage. A decisions addendum fixes the
   roles first: this copy tunes; a second copy, built by a fresh agent with no repo access, is held out. Deliverables:
   its learning curve against F by hand bucket (1-30, 31-100, 101-200), its result against a field without F, and F's
   current numbers in all three cells.
4. **S18 (strength): horizon-aware ICM.** One pre-registered form (blinds owed before the cap or the stack's next
   button, whichever is sooner) in Hero's curve and rival 3's `icm_points`. A late-table report (points and bust rate on
   tables that reach hand 150 with three or more alive) and a guard rules file with a 150-hand cap. Confirm, guards (all
   payout tables, doubling blinds), variants (fast_schedule, antes_from_level_3, top_heavy), elite. Also add to
   `cap_vol_bb`'s comment that it models chip ranks at the cap, not the official ICM split, so it stays off.
5. **R7 (robustness): the all-in runout term.** A `climb_accept` option; the check that the term averages zero; re-runs
   of two batch-5 comparisons; the interval ratio per cell. Adopted only by a protocol addendum written before use, and
   only if the checks pass.
6. **V-i (variants): twist decisions as value of information.** One multiplier on the priced value of every twist
   decision (three values fixed in advance), plus the showdown-tax read for payoff hooks. Aware stage with
   `generic:<entry>` on the seven decision-bearing entries; variants with addendum 7; then held out.

### Round 2 (after round 1, S14, S15 and S6 report): six workers, tracks strength, the hour and robustness

What round 1 finds may reorder this; each item says what it waits for.

1. **S20 (strength): short-handed preflop, whatever S14 leaves.** If S14's `pre_3way` and `pre_hu` routes pass, take
   them through held-out confirmation with S6. If `pre_3way` is still behind, extend S13's three-handed tree (SB flat,
   BB 4-bet, two 3-bet sizes, card bunching) and add four- and five-alive ICM jam/fold tables, gated like S6 or by the
   strong-table read. `--aim strong`, plus the three-handed exploit cells and top_heavy.
2. **S19 (strength): the counter-exploitation alarm and forgetting.** Needs R6's cells. For each exploit that fires
   (the layer's steals and stab, rival 3's widening, the size and probe reads), revert a seat on a move of 2 standard
   errors in its response stat with at least 10 observations; decay profiler counts 1% a hand. A decisions addendum
   makes the `adapt` cells exploit fields under addendum 6 before any result.
3. **S21 (strength): cover-and-jam at 10-16 bb with an observed jam-call read.** Extend rival 3's short branch to
   16 bb when we cover the likely caller and its observed jam-call rate (prior from the ICM-correct rate, worth 5) is
   0.1 or less; never against seats that have called jams wide. Realistic is the guard that killed this twice; add the
   jam-EV-by-caller report and the `adapt` cells.
4. **H6 (the hour): the field reader.** Collect what Menlo Park (Nov 6) and Cambridge (Nov 9) make public: the twist,
   the kit, whether logs are given. Build a parser for whatever a kit logs, giving the field's mix (VPIP and PFR,
   shove rates, bust causes, timeouts), and a recipe rule fixed in advance. Rehearse it in a drill whose kit writes the
   previous tournament's logs; measure minutes to a recipe and the window stage on that field.
5. **R8 (robustness): off-size test bots.** A min-bettor, an overbet bluffer and an off-grid prober in the bestiary; a
   `probe` field; F's numbers there. Fix only what loses (the pseudo-harmonic mapping in the specialist if S6 ships;
   a size-read bucket for bets under 0.25 pot). Also a kit with a fixed menu of pot-fraction tokens through the adapter.
6. **S22 (strength): opponent-specific postflop ICM.** The diagnostic on S12's recordings first; a dial only if
   decisions flip often enough to matter. Guards with top-heavy payouts first, then elite and confirm. In reserve if a
   slot frees: item 12, the learned light 3-bets, at 400 seeds.
