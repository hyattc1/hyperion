# Should the climb accept on a weighted score? A review of the acceptance rule

Written 2026-11-03. The owner asked whether "beyond noise up somewhere that matters, beyond noise down nowhere" is
too strict, since a change can be clearly positive overall and still fail on one small loss. This report proposes a
weighted rule, re-scores every past candidate it can find data for, and recommends what to do.

No code was changed and no simulation was run. The inputs are the 244 `climb_accept` verdict JSONs in the session
scratchpad (`goal/`), the per-seed samples in their caches (used only to measure how correlated the cells are), and
the logs: `docs/drills/goal-log.md`, `docs/drills/climb/s9..s16-log.md`, `docs/decisions.md`. The scripts and the
rule as first written are in the scratchpad at
`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/acc/` (`rule_fixed.json`,
`wrule.py`, `registry.py`, `exact.py`, `final.py`; results in `final_rows.json`).

**Unit.** Every number below is in *night points*: points of one 8-max table on the 8..1 table. F scores about 6.0
there against `night`. +0.01 is about 0.17% of F's score; batch 5 as a whole was worth +0.06.

## Findings

1. **The small losses that sank candidates were nearly all real, and fixing them cost time, not points.** Of the 14
   rejections for small losses, 13 had a mechanism found afterwards. Only FIN's toss_or_holdem cell was noise. Most
   were a gain leaking onto tables it was not built for:
   - twist tables: V-b on lowball, G2 on bounty and auction, Z and Z2 on several twists;
   - odd bettors: C7 on one-size bettors, D1 on night seats that rarely c-bet;
   - ordinary opponents: S5 heads-up against ordinary bots.

   Ten were followed by a gated or narrower version that kept the gain and dropped the side effect. Nine of those
   versions are already accepted, 35 minutes to 6.5 hours after the rejection: V-b to V-b fixed, G2 to G2 fixed, C7
   and D1 to D3, Z and Z2 to Z3, S5 to S6, FIN and S2-A to the 3-bet defence. The tenth, S15c, is on H19 now. On
   held-out seeds, the gated version's weighted value was always within noise of the original's:
   - better for D3 (+0.018 against D1's +0.006) and for the fixed strong route;
   - about equal for S6 (+0.0050 against S5's +0.0047);
   - lower but within noise for Z3.

   So the strict rule has worked as a side-effect alarm. The price was about 20 hours of wall-clock across tracks and
   about seven extra held-out sets, not lost gains.
2. **The weighted rule is not more lenient. It is strict in a different place.** It would have rescued three held-out
   rejections: V-b on H1 (lowball), FIN with V-b on H2 (bonus_card), and S5 on H14 (base weights only). It would also
   have rejected two held-out accepts:
   - Z3 on H12: +0.004, exact interval ±0.008;
   - V-f on H15: +0.002 ± 0.002.

   It also rejects G2 fixed (H6) under worst-case weights, and the T2 and S15c screens. Their gains sit in cells that
   carry little of the night (exploiter 2 heads-up, one twist at 3%), and the rest of their cells add noise. The
   current rule passes them because one cell is up and none is down. The weighted rule asks for a net gain it can see.
3. **The weighted rule's screen verdict predicts its held-out verdict better.** It agrees on 12 of 15 screen/held-out
   pairs; the current rule agrees on 9. Of the weighted rule's 10 screen accepts, 8 held on held-out seeds. Of the
   current rule's 14, 8 held. Every miss by the current rule was a fresh set pushing one or more small cells across
   zero. In 4 of those 6 misses, the failing cell was one the screen never ran, ran at 50-100 seeds, or ran on an older
   base.
4. **Screens overstate the gain by about half, but no held-out gain was negative.** The median ratio of held-out to
   screen weighted gain is 0.51. All 15 candidates that reached a held-out set had a positive weighted mean there.
5. **The cells are nearly uncorrelated.** The pairing is per seed, but the cells use different fields, and the
   paired differences barely move together. I computed the exact interval of the weighted sum from the per-seed
   caches in 105 runs:
   - against the interval that assumes independence, it is 0.93-1.40 times as wide (0.98-1.16 on full held-out
     runs);
   - the textbook "conservative" bound (all cells perfectly correlated) is 1.3-4.5 times too wide;
   - a bound that treats cells inside a family as perfectly correlated and families as independent was never narrower
     than the exact interval, and is the one I recommend.
6. **The weights put numbers on the owner's question.** Per held-out set, the biggest weighted gains were:
   - twist play: V-b +0.07 to +0.09, V-e +0.04;
   - the 3-bet defence: +0.02 to +0.07, depending on how adapter cells are shared;
   - strong-table work: D3 +0.018, the strong route +0.011;
   - exploit-cell work: S6 +0.005, Z3 +0.004.

   Being very strong in a few areas pays only in proportion to how much of the night those areas are. Heads-up play
   against an adapter is a small share under any plausible mix.
7. **Most verdicts do not depend on the exact weights.** Across the plausible ranges below, only four held-out
   verdicts change sides: S5 on H14, G2 fixed on H6, D1 on H8 and Z on H7. K11, K17 and K18 would too, but the cap
   rejects them anyway.

## Recommendation: adopt it as a second route, narrowly; keep the current rule as the main route

Do not replace the current rule. Its strictness has found real side effects, and gating them out has not cost
measured value. A weighted rule nets small losses away without saying why, so it would have shipped those side
effects: the lowball leak, the dry c-bet, S5's top-heavy loss. One of them, the dry c-bet, is a bet that a later
exploiter also attacked.

Do not keep the current rule unchanged either. The case the owner describes has not happened yet, but it can:
- a broad gain with one loss that no gate separates, like K18 (strong tables up, exploiter 1 three-handed down);
- or a change accepted for one up cell whose net value cannot be seen, like Z3 and V-f.

The weighted score handles both. The second route:

1. **Route 2.** The current rule rejects a candidate for cells down. It is still accepted when, on a fresh held-out
   set with every stage run:
   - (a) the worst-case weighted lower bound (W-min below) is above zero, using the family-block interval, or the
     exact per-seed interval once `climb_accept` computes it;
   - (b) no cell breaks the cap;
   - (c) no judge is beyond noise down at batch end;
   - (d) each down cell is named in the log with what was found: the mechanism, or a replication that does not show
     it.

   Condition (d) keeps the side-effect alarm. The route is for losses that cannot be gated away, not for skipping the
   gate.
2. **What it would have changed in the past:** V-b on H1 and FIN with V-b on H2. V-b would have shipped about 35
   minutes sooner, with the lowball leak. The 3-bet defence would have shipped about 3 hours sooner (batch 3 instead of
   batch 4), together with the dry c-bet, which in fact never shipped. Nothing else. The route would rarely fire, which
   the data say is right.
3. **Print the weighted score on every run now, with no decision power.** That means W, its interval, W-min and the
   cap check, beside the current verdict. The per-seed samples are already in hand when the verdict is printed. The
   exact interval is about 30 lines of code and is about 1.7 times narrower than the block bound. A week of runs
   then compares the two rules prospectively, which the re-score below cannot do honestly.
4. **Commit the weights file before the next candidate,** and change it only by a `docs/decisions.md` addendum.
5. **Screens should run every stage, at full seeds, on the current base,** before a held-out set is spent. Four of
   the current rule's six screen-to-held-out failures were cells the screen never looked at properly.
6. **Read small accepts as small.** Under the current rule, a change that is up in one exploit cell and level
   elsewhere passes, and that is fine: nothing measured is lost. But such accepts (Z3, V-f) should not be read as the
   night score rising, nor as progress against the stop rule's spirit.

## The proposed rule, written so it can be fixed in advance

### Units: every cell in night points

| cell's table | factor | why |
|---|---|---|
| 8-max, 8..1 (night, guards, elite stage, variants, aware) | 1 | the night cell's own table |
| 8-max, 10/7/5/4/3/2/1/0 (night @brief, the 8-max exploit cells) | 0.7 | ratio of spreads, 7/10 |
| 8-max, 50/25/12/6/3/2/1/1 (night @th, top_heavy) | 1/7 | 7/49 |
| heads-up, 10/7 | 1/3 | the night has no heads-up tables: heads-up decides 8 against 7 on an 8..1 table |
| three-handed, 10/7/5 | 0.4 | it decides 8/7/6 (spread 2 of 5) |

### Weights: how likely the night's tables look like each family

The night has a twist (`docs/drills/climb/variants-ranked.md`: plain hold'em 2.5%, structure-only about 10%). Half
the weight goes to twist cells, half to plain hold'em cells:
- the plan's backlog says "strength under the variant is half the night";
- the likeliest families play ordinary hold'em after one twist step (about 48%: discard 20, bounty 11, buy 7, swap
  6, exposed 4), so play against the room is the other half.

A change gated to hold'em tables scores zero on the twist half. That halves its value, which is right on a night with
a twist, and does not change its verdict, since its twist cells are 0 ± 0.

| family | weight | plausible range | cells (share inside the family) |
|---|---|---|---|
| Ordinary room | 0.20 | 0.10-0.35 | night 0.40, night_hard 0.20, realistic 0.10, night @10/7/5 0.10, night @50/25/12 0.10, night with doubling blinds 0.10 |
| Strong tables | 0.15 | 0.05-0.30 | elite_night 0.25, elite 0.20, elite_b 0.20, top 0.15, mirror 0.10, mirror_b 0.10 |
| Adapters | 0.15 | 0.05-0.30 | 8-max, three-handed and heads-up a third each; inside a format, each adapter bot (exploiters 1-3, adapt1) a fixed quarter; a bot not run counts 0 ± 0 |
| Twist, twist-blind field | 0.20 | 0.10-0.30 | the 26 catalogued variants on realistic, by their probability in variants-ranked.md |
| Twist, twist-aware field | 0.30 | 0.15-0.45 | the aware cells, by the probability of their twist; cells on the same twist split it |

Why these numbers:
- **Ordinary room.** Pittsburgh's room is more likely `night_hard` than `night`: CMU has the most Castle Challenge
  entries, 364 of 3,740 (goal log 2026-11-01 20:50). Night keeps the largest share as the protocol's primary field,
  and night_hard has the next largest (0.20) for that reason. Even
  there, 70% of seats are one-hour builds, weak bots and decent chart bots. The payout and schedule guards stand for
  the add-on levers: a steeper table 35%, roughly doubling blinds 40%.
- **Strong tables.** 0.15 is 30% of the hold'em half. That is about the share of `night_hard` tables with three or
  more strong seats (30% strong seats gives 35%; four or more gives 13%). It is deliberately above the all-strong
  frequency, because the owner expects strong prepared bots and that is where top teams meet. Filler seats are random
  copies of submitted bots, so the room's mix is the submissions' mix. A copy of F at F's own table is rare, so the
  mirror tables (three copies of F) get the smallest shares. They stand for "a table of near-equals".
- **Adapters.** `docs/research/Edges against strong opponents.md` (finding 4) names the real threat as a bot that
  learns F inside one table. The blind adapt2 found the same heads-up folding leak as our exploiters. If one seat in
  twenty adapts like that, about 30% of tables hold one, hence 0.15, 30% of the hold'em half. Our exploiters are
  counters tuned for hours against a black box, which no team has on the night (the rules reset bot state per
  table). So exploit cells overstate adaptation, and the range runs down to 0.05.
- **Twist cells.** The twist-aware fields weigh more than the twist-blind ones because every bot on the night knows
  the twist (the owner, goal log 08:09). The twist-blind fields cover all 26 entries; aware cells exist for about 15.

### The test

Each family's interval is the weighted sum of its cells' half-widths (perfect correlation inside the family). The
families' intervals are combined as independent: the square root of the sum of squares. **Accept when the weighted
mean minus that interval is above zero.** This is the family-block bound. Measured against the exact per-seed
interval in 105 runs, it was never narrower: the exact interval was at most 0.95 of it, and typically it is 1.7 times
wider than the exact one. Once
`climb_accept` computes the exact interval, use that.

### Guards

- **Cap.** No cell may be beyond noise below -0.03 night points, i.e. its unit-converted upper bound below -0.03. That
  is about 0.5% of F's night score, about one accepted part's night gain (the strong route +0.025, D3 +0.032), and a
  third of batch 5's. Per payout scale, in the cell's own points:
  - 8..1: 0.03;
  - 10/7/5/4/3/2/1/0: 0.043;
  - 50/25/12/6/3/2/1/1 and top_heavy: 0.21 (of 100);
  - heads-up 10/7: 0.09;
  - three-handed 10/7/5: 0.075.
- **Judges.** No judge may be beyond noise down, measured once per batch as now. In the record no batch had one:
  batches 3, 4 and 5 were all level, with two cells up in batch 5.
- Timing as now.

### The worst-case variant (W-min)

The same test, with each family's weight anywhere in its plausible range (summing to 1), set as unfavourably to the
candidate as possible. The lower bound is concave in the weights, so the minimum sits at a corner of the ranges; the
script enumerates them. The twist half never drops below 0.25. W-min guards against weights fitted after the fact and
against a room that differs from the guess. Route 2 uses W-min.

### Missing cells

- A cell documented as identical by construction counts as 0 ± 0: the 22 twist variants for a change gated to hold'em
  tables, and plain hold'em for a variant-only change.
- Inside a family, the cells that ran share the family's weight. Adapters are the exception, with fixed per-bot
  shares (see the risks).
- A family that was not run is dropped and the others reweighted. That is allowed on a screen and never under
  route 2.

## Re-scoring

How to read the tables:
- *Current rule*: the protocol as `climb_accept` applies it, with addenda 6-8 and addendum 7's replicate for a lone
  variant cell.
- *W*: the base weights with the block bound and the cap. A *reject* with a positive bound means the cap failed.
- *W-min*: the worst-case weights.
- *Fixed adapter shares*: W-min with each adapter bot holding a quarter of its family.
- *Exact*: the lower bound with the exact per-seed interval. It is a diagnostic, available only where the cache
  exists.

### Held-out sets

| candidate | set | current rule | W ± half | W | W-min | W-min, fixed adapter shares | exact LB |
|---|---|---|---|---|---|---|---|
| V-b | H1 | replicate (lowball -0.062) | +0.0877 ± 0.0248 | accept | +0.0315 accept | +0.0315 accept | +0.0743 |
| V-b fixed | H2 | accept | +0.0718 ± 0.0244 | accept | +0.0237 accept | +0.0237 accept | +0.0588 |
| V-c | H3 | accept | +0.0079 ± 0.0033 | accept | +0.0021 accept | +0.0021 accept | +0.0053 |
| V-e | H10 | accept | +0.0434 ± 0.0142 | accept | +0.0146 accept | +0.0146 accept | +0.0383 |
| V-f | H15 | accept | +0.0022 ± 0.0063 | **reject** | -0.0061 reject | -0.0061 reject | -0.0001 |
| V-h | H18 | accept | +0.0043 ± 0.0009 | accept | +0.0017 accept | +0.0017 accept | +0.0034 |
| FIN | H1 | replicate (toss), passed on H2 | +0.0997 ± 0.0196 | accept | +0.0114 accept | -0.0047 reject | +0.0893 |
| FIN + V-b | H2 | replicate (bonus_card), then failed pooled with H3 | +0.1421 ± 0.0280 | **accept** | +0.0443 accept | +0.0281 accept | +0.1278 |
| 3-bet defence | H3 | accept | +0.0676 ± 0.0075 | accept | +0.0184 accept | +0.0024 accept | +0.0633 |
| Z | H7 | reject (aware short_deck -0.042) | +0.0129 ± 0.0204 | reject | -0.0196 reject | -0.0208 reject | +0.0029 |
| Z2 | H9 | reject (six variant cells, two aware) | +0.0066 ± 0.0149 | reject | -0.0203 reject | -0.0214 reject | -0.0013 |
| Z3 | H12 | accept | +0.0044 ± 0.0145 | **reject** | -0.0243 reject | -0.0254 reject | -0.0032 |
| S5 | H14 | reject (night_hard, realistic -0.005; top_heavy -0.247; antes -0.010) | +0.0047 ± 0.0038 | **accept** | -0.0027 reject | -0.0035 reject | +0.0029 |
| S6 | H16 | accept | +0.0050 ± 0.0020 | accept | +0.0008 accept | +0.0002 accept | +0.0039 |
| strong route (G2) | H4 | reject (auction, bounty, knockout -0.02 each) | +0.0033 ± 0.0072 | reject | -0.0088 reject | -0.0092 reject | -0.0010 |
| strong route fixed | H6 | accept | +0.0106 ± 0.0070 | accept | -0.0012 reject | -0.0020 reject | +0.0064 |
| C7 | H5 | reject (realistic -0.096, three structural variants -0.10 to -0.13) | +0.0190 ± 0.0177 | reject (cap: realistic, straddle) | -0.0287 reject | -0.0288 reject | +0.0088 |
| D1 | H8 | reject (night -0.045) | +0.0062 ± 0.0102 | reject | -0.0147 reject | -0.0149 reject | +0.0007 |
| D3 | H11 | accept | +0.0180 ± 0.0083 | accept | +0.0039 accept | +0.0037 accept | +0.0131 |
| batch 5 combined | H13 | accept | +0.0596 ± 0.0201 | accept | +0.0303 accept | +0.0273 accept | +0.0481 |

### Screens only (never held out)

| candidate | current rule | W ± half | W | W-min | W-min, fixed adapter shares | families not run |
|---|---|---|---|---|---|---|
| S2-A (first, loose 3-bet defence) | reject (night -0.037, three guards) | +0.1602 ± 0.0255 | **accept** | +0.0196 accept | -0.0218 reject | both twist families |
| S2-P20 | reject (two guards) | +0.1448 ± 0.0212 | **accept** | +0.0371 accept | +0.0038 accept | both twist families |
| S2 big-value size | reject (doubling blinds) | +0.0069 ± 0.0149 | reject | -0.0190 reject | -0.0207 reject | both twist families |
| C1 (size read, ungated) | reject (exploit heads-up and three-handed -0.28) | +0.0118 ± 0.0558 | reject (cap) | -0.0892 reject | -0.0679 reject | aware |
| K4 | replicate (fast_schedule) | +0.0075 ± 0.0133 | reject | -0.0123 reject | -0.0123 reject | - |
| K11 | reject (exploit_hu -0.713, exploit_3 -0.867) | +0.0010 ± 0.0143 | reject (cap) | -0.0431 reject | -0.0225 reject | - |
| K17 | reject (exploit_hu, exploit_3) | -0.0074 ± 0.0086 | reject (cap) | -0.0418 reject | -0.0196 reject | - |
| K18 | reject (exploit_3 -0.238) | +0.0045 ± 0.0073 | reject (cap, by 0.002) | -0.0143 reject | -0.0060 reject | - |
| K19 | replicate (fast_schedule -0.003) | +0.0019 ± 0.0039 | reject | -0.0052 reject | -0.0030 reject | - |
| T2 (trust weight) | accept, parked | -0.0001 ± 0.0130 | **reject** | -0.0240 reject | -0.0240 reject | - |
| T3 | reject (realistic, top_heavy, antes) | -0.0022 ± 0.0143 | reject | -0.0285 reject | -0.0262 reject | - |
| S15 (stab read, ungated) | reject (realistic, doubling) | -0.0005 ± 0.0073 | reject | -0.0142 reject | -0.0126 reject | - |
| S15b | reject (night at the bound, per the log) | -0.0000 ± 0.0054 | reject | -0.0095 reject | -0.0061 reject | - |
| S15c (now on H19) | accept | +0.0014 ± 0.0034 | **reject** | -0.0040 reject | -0.0031 reject | - |
| S17-c1 (stab size) | reject (realistic) | +0.0094 ± 0.0290 | reject | -0.0267 reject | -0.0267 reject | aware |

The S15 rows come from the tables in `s15-log.md`, since no JSON was written. V-h's screen comes from the goal log.

### Screen to held-out

| candidate | held-out set | current rule, screen -> held-out | W | W-min | weighted gain, screen -> held-out |
|---|---|---|---|---|---|
| V-b | H1 | reject -> replicate | reject (cap) -> accept | reject (cap) -> accept | +0.079 -> +0.088 |
| V-c | H3 | accept -> accept | accept -> accept | accept -> accept | +0.018 -> +0.008 |
| V-e | H10 | accept -> accept | accept -> accept | accept -> accept | +0.054 -> +0.043 |
| V-h | H18 | accept -> accept | accept -> accept | accept -> accept | +0.004 -> +0.004 |
| FIN | H1 | accept -> replicate, passed | accept -> accept | accept -> accept | +0.107 -> +0.100 |
| 3-bet defence | H3 | accept -> accept | accept -> accept | accept -> accept | +0.132 -> +0.068 |
| Z | H7 | accept -> **reject** | reject -> reject | reject -> reject | +0.029 -> +0.013 |
| Z2 (Z's screen) | H9 | accept -> **reject** | reject -> reject | reject -> reject | +0.029 -> +0.007 |
| Z3 (Z's screen) | H12 | accept -> accept | reject -> reject | reject -> reject | +0.020 -> +0.004 |
| S5 | H14 | accept -> **reject** | accept -> accept | accept -> **reject** | +0.012 -> +0.005 |
| S6 | H16 | accept -> accept | accept -> accept | accept -> accept | +0.005 -> +0.005 |
| strong route | H4 | accept -> **reject** | reject -> reject | reject -> reject | +0.010 -> +0.003 |
| C7 | H5 | accept -> **reject** | accept -> **reject** (cap) | reject -> reject | +0.030 -> +0.019 |
| D1 | H8 | accept -> **reject** | accept -> **reject** | accept -> **reject** | +0.023 -> +0.006 |
| D3 | H11 | accept -> accept | accept -> accept | accept -> accept | +0.019 -> +0.018 |

| rule | pairs agreeing | screen accepts | of which held |
|---|---|---|---|
| current | 9 of 15 | 14 | 8 |
| W | 12 of 15 | 10 | 8 |
| W-min | 12 of 15 | 9 | 7 |
| W-min, fixed adapter shares | 12 of 15 | 6 | 5 |

Some caveats on the pairs:
- Some pairs share a dial spec but not a code version or base. V-b's screen predates the fixed-limit and Omaha fix;
  the strong route's screen ran on batch 2, before V-b let rival 3's core reach bounty tables.
- Z2 and Z3 have no screen of their own; Z's stands in.
- Part of the weighted rule's better agreement is that it says no to tiny effects on both sets (Z, Z2, the strong
  route).

### Did the rescued ones hold up?

- **S5 (rescued by W, not by W-min).** Its weighted gain fell from +0.012 on the screen to +0.0047 on H14 and stayed
  positive (exact lower bound +0.003). Its four small losses were real: S13b's survey found the specialist playing
  heads-up against LooseAggroStudent, RivalBot, PushFoldBot and ChartTAG. The gated S6 kept the same weighted gain on
  H16 (+0.0050) with those cells identical. So it held up, but the gate made it free.
- **FIN, and FIN with V-b (rescued by W and W-min).** Exploit gains replicated on H1, H2 and (as the defence alone)
  H3. The dry c-bet's bonus_card loss also replicated in direction: -0.049, then -0.020, pooled -0.030 ± 0.025. On
  400 extra screen seeds the c-bet alone was -0.025, and exploiter 2, built against F with FIN, found that c-bet
  folds 78% to a check-raise. Held up on the weighted score; the loss was real and came with a leak.
- **V-b on H1 (rescued by every variant).** The lowball loss was real, since the dial reached lowball's mirrored
  classes. The fixed version was accepted on H2 35 minutes later.
- **D1 (screen accept under W).** It did not hold up. The strong-table gains shrank on H8 (elite +0.084 to +0.008)
  and night was -0.045. S12c traced the night loss to four night seats that c-bet 25-39%. D3 fixed it and gained on
  night.
- **C7 (screen accept under W).** It did not hold up. The cap caught realistic (-0.096) and straddle (-0.128). The
  read misread one-size and broken bettors.
- **Z2.** It would not have been sent: W rejects its proxy screen and H9.
- **K18, K11, T3.** None was rescued:
  - K11 and K17 lose 0.7 to 0.9 points heads-up and three-handed against exploiter 1;
  - K18 misses the cap by 0.002 (exploit_3 -0.238 ± 0.159);
  - T3's weighted gain is negative.

## Risks

- **Weights chosen after seeing the data.** I read the logs before writing the weights. I fixed them in
  `rule_fixed.json` before computing any re-score, then changed two things after seeing results; both are below.
  W-min, the committed file and a prospective comparison are the defence.
  - **The interval.** As first written it was the perfect-correlation bound. Measured against the exact per-seed
    interval it is 1.3-4.5 times too wide, which would make the weighted rule stricter than the current one: it
    rejects D3 on the screen and S5 and the strong route on held-out seeds. The replacement was chosen by calibration
    against the exact interval, not by which candidates pass.
  - **Fixed adapter shares.** The original rule shared the adapter family among the bots that ran. Early on only
    exploiter 1 existed, so a change tuned against it took the whole family: S2-A shows +0.16, the defence +0.13 on
    the screen. With fixed quarters those become +0.03 each. This change turns FIN on H1 into a reject under W-min,
    and S5 on H14 into a reject even under the base weights.
- **Field mix.** The adapter weight is the least grounded: nobody knows how many bots on the night learn within a
  table, and our exploiters overstate it. Pittsburgh's strength is a guess too. Within the ranges, S5 on H14, the
  strong route on H6, D1 on H8 and Z on H7 change sides.
- **Short-handed units.** The heads-up and three-handed factors assume the night pays 8..1. Under the 10/7/5 table or
  a steep one, heads-up decides more. At a mix of 30% 8..1, 35% brief and 35% steep, both factors rise to about
  0.75. That raises every exploit-aimed change (S5's W becomes +0.011 on H14) but turns no verdict above, Z3 and V-f
  included.
- **Correlated cells.** Measured, not assumed: across fields the paired differences are nearly independent. The block
  bound covered the exact interval in all 105 runs, but a future field that shares seats with another (a new night
  variant) could correlate more, so keep checking `exact / block` in the printed output.
- **The cap's shape.** The cap tests the upper bound, so a noisy cell can pass with a point loss beyond the cap. C7's
  antes cell did: -0.103 ± 0.090.
- **What the weighted score cannot see.** Hold'em cells cannot say whether a gain survives the twist. Twist cells
  measure the twist only against the realistic and aware fields, never against strong or adaptive bots under a
  twist.
- **Small sample.** There are 15 pairs, several on older bases. The agreement counts are anecdotes with a direction,
  not a measured error rate.
- **Losing the alarm.** Thirteen of fourteen small losses were real side effects. Any rule that nets them silently
  will ship some. Route 2's condition (d), naming the down cell and what was found, is there for that.
