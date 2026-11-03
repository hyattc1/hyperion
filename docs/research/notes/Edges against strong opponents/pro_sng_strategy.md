# Edges against strong, prepared opponents: what pro SNG / MTT / heads-up players do differently

Notes for the Sequoia "No Limit" 8-max SNG bot: 2,000 chips, 10/20 blinds rising every 25 hands, a 200-hand cap, points by finish position, ICM for survivors at the cap, 1 ms per decision in Python, opponents reset every table. Compiled 2026-11-03.

**Tags.** [solver] = solver, HRC/ICM-calculator or nodelock output, or exact game math published by a training site. [computed] = arithmetic or ICM/equity computation done for these notes (method stated; reproduce with `hyperion/core/icm.py` and `tables/hu_matrix.json`). [math] = closed-form arithmetic. [expert] = coach or pro opinion. [data] = population/mass-data statistics (human pools unless stated). [paper] = peer-reviewed or arXiv. [book] = book reference. [anecdote] = forum post, single hand or single report.

**Read these caveats first.**
- Almost every published solver number is either 100 bb cash (no ante) or MTT (with a 1 bb big-blind ante). This format has **no ante** as far as the rules say, so MTT opening and defending ranges are too loose as written (e.g. BTN opens 42% in cash vs 53% in an MTT at 6-max 100 bb [solver], [GTO Wizard, tournaments vs cash](https://blog.gtowizard.com/poker-strategies-tournaments-vs-cash-games/)).
- Population data are from human online pools. Strong bots will not share human leaks such as river under-bluffing. Treat those as priors to test, not facts.
- The session's shared web-search budget ran out partway through, so some planned lookups did not happen. They are listed in the gaps section at the end. Book claims marked "(not re-checked)" are from memory of the book and were not verified in this session.
- Classics are dated: Harrington on Hold'em II (2005), The Mathematics of Poker (2006), Kill Everyone (2007; 2nd ed. 2009), Moshman's Sit 'n Go Strategy (2007) and Heads-Up NLHE (2008), Applications of NLHE (2013). Their ICM and push/fold maths still holds. Their population reads predate solvers.

## Summary: what the best players do differently against strong fields
1. **They make others call and avoid calling themselves.** Under ICM a bad call costs ≈4× a bad shove (§1.6). Pushing ranges are very sensitive to how tight the callers are: removing one hand from a caller's range widened a correct push from 17.5% to 27% (§1.6). In this format, with points for every place, a medium stack covered by a bigger one needs 65-77% equity to call, so the cover can jam close to any two into ICM-correct callers (§0).
2. **They read the payout shape before anything else.** Flat payouts put the bubble at hand 1: 67-70% equity is needed to stack off on the first hand under 10/7/5/4/3/2/1/0 or linear points, against 56% for 50/30/20 (§0). The same chip lead is worth far more pressure in a small field with flat pay (§1.2, §1.4).
3. **Near-equilibrium games are won preflop and on the blinds.** Pluribus never adapted and beat elite pros. Top Spin players call preflop the "most underestimated street" and win only ≈10% of a 25 bb stack per game. The main extra edge is opponents' fold/call width at the 10-25 bb jam and re-jam nodes (§2.4, §3.3, §4.1).
4. **They deviate small, late and only where the opponent deviates.** Best responses flip on tiny frequency changes and gain little. Within 200 hands only preflop stats are estimable. The bot literature (ACPC 2012/2016, DBR, DBBR, safe exploitation) says: play equilibrium against strong agents and exploit with what you have already won (§7).
5. **They simplify sizing.** One size per node costs ≈0.01-0.3% of the pot and hides tells. Sizes drop as stacks shorten (10-33% c-bets at 20-40 bb; turn ≈50%, overbets gone below ≈40 bb) (§5).
6. **Multiway, they stop bluffing, defend per player at 1 − α^(1/n), and squeeze linear** (§6).

## 0. What this format does to the standard advice (computed; read first)

The pros' ICM advice was built for 50/30/20 SNGs and MTT final tables. This format pays points for every place (hyperion assumes 10/7/5/4/3/2/1/0, with linear 8..1 and top-heavy tables as robustness checks), and that changes where the pressure is.

- **The bubble is at hand 1.** Equity needed to call an all-in from an equal stack, with blinds ignored, by players left (8 → 2) [computed, Malmuth-Harville]:

  | Points table | 8 | 7 | 6 | 5 | 4 | 3 | 2 |
  |---|---|---|---|---|---|---|---|
  | 10/7/5/4/3/2/1/0 | **67%** | 66% | 64% | 62% | 60% | 58% | 50% |
  | linear 8..1 | **70%** | 69% | 68% | 67% | 64% | 60% | 50% |
  | 50/30/20 | 56% | 57% | 58% | 61% | **65%** | 57% | 50% |
  | 65/35 | 53% | 53% | 54% | 55% | 57% | **61%** | 50% |
  | winner-take-all | 50% | 50% | 50% | 50% | 50% | 50% | 50% |

  - Calibration: PokerStrategy's ICM tables give 55% (BF 1.2) for a 50/30/20 9-max at the start and **65-67% (BF 1.9) on a 9-max bubble with four equal stacks** [solver/ICM calc], [PokerStrategy, Bubble factor in SnG formats](https://www.pokerstrategy.com/strategy/sit-and-go/bubble-factor-sng-forms/). Under 10/7/5/4/3/2/1/0, every hand of the opening levels is as tight as a classic SNG bubble.
  - The pressure falls with each bust under flat tables and rises toward the bubble under top-heavy ones. Heads-up is pure chip-EV under every table, because two-player ICM is linear.
- **Medium stacks covered by a bigger stack are squeezed hardest.** Six left at 5000/3500/3000/2000/1500/1000 (10/7/5 table): 3500 calling 5000 needs 70%; 5000 calling 3500 needs 61%; 3000 calling 3500 needs 68%; 5000 calling 1000 needs 52%; 1000 calling 5000 needs 61%. Linear 8..1 is harsher (77/66/74/53/63%). [computed] This matches the published pattern: in an 18-man SNG near the bubble the second-biggest stack had the highest risk premium (+25.9%) against the leader [solver], [PokerStrategy SNG 2380](https://www.pokerstrategy.com/strategy/sit-and-go/2380/1/).
- **Small-blind vs big-blind push/fold under each table** (six left as above, blinds 75/150 = level 5 of the repo's assumed schedule, jam-or-fold, everyone else folded, damped fictitious play on `tables/hu_matrix.json`, no card removal, no limp/min-raise option) [computed]:

  | Spot | chip-EV jam / call | 10/7/5/4/3/2/1/0 | linear 8..1 | 50/30/20 |
  |---|---|---|---|---|
  | Leader SB 5000 vs BB 3000 (20 bb eff) | 40% / 21% | **100% / 3%** | 100% / 2% | 84% / 10% |
  | SB 3000 vs leader BB 5000 (20 bb) | 40% / 21% | 31% / 7% | 38% / 5% | 40% / 10% |
  | SB 2000 vs covering BB 3500 (13 bb) | 49% / 30% | 47% / 12% | 53% / 10% | 50% / 19% |
  | Covering SB 3500 vs BB 2000 (13 bb) | 49% / 30% | **100% / 9%** | 100% / 3% | 69% / 19% |
  | Four left, SB 7000 vs BB 4000 (26.7 bb) | 34% / 16% | 97% / 8% | 100% / 3% | 100% / 3% |
  | Three left, equal (35 bb) | 27% / 12% | 33% / 6% | 32% / 6% | 30% / 7% |

  - The chip-EV column agrees with heads-up Nash (the repo's own solve: 20 bb SB jam 39.9% / BB call 21.7%; 10 bb 57.8% / 37.6%; `tables/pushfold_hu.json`).
- **The best response flips with the caller's width.** For the leader SB 5000 vs BB 3000 (10/7/5 table), the best jam width and the points gained per SB hand dealt versus always folding the SB [computed]:
  - BB calls 3% (ICM-correct): jam 100%, **+0.070 points**. BB calls 6%: jam 100%, +0.041.
  - BB calls 10%: jam 81%, +0.016. BB calls 15%: jam 15%. BB calls 21% (a chip-EV caller): jam 13%, +0.010.
  - Jamming any two into a chip-EV caller *loses* 0.057 points per hand. The caller also does worse: −0.041 points against folding every hand, versus +0.016 for the correct 3% call. Both players lose, and the rest of the table collects the difference, as Gilbert's theorem says.
  - Practical rule: the covering stack's any-two pressure is the biggest edge in this format, but only against opponents who call like ICM players. Against chip-EV callers, jam tighter than chip-EV.
- **Early 100 bb stack-offs.** Hand 1: we 3-bet to 7 bb and face a 4-bet jam. Calling needs 46% (chip-EV), **64% (10/7/5)**, 67% (linear) or 52% (50/30/20). Against a QQ+/AK jam range only AA calls under 10/7/5 or linear (KK has 59%); KK calls under 50/30/20. Against TT+/AQ+/A5s, AA and KK call under 10/7/5, and only AA under linear. [computed; ICM ignores skill edges and the future game, so real thresholds are a little lower]
- **Laddering pays.** With six left, when the 1500 stack busts, the 1000 stack gains +0.58 points (10/7/5 table; first-to-sixth spread is 8), +0.57 (linear), +0.70 of 50 (50/30/20), and 0 under winner-take-all. [computed]
- **The 200-hand cap is a hard horizon, and nothing published covers it.** Several searches found no strategy for tournaments that end at a fixed hand count and settle by ICM. The nearest analogues are PokerStars Time Tourneys (2011; the pool was split by chip share when time ran out, so there was no ICM pressure; PokerNews, search snippet only) and ICMIZER's Fifty50 write-up, which ends at a player count ([ICMIZER](https://www.icmizer.com/en/blog/analyzing-fifty50-poker-tournaments-with-icm-calculator/)).
  - Inference: at the cap, Malmuth-Harville ICM *is* the payoff, so ICM's known biases (blinds, position, future skill edge; §1.8) shrink to zero as the cap nears.
  - Cost of folding every hand to the cap under the repo's schedule (10/20 … 200/400) is about (200 − h) × (sb + bb) / n chips [computed]. From hand 176: 3,750 chips with 4 alive, 5,000 with 3. From hand 186: 2,250 / 3,000. From hand 191: 1,500 / 2,000. From hand 196: 750 / 1,000.
  - Any stack above that can ladder to the cap risk-free. That makes covered players fold more and the cover's steals freer as the cap nears.
  - In hyperion's own sim, about half of tables end at the cap with two or three survivors, and rival 1's lowest-bust-rate strategy "folds its way to the cap when it can afford the blinds" (`docs/decisions.md`).
- **No antes changes the steal maths** [math; zero-equity bluff, folds needed]:
  - BTN open 2.0 / 2.2 / 2.5 bb: 57 / 59 / 62% folds needed, against 44% for a 2 bb open with a 1 bb big-blind ante.
  - SB open to 2.0 / 2.5 / 3.0 bb vs the BB: 50 / 57 / 62%.
  - SB open-jam of 5 / 10 / 15 / 20 bb: 75 / 86 / 91 / 93% before counting equity when called.
  - BB re-jam over a 2 bb BTN open at 10 / 15 / 20 / 25 bb: 72 / 80 / 84 / 87%.
  - With 1.5 bb in the middle instead of 2.5 bb, steals and re-steals earn less than MTT sims show, and the ranges in those sims (e.g. BTN 53% at 100 bb) should not be copied.

## 1. ICM pressure: how strong players use it and exploit it

### 1.1 Definitions and anchor numbers
- **Bubble factor** BF = (EV now − EV if you lose) / (EV if you win − EV now). Equity needed for a pure stack-off = BF / (BF + 1). Example: a 4000-chip BB has 29.23% of the pool now, 40.16% if he wins and 0 if he loses, so BF = 2.67 and he needs ≈73%, i.e. calls 99+ only. [solver] [ICMIZER, bubble factor](https://blog.icmizer.com/bubble-factor-advanced-fgs-better-limps-and-more/)
- **Risk premium** (RP) = extra equity over chip-EV pot odds. It is specific to each opponent pair.
  - Negreanu's WSOP spot: 28 bb in the BB against a 57 bb chip leader, BF 2.8, RP +23.7%. The solver calls ≈2% (TT+), and AK folds. [solver] [PokerNews/GTO Wizard](https://www.pokernews.com/strategy/daniel-negreanu-tens-gto-wizard-icm-analysis-52492.htm)
  - GTO Wizard toy example: 37.5% chip-EV vs ≈47% ICM. The article calls this a 12% premium; its numbers give ≈9.5 points. [solver] [GTO Wizard, ICM basics](https://blog.gtowizard.com/icm-basics/)
- *Kill Everyone* (Nelson, Streib, Heston, 2007; 2nd ed. 2009) popularised the bubble factor. Its Sunday Million chart peaks at ≈1.6 on the money bubble and ≈1.7 before the final table, and is 1.0 heads-up. Seen secondhand via Dara O'Kearney. [book/expert] [PokerStrategy (O'Kearney)](https://www.pokerstrategy.com/?p=35846)
- **Gilbert (2009), proved:** under ICM a fair two-player bet lowers both players' expected prize and raises every uninvolved player's (not true in general for 3+-way pots). Henke's WPT final-table test found ICM modestly **overestimates small stacks and underestimates big stacks**. [paper] [Gilbert, arXiv:0911.3100](https://ar5iv.arxiv.org/html/0911.3100)

### 1.2 Who is squeezed: covering, medium and short stacks
- RP is higher against stacks that cover you and lower against stacks you cover; every stack except the biggest tightens near the bubble. [expert] [GTO Wizard, ICM basics](https://blog.gtowizard.com/icm-basics/)
- Money bubble, 1,000-runner MTT [solver] ([GTO Wizard, money bubble vs FT bubble](https://blog.gtowizard.com/money-bubble-vs-final-table-bubble/)):
  - The short BTN has BF 2.06 against everyone (+17.3% equity). The medium SB has 1.8 when covered but 1.12 against the shorter BTN. The big BB has 1.04.
  - At the final-table bubble the short stack peaks at only 1.18, while big against second-big is 1.44 (+9.1%): pressure moves from short stacks to medium and big ones.
  - Smaller fields raise big-stack pressure: the leader's peak BF is 1.36 with 1,000 runners and 1.62 with 200; the middle stack's is 1.70 and 1.83.
  - On the money bubble, doubling up adds +65% relative equity for the big stack and only +33% for the short.
- 18-man SNG near the bubble (40/30/20/10) [solver] ([PokerStrategy 2380](https://www.pokerstrategy.com/strategy/sit-and-go/2380/1/), [2352](https://www.pokerstrategy.com/strategy/sit-and-go/2352/1/)):
  - The second-biggest stack (7000) has RP **25.9%** against the 10000 leader; 5000 vs leader 23.1%; the shortest (2000) only 12.8%.
  - The leader's own RP is 14.6% against 7000 and 2.9% against 2000.
- Final tables [solver]:
  - A 30 bb CO facing a 63 bb covering BTN has RP 18.1% and opens 26.1%; a 27 bb CO who covers the BTN opens 30.5%. [GTO Wizard, OOP vs covering stack](https://blog.gtowizard.com/icm-survival-guide-how-to-play-oop-vs-a-covering-stack-at-the-final-table/)
  - A 35 bb CO vs a 75 bb leader in the SB has RP 17.8%, while the leader's RP vs the CO is 6.6%. The CO opens 26% against 37% under chip-EV. [GTO Wizard, IP vs chip leader](https://blog.gtowizard.com/icm-strategy-playing-ip-against-the-chip-leader-on-the-final-table/)
- Postflop, medium-vs-medium and short-vs-short pots carry the most ICM pressure; big-vs-short plays closest to chip-EV. [solver] [GTO Wizard, ICM postflop](https://blog.gtowizard.com/how-icm-impacts-postflop-strategy/)
- Mega-stack toy model (9-man SNG, 50/30/20, push/fold) [solver] ([GTO Wizard, when to ladder](https://blog.gtowizard.com/when-to-ladder-in-tournaments/)):
  - At 40 bb, the CO's opponents call only JJ+ (AK folds).
  - At 400 bb, the CO shoves ≈2× wider, the BB's BF against it roughly doubles, and the BB needs KK+.
  - Add a 2 bb micro-stack in the SB and the BB's BF becomes **7.71 (≈88%)**: it folds AA.

### 1.3 Big-stack pressure (the main ICM edge)
- ICMIZER, 90-man SNG bubble, 14 left; chip leader 44 bb in the CO, next stack 25 bb [solver] ([ICMIZER, cost of not being aggressive](https://blog.icmizer.com/high-cost-of-not-being-aggressive-enough/)):
  - The leader shoves almost any two (AA +$4.29, 32s +$0.12, 32o −$0.18).
  - The 25 bb SB can call only the best pairs and AKs (AKo −$1.82, AJs −$2.09).
  - The same table inside a 300-man MTT shoves much narrower. The leader's calling BF is 1.2 (88+, AJ+); the second stack's is 1.6 (99+, AJ+, ATs).
- In the Negreanu spot, the chip-leader SB never folds or limps: 71.7% shove, 28.3% raise to 3.5 bb. [solver] (PokerNews link above)
- Carlos Welch on SNG bubbles (2017) [expert] ([PokerNews](https://www.pokernews.com/strategy/10-tips-for-sit-go-success-on-the-money-bubble-27891.htm)):
  - The biggest stack shoves "extremely wider than Nash on everyone"; medium stacks shove "moderately wider than Nash" except into the biggest stack.
  - Everyone should "call tighter than Nash … regardless of your stack size".
- Covering players also lead and bet more postflop. Covered players check back, size down and avoid big pots. See §1.7.

### 1.4 The short-stack ladder
- Micro-stack toy model (SB 2 bb): BTN and BB call only AA (KK folds), and the BB cashes 96.5% of the time: "play tight, secure the min-cash, then play for the win". [solver] (when-to-ladder link above)
- **Flat payouts make laddering worth more.** At a 30 bb final table, average RP is 17.2% with flat payouts vs 11.5% top-heavy. HJ check-back frequency is 82% (flat) / 66% (top-heavy) / 15% (chip-EV). [solver] [GTO Wizard, payout structures and postflop](https://blog.gtowizard.com/how-payout-structures-reshape-postflop-strategy/)
- 6-max SNG, short SB with an equal short BB facing a big stack's 97% BTN shove: the SB's profitable call is only 5% (AQo loses). Beating the other short stack raises equity from 22.45% to 43.33%; beating the big stack only to 33.23%. [solver] [ICMIZER, short stack on the bubble](https://www.icmizer.com/en/blog/playing-short-stack-on-bubble/)
- Dara O'Kearney: it is "100% correct to pass marginally profitable spots in chip terms" when two others are likely to clash, but blinding away to ladder is a mistake. [expert] [PokerStrategy](https://www.pokerstrategy.com/?p=35846)
- Countervailing force: per-hand profit is almost always negative in the BB, and taking the BB costs several times the profit of a correct UTG push. [solver/expert] (2380 link above)

### 1.5 Calling ranges against shoves at 4-15 bb
- 9-max SNG, 4 left: BB 4400 facing a 5100 SB shove needs 45.5% by chip-EV and 69.7% by ICM, i.e. 99+ against a random hand. [solver, 2011] [CardPlayer (Hilger)](https://www.cardplayer.com/?p=1034923)
- 50/30/20, 4 left: BB 3000 facing SB 5000 needs 44% on pot odds and ≈64% by ICM. Against an 80% shove range that is 88+/AJs+/AQo+ (≈6% of hands). [solver] [PokerListings](https://www.pokerlistings.com/poker-strategies/tournament-nl-holdem/how-to-play-most-profitably-on-the-bubble-with-the-help-of-icm)
- Under 10 bb on the bubble [solver] ([GTO Wizard, under 10 bb part 2](https://blog.gtowizard.com/playing-under-10bb-part-2-icm/)):
  - An 8 bb LJ facing an 11 bb UTG shove needs ≈65%. An 8 bb HJ shoves 12% under ICM vs 30% under chip-EV.
  - RP is 18.9% (8 bb HJ) and 19.2% (4 bb CO) on the bubble, but 8.3% and 1.6% for UTG at a final table.
- 9-max, 3 paid, facing an almost-any-two push: the BB (largest, BF 2.7) calls the top 2.7%, the SB 3.5%, the BTN 9.4%. [solver] (ICMIZER bubble-factor link above)

### 1.6 Exploiting opponents who ignore ICM, or over-respect it
- **Callers too tight → push much wider** [solver]:
  - 18-man SNG, 6 left: removing TT alone (0.45% of hands) from the BB's calling range widens the HJ's push from 17.5% to 27%. [ICMIZER, difficult SNG spots](https://icmizer.com/en/blog/analysis-of-difficult-sng-push-fold-spots)
  - A BTN raising 40% instead of 34% and overcalling only JJ+ instead of 4.2% widens the SB's best-response push from 17% to 50%; QJs goes from +0.24% to +0.45% of the pool. [ICMIZER, editing ranges](https://blog.icmizer.com/perfect-poker-strategy-with-icmizer-editing-ranges-advanced-guide/)
  - Negreanu nodelock: a BB calling only KK+ moves the SB shove from 71.7% to 81.8%; a BB calling 4.2% (instead of ≈2%) drops it to 43.8%, with the raise going to 56.1%. (PokerNews link above)
  - An opponent who 3-bets 9% less than optimal lets the BTN open >45% instead of ≈27% (GTO Wizard post on X, search snippet only). [solver, unverified]
- **Shovers too tight → call tighter:** if the SB's push range tightens from 53% to 30%, the BB's call falls from 22% to 11% (A7s goes from +0.98% to −0.22% of the pool). [solver] (editing-ranges link above)
- **Callers too wide (ICM-ignorers) → shove tighter and more value-heavy; never call wider against their wide shoves** [solver/expert]:
  - Value-heavy shoves against a calling station beat the GTO line ($7,323-7,979 vs $7,247).
  - The maximum bluffing exploit against a nit needs the read to be right 95.9% of the time. "Lean towards lower-variance exploits" under heavy ICM, because equity leaks to the players who fold.
  - Source: [GTO Wizard, limitations of Nash in ICM spots](https://blog.gtowizard.com/the-limitations-of-nash-equilibrium-in-icm-spots/). Knowing a shover pushes almost everything still does not let you call wider (PokerListings link above).
  - This format confirms it (§0): jamming any two into a 21% chip-EV caller loses points.
- **What ignoring ICM costs** [solver]:
  - In push/fold sims (200 players, 7 bb average), playing chip-EV until the final table lost **13% of the buy-in**. ICM becomes significant at 50-37.5% of the field left, "roughly three times the bubble". [GTO Wizard, when ICM becomes significant](https://blog.gtowizard.com/when-does-icm-become-significant-in-mtts/)
  - Chip-EV postflop play loses >10% of the buy-in per flop on the bubble or at a final table, and >30% in 3-bet pots. [GTO Wizard, theoretical breakthroughs in ICM](https://blog.gtowizard.com/theoretical-breakthroughs-in-icm/)
  - Chip-EV *preflop* ranges are a bigger error than chip-EV postflop: when the BB uses a chip-EV range, UTG gains 0.51 bb and the BB loses 0.52 bb in one flop node. [GTO Wizard, chip-EV when ICM matters](https://blog.gtowizard.com/what-happens-when-playing-chip-ev-and-icm-is-significant/)
  - Near the bubble, a bad call (ATs vs AJs) costs 0.41% of table equity against 0.1% for a bad shove (≈4×). Ranking: bad calls > bad bets > bad shoves/folds. [GTO Wizard, which mistakes cost most](https://blog.gtowizard.com/understanding-which-mistakes-cost-you-the-most-money/)

### 1.7 Postflop ICM (GTO Wizard postflop ICM, single spots written up by Barry Carter)
- 30 bb UTG vs BB on J♥9♦8♦, six left, BB 60 bb covering. Chip-EV: BB checks 100% and UTG c-bets 100% when checked to. ICM: UTG bets **under half the time** ("C-bet half as much"), and BB leads ≈9% with made hands and draws; UTG rarely raises or folds against the lead. [solver] [PokerStrategy, lead more when ICM is significant](https://www.pokerstrategy.com/news/content/You-should-lead-more-when-ICM-is-signifcant_132406/)
- 25 bb HJ vs BB on AQ9r, bubble, BB with a 2:1 chip lead [solver, toy game] ([PokerStrategy, ICM changes postflop](https://www.pokerstrategy.com/?p=37402)):
  - BB leads ≈15% (chip-EV ≈0%) despite a 66% range disadvantage. The covered HJ bets much less when checked to; big bets nearly vanish, and KK almost never bets.
  - Facing a check-raise, HJ folds 42% (chip-EV 33%) and shoves some TPTK.
  - Recap: the covering player is more aggressive and leads more; the covered player checks back more; sizes drop; low-variance lines; "fold equity is the most important form of equity".
- Final-table bubble, UTG 40 bb vs BB 120 bb on 8♣5♠2♦ [solver + author estimate] ([PokerStrategy, postflop ICM analysis](https://www.pokerstrategy.com/?p=37591)):
  - BB leads ≈24% (chip-EV 0%). UTG's main size falls to 33% pot.
  - Node-locking UTG to overbet its chip-EV range: BB's fold frequency drops from ≈60% to ≈22% and its raise frequency rises from ≈10% to ≈53%. The author estimates the covered player's chip-EV overbetting as a ≈2 bb/100 leak.
- MTT c-bets under ICM (25% of field left): 50% bets on 654r shrink to 20%, and near the bubble the BTN range-bets small. [solver] [GTO Wizard, bullying the blinds](https://blog.gtowizard.com/bullying-the-blinds-with-continuation-bets/)

### 1.8 ICM model bias and FGS
- Malmuth-Harville overvalues short stacks and undervalues big ones. Ben Roberts' model (6-max 65/35, 3 left): a 500-chip BB facing a 1500 shove calls 57.8% under Malmuth-Harville vs 72.5% under Roberts; the reverse spot is 78.9% vs 69.5%. [model, 2012] [ICMIZER, Roberts model](https://icmizer.com/en/blog/ben-roberts-icm-model)
- Kim (2025; 2,500 snapshots, 33,478 players): ICM underestimates the top stack quartile by +0.56 points of the pool (p = 0.004) and overestimates the bottom quartile by −0.44 (p < 0.001); medium stacks are not significant. [data/paper] [arXiv:2506.00180](https://arxiv.org/html/2506.00180v2)
- Harville and Roberts each lose ≈1% of the buy-in against the exact equilibrium, and ICM predicted results within $0.39 per player in simulation. [solver] (GTO Wizard when-ICM-significant link above)
- ICM ignores blinds, position and blind rotation. With 2 bb stacks, ICM says UTG pushes 6% and SB 39%; future game simulation (FGS) reverses this to UTG 45%, SB 12%. FGS matters with 6 or fewer players and under 10 bb (especially ≈5 bb). [solver] [ICMIZER, FGS](https://icmizer.com/en/blog/icm-to-fgs-future-game-simulations)
- FGS values 3-12 bb stacks above ICM; a 10 bb UTG adds 22, T8s, 98s, A6s and A3s to its push range compared with chip-EV. [solver] (2380 link above)
- Inference for this format: as the cap nears, use pure ICM (it is the payoff). Earlier, shade toward big stacks (FGS and empirical bias), and the covering stack's future edge is worth more than ICM says.

## 2. Short-handed and heads-up endgames

ICM context for this format: three-handed calls need 57-60% with equal stacks; heads-up is chip-EV under every points table (§0). Endgame specialists therefore play heads-up as a pure chip game. In hyperion's sim about half of tables end at the cap with two or three survivors, so 3-handed play matters as much as heads-up.

### 2.1 Heads-up SB first in: limp, min-raise or jam, by depth
- Poker Academy heads-up charts (chip-EV, **0.25 bb ante**, solver not named) [solver] ([poker.academy](https://poker.academy/blog/post/how-to-play-heads-up-poker-in-tournaments)):

  | Depth | Limp | Raise | Jam | Fold |
  |---|---|---|---|---|
  | 8 bb | n/a | n/a | 48.7% | 21.2% |
  | 10 bb | 61.1% | none in tree | 28.8% | 10.1% |
  | 15 bb | 82.7% | starts here | | |
  | 20 bb | 73.0% | 24.9% (to 2 bb) | 1.1% | 0.9% |
  | 40 bb | 43.7% | 53.1% (to 2.2 bb) | 0 | 3.2% |
  | 60 bb | 34.6% | 61.5% (to 2.3 bb) | 0 | n/a |

  - The SB never jams first-in from 25 bb up. Limping dominates to ≈20-30 bb, and raising overtakes it between 20 and 40 bb.
  - The ante widens these slightly; with no ante, expect a little more folding.
- GTO Wizard, 10 bb heads-up: the SB plays ≈88% of hands, ≈22% as jams. At 20 bb, hands with ≥70% equity mostly min-raise, 50-70% mix limp and raise, and <50% mostly limp. [solver] [GTO Wizard, isolating limpers](https://blog.gtowizard.com/isolating_limpers_in_short_stack_hu/)
- At 8 bb heads-up in Spins, the SB limps polarised: strongest and weakest hands limp, the middle jams. [solver] [GTO Wizard, top 5 Spin mistakes](https://blog.gtowizard.com/top-5-mistakes-in-spin-gos/)
- At 14 bb chip-EV the button "almost never min-raises" (it limps), but **the EV gain from limping over simpler strategies is minimal at equilibrium**. [solver] [GTO Wizard, BB in limped pots](https://blog.gtowizard.com/disciplining-big-blind-in-limped-pots/)
- Min-raise vs jam: AA UTG 8-handed at 10 bb is worth 5.79 bb min-raised vs 5.51 bb jammed (−0.28 bb). With a min-raise option the button "is able to open over 2x more hands". [solver, HRC] [Upswing push/fold charts](https://upswingpoker.com/push-fold-tournament-strategy-charts/)
- Human heads-up SNG advice (Yaniv, Upswing 2017) [expert] ([Upswing HUSNG](https://upswingpoker.com/husng-strategy-heads-sit-go-explanation/)):
  - 50 bb+: open ≥80% (many open 90-100%), mostly 2.5×.
  - Below ≈30 bb: limping is fine and min-raise is the default size.
  - 11-24 bb: mix min-raise and limp. 7-11 bb: Nash push/fold plus some limps.

### 2.2 Heads-up BB: against limps, min-raises and jams
- Facing a limp at 10 bb: check 49.5%, raise to 2.5 bb 15.2%, jam 35.2%. At 60 bb+ no jams; raise 34-37%. [solver] (poker.academy link above)
- Iso sizes at 20 bb are 3 bb / 6 bb / all-in (2.5 / 4 / all-in at 10 bb). **Facing an all-in iso at 20 bb the SB folds ≈82%.** Iso frequency rises, with more all-in isos, as stacks shrink. [solver] (GTO Wizard isolating-limpers link above)
- Exploits in the same article [solver]:
  - An SB that jams too many 50-60%-equity hands at 10 bb → the BB isolates ≈11% more, mostly with the non-all-in size.
  - A capped (recreational) limp range → isolate more, mostly all-in.
  - An SB that never min-raises at 16 bb has stronger limps → isolate less and smaller.
- 50 bb, 0.12 bb ante: the SB folds only 4% and raises 64%; the BB raises 34% over a limp, to 6 bb. If the SB folds 8% instead of 4%, the BB's raise-over-limp rises from 34% to 48% and its size drops from 6 bb to 4 bb. If the SB opens 72% instead of 64% (no longer limping its best hands), the BB attacks limps more often and smaller. [solver] [GTO Wizard, exploiting SB preflop mistakes](https://blog.gtowizard.com/heads-up-exploiting-sbs-preflop-mistakes/)
- Facing a min-raise [solver] (poker.academy link above):
  - 20 bb vs a 2 bb open: fold 19.0%, jam 18.5%, small 3-bet 9.4%, call ≈53%.
  - 40 bb vs a 2.2 bb open: call 56.5%, 3-bet to 6.9 bb 17.6%, jam 6.0%, fold 19.9%. At 100 bb fold 29.7%.
  - Total defence is 70-81% at every depth. Calling a 20 bb jam: 24.6%; a 10 bb jam: 40.5% (with ante).
- Upswing (2017), 50 bb+: defend ≥85% vs a min-raise with ≈20% 3-bets; ≈60% vs 3× with ≈22% 3-bets. [expert] (Upswing HUSNG link above)

### 2.3 Three-handed (Spin & Go-like: 25 bb, no antes)
- Button: 38.5% played, no limps, 2 bb opens. Copying the MTT habit of ≈48% with limps (built for antes) is a leak without antes. [solver] [GTO Wizard, top 5 Spin mistakes](https://blog.gtowizard.com/top-5-mistakes-in-spin-gos/)
- Without antes the button's range is tighter and linear. [solver] [GTO Wizard, value-bluffing from the button](https://blog.gtowizard.com/the-art-of-value-bluffing-from-the-button/)
- Size trees used by solvers [solver, no frequencies] ([SimpleGTO](https://simplegto.com/learn/spin-and-go-preflop-strategy)):
  - Button opens 2 bb at every depth; SB opens 3 bb at 25 and 20 bb. At ≤15 bb the tree is 2 bb or all-in.
  - 3-bets at 25 bb: SB 2.75× or all-in, BB 3.25× or all-in. 4-bets are all-in.
- Commercial guide (GTO Gecko, solver not named) [expert] ([GTO Gecko](https://gtogecko.com/blog/spin-and-go-strategy)):
  - 25 bb: button min-raises ≈40%; BB defends 65-70% vs a min-raise and 3-bets 10-14% to ≈6 bb.
  - 7-10 bb: button jam-heavy, ≈1/3 of hands.
  - Heads-up at 15-20 bb: button plays 70-80%, BB defends ≈70%.
  - Recreational BBs fold 50-60% to a 2 bb open; the solver folds ≈30%.
- 3-way at 20 bb with a 1 bb ante (MTT) [solver] ([GTO Wizard, open-shove vs player profiles](https://blog.gtowizard.com/when-to-open-shove-vs-different-player-profiles/)):
  - Button opens 42.5%, ≈1/4 as jams; the SB re-jams its top 26.5%.
  - Against two blinds who never 3-bet bluff, the button opens up to **76%** and jams nearly vanish. Against two maniacs it min-opens ≈10% and jams more than it min-raises.
  - "The biggest deciding factor in how wide you can open is how aggressive your opponents are with 3-bets." Adjust most to the player most likely to act (usually the BB).
- Multiway theory [theory/solver] ([GTO Wizard, limitations of Nash in ICM spots](https://blog.gtowizard.com/the-limitations-of-nash-equilibrium-in-icm-spots/); [quirks of Nash in multiway](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/)):
  - Nash's can't-lose guarantee holds only in two-player zero-sum games. In 3+ player games two opponents can shift EV away from a third who plays an equilibrium; 3-player Kuhn poker has infinitely many equilibria (Szafron, Gibson & Sturtevant, AAMAS 2013).
  - 3-handed final-table example: bluffing a nit gains ≈$62-120 but risks a −$1,394 backfire, so the read must be right 95.9% of the time. When the button and BB stack each other, the folded SB gains a lot.

### 2.4 How endgame specialists beat good players
- Heads-up and SNG ROIs (Upswing 2017) [expert]: hyper 1-5%, turbo 3-9%, regular speed up to 12%. "Hypers reward specialization"; "play aggressively until your opponent gives you a reason to stop." (Upswing HUSNG link above)
- Spins (coach LORDbobby89) [expert] ([PokerStrategy, Spin win rates](https://www.pokerstrategy.com/news/content/What-winrates-are-possible-at-low-midstakes-Spins_125891/)):
  - ≈6% EV-ROI at $5; the best $25 regs ≈3.5%.
  - **Preflop is "the most underestimated street"**; niche postflop lines barely move win rate; GTO becomes necessary from ≈$25.
- Conversion: EV-ROI = (cEV/500 + 1)(1 − rake) − 1, with cEV = chips won per game, adjusted for all-in luck. [expert] ([PokerStrategy, chip-EV metric](https://www.pokerstrategy.com/news/content/Why-ChipEV-is-the-most-important-Spin-Go-metric_104944/))
  - Arithmetic: a 3.5% EV-ROI at 5-7% rake is ≈45-56 chips per game rake-free, ≈9-11% of a 25 bb (500-chip) stack.
  - Breakeven cEV is 38.5 chips at Betclic's rake; an example winner had cEV 68; ≥1,000 games are needed for a stable estimate. [expert] ([Poker Sciences](https://pokersciences.com/en/learn/spin/part-1/chapter-4))
  - Implication: even elite short-stack specialists win only ≈10% of a stack per game from good fields. Edges in near-Nash games are small and preflop-dominated.
- GTO Wizard's top Spin mistakes [solver/expert] (top-5 link above):
  - Making Nash calls against recreational jams: recreational players jam tighter, so call tighter.
  - Over-folding to regs' small c-bets in limped blind-vs-blind pots at 22 bb.
  - Over-calling recreational c-bets: correct folding rises from 33% to 50%.
- Moshman (c. 2013; date inferred from the page's image paths) [expert] ([PokerStrategy interview](https://www.pokerstrategy.com/?p=30123)):
  - Once fields filled with regs, the old tight wait-for-busts style blinded out; talented players loosened early and added postflop play.
  - Light CO 3-bets against a reg's open became common because neither reg wants a big early pot and the 3-bettor has position and initiative.
  - "Even aspects of shove/fold are not solved."
- Bot benchmark: GTO Wizard AI beat Slumbot by 19.4 bb/100 over 150k hands at 200 bb. Slumbot does not adapt and maps bet sizes onto a fixed set. [solver, self-reported] ([GTO Wizard, crushing Slumbot](https://blog.gtowizard.com/crushing-a-top-hunl-poker-bot/))

## 3. Push/fold, hyper-turbo and Spin & Go short stacks

### 3.1 Heads-up Nash push/fold, no ante (SB jam % / BB call %) [solver]

| Stack | HRC raw data (combo-weighted count) | PokerStrategy no ante | PokerStrategy 10% ante | hyperion's own solve |
|---|---|---|---|---|
| 5 bb | 71.5 / 62.1 | 74.1 / 68.6 | 78.6 / 73.2 | 72.3 / 61.7 |
| 10 bb | 58.3 / 37.4 | 56.6 / 38.5 | 60.8 / 43.0 | 57.8 / 37.6 |
| 15 bb | 45.7 / 28.5 | 45.7 / 28.4 | 49.0 / 30.6 | 44.7 / 28.1 |
| 20 bb | 40.2 / 21.7 | 40.9 / 21.7 | 44.5 / 23.8 | 39.9 / 21.7 |
| 25 bb | 36.3 / 17.3 | n/a | n/a | 35.7 / 17.3 |

- Sources: HRC file [holdemresources_hu_equilibrium.zip](https://www.holdemresources.net/hrdata/holdemresources_hu_equilibrium.zip) via [HRC HU Nash](https://www.holdemresources.net/hune) (169 hands × 1-200 bb in 0.05 bb steps; stacks measured before blinds, so it drops straight into a lookup table); [PokerStrategy Nash ranges](https://www.pokerstrategy.com/strategy/sit-and-go/push-fold-play-nash-ranges/); `tables/pushfold_hu.json` for hyperion's column.
- HRC cut-offs (push up to / call up to): K2o 11.65 / 8.15 bb; Q2o 7.05 / 5.6; 22 59.75 / 15.05; A8o 42.65 / 33.5; 72o 1.6 / 2.65. [solver]
- Sklansky-Chubukov numbers are the largest stack at which an SB jam is profitable even if the BB sees your cards, so they are lower bounds, not a strategy. Examples: A8o 36, K9o 18, K6o 13.3, J7s 9, 98s 8, 86s 5, AQs 137 bb. Rules of thumb: ×1.5 with antes; halve on the button. [math/expert] ([PokerListings](https://www.pokerlistings.com/poker-strategies/tournament-nl-holdem/a-fail-safe-profitable-strategy-for-some-parts-of-poker-tournaments); Sklansky & Miller, *No Limit Hold'em: Theory and Practice*, 2006 [book])

### 3.2 8-9 handed at 10-15 bb, by position [solver]
- HRC 8-handed MTT, total (min-raise + jam) as % of hands ([Upswing push/fold charts](https://upswingpoker.com/push-fold-tournament-strategy-charts/)):

  | Depth | UTG | UTG1 | LJ | HJ | CO | BTN | SB |
  |---|---|---|---|---|---|---|---|
  | 10 bb | 16.1 (7.6 + 8.5) | 18.8 | 21.5 | 26.3 | 32.2 | 38.4 (9.1 + 29.3) | 75.2: jam 54.3, limp 16.9, min-raise 4 |
  | 15 bb | 14.8 (all min-raise) | | | | | 38.9 (16.6 + 22.3) | 78.7: jam 34.5, limp 35.9, min-raise 8.2 |

  - These are MTT charts with antes; the article's CO row at 15 bb doesn't add up.
- ICMIZER push-only at 10 bb: UTG 13.1%, SB 67.1% (same link).
- GTO Wizard chip-EV at 10 bb: button jams 33.9% and min-raises 5.5% (ICM: 30.2% / 9.7%); UTG jams 11.4% and raises 4.2%. [GTO Wizard, short-stacked play](https://blog.gtowizard.com/short-stacked-play-in-mtts/)
- Rough 9-handed no-ante jams: UTG ≈12, HJ ≈16, CO ≈25, BTN ≈40, SB ≈50%. [expert, commercial] ([Deepfold](https://deepfold.co/en/blog/push-fold-complete-guide)) A 2026 marketing page gives a similar 9/16/28/38% for MP/CO/BTN/SB. [unverified]
- **Card bunching** (9-max, 7.5 bb, 10% ante): after 7 folds the SB's correct jam is 69.3%, not the standard 77.3%. ≈24% of the standard combos lose money (75o up to 0.5 bb). The BB's call drops from 62.3% to 52.5%. UTG barely moves (17.3% vs 18.3%). [solver] [HRC, card bunching](https://www.holdemresources.net/blog/card-bunching-effects/)
- In GTO Wizard MTT trees, min-raises turn into jams from 9 bb down and vanish at ≤7 bb. Button open-limping is polar at 14-25 bb, mostly replaced by jams at 10 bb, and gone at 8 bb. [solver] ([under 10 bb part 1](https://blog.gtowizard.com/playing-under-10bb-part-1-cev/); [open-limping buttons](https://blog.gtowizard.com/curious-case-of-open-limping-buttons/))

- Harrington's M-zones [book, 2005] (*Harrington on Hold'em* Vol. II; summary at [Wikipedia, M-ratio](https://en.wikipedia.org/wiki/M-ratio)):
  - M = stack / (SB + BB + antes). Green M ≥ 20; yellow 10-20; orange 6-10 ("be first in"); red 1-6 (push or fold only); dead < 1. Effective M scales M by players left / 10.
  - With no antes M = stack / 1.5 bb, so red is under 9 bb and orange 9-15 bb. Short-handed, effective M puts most stacks in red sooner: 5-handed, M 9 is effective M 4.5. Solver charts (above) supersede the zones, but the zones are a sane fallback when a variant breaks the tables.

### 3.3 Edges that remain when everyone is near-Nash
- **Callers' errors create the edge, and you collect it by moving your jam range.** PokerStrategy hand-EV at 9 bb (bb won by jamming) [solver]:

  | BB calls this % of hands | 20% | 30% | 43% (Nash) | 55% | 70% |
  |---|---|---|---|---|---|
  | Weak hand inside the Nash jam range | +0.76 | +0.48 | +0.08 | −0.26 | −0.64 |
  | Hand just outside it | +0.68 | +0.30 | −0.18 | −0.54 | −0.68 |

  - If the caller is too tight, add jams; if too loose, drop the weakest jams. Mirror rules apply for callers. (PokerStrategy Nash link above)
- ICMIZER: a BB calling 25% instead of 2.3% cuts the SB's profitable jam from any two to 34%. [solver] [ICMIZER, Nash calculator](https://www.icmizer.com/en/blog/nash-calculator-and-nash-equilibrium-strategy-in-poker/) The format-specific version is in §0.
- Removing one hand (TT, 0.45% of combos) from a caller's range widens a correct push from 17.5% to 27% (§1.6). Push ranges are very sensitive to how tight calls are; call ranges are less sensitive to push width.
- **Calling mistakes cost ≈4× jamming mistakes** near the bubble (§1.6). Under ICM the jammer has fold equity and the caller has only risk: on a Double-or-Nothing bubble the caller's bubble factor is 5.1-5.4 (83% equity needed) [solver] ([PokerStrategy, bubble factor in SnG formats](https://www.pokerstrategy.com/strategy/sit-and-go/bubble-factor-sng-forms/)).
- The only edge besides reads is richer actions. Limp and min-raise options beat pure jamming by small amounts (0.28 bb with AA at 10 bb; "minimal" at 14 bb heads-up). Their value is that they create more spots where opponents can err (over-folding to isos, over-limping).
- A simplified heads-up push/fold strategy reportedly left the SB ≈−0.05 bb per hand against a fuller strategy. [anecdote, 2+2 search snippet; page 403] ([2+2 thread](https://forumserver.twoplustwo.com/185/heads-up-sng-spin-gos/alternative-much-better-short-stack-heads-up-strategy-1648858/))

## 4. Against tight, competent players: where the money comes from, and where it doesn't

### 4.1 How an equilibrium player wins at all
- An unadjusted equilibrium strategy profits only when opponents take actions that should never be taken (dominated actions). It gains nothing from wrong mixing frequencies unless it adapts. [solver] [GTO Wizard, what GTO aims to achieve](https://blog.gtowizard.com/what-does-gto-aim-to-achieve/)
- Brad Wilson: ≈80% of a player's profit comes from recreational players. Against an all-reg field the edge is thin and comes from the weakest seats. [expert, secondary summary] ([Buteau, lessons from Brad Wilson](https://www.antoinebuteau.com/lessons-from-brad-wilson/))
- Pluribus never adapted and still beat elite pros at 6-max 100 bb [paper]:
  - +48 mbb/game (SE 25) over 10,000 hands vs five pros; +32 mbb/game (SE 15) with one human and five Pluribus copies. ([Brown & Sandholm, Science 2019](https://par.nsf.gov/servlets/purl/10119653))
  - Meta's write-up gives ≈5 bb/100 (p = 0.021) for the five-human format, and human losses of 2.3 bb/100 on average in the one-human format (Elias −4.0, Ferguson −2.5, Loeliger −0.5). ([Meta AI](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/))
- Spin specialists: preflop is "the most underestimated street" and niche postflop lines barely move win rate (§2.4).
- hyperion's own measurement agrees. Against its strongest rival, the rival netted +2,802 chips per table in hands that ended preflop without a showdown, against Hero's +898. In levels 4-8 the rival raised and took the pot down 13.0 times per table (+17.2 bb) against Hero's 9.2 (`docs/decisions.md`).

### 4.2 Which mistakes cost the most (40 bb MTT chip-EV sim and an ICM bubble sim) [solver]
([GTO Wizard, which mistakes cost the most](https://blog.gtowizard.com/understanding-which-mistakes-cost-you-the-most-money/))
- Folding J6s in the BB instead of defending: 0.26 bb (≈26 bb/100 if it came up every hand). Under-defending the BB is expensive.
- Using a 50% bet instead of 25%: 0.31 bb on the flop but 0.87 bb on the turn, because errors grow with the pot.
- Near the bubble: a bad call (ATs vs AJs) costs 0.41% of table equity against 0.1% for a bad shove. Ranking: bad calls > bad bets > bad shoves/folds.

### 4.3 Steals, re-steals and BB defence
All GTO Wizard MTT figures below assume a 1 bb total ante; this format has none (§0), so read them as upper bounds.
- Ante effect, 6-max 100 bb: BTN opens 42% (cash) vs 53% (MTT). BB total VPIP vs a BTN open is ≈40% (cash) vs ≈75% (MTT): calls ≈26% vs 61%, 3-bets ≈14% in both. [solver] [GTO Wizard, tournaments vs cash](https://blog.gtowizard.com/poker-strategies-tournaments-vs-cash-games/)
- 20 bb chip-EV: BTN opens 42.5%, ≈1/4 of them as jams. The SB facing a BTN min-open continues almost only by jamming, with its top 26.5%. BTN opens ≈10% against two maniac blinds and up to 76% against two that never bluff. [solver] [GTO Wizard, open-shove vs player profiles](https://blog.gtowizard.com/when-to-open-shove-vs-different-player-profiles/)
- ICM sim, 25% of the field left [solver] ([GTO Wizard, ICM vs chip-EV BB 3-bets](https://blog.gtowizard.com/icm-vs-chipev-the-hidden-logic-behind-bb-3bets/); [ICM and 3-bet pots](https://blog.gtowizard.com/how-icm-reshapes-3-bet-pots-and-why-you-cant-trust-chipev/)):
  - BTN opens ≈37% at 20 bb and ≈45% at 30 bb.
  - BB 3-bets to 6 bb at 20 bb, 7.5 bb at 30 bb and 10 bb at 50 bb.
  - SB shoves "quite a lot" at 20 bb, a few hands at 30 bb, and none at 50 bb.
- Opening by depth, chip-EV: UTG 16.5% at 100 bb, 17.7% at 50 bb, 15.8% at 17 bb. BTN at 10 bb jams 33.9% and min-raises 5.5%; at 13 bb jams 25% and min-raises 13.1%. [solver] ([short-stacked play](https://blog.gtowizard.com/short-stacked-play-in-mtts/); [stack sizes and ranges](https://blog.gtowizard.com/how-stack-sizes-change-your-range/))
- GTO Wizard says its mass data show the BB 3-bets far too little, and rarely with "creative" hands (no sample size given). [data] [GTO Wizard, 3 biggest leaks](https://blog.gtowizard.com/the_3_biggest_leaks_killing_your_winrate/) Light 3-bets in position against reg opens are the expert counterpart (Moshman, §2.4).
- Re-steal range anecdote: a 20 bb re-shove range against a BTN 2 bb open with most Ax, most pairs, and suited broadways down to T9s. [anecdote, search snippet; page now 404] ([rec.poker](https://rec.poker/?p=20668))
- Break-even fold rates for these plays without antes are in §0 (e.g. a 15 bb BB re-jam over a 2 bb BTN open needs 80% folds before equity).

### 4.4 Postflop sources of EV against good players [solver]
- **Delayed c-bets and thin value:** on a favourable flop (AK8) LJ bets 90% of its range. After the flop checks through, LJ should value-bet thinner, raise rarely, and fold more to big bets on boards that favour it. [GTO Wizard, delayed c-betting](https://blog.gtowizard.com/delayed-c-betting/)
- **Turn probes** after the BTN checks back T72r (cash): on an A turn probe big only (13.7 bb into 5.5 bb, ≈250% pot); on draw-completing turns probe small; on blanks mix. Against players who c-bet too often, check-raise the flop instead of probing. [GTO Wizard, turn probe](https://blog.gtowizard.com/the-turn-probe-bet/)
- **Capped ranges:** if UTG never checks overpairs on the flop (nodelock), the BB's turn betting rises to ≈40% and large overbets more than double. [GTO Wizard, capped ranges](https://blog.gtowizard.com/punish_the_unstudied_capped_ranges_and_bluffing_imbalances/)
- **Over-aggressive flop bettors:** a BTN that bets all its top pairs gains 16 bb/100 in betting EV but loses 6 bb/100 overall on the flop. The BB answers with 253%-pot overbet leads using 41% of its range when the turn pairs the K. [GTO Wizard, attacking aggressive opponents](https://blog.gtowizard.com/attacking-aggressive-opponents-when-they-check-back-flop/)
- **Size of single errors** (nodelock) ([GTO Wizard, five imbalances](https://blog.gtowizard.com/the-five-imbalances-of-exploitative-poker/)):
  - A BB that never folds to a 33% c-bet raises the CO's EV from 3.7 to 4.71 bb.
  - A BB check-raising ≈23% instead of ≈6% raises the CO's EV from 3.7 to ≈4.5 bb.
  - A BB folding 48% to an overbet instead of 58% moves its EV from 2.1 to 2.2 bb (≈10 bb/100).
  - Against a price-sensitive BB the CO's betting frequency rises from 58% to 76%.
  - If the CO always bluffs ace-high on the flop, the BB's turn lead on an A rises from ≈6% to ≈70% and the CO's turn EV falls from 3.8 to 2.4 bb.
- **Multi-street bluff maths:** three pot-sized barrels need 72.2% folds on the river, not 50%. Worked example line totals: bet-bet-bet +0.53 pots, bet-check-bet +0.45, bet-bet-give up +0.03. A profitable river bluff does not pay for losing flop and turn bluffs, so "they over-fold rivers, so steer into those lines" is a trap. [GTO Wizard, multi-street bluffs](https://blog.gtowizard.com/the-math-of-multistreet-bluffs/)
- **River over-folding to big sizes** [data, mid-stakes human]: GG NL100-200, BTN vs BB, third barrel, n = 18,639. Fold rate 59.4% overall (the page's own arithmetic gives 59.8%). By size: 50% pot 54.7%, 100% pot 57.8%, 175% pot 70.6%; minimum-defence benchmarks are 33%, 50% and 64% folds. Because the BB's range is capped, folding above those can be correct. ([GTO Killer](https://gtokiller.com/blog/river-triple-barrel-overfold/))

### 4.5 Where the money does not come from
- **Pure bluffs multiway.** "Pure bluffs are ineffective multiway." With eight defenders, a 10%-pot bet needs each player to defend only ≈26%, against ≈91% heads-up. [solver] [GTO Wizard, 10 multiway tips](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/)
- **Bluff-catching against a bot that never bluff-raises:** the SB needs 25.5% equity to call and has ≈0%, so fold every bluff-catcher. Equilibrium river calls of ≈38% drop to ≈0% against a nitty BB. [solver] (GTO Wizard 3-biggest-leaks link above)
- **Bluffing calling stations:** stop bluffing and bet thinner. [solver] (what-GTO-aims link above)
- **Calling wide under ICM:** ≈4× as costly as shoving wrong (§4.2). In this format the caller's risk premium is +10 to +25 points through the early and middle levels (§0).
- **Postflop frequency reads on strong bots within 200 hands:** the samples are too small to separate a strong bot's postflop frequencies from equilibrium (§7.4). Preflop opens, 3-bets and fold-to-steal are the readable stats.

## 5. Bet sizing

### 5.1 What drives size [solver]
([GTO Wizard, mechanics of c-bet sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/))
- Size up with a nut advantage, when the opponent holds many hands with reasonable equity, when the hands that fold have real equity, and when your range has few middling hands. Size down when the opponent holds many nutted hands or your range has many middling hands that want protection.
- Dry boards → small; wet boards → large; very wet boards → small again. **Range advantage sets frequency; nut advantage sets size.**
- Board examples (cash, BTN vs BB, 100 bb):
  - Q♥Q♣6♦: mostly 33% pot; the BB folds 37%.
  - K♥J♥7♦: 75% and 125% pot; the BB folds 62% to the 125% bet.
  - Q♦J♦T♦: ≈half bets, half checks, mostly small.
- Cash BTN vs BB flop heuristics: disconnected boards use 33% often and 130% is also common; boards where an open-ended straight draw is possible lean to 66% and are bet less; paired boards are bet often and small; monotone cuts both frequency and size sharply; A-high boards are bet *less* often than 8- to K-high. [solver] [GTO Wizard, IP c-betting heuristics](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/)

### 5.2 Tournament depths (20-40 bb), the depths this format plays at most [solver]
- 20 bb chip-EV: BTN c-bets 78% overall, mostly small, sometimes 55% and rarely 83%. ICM with 25% of the field left: 50% bets on 654r shrink to 20%, and near the bubble the BTN range-bets. [GTO Wizard, bullying the blinds](https://blog.gtowizard.com/bullying-the-blinds-with-continuation-bets/)
- 40 bb: BTN c-bets ≈75% against a BB caller and ≈50% against an SB caller. [GTO Wizard, defending the blinds in MTTs](https://blog.gtowizard.com/flop-heuristics-for-defending-the-blinds-in-mtts/)
- 3-bet pots shallow: c-bets as small as 10% pot. At 40 bb on A93r, the BTN bets 10% pot with more than half its range. [GTO Wizard, c-betting IP in 3-bet pots](https://blog.gtowizard.com/c-betting-ip-in-3-bet-pots/)
- 30 bb on T♥T♦2♥: the CO bets 20% pot with essentially its whole range. [GTO Wizard, pushing equity with small bets](https://blog.gtowizard.com/pushing-equity-with-small-bets/)
- OOP at 40 bb: UTG against a BTN caller bets barely half its range, mostly small; on 986 two-tone it checks 65%. [GTO Wizard, OOP c-betting in MTTs](https://blog.gtowizard.com/flop-heuristics-oop-c-betting-in-mtts/)
- Heads-up BB donk frequency at 40 bb is ≈2% on average and barely 7% on connected flops (chip-EV). Under ICM the covering BB leads 9-24% on the spots in §1.7. (defending-the-blinds link above)

### 5.3 Overbets and geometric sizing [solver]
- Geometric sizing (the same pot fraction each street, ending all-in) is 110-116% pot per street in a 100 bb single-raised pot. The BTN uses 125% almost exclusively when it bets AK6r. On a QJ2-6 turn at 50 bb the BTN bets 200% and the BB folds ≈67%. [GTO Wizard, larger than geometric](https://blog.gtowizard.com/why-so-much-an-exploration-of-larger-than-geometric-bet-sizing/)
- On K84 with a Q♠ turn at 100 bb, UTG bets ≈40% of its range, always bigger than pot. At 20 bb its most common turn bet is 50% pot: **shallow stacks remove the need for overbets**. [GTO Wizard, principles of turn strategy](https://blog.gtowizard.com/principles-of-turn-strategy/)
- A nut advantage is close to necessary for overbets but not sufficient. [solver, GTO Wizard turn-article search snippets]
- SPR arithmetic for this format [math]: at level 1 (100 bb), a 2.2 bb open called heads-up makes a ≈5-6 bb pot with SPR ≈17-20, so overbets and geometric lines exist. At level 4 (50/100) a 2,000-chip stack is 20 bb; after a 2.2 bb open and a BB call the pot is 4.9 bb and SPR ≈3.6, so overbets collapse into jams. The deep-stack sizing toolbox matters only for the first ≈50-75 hands, and only for stacks that have grown.

### 5.4 Block bets and small river bets [solver]
- An OOP block bet of ≈10% pot is "nearly the same as a check". It is best against opponents who won't raise without near-nuts, and adds a little value from medium hands. ([GTO Wizard, nasty rivers OOP](https://blog.gtowizard.com/navigating-nasty-rivers-out-of-position/); [principles of river play](https://blog.gtowizard.com/principles-of-river-play/))
- OOP can value-bet thinner because a check does not close the action. A value bet must win >50% when called. (river-play link above)
- When flop and turn check through at 40 bb, value bets get thinner and small: with a 16% pot block even a pair of 2s bets for value, and bottom pair often bets small. [GTO Wizard, thin value in checked-down pots](https://blog.gtowizard.com/mastering-thin-value-bets-in-checked-down-pots/)
- A multiway 80 bb tournament hand where the solver chose a 25% river block with AKs. [solver, single hand] ([PokerNews](https://www.pokernews.com/strategy/this-is-how-the-pro-s-play-multiway-pots-51467.htm))

### 5.5 How many sizes, and what simplification costs [solver]
- Flop, UTG vs BB, 100 bb: one size vs three sizes (40/67/127%) differ by ≈0.01 bb on most flops and 0.02 bb at worst (<0.5% pot). The river matters most, then the turn, then the flop. If you use two sizes, make them very different; 40% vs 66% isn't worth it. [GTO Wizard, do multiple sizes matter](https://blog.gtowizard.com/do-multiple-sizes-matter/)
- River, heads-up 100 bb, 500 spots: the best single size per spot (chosen dynamically) loses only **0.30% of the pot** against an 8-size strategy, and 0.05% against the best possible single size. The best fixed size overall is ≈75-100% pot IP and ≈50% OOP. [GTO Wizard, dynamic sizing benchmarks](https://blog.gtowizard.com/dynamic-sizing-benchmarks/)
- Against Slumbot (heads-up, 150k hands), the one-size strategy won 19.4 bb/100 against 13.1 bb/100 for the complex one. [solver, self-reported] [GTO Wizard, dynamic sizing](https://blog.gtowizard.com/dynamic-sizing-a-gto-breakthrough/)
- Pluribus used 1 to 14 bet sizes depending on the spot. [paper] (Science 2019 link in §4.1)

### 5.6 Polarised vs merged, and bluff ratios [solver/math]
- Polarised betting means nuts plus bluffs; the caller bluff-catches. Merged (linear) betting means strong plus medium hands bet small for thin value and protection. Polarised goes with big sizes and nut advantage; merged with small sizes, range advantage and capped opponents. (§5.1 sources)
- River bluff share of a polarised bet of size s (fraction of pot) is s / (1 + 2s): 33% pot → 20% bluffs; 50% → 25%; 75% → 30%; pot → 33%; 150% → 37.5%; 200% → 40%. MDF = 1 / (1 + s); alpha = s / (1 + s). [math] [GTO Wizard, MDF & alpha](https://blog.gtowizard.com/mdf-alpha/); Chen & Ankenman, *The Mathematics of Poker* (2006) [book, not re-checked]
- These ratios hold only on the river with nut-or-air ranges. Rough value share by street: ≈1/3 on the flop, 1/2 on the turn, 2/3 on the river; slightly more value-heavy for blockers and rake. [solver] [GTO Wizard, mathematical misconceptions](https://blog.gtowizard.com/mathematical-misconceptions-in-poker/)

### 5.7 Sizing tells: using them and hiding them
- Strong players often simplify to one size (e.g. 33% pot 100% of the time). Players who always use each hand's preferred size are unbalanced and exploitable; in Galfond's example, AQ becomes a fold. [expert] [Galfond, exploiting GTO bet sizing](https://www.philgalfond.com/articles/exploiting-gto-bet-sizing/)
- If a player's large size holds only flushes, fold almost everything to it and attack the small size (nodelock, not observed play). [solver] [GTO Wizard, sizing tells](https://blog.gtowizard.com/punish-the-unstudied-preflop-mistakes-sizing-tells/)
- If an opponent check-raises small bets more, stop using the small size with strong hands; against passive players bet large. [solver] [GTO Wizard, overchoice](https://blog.gtowizard.com/overchoice-making-sense-of-multiple-sizings/)
- Attack imbalances [solver] (five-imbalances link in §4.4):
  - A condensed range → big sizes. An over-polarised range → small sizes. A perfectly polarised range → bluff-catch it.
  - Price-sensitive (folds too much to big bets) → overbet. Price-insensitive → bet thinner.
- Hiding: one balanced size per node costs ≈0.05-0.3% of the pot (§5.5). Pluribus avoided tells by computing, for each action, the strategy for every hand it could hold. [paper] (Meta link in §4.1)
- Even 500NL-1000NL online regs reportedly bet large with strong hands and draws and small with middling hands and air. Unquantified. [data/expert] [Upswing, deviate from GTO](https://upswingpoker.com/deviate-from-gto/)
- For a bot: other teams' bots will often map hand-strength buckets to fixed sizes. That is the sizing tell to read: track the showdown strength behind each size bucket, per seat.

## 6. Multiway pots

### 6.1 How strategy tightens [solver]
- LJ open with SB and BB both calling (8-max, 100 bb, chip-EV) [GTO Wizard, IP vs two callers](https://blog.gtowizard.com/playing-in-position-against-two-callers/):
  - LJ checks 11 points more than heads-up, and pot-sized c-bets drop from 18% to 1.3%.
  - LJ's EV falls for nearly every hand. The BB's 3-bet range becomes almost purely linear.
  - The SB leads ≈9.8%, mostly at 33%, on low and middle boards.
- General rules ([GTO Wizard, 10 multiway tips](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/)):
  - The defence burden is shared: each player defends 1 − α^(1/n), with α = bet / (bet + pot). On A♣T♣2♠ the per-player burden is ≈25% vs ≈44% heads-up.
  - Tighten value thresholds and stop range-betting. Nut potential is "king" and blocker effects are amplified.
  - "There is no such thing as an unexploitable strategy in multiway scenarios."
- Facing a 1/4-pot c-bet with the BB still to act behind (T74 two-tone, ≈40 bb): the BTN folds 31%, calls 39%, raises 30% (heads-up: 10/73/17). A raise makes the BB fold ≈85%, against ≈45% if the BTN just calls. Against larger c-bets the BTN raises less. [GTO Wizard, monkey in the middle](https://blog.gtowizard.com/monkey-in-the-middle-3-way-pot-heuristics/)
- 3-way pots: the BB probes the turn selectively, usually large (often pot), and needs a favourable turn card. [GTO Wizard, probing 3-way](https://blog.gtowizard.com/probing-out-of-position-in-3-way-pots/)
- Not every multiway spot is small-bet. On Q♠T♠7♥ 3-way the solver prefers a larger c-bet and the SB is supposed to donk. [GTO Wizard, 3-way solving](https://blog.gtowizard.com/now_live_3_way_solving_nodelocking_2_0_and_50k_icm_ft_sims/)
- In one deep 3-bet multiway hand the solver bets only ≈11.7% of hands, and the OOP player mostly checks. [solver] [PokerNews](https://www.pokernews.com/strategy/struggling-in-multiway-pots-gto-wizard-shows-the-answer-51069.htm)
- Exploit less multiway: other players can punish your deviation (Brokos, §7.1). Under ICM the uninvolved players gain from any fight (Gilbert, §1.1).

### 6.2 Squeezes and overcalls [solver]
- BB squeezing a CO open plus a BTN call at ≈40 bb [GTO Wizard, squeezing range](https://blog.gtowizard.com/how-to-construct-a-squeezing-range/):
  - Cash (NL500): 9.8%, mostly to 10 bb, against an 8 bb heads-up 3-bet.
  - MTT chip-EV: 12.1%, about half as jams. ICM bubble: 10.7%, almost no jams.
  - KQs-KTs, QJs and JTs squeeze multiway but never 3-bet heads-up.
- AQs in the BB at 50 bb after a UTG open: calling is worth 2.39 bb and 3-betting 2.25 bb heads-up. With two callers, calling falls to 2.15 bb and 3-betting rises to 3.21 bb, so the squeeze gains ≈1 bb. [GTO Wizard, overcalling from the BB](https://blog.gtowizard.com/overcalling-from-the-bb/)

### 6.3 Limps and donks
- Pluribus dropped limping (except from the SB) during self-play and donk-bet "far more often" than the pros. [paper] (Science 2019 link in §4.1)
- Multiway, an iso-raise or squeeze with a linear range beats limping behind. A limped multiway pot is where stronger players' edges shrink most. [inference from §6.1-6.2]

## 7. Balance vs exploitation against strong opponents

### 7.1 When and how fast top players deviate
- **Bigger deviations need stronger reads.** The penalty for a wrong read grows with the size of the deviation. How far to move depends on how big the opponent's mistake is and how confident the read is. Multiway, there is less room to exploit one player because the others can punish you. [expert] Brokos, Feb 2023, [GTO Wizard, exploitative dynamics](https://blog.gtowizard.com/exploitative-dynamics/)
- **Best responses flip on tiny deviations and gain little.** In Brokos's river example, the caller calling 52% instead of 50% makes the in-position player stop bluffing entirely. Mixed hands flip; pure hands don't. [solver] (same link) The ICM version is in §0: the cover's best jam width goes from 100% to 15% as the caller widens from 6% to 15%.
- **Exploit only the nodes that actually deviate.** Jayser1337: ignore rare lines solvers like but players almost never use. If the population c-bets ≈75% on 654r, the BB's balanced lead becomes a 100% check once nodelocked. [expert] [GTO Wizard, pro features](https://blog.gtowizard.com/top_gto_wizard_features_the_pros_prioritize/)
- **Downstream strategies are fragile.** Kevin Rabichow: "I don't trust any single equilibrium strategy on the river." Nodelocking the BB's flop check-raise from 12.5% to 7.5% moved its river leads from ≈11% to 0%. [expert/solver] (same link)
- **Nodelocking mechanics:** unlocked hands "adapt to minimize EV losses", and a flop lock assumes perfect play on later streets. [solver] [GTO Wizard, nodelocking](https://blog.gtowizard.com/introducing-nodelocking/)
- **Doug Polk (updated Dec 2025):** play a GTO-based default with no reads; it works against "almost any opponent, especially the tougher ones". Exploiting "opens the door for your opponents to exploit you back". "Be careful not to make adjustments with too little or unreliable information." He gives no hand count. [expert] [Upswing, GTO vs exploitative](https://upswingpoker.com/gto-vs-exploitative-play-game-theory-optimal-strategy/)
- **A showdown is a hypothesis.** Only hands the solver plays purely the other way (pure check, pure fold) prove a mistake; a hand from a mixed spot proves nothing. Aggression shown once may not persist, especially after the player is caught. [expert] Wee, Apr 2024, [GTO Wizard, exploits from showdown](https://blog.gtowizard.com/building-exploits-from-showdown/)
- **Frequent small leaks matter more than rare large ones.** The most expensive per-hand mistakes "are not always the most costly to your overall win rate because they might not occur often". [expert] ([GTO Wizard, fixing a leak](https://blog.gtowizard.com/fixing-a-poker-leak-part-1-spotting-and-correcting-errors/), search snippet)
- **ICM makes exploits riskier.** "Lean towards lower-variance exploits in spots with lots of ICM pressure." The max-bluff exploit of a nit needed the read to be right 95.9% of the time. [solver] (§2.3, limitations-of-Nash link)
- **What one exploited leak is worth:** typically 0.1-1 bb each time the node occurs (§4.4). A spot that comes up in 5% of hands is worth ≈0.5-5 bb/100. Forcing the BB to call 100% on a flop costs it 0.47 bb ("47 bb/100" if it came up every hand). The risk side is unbounded if the read is wrong and the opponent adapts. [solver + arithmetic] ([GTO Wizard help, nodelocking](https://help.gtowizard.com/how-to-use-nodelocking/), search snippet)

### 7.2 Population exploits (human pools; numbers are thin)
- **River raises are under-bluffed "at every stake"**, and calls are justified only against known big bluffers, "few and far between, even at high stakes". Author's view, no dataset. [expert] Dan B., Jan 2019, [Upswing](https://upswingpoker.com/winning-calls-that-lose/)
- "Against the vast majority of players… you're better off exploitatively folding all bluff-catches"; turn and river play is "not as sharp" as preflop and flop. [expert] [Upswing, avoiding poker theory](https://upswingpoker.com/avoiding-poker-theory/)
- Most 500NL regs reportedly 3-bet less than the 13.5% GTO figure in the author's example. Unquantified. [data, unquantified] (Upswing deviate-from-GTO link in §5.7)
- The one hard number found for a micro pool ($0.02/$0.05 Zoom, PokerStars): ≈56% of the BB's turn-probe range is unmade hands (J♠6♠5♣T♥, BTN vs BB). [data] [GTO Wizard, over-bluffed lines](https://blog.gtowizard.com/calling-down-the-over-bluffed-lines-in-lower-limits/)
- Low and mid stakes under-check overpairs on the flop and under-bluff rivers with weak pairs. Assertion only. [expert] [GTO Wizard, capped ranges](https://blog.gtowizard.com/punish_the_unstudied_capped_ranges_and_bluffing_imbalances/)
- River folds rise with size (54.7% at 50% pot to 70.6% at 175% pot) in mid-stakes data (§4.4). [data]
- **Relevance to bots:** these are human leaks (fear, fatigue, imbalance on rare lines). A strong bot built from a solver or self-play will not share them. A hastily built bot has different leaks, usually fixed sizes, no river bluffs or no mixing. Use these as priors to test per seat, not as defaults.

### 7.3 MDF, alpha, and why MDF is a floor only sometimes
- MDF = pot / (pot + bet); alpha = bet / (pot + bet) = 1 − MDF; generally alpha = risk / (risk + reward). The simple forms are valid only for the first bet: facing a raise from $60 to $200 into $100, alpha is 55.5%. [solver/math] Tombos21, Jul 2022, [GTO Wizard, MDF & alpha](https://blog.gtowizard.com/mdf-alpha/)
- Table (s = bet / pot) [math]: 33% → MDF 75%, alpha 25%; 50% → 67 / 33; 75% → 57 / 43; pot → 50 / 50; 150% → 40 / 60; 200% → 33 / 67.
- **Solvers defend below MDF out of position** [solver] ([GTO Wizard, misconceptions](https://blog.gtowizard.com/mathematical-misconceptions-in-poker/); MDF & alpha link):
  - Across all 1,755 flops and c-bets of 20-200%, the BB "consistently over-folds" relative to MDF when OOP, and defends close to MDF in position (BvB with the BB acting last).
  - Reasons: OOP, the bettor's bluffs earn EV even when checked back; bluffs have equity before the river; MDF applies only to hands that beat a bluff.
  - CO vs BB on QQ3r facing a 33% c-bet: MDF says defend 75%; the solver folds "almost half".
  - Rule: "Defend closer to MDF in position, over-fold out of position." "Under-defending is almost certainly less exploitable than over-defending in most cases." Do **not** apply MDF against an opponent who under-bluffs.
  - Defend *wider* than MDF against early shoves on draw-heavy boards (the solver over-calls a 134% 4-bet-pot flop shove by ≈10% over MDF) and against bluffs that keep equity.
- **Using it to find over-folders:** compare an opponent's fold% to the solver's baseline for that node, not to MDF. A zero-equity bluff is +EV only if fold% > alpha, with multi-street lines evaluated as a whole (three pot-sized barrels need ≈72% river folds, §4.4). [solver/derived]
- **Under ICM, MDF is wrong by construction.** The caller's required equity carries the risk premium (+10-25 points through most of this format, §0), so correct folding sits far above alpha. Opponents who defend to chip-EV MDF are giving points away; opponents who fold far more than MDF may simply be correct.

### 7.4 Small samples: what 200 hands can and cannot tell you [paper/expert]
- **Pluribus never adapted** and beat elite pros (§4.1).
- **ACPC 2012:** Hyperborean's on-the-fly exploitation raised its winnings against a few opponents, but "playing our approximate equilibrium would have been better" in many cases because many entries were near-equilibrium. The exploitative Little.Rock won the NL total-bankroll event by preying on weak entries. [paper/anecdote] ([IEEE Spectrum](https://spectrum.ieee.org/champions-declared-in-ai-poker-tournament))
- **ACPC 2016:** all top-4 heads-up NL entries used CFR, and the top 3 were "within $2 per hand". The exploit-seeking Nyx won only the uncapped total-bankroll event and lost narrowly to the top 3. [anecdote] ([PokerNews](https://www.pokernews.com/strategy/poker-ai-2016-annual-computer-poker-competition-24246.htm))
- **Restricted Nash response** (Johanson, Zinkevich, Bowling, NIPS 2007): the opponent is forced to follow the model with probability p, trading exploitation for robustness. Pure best responses are brittle; RNR is "substantially more robust". [paper] ([NeurIPS](https://proceedings.neurips.cc/paper/2007/hash/6e7b33fdea3adc80ebd648fffb665bb8-Abstract.html))
- **Data-biased response** (Johanson & Bowling, AISTATS 2009, limit hold'em) [paper] ([PMLR](https://proceedings.mlr.press/v5/johanson09a/johanson09a.pdf)):
  - With fewer than ≈100k observed games, raising p made RNR both more exploitable and less exploitative.
  - DBR instead sets a per-node confidence from the observation count n: "10-step" (none below 10 observations), "0-10 linear" (Pmax·n/10), "1-curve" (Pmax·n/(1 + n)). Unobserved nodes get 0, i.e. equilibrium.
  - At 100-1,000 observations, the gain in exploitation was "very small" and the added exploitability only marginal.
- **Deviation-based best response** (Ganzfried & Sandholm, AAMAS 2011) [paper] ([PDF](https://www.cs.huji.ac.il/~jeff/aamas11/papers/B4_R56.pdf)):
  - Shrinks observed frequencies toward equilibrium with a Dirichlet prior of 5 fictitious hands, plays equilibrium for the first 1,000 hands, then updates every 50.
  - It still lost for "several hundred hands" against AlwaysRaise and GUS2, because the prior filled unexplored lines wrongly.
  - The authors: it "might actually become significantly exploitable to strong opponents… play the equilibrium against strong opponents… only attempting to exploit… if a win rate above some threshold is attained".
- **Safe exploitation** (Ganzfried & Sandholm 2015, ACM TEAC): risk only accumulated "gifts" (profit above the game value). In generalised Kuhn poker it scored 0.270 vs 0.141 for static equilibrium against a random opponent, and −0.0609 vs −0.0611 against an equilibrium opponent, so it costs essentially nothing. [paper, via Jeary & Turrini 2023] ([arXiv:2307.12338](https://ar5iv.labs.arxiv.org/html/2307.12338))
- **Bayes' Bluff** (Southey et al., UAI 2005): in Texas hold'em "two hundred hands does not provide enough information to effectively concentrate the posterior". A frequentist model can lock itself into folding and never collect the data to correct itself. [paper] ([arXiv:1207.1411](https://arxiv.org/abs/1207.1411))
- **Multiplayer Kuhn** (Ganzfried et al., arXiv 2212.06027): a Bayesian best response with Dirichlet priors centred on Nash won 48 milli-chips per hand vs 37 for the best Nash agent. With uninformed priors it scored −54, so the prior mean matters most. Starting exploitation anywhere between hand 0 and 200 gave similar results. [paper] ([arXiv](https://arxiv.org/html/2212.06027v4))
- **Implicit modelling** (Bard et al., AAMAS 2013): instead of estimating opponent parameters, pick online among a fixed portfolio of precomputed robust responses by their (variance-reduced) observed performance. It "would have won" the 2011 ACPC heads-up limit exploitation event. [paper, abstract] ([U. Alberta](https://webdocs.cs.ualberta.ca/~bowling/publications/b2hd-13aamas-implicitmodelling.html))
- **Showdown data are biased:** folding hides cards, so showdown samples are "missing not at random" and confidence sets built from them can under-cover. Halving the error needs ≈4× the hands. [paper, 2026 preprint] ([arXiv:2608.09954](https://arxiv.org/abs/2608.09954))
- **HUD rules of thumb** [expert]:
  - VPIP/PFR ≈20 hands; 3-bet, fold-to-3-bet, flop c-bet and fold-to-c-bet ≈100; turn ≈300; river and fold-to-4-bet 500-1,000; at least 5 opportunities to look at a stat and 10 to trust it. ([Blackrain79](https://www.blackrain79.com/2017/11/poker-hud-stat-sample-size.html))
  - Stricter: VPIP/PFR marginal at 100 hands, reliable at 500+. ([poker.academy](https://poker.academy/blog/post/poker-hud-for-you-take-the-advantage), snippet)
  - 300 hands gave only 11 c-bet opportunities (Laplante). ([PokerNews](https://www.pokernews.com/strategy/teachable-moments-from-twitch-ryan-laplante-hud-stats-32348.htm))
- **Binomial 95% intervals at this format's sample sizes** [math]: VPIP 25% over 200 hands ±6 points; 3-bet 8% over 80 chances: 2-14%; fold-to-c-bet 45% over 20 chances: 23-67%; a river fold rate over 8 chances: 15-85%. **Within one table only preflop open, VPIP, PFR, fold-to-steal and maybe 3-bet are estimable; postflop reads on a strong bot stay inside equilibrium noise.**
- **Shrinkage** (DBBR/DBR style) [derived]: estimate = (k + m·p_eq) / (n + m). 14 folds in 20 (70%) with a 45% prior gives 65% at m = 5 and 57.5% at m = 20.

## Gaps, unverified items and what to do next
- **Not found anywhere:** strategy for tournaments that end at a fixed hand count and settle by ICM (§0); published 8-handed or 4-handed SNG push ranges under ICM ("big stack X% vs Y% chip-EV"; these need HRC or ICMIZER runs); 3-handed push/fold Nash numbers (HRC's 3-way calculator is interactive only).
- **Format-specific numbers here are computed, not published:** Malmuth-Harville, jam-or-fold only, no card removal. Before acting on §0's SB-vs-BB table, re-run it with the real points table, blind schedule and seat count announced at build time. Every input is already in the repo.
- **Not read directly (secondhand or from memory):** *Kill Everyone* (2007/2009), *The Mathematics of Poker* (2006), Moshman's *Sit 'n Go Strategy* (2007) and *Heads-Up NLHE* (2008), Janda's *Applications of NLHE* (2013), Acevedo's *Modern Poker Theory* (2019), Clarke's *The Grinder's Manual*. No numbers here rely on them except where a web source restates them.
- **Paywalled or blocked:** GTO Wizard charts (images, so many exact frequencies are missing), a GTO Wizard post on X (402), gtolab.com (403), 2+2 threads (403), Freenachos AMA (403), Poker MDA and Hand2Note population data (paid), Upswing Lab (paid), the ACPC site (bad certificate), and the full Ganzfried & Sandholm 2015 and Bard et al. 2013 papers.
- **Not reached because the search budget ran out:** Run It Once, Red Chip, PokerCoaching and PokerSnowie strategy pages; interviews with Loeliger, Holz, Bencb, Rolle and Sulsky; dedicated block-bet articles; open frequencies by seat at 8-max without antes.
- **Excluded as low quality:** DeucesCracked 2026 blog posts (generic, unsourced numbers), the velnor.it.com "61% fold to river overbet" figure (garbled page), GrindLab, and GTO Gecko numbers (marketing, solver not named; used only where marked [expert]).

## Testable for a bot

Each item gives the behaviour, how to measure it, and the expected edge where a source gives one. "Measure" means hyperion's paired duplicate-seed protocol (`tools/climb_accept.py`) across the realistic, top and night fields, the judges, and the three payout tables. Where hyperion has already tried something close, the result from `docs/decisions.md` is noted so it isn't re-run blind.

1. **Per-pair ICM threshold on every all-in call, from the announced points table.**
   - Behaviour: call only if equity against the estimated range ≥ ICM break-even for *this* opponent pair. This includes deep stack-offs: 64-67% at hand 1 under 10/7/5 or linear; KK folds to a QQ+/AK 5-bet range (§0). Ban chip-EV calling outright.
   - Measure: points, and bust rate in levels 1-3, with and without the gate, under each payout table.
   - Expected edge: chip-EV play until the final table cost 13% of the buy-in in GTO Wizard's sims (§1.6). In this format a chip-EV BB calling 21% where 3% is correct loses ≈0.06 points per occurrence (§0, computed).
   - Hyperion: already has an ICM call gate. Its flat extra risk-of-ruin margin (0.05-0.10) was within noise. Check that the gate prices deep preflop stack-offs with the full table rather than a margin.
2. **Cover-and-jam, conditioned on how the target calls.**
   - Behaviour: when we cover the players left to act and effective stacks are ≤25 bb, widen SB and BTN jams toward any two against seats whose shrunk call-vs-jam rate is ICM-tight (≤6%). Fall back to chip-EV width or tighter (≈13-15%) against seats that call jams wide (≥15%).
   - Measure: points per table, and SB/BTN jam EV by target bucket.
   - Expected edge: +0.070 points per SB hand for an any-two jam against a 3% caller, against +0.031 for a chip-EV 40% range (§0, computed). ICMIZER's 44 bb leader shoves almost any two (QJs +0.24% → +0.45% of the pool when callers tighten); one hand removed from the caller's range widens a correct push from 17.5% to 27% (§1.6).
   - Note the cliff: any two into a 21% caller loses 0.057 points per hand.
3. **Covered/covering postflop mode.**
   - Behaviour: when an opponent in the pot covers us and our bubble factor against them is ≥1.3, c-bet about half as often, size ≤33%, never overbet, and check back marginal hands. When we cover, lead 10-25% of the BB range on flops where the chip-EV solution checks 100% (made hands plus draws), and keep betting.
   - Measure: points at tables with ≥2:1 stack ratios, mode on vs off.
   - Expected edge: a covered player overbetting its chip-EV range is a ≈2 bb/100 leak (Carter, §1.7). Chip-EV postflop on a bubble costs >10% of the buy-in per flop and >30% in 3-bet pots (GTO Wizard, §1.6).
4. **Cap-aware laddering and cap-aware stealing.**
   - Behaviour: from hand ≈170, compute the blind cost of folding to the cap, (200 − h)(sb + bb)/n (e.g. 2,250 chips at hand 186 with 4 alive). If our stack exceeds it and the table is not winner-take-all, fold all-ins that are only marginally +ICM. As the cover in the last 25 hands, widen steals against stacks that can fold to the cap.
   - Measure: points from tables reaching hand 175 with 3+ alive.
   - Expected edge: no published number; nothing in the literature covers hand caps. Hyperion's rival 1 does exactly this and has the lowest bust rate of the competent bots (60.5% and 66.1%).
   - Hyperion: the hand-cap-aware value curve (`cap_vol_bb`) was built but not swept; sweep it alongside this rule.
5. **No-ante preflop calibration.**
   - Behaviour: build open, defend and steal ranges from no-ante solutions (cash, HRC-SNG or Spin-style), not MTT charts with antes. Indicative targets: 6-max-style BTN ≈42% at 100 bb (MTT 53%); 3-handed BTN ≈38.5% at 25 bb, 2 bb opens, no limps (GTO Wizard calls the ≈48%-with-limps MTT habit a leak); opens 2.0-2.2 bb.
   - Measure: fold-to-steal achieved, steal EV in bb, points.
   - Expected edge: not quantified. The steal maths: a 2.0 bb steal needs 57% folds without an ante vs 44% with one (§0).
6. **Re-steal jam ladder at 12-25 bb, priced by the opener's observed open width.**
   - Behaviour: from the SB and BB, jam over late-position opens with a range priced by the opener's shrunk open % and the ICM gate. The re-jam needs 72-87% folds as a pure bluff at 10-25 bb (§0). At 20 bb the solver's SB continues almost only by jamming, with its top 26.5% against a BTN min-open (§4.3).
   - Measure: re-jam EV per opportunity, points.
   - Hyperion: `reshove_mid_bb` 25 passed alone (+0.052 ± 0.049 vs rival 1); the exploitative re-shove price failed the strong room (−0.14). Keep the priced version and leave out the exploit price.
7. **Heads-up and 3-handed endgame specialist route.**
   - Behaviour: heads-up ≤12 bb, HRC Nash push/fold lookup (SB 58.3% / BB 37.4% at 10 bb; 40.2% / 21.7% at 20 bb). Heads-up 12-25 bb: limp-heavy SB (≈60-80% limps, ≈25% min-raises at 20 bb, almost no folds), BB isolating limps with all-in sizes (the SB folds ≈82% to a 20 bb all-in iso) and defending 70-81% against min-raises. 3-handed: button opens tighten when the BB 3-bets more (42.5% → 10% against two maniacs; up to 76% against two passive blinds).
   - Measure: heads-up and 3-handed head-to-head points against exploiter 2 and the rivals.
   - Expected edge: the equilibrium gain of limp/min-raise over pure jam is small (0.28 bb with AA at 10 bb; "minimal" at 14 bb). The value is in opponents' errors: over-folding SBs let the BB raise limps 48% instead of 34% (§2.2).
   - Hyperion: exploiter 2 still beats F heads-up (9.20 to 7.80) and 3-handed (8.23 to 7.35); `short_route` (S13) is in held-out confirmation, so this item is that test.
8. **Per-seat jam-calling read moves our jam range, not our calling range.**
   - Behaviour: shrink each seat's call-vs-jam rate toward the field prior, (k + m·p)/(n + m) with m ≈ 5-10. Add jams against tight callers and drop the weakest jams against loose ones. Do not widen *our* calls against wide jammers under ICM.
   - Measure: jam EV by caller bucket.
   - Expected edge: at 9 bb a weak in-range hand earns +0.76 bb against a 20% caller and −0.64 bb against a 70% caller; a just-outside hand +0.68 / −0.68 (PokerStrategy, §3.3). Against a BB calling 25% instead of 2.3%, the SB's profitable jam falls from any two to 34% (ICMIZER).
9. **Bluff-catcher discipline against strong bots.**
   - Behaviour: out of position, fold more than MDF (the solver does; MDF is not a floor OOP). Facing river raises and big river check-raises, fold bluff-catchers unless that seat has shown a river-raise bluff at showdown at this table. In position, defend closer to MDF.
   - Measure: EV of river calls by seat class.
   - Expected edge: against a never-bluff-raiser the bluff-catcher has ≈0% of the 25.5% it needs (GTO Wizard). Human pools under-bluff river raises "at every stake" [expert]. For bots this is a prior to verify.
10. **One size per node, two on the river, small at tournament depths.**
    - Behaviour: flop c-bets in one size by texture bucket (20-33% on dry, paired and high-card boards; 66-75% on draw-heavy boards; check more on monotone and middling boards; 10-25% in shallow 3-bet pots). Turn ≈50% at ≤40 bb (no overbets below ≈40 bb). River ≈50% OOP or 75-100% IP, plus jam.
    - Measure: points, and latency (fewer branches).
    - Expected edge: one flop size vs three loses ≈0.01-0.02 bb; one river size loses 0.3% of the pot against 8 sizes. A one-size bot beat Slumbot 19.4 vs 13.1 bb/100 against a multi-size one. It also removes our own sizing tells (§5.5).
11. **Multiway mode (3+ players see the flop).**
    - Behaviour: c-bet less (checks +11 points; pot-sized c-bets 18% → 1.3%), no pure-air bluffs, value thresholds up, each player defends 1 − α^(1/n), prefer nut-potential hands. Squeeze ≈10-12% with a linear range and a bigger size (10 bb at 40 bb).
    - Measure: EV of multiway pots, points.
    - Expected edge: AQs in the BB gains ≈1 bb squeezing instead of calling with two callers in (3.21 vs 2.15 bb; §6.2).
12. **Sizing-tell reader per seat.**
    - Behaviour: per seat, log showdown strength by bet-size bucket and street. Once a bucket shows only value (e.g. ≥3 showdowns, all top pair or better), fold marginal bluff-catchers to it and attack the seat's other size. If a seat uses one fixed size, read its frequencies instead.
    - Measure: EV facing bets, per seat class.
    - Expected edge: no number; the nodelock example (large size = flushes only) turns most calls into folds (GTO Wizard, §5.7). Showdown data are biased, because folded hands are never seen, so require more evidence than the naive count suggests.
13. **Exploit gate: risk only what you have won.**
    - Behaviour: play the baseline against every seat. Enable a seat-specific deviation only when (a) its shrunk stat is outside the 95% interval of the equilibrium value with ≥10 opportunities (DBR's 10-step rule) and (b) our net chips won from that seat are positive. Cap the deviation's size by that surplus.
    - Measure: performance against the strong judge field (should not drop) and the weak field (should rise).
    - Expected edge: safe exploitation roughly doubled the static win rate against a random opponent in generalised Kuhn poker (0.270 vs 0.141) at no cost against an equilibrium opponent (−0.0609 vs −0.0611) (§7.4). Hyperion's history fits: most exploit levers gained against one rival and lost in the strong room.
14. **Multi-street bluff planning by whole-line EV.**
    - Behaviour: choose barrel lines by total line EV, not by the next street's fold rate. Prefer bet-bet-bet or bet-check-bet over bet-bet-give-up, and use blockers for river bluffs. Keep the river bluff share ≤ s/(1 + 2s) (25% at half pot, 33% at pot).
    - Measure: EV of bluff lines by line type.
    - Expected edge: in GTO Wizard's worked example the lines are worth +0.53, +0.45 and +0.03 pots; three pot-sized barrels need 72% river folds (§4.4).
