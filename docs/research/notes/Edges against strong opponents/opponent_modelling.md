# Opponent modelling and safe exploitation in 200-hand, 8-bot tables

Scope. The setting: Sequoia "No Limit" format, eight anonymous bots per sit-and-go, at most 200 hands, reads reset at every table, under 1 ms per decision in Python, scored by finishing position/ICM. The field mixes strong prepared bots that will try to exploit us with weak ones. These notes complement `../Sequoia poker bot competition prep/exploitative_play.md`, which covers archetype playbooks, chump-bot LBR numbers and push/fold. This file goes deeper on four things: how fast reads converge, how much to risk, how strong-but-rigid bots lose, and portfolio versus explicit models. Some sources there are re-cited here where needed.

**Bottom line.**
- **What the evidence measured.** Against strong opponents, adapting has historically cost money. Alberta's exploiting entries lost 8-37 mbb/g to every strong limit bot and 105-184 to strong no-limit bots, where their equilibrium siblings mostly won. They made it back, and more, only from weak and buggy bots ([Bard PhD 2016](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)).
- **What worked inside short matches** (1,000 to 3,000 hands, so still 5-15× our 200):
  - static strategies pre-tuned to the population;
  - small portfolios of robust responses;
  - narrow detectors for gift-giving bots;
  - probing the bet sizes of bots built on fixed size abstractions.
- **Recommended shape** (judgement): an unreadable, threshold-mixed baseline, plus gift detectors, plus Beta-shrunk pooled reads with a 10-observation trust floor. Exploits run only in pots that are heads-up against the target, under a small per-seat risk budget and a behavioural revert alarm.

Tags: **[Exp]** measured result; **[Theory]** proof or derivation in the source; **[Opinion]** practitioner or author judgement; **[Computed]** arithmetic or simulation done for these notes (script logic described inline; not from a source).

---

## 1. Small-sample modelling: priors, observation counts, archetypes

### Takeaway
At 200 hands, an explicit per-situation model of a strong bot will not converge. Even in Kuhn poker (a 3-card toy game) maximal exploitation took 200+ hands. What does work at this horizon:
- a weak prior (2 to 5 pseudo-observations) centred on a sensible default and shrunk toward it by `n/(n+s)`;
- best response to the posterior mean, not to the most likely archetype;
- a handful of pooled, fast-converging statistics.

Degenerate bots (always-call, always-raise, always-fold or timing out) are identified with certainty in about 5 hands. Stations take about 10 hands, and maniacs or random bots about 35. Nit, TAG and LAG cannot be told apart reliably from preflop frequencies inside 200 hands.

### Findings
- **[Exp] Kuhn poker, 200-hand matches (Hoehn, Southey, Holte & Bulitko, AAAI 2005).**
  - Parameter learning with a Beta prior took about 200 hands to nearly converge to the maximum exploitation rate against one opponent, and several hundred against others. "One cannot expect to achieve maximal exploitation in a small number of hands."
  - Exploring first and switching to the best response at hand 50 was "close to the best possible total winnings" for 50-, 100-, 200- and 400-hand games, across all six opponents.
  - Weak priors (Beta(1,1), i.e. 2 fictitious observations) "clearly do better than the strong" (20 fictitious), especially when the prior is wrong.
  - Among equal-value Nash strategies, the ones that explore more (γ > 0.7 in Kuhn) learned faster and won more in total.
  - — [Hoehn et al. 2005](https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf)
- **[Exp] Same paper, Exp3 over 7 experts (six pure strategies plus Nash).**
  - Exp3 with learning rate ρ = 1 and exploration ψ = 0.75 did worse than parameter learning in all but one case, and "does not converge within 900 hands."
  - Two tweaks helped at short horizons: keep a separate score per private card held, and share reward across experts that recommend the same action.
  - Caveat: Kuhn has only 2 opponent parameters, so explicit models are cheap there. Section 4 shows the ranking reverses in large games. — [Hoehn et al. 2005](https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf)
- **[Exp] Bayes' Bluff (Southey et al., UAI 2005), 200-hand trials.**
  - Leduc hold'em, opponents drawn from the prior: MAP and Thompson responses "converge within the first ten hands", while Bayesian best response was more erratic. The uninformed frequentist (Vexbot-style) model "is clearly behind".
  - Texas hold'em with a 10-parameter expert-informed prior: Thompson's and the frequentist model gave "very similar performance", with a small late edge to Thompson. The authors: "two hundred hands does not provide enough information to effectively concentrate the posterior on good models of the opponent in this larger game." They suggest strongly correlated priors are needed.
  - — [Southey et al. 2005](https://poker.cs.ualberta.ca/publications/UAI05.pdf)
- **[Exp] Respond to the posterior mean (Ganzfried & Sun).** With Dirichlet(2) priors, the exact Bayesian best response (EBBR, i.e. best response to the posterior mean) beat MAP and Thompson's responses. After 25 observations: EBBR +0.0002/hand, BBR −0.0065, MAP −0.2664, Thompson −0.2996, Nash −0.3751; game value −0.75 for the modeller's seat. The single-observation computation ran in under 8 µs, but numerically unstable (NaN) beta functions appeared from n ≈ 100 prior counts. — [Ganzfried & Sun, arXiv 1603.03491](https://arxiv.org/pdf/1603.03491)
- **[Exp/Method] DBBR's shrinkage formula (Ganzfried & Sandholm, AAMAS 2011).**
  - Posterior action probability = `(p*·Nprior + c_a) / (Nprior + Σc)`. Here p* is the equilibrium's probability at that public history and Nprior = 5.
  - DBBR played pure equilibrium for the first 1,000 hands of a 3,000-hand match and refit every 50 hands.
  - The authors warn that DBBR "might actually become significantly exploitable to strong opponents". They propose exploiting only when a running win rate clears a threshold. — [Ganzfried & Sandholm 2011](https://www.cs.cmu.edu/~sandholm/opponentModeling.aamas11.pdf)
- **[Theory+Exp] Confidence per decision point (Johanson & Bowling, DBR, AISTATS 2009).**
  - Data-biased response pins the opponent to the model with probability Pconf(I) at each information set I, instead of one global p.
  - Theorem 1: setting Pconf(I) = n_I/(s + n_I) is exactly the response that is robust to every independent Dirichlet prior of strength ≤ s.
  - Tested schedules: "1-Step" (trust after 1 observation) still overfit. "10-Step" (zero trust below 10 observations), "0-10 Linear" (trust rises linearly to Pmax at n = 10) and "1-Curve" (s = 1) did not overfit, "even at the last datapoint where Pmax is set to 1."
  - Unobserved decision points get Pconf = 0, meaning "assume a worst-case opponent" there, not a default policy.
  - — [Johanson & Bowling 2009](https://proceedings.mlr.press/v5/johanson09a/johanson09a.pdf)
- **[Exp] A single global trust parameter fails on thin data.**
  - Restricted Nash response (RNR) built from fewer than 100,000 observed games was "both more exploitable and less exploitive" than equilibrium as p rose. Data-biased response (DBR) with the 0-10 Linear schedule "perform[ed] well, regardless of the quantity of observations" tested (100 to 1M games).
  - Models built from self-play data (the opponent never visits some lines) were "of no use" for RNR. DBR still produced useful counter-strategies from that data.
  - For scale: heads-up limit per-game SD ≈ 6,000 mb/g, so ">1 million games" are needed to separate 10 mb/g at 95%. — [Johanson & Bowling 2009](https://proceedings.mlr.press/v5/johanson09a/johanson09a.pdf)
- **[Exp] Which features predict the next action (Poki, multiplayer limit hold'em).**
  - An offline neural net predicted real opponents' post-flop actions with "80% accuracy, and up to 90% in some cases."
  - The two strongest features were **previous action** and **previous amount to call**. Adding them as model contexts raised Poki's win rate against weak IRC players from about +0.09 to +0.22 sb/hand.
  - In the stronger game the gain was not significant (about +0.08). The new model was "more committal ... more successful against predictable players, but also more easily deceived against tricky opponents", e.g. by slowplays.
  - Baselines: no opponent modelling ≈ break-even; a generic model +0.08 and +0.05 sb/h. — [Davidson et al. 2000](https://poker.cs.ualberta.ca/publications/ICAI00.pdf)
- **[Exp] Opponents that change strategy (Bard & Bowling, AAAI 2007, Kuhn, 1,000 hands).**
  - A particle filter that wrongly assumed a stationary opponent "would actually lose money" against a switching opponent.
  - The best single fixed motion model across all five opponents was model C: switch probability 0.01 per hand, drift σ = 0.02.
  - Modelling even a static opponent with slight drift was beneficial. — [Bard & Bowling 2007](https://poker.cs.ualberta.ca/publications/AAAI07-om.pdf)
- **[Exp, 2026 preprint, not peer reviewed] Folds hide cards.** Showdown-only estimates "converge to behavior conditional on reveal, not overall behavior". Hands needed scale with 1/(half-width²) and inversely with how often the opponent continues to showdown. Implication: do not infer bluff frequency from shown-down hands alone. — [Guo, arXiv 2608.09954](https://arxiv.org/abs/2608.09954)
- **[Opinion] Practitioner HUD sample sizes:** see §1b.

### Computed here (binomial arithmetic and a small simulation; setup stated inline)
- **[Computed] Standard error of an observed frequency, sqrt(p(1−p)/n):**

  | n | p = 0.10 | p = 0.25 | p = 0.50 |
  |---|---|---|---|
  | 10 | ±0.095 | ±0.137 | ±0.158 |
  | 20 | ±0.067 | ±0.097 | ±0.112 |
  | 50 | ±0.042 | ±0.061 | ±0.071 |
  | 100 | ±0.030 | ±0.043 | ±0.050 |
  | 200 | ±0.021 | ±0.031 | ±0.035 |

  A 90% interval of ±0.10 needs 25, 51 and 68 opportunities for p = 0.10, 0.25 and 0.50; ±0.05 needs 98, 203 and 271. At 200 hands, only stats with an opportunity every hand (VPIP, PFR, preflop fold) reach ±0.05.
- **[Computed] Rule of three for deterministic tells.** If a bot has done the same thing in n of n identical spots, the 95% upper bound on its deviation rate is 1 − 0.05^(1/n): 0.45 at n = 5, 0.26 at 10, 0.14 at 20, 0.10 at 30. Ten to twenty consistent observations make a "this bot always does X here" read usable. That is far fewer than a mixed stat needs, which is why rigid bots are the cheapest to read.
- **[Computed] Archetype identification from preflop first action only.**
  - Setup: 9 archetypes defined by fold/call/raise probabilities (nit .86/.03/.11, TAG .78/.04/.18, LAG .68/.06/.26, station .50/.45/.05, maniac .30/.20/.50, uniform-random 1/3 each, always-call, always-raise, always-fold, each with 0.5% smoothing). Uniform prior over the 9; stop at posterior ≥ 0.95; 2,000 trials each.
  - Hands to a confident call (median / 90th percentile / share never resolved in 200 / share confidently wrong):

    | Archetype | Median | 90th pct | Unresolved | Wrong |
    |---|---|---|---|---|
    | Always-call | 5 | 5 | 0 | 0 |
    | Always-raise | 5 | 5 | 0 | 0 |
    | Station | 11 | 22 | 0 | 2.1% |
    | Folder / timeout | 22 | 45 | 0 | 0.2% |
    | Maniac | 35 | 79 | 0.4% | 6.8% |
    | Random | 34 | 81 | 0.1% | 8.4% |
    | LAG | 88 | >200 | 13% | 2.5% |
    | Nit | 109 | >200 | 18% | 5.2% |
    | TAG | 174 | >200 | 33% | 7.9% |

  - Lesson: classify the extremes and keep the "solid" cluster on the default strategy; maniac and random get confused about 7-8% of the time. Post-flop signals (fold-to-bet, raise frequency facing a bet) separate maniac from random faster, because a random bot folds to bets about a third of the time and a maniac rarely does.

### Inferences
- Use `posterior = (s·prior + k)/(s + n)` with s = 2 to 5, centred on our baseline's (or the population's) frequency. Act on the posterior mean, scaled by a DBR-style trust weight `n/(n + s)` and floored to zero below about 10 observations in that spot. This is DBR's 10-Step or 0-10 Linear schedule in table form, and it is O(1) per decision.
- Pool aggressively: one "folds to a bet" rate across streets and sizes, and one "raises when facing a bet" rate. Per-street, per-size cells will sit under 10 observations for the whole table.
- Key the model on previous action and amount to call (Poki's best features), not on the board.
- Discount old observations slightly (about 1% per hand, Bard & Bowling's best fixed setting), since adaptive bots will shift once they read us.

### 1b. Practitioner sample sizes (HUD stats)
- **[Opinion] Hands needed before a stat is usable, by source:**

  | Stat | BlackRain79 | Upswing (2020) | Poker Copilot |
  |---|---|---|---|
  | VPIP / PFR | 20 | ~300 | outline at 10, "good idea" at 100 |
  | 3-bet | 100 | ~1,000 | ≥1,000 |
  | Fold to 3-bet | 100 | ~1,500 | — |
  | Flop c-bet / fold to c-bet | 100 | "a few thousand" | — |
  | Turn c-bet and fold | 300 | — | — |
  | River c-bet and fold | 1,000 | — | — |
  | 4-bet / fold to 4-bet | 500 | — | — |
  | WTSD, W$SD, WWSF | — | ~8,000 | — |

  Other notes from the same sources:
  - BlackRain79: look at the opportunity count, at least 5 and ideally 10.
  - Poker Copilot: fold-to-c-bet is useful after "a few hundred" and reliable only at "thousands, if not tens of thousands".
  - Sources: [BlackRain79](https://www.blackrain79.com/2017/11/poker-hud-stat-sample-size.html); [Upswing HUD guide](https://upswingpoker.com/poker-hud/); [Poker Copilot VPIP/PFR](https://pokercopilot.com/poker-statistics/vpip-pfr); [Poker Copilot c-bet](https://pokercopilot.com/poker-statistics/continuation-bet)
- **[Opinion+anecdote] Count opportunities, not hands.** One player had only 11 c-bet opportunities in 300 hands, which scales to about 7 per 200-hand table. — [Laplante via PokerNews](https://www.pokernews.com/strategy/teachable-moments-from-twitch-ryan-laplante-hud-stats-32348.htm)
- **[Math] Standard error √(p(1−p)/n), n = opportunities.**
  - At 95%: a 50% stat is ±21.9 points at n = 20 and ±9.8 at n = 100. A 25% stat is ±19.0 and ±8.5.
  - Telling a 35% from a 46.5% button-open rate needs about 73 opportunities, roughly 438 hands at 6-max.
  - Solver opening frequencies (GTO Wizard NL200): BTN 46.5%, CO 30.6%, LJ 18.5%.
  - — [poker.academy](https://poker.academy/blog/post/poker-hud-for-you-take-the-advantage)
- **[Math] Use Wilson or Agresti-Coull "plus four", (x+2)/(n+4), not the Wald interval.** At small n or p near 0 or 1 (0/3, 3/3) the Wald interval collapses. — [Wikipedia: binomial proportion CI](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval)
- **[Opinion, unsourced data] Population priors for human regulars.**
  - Upswing (6-max): VPIP ≈ 25, PFR ≈ 19, 3-bet ≈ 8, WTSD ≈ 30, fold to 3-bet 40-50, fold to c-bet "generally below 50".
  - Poker Copilot: regulars 19/17 to 25/23; fish 40/15, 52/5 or 75/10; fold to c-bet 42-57% for good low-stakes players; 3-bet 5-9%.
  - These describe human pools. A bot field's prior should come from our baseline's own frequencies or from practice logs.
  - — [Upswing](https://upswingpoker.com/poker-hud/); [Poker Copilot blind stealing](https://pokercopilot.com/poker-statistics/blind-stealing)
- **[Exp] Uninformed priors can be worse than none.** Three-player Kuhn, 3,000-hand matches (Ganzfried, Wang & Chiswick, arXiv 2212.06027):
  - With the prior mean set to a Nash strategy (strength η = 4 pseudo-counts per decision), multiplayer Bayesian best response scored 48 millichips/hand: first of 14, above the best Nash agent's 37.
  - With a flat Dirichlet(2) prior it fell to −54, second to last. "It is critical to use an informed prior mean strategy."
  - Starting to exploit at hand 0 or at hand 200 made little difference; η from 1 to 8 barely mattered.
  - — [Ganzfried, Wang & Chiswick](https://arxiv.org/pdf/2212.06027v4)

---

## 2. Safe exploitation: how much to risk, and how to tell we are being counter-exploited

### Takeaway
The exploitation-versus-exploitability curve is highly concave. Restricting a counter-strategy to about 100 mb/h of worst-case loss keeps a large share of the exploitation of weak bots. It loses only 11 to 45 mb/h to an equilibrium bot, while a pure best response loses up to 620 to bots it was not built for. "Safe" schemes that risk only what has been won (RWYWE) are robust but give up most of the gain against near-equilibrium opponents with mild leaks. Detecting counter-exploitation from results is nearly hopeless inside 200 hands unless the leak exceeds about 1 bb/hand: guard structurally, not statistically.

### Findings
- **[Exp] Pure best responses are brittle.** Frequentist best responses (FBR) against 7 limit bots (Johanson, Zinkevich & Bowling, NIPS 2007):
  - Each FBR beat its target: PsOpti4 137 mb/h (vs a previous best of 75), A60 2,170, A80 1,048.
  - The same strategies lost to other bots: 20 to 442 mb/h to PsOpti4, and 41 to 620 mb/h to the equilibrium bot CFR5.
  - Every FBR except the one trained on A60 lost to A60, even though A60 "is exploitable for over 2000 mb/h". FBR row averages: −148 to +3. CFR5 averaged +56. — [Johanson et al. 2007](https://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf)
- **[Exp] Restricted Nash responses, with p chosen so exploitability ≈ 100 mb/h.**
  - Exploitation of their target: PsOpti4 85 (FBR 137, CFR5 36); A60 582 (FBR 2,170, CFR5 93); A80 293 (FBR 1,048, CFR5 41).
  - Losses to CFR5 were only 11 to 45 mb/h. Row averages were +43 to +78, against +56 for CFR5.
  - "The curves are highly concave meaning that dramatic reductions in exploitability can be achieved with only a small sacrifice in the ability to exploit the model."
  - Mixed with UCB1 over 4 RNR experts in 1,000-hand matches, RNR experts beat the equilibrium against two unseen "holdout" bots; FBR experts did not. — [Johanson et al. 2007](https://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf)
- **[Exp] Safe opponent exploitation (Ganzfried & Sandholm, TEAC 2015), Kuhn poker, 1,000-hand matches, 40,000 opponents per class.**
  - Setup: Dirichlet prior of 5 fictitious hands at equilibrium. Win rates in $/hand; game value −0.0556.

    | Opponent | RWYWE (risk what you've won) | Best Equilibrium | Unsafe best response |
    |---|---|---|---|
    | Random | 0.3636 | 0.1450 | 0.4700 |
    | Near-equilibrium static (±0.2 per action) | −0.0110 | −0.0148 | **+0.0548** |
    | Dynamic (random for 100 hands, then nemesis) | −0.0204 | −0.0352 | **−0.1209** |

  - Reading: safety costs little against gift-givers, but most of the available edge against mildly unbalanced, stationary opponents. Unsafe responses collapse against opponents that switch to counter-exploit.
  - Full safety is possible only if the opponent gives "gifts" (dominated plays). Computing ε-safe best responses needs an LP on the scale of equilibrium computation. — [Ganzfried & Sandholm 2015](https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf)
- **[Exp] Exploiting cost the adaptive entry real money against strong opponents (ACPC 2013 heads-up limit, 3,000-hand matches).**
  - Alberta's portfolio agent (Hyperborean TBR) vs its own equilibrium entry (Hyperborean IRO): TBR lost to every strong bot, while IRO beat four of the five (marv −37 vs +15; zbot −26 vs +10; littlerock −11 vs +22; propokertools −8 vs +27; neo poker lab −32 vs −11 mb/g).
  - TBR won more against weak bots (liacc 527 vs 390; slugathorus 617 vs 441). Net average was +149 vs +131, i.e. +13.3%.
  - In no-limit 2013, the more aggressive DBR (Pmax 0.5) won more uncapped on the benchmark server but "performed poorly against equilibrium-based opponents". The team shipped Pmax 0.25, which still beat weak bots by more than the 750 mbb/g cap. — [Bard PhD thesis 2016, §6.2](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Exp] Tilted strategies: exploitative-leaning variants at almost no worst-case cost.**
  - Polaris 2008 switched between 5 component strategies "of varying aggressiveness". Some were equilibria of "tilted" games, e.g. +7% payoff when winning a showdown, or −7% when folding.
  - In the untilted game the tilts were exploitable for 227 to 264 mbb/g, against 235 for the plain equilibrium in the same 266m abstraction. A sweep found a 4% winner bonus at 261.2 vs 267.2 for the equilibrium.
  - Aggression bias can be added offline without raising exploitability. — [Johanson PhD thesis 2016, Table 2.3 and §2](https://poker.cs.ualberta.ca/publications/2016-johanson-phd-thesis.pdf)
- **[Exp, 2026 preprint] Certify before you exploit.** Track action frequencies with anytime-valid confidence sequences. Treat a deviation as exploitable only once its interval separates from the equilibrium reference, then solve a restricted response and check it with a full best response before deploying. Reported 6.2× the steady-state gain of a binary "verified by money won" gate in Leduc, with every deployed strategy inside the risk budget. — [Li & Huang, arXiv 2607.28520](https://arxiv.org/abs/2607.28520)
- **[Theory] "Get taught and exploited".** An opponent can play aggressively, let us adapt, then switch. Risking "only the amount won so far" is not by itself safe in the finitely repeated game. The safe version is ε-safe best response with ε = gifts accrued in expectation. — [Ganzfried & Sandholm 2011](https://www.cs.cmu.edu/~sandholm/opponentModeling.aamas11.pdf); [Ganzfried & Sandholm 2015](https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf)
- **[Exp] Results are noisy; variance reduction helps (AIVAT, heads-up no-limit at 100bb).**
  - Raw per-hand SD was about 26 chips at 1/2 blinds (≈ 13 bb/hand).
  - AIVAT, using one agent's own strategy plus a value function, cut SD by "a bit more than 68%" (to ≈ 8.3 chips), "the same statistical significance with ten times less data".
  - Even the simpler MIVAT with imaginary observations cut SD by 39%. — [Burch et al., AIVAT, arXiv 1612.06915](https://arxiv.org/pdf/1612.06915)
- **[Computed] Hands needed to detect that one opponent is beating us (one-sided 90%, n = (1.28·SD/δ)²):**

  | Loss rate δ | Raw chips (SD 13 bb) | AIVAT-like (SD 4.15 bb) |
  |---|---|---|
  | 0.25 bb/hand | 4,442 | 453 |
  | 0.5 bb/hand | 1,111 | 114 |
  | 1 bb/hand | 278 | 29 |
  | 2 bb/hand | 70 | 8 |

  Inside one 200-hand table, results-based alarms only catch catastrophic leaks, and only with luck-adjusted accounting (at minimum, all-in equity instead of outcome).

### Inferences
- Budget per opponent. Deviate from the baseline only as far as an RNR/DBR-like trust schedule allows. Size the total deviation against any seat so that a fully adapted opponent wins back at most about 0.1 to 0.2 bb/hand; this mirrors the ≈100 mb/h ε that worked for RNR. Exploit far harder (up to a full best response) only against seats showing "gifts": dominated actions such as folding when checking is free, calling all-ins with trash, timeouts, illegal-action fallbacks.
- Detect counter-exploitation by behaviour, not results. Compare the opponent's response frequencies before and after our deviation started (for example, their raise-vs-our-c-bet rate). A jump bigger than about 2 SE once we turned on an exploit is the alarm; then revert to baseline for that seat. Adaptive bots will have to show their adaptation in exactly the stat our exploit leans on.
- Luck-adjust the per-seat ledger: all-in EV for all-ins, and equity at showdown. This makes the "won so far" budget usable within 200 hands.

---

## 3. Exploiting strong but predictable bots, and hiding our own tells

### Takeaway
Strong equilibrium-style bots are beaten through their rigidities, not their frequencies:
- fixed bet abstractions, exploited by off-tree sizes and tiny bets mapped badly;
- coarse card abstractions, exploited by local best response with a single pot-sized bet;
- determinism.

Purifying (de-randomising) a strategy often wins more against other bots, but it raises worst-case exploitability by up to +86% and leaks information; a threshold around 0.15 was the sweet spot in one test. Past ACPC fields rarely adapted: 15 of the 17 described 2010 entries played fixed strategies, and no 2012 no-limit entry exploited bet sizes. Purified bots therefore went unpunished. A field built specifically to exploit us will not be so forgiving.

### Findings
- **[Exp] Local best response (LBR) against top no-limit ACPC bots (Lisý & Bowling 2017).**
  - Lower bounds on exploitability with fold/call only: 1,048 (Hyperborean 2013), 721 (Hyperborean 2014), 522 (Slumbot 2016), 407 (Act1 2016) mBB/h.
  - Adding pot and all-in on streets 3-4 raised them to 4,040, 3,852, 4,020 and 2,597. "Most of the exploitation of LBR against all bots is realized with only using a single pot-bet option."
  - Against a random-legal-action bot, LBR with fold/call/pot/all-in on streets 3-4 wins 80.7 BB/h, because after an all-in "the bot will fold half of his hands." — [Lisý & Bowling, arXiv 1612.07547](https://arxiv.org/pdf/1612.07547)
- **[Exp/Theory] Bets between a bot's fixed sizes (Ganzfried & Sandholm, IJCAI 2013).**
  - All prior heuristic translation mappings are "highly exploitable", and deterministic mappings more so than randomized ones.
  - Bots that "map small bets to the smallest positive betting size in the abstraction (e.g., ½ pot) ... could be significantly exploited by an opponent who makes extremely small bets as bluffs."
  - Their pseudo-harmonic mapping, f(x) = (B − x)(1 + A) / ((B − A)(1 + x)) for a bet x between abstract sizes A < B (pot fractions), had zero exploitability in the clairvoyance game and "performs competitively" against 2012 ACPC agents. — [Ganzfried & Sandholm 2013](https://www.ijcai.org/Proceedings/13/Papers/028.pdf)
- **[Exp] Purification: less randomness, more profit against bots, more exploitable.**
  - 2010 ACPC no-limit: Tartanian4-TBR (always plays the highest-probability abstract action) beat its sibling Tartanian4-IRO (threshold 0.15) head-to-head by 80 mbb/h. It did better against every opponent but one and won total bankroll. "The opponents ... were either not trying or not able to find successful exploitations." Of 17 described 2010 entries, "15 played fixed strategies".
  - In limit, purification raised Hyperborean's exploitability from 235 to 437 mbb/h (+86%). GS6 was least exploitable at an intermediate threshold of 0.15 (318 mbb/h, vs 464 unrounded and 350 purified).
  - The authors' explanation: "If there is too much thresholding, the resulting strategy does not have enough randomization, so it signals too much to the opponent about the agent's private information."
  - In Leduc, purification improved 19 of 24 abstract strategies against an equilibrium opponent; the best went from −43.8 to −1.86 mb/h. — [Ganzfried, Sandholm & Waugh, AAMAS 2012](https://www.cs.cmu.edu/~sandholm/StrategyPurification_AAMAS2012_camera_ready_2.pdf)
- **[Exp] Buggy and chump bots decide totals.** ACPC organisers capped per-match winnings at 750 mbb/g because "buggy agents (e.g., POMPEIA in the 2011 heads-up no-limit competition) ... effectively decided the outcome of several total bankroll events."
  - Alberta's 2012 entry kept dedicated counter-strategies for always-raise and always-call opponents, used "only when the opponent was detected" as such. They dropped them in 2013 because the portfolio already hit the cap against such bots.
  - Weak bots also lost heavily to plain equilibria: unamur tbr lost to zbot (CFR) at 187 mbb/g against a worst loss of 213. — [Bard PhD thesis 2016, §6.2](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Exp] Static imitation was hard to beat.** Marv Andersen's total-bankroll winners (Calamari 2011; marv/Bacalhau 2013; Escabeche 2014) were "stationary strategies generated by training a neural net to imitate the play of previous ACPC winners", yet "consistently managed to be successful ... by striking an effective balance between performance against strong agents and capitalizing on exploitable agents." — [Bard PhD thesis 2016](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Opinion, from the existing notes] One-hour CFR bots use 2-size abstractions.** The 2017 MIT Pokerbots winner bet only 66% pot or all-in, raised only pot or all-in, and mapped off-tree bets to the nearest abstract action. — [Chintamaneni 2017](https://github.com/Fro116/Pokerbots)
- **Student-competition write-ups:** see §3b.

### Inferences
- Probe for fixed sizing and deterministic responses in the first orbit. Then use: (a) a bet size halfway between their apparent sizes (geometrically); (b) a tiny bet (≈10-20% pot) as a cheap bluff against bots that map it up to ½ pot; (c) a pot-sized bet on turn and river against bots that fold too much to it. The off-tree probe costs little if our own baseline defends with the pseudo-harmonic call frequency 1/(1 + x).
- For our own play, keep a threshold-style mix rather than full purification. Drop actions under about 10-15% probability and renormalise the rest, and never let size encode strength (one size per spot for value and bluffs, or two sizes each with both). The ACPC evidence says deterministic play wins more against static bots. The GS6 and Hyperborean numbers say full purification costs 10-86% more worst-case exploitability than the best threshold, which a strong adaptive field will collect.
- Randomness in Python costs time, not chips. One `random()` call per decision, or a hash of the hand id and seat, is microseconds. The chip cost of mixing is only the EV gap between near-indifferent actions.

### 3b. Student and competition write-ups: who beat whom, and how
- **[Exp] Bet-size probing won the 2009 no-limit bankroll event.**
  - Hyperborean-BR "would perform exploration by raising different amounts and observing the opponent's response". It then exploited translation errors if its model said that would work, otherwise it fell back to soft-translation equilibrium.
  - Average 1.42 sb/h against 0.27 for its equilibrium twin.
  - In 2007, PokeMinn's no-limit bot, second to last overall and possibly "written the night before", beat second-placed GS3 by **42.06 sb/h**. GS3's fold/call/pot/all-in abstraction misread over-pot bets.
  - — [Schnizlein MSc 2009](https://poker.cs.ualberta.ca/publications/schnizlein.msc.pdf)
- **[Exp] Lab tests of translation exploits.** A bot that ignores its own cards beat a hard-translation player by 27.01 $/h but lost 5.66 to soft translation. "Bet big with top 25%, small otherwise" won 5.42 against hard translation and 1.50 against soft. — [Schnizlein, Bowling & Szafron, IJCAI 2009](https://poker.cs.ualberta.ca/publications/IJCAI09-nolimit.pdf)
- **[Exp] Even 2012-era fields did not punish exploitable translation.** The most exploitable mapping still did best on average against the 2012 ACPC field, because "none of the programs ... were attempting any exploitation of bet sizes". — [Ganzfried & Sandholm 2013](https://www.ijcai.org/Proceedings/13/Papers/028.pdf)
- **[Exp] No-limit 2013-2014: the exploiter lost to every strong bot but topped the uncapped table.**
  - Hyperborean TBR lost to Slumbot, Nyx, Tartanian6, LittleRock and Koypetition, e.g. Tartanian6 −105 ± 91 and LittleRock −111 ± 84 mbb/g. The equilibrium sibling beat those two at +38 and +133.
  - It crushed weak bots: HITSZ 8,927 vs 542 for the sibling; liacc 5,709 vs 3,204.
  - The equilibrium sibling played its common equilibrium "until the opponent is observed making a minimum-sized bet on at least 1% of the hands played so far", then switched to a min-bet-aware strategy. That is a cheap, narrow trigger.
  - In 2014 the top static bots already took 90.8-92.2% of the capped value available from the four weak bots, leaving "a slim margin" for adaptive play.
  - — [Bard PhD thesis 2016, Tables 6.10-6.12](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Exp] Sartre's opponent-type adaptation.** No adaptation for the first M = 300 hands, then classify the opponent by bet frequencies. Against unseen opponents, only 2 of 5 adapted variants (N = 4, 5) improved significantly, and Bard et al. call the gain "marginal". — [Rubin PhD 2013](https://www.cs.auckland.ac.nz/research/gameai/dissertations/Rubin_PhD_13.pdf); [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **[Exp] Humans found Claudico's sizing leak.** Humans won 9.16 BB/100 over 80,000 hands. Raises just off the bot's sizes made it misjudge the pot (folding A4s after committing over half its stack). Doug Polk called translation its "biggest weakness". — [Ganzfried, arXiv 1510.08578](https://arxiv.org/pdf/1510.08578)
- **[Self-report] MIT Pokerbots 2013 (JJR, 2nd in the new-team bracket).**
  - Played a flat strategy for the first **20 hands** to observe.
  - Tracked raises, all-ins, calls, 3-bets and c-bets per street and position.
  - Aggression score 1.2·raises + 1.5·3-bets + 2.0·all-ins + 1.2·c-bets, passed through sigmoids to set raise size (1-5× min-raise) and an equity adjustment (0.5-0.85).
  - Never tuned on data. — [Rubin 2013 strategy PDF](https://raw.githubusercontent.com/JeremyRubin/pokerbots2013/master/Strategy.pdf); [project page](https://www.mit.edu/~jlrubin/projects/pokerbots/)
- **[Self-report] MIT 2017 winner (CFR, no modelling).** Pruned actions ≤10% probability to zero. The author identified a tell he never fixed: "didn't discard" read as a strong hand. — [Fro116 report](https://raw.githubusercontent.com/Fro116/Pokerbots/master/report.pdf)
- **[Anecdote] MIT 2017 SPAM tuned offline to scrimmage logs.** The field had many "aggressive all in bots", so they tightened and became wary of huge raises. CFR bots folded to large raises, so they bet smaller with strong hands. — [SPAM README](https://github.com/sebLopezCot/SPAM_pokerbot_2017)
- **[Organiser slides] MIT Pokerbots 2025 and 2026 final debriefs.**
  - Winners inferred hidden bounty cards "from bet sizing", i.e. sizing leaked private information.
  - They used "unconventional bet sizes to push opponents into unfamiliar spots" and "infer[red] opponent playstyle over game history with hand crafted features".
  - Winners "check folded the last ~100 hands" once a binomial model said the lead was safe.
  - — [MIT 2026 final presentation](https://raw.githubusercontent.com/mitpokerbots/class-resources-2026/main/Final%20Presentation.pdf); [MIT 2025 final event](https://raw.githubusercontent.com/mitpokerbots/class-resources-2025/main/Slides/finalevent.pdf)
- **[Course opinion] MIT 2026 Lecture 3.** "Easy to read = Exploitable ... Almost never want to do one action at 100% frequency." The worked all-in-bot counter calls at equity ≥ 0.4975 with 400-chip stacks. Lecture 6 suggests a bandit over bots per hand or per 25-hand block. — [Lecture 3](https://raw.githubusercontent.com/mitpokerbots/class-resources-2026/main/Lectures/Lecture%203.pdf); [Lecture 6](https://raw.githubusercontent.com/mitpokerbots/class-resources-2026/main/Lectures/Lecture%206.pdf)
- **[Self-report, internal A/B] IIT Pokerbots 2026, 1,000-hand matches.**
  - Tracked VPIP, PFR, fold-to-bet and post-flop aggression, with classes for shove-bot, station and LAG.
  - All-in call thresholds: 0.65 vs rare raisers, 0.52 vs shove-bots, 0.60 by default.
  - Hid tells by adding uniform(0, 0.12)·pot noise to sizes and ±0.02 to the river call threshold.
  - Final version went 154-92. "Tighter when behind" went 17-23 against baseline ("more predictable and exploitable"). Removing a log-visible "leak" went 15-25, because logs hide the fold equity lost.
  - — [snivellus38/pokerbots_2026](https://github.com/snivellus38/pokerbots_2026)
- **[Self-report] IIT 2026, 2nd of 400+.** Recalibrated the opponent model every 18 hands, blending recent and cumulative behaviour, and picked from about 120 variants by best-of-N round robins favouring "low variance, and limited overfitting". Another team (49th of 500) found a standalone profiling bot "overfit to specific opponent styles". — [anantjain29](https://github.com/anantjain29/iit-pokerbots-2026); [Bhavana-B-del](https://github.com/Bhavana-B-del/IITM-Pokerbots-2025)
- **[Self-report + code] CMU AI Poker 2024, 2nd place.** One read only: after ≥10 hands, if the opponent went all-in on more than 98% of them, call with equity above 0.5, otherwise check-fold. — [kawashite/poker-engine-2024](https://github.com/kawashite/poker-engine-2024)

---

## 4. Implicit modelling and portfolios versus explicit models over short horizons

### Takeaway
In large games, a small portfolio (about 4) of precomputed robust responses, selected online by an Exp3/Exp4-style bandit with a probability floor and off-policy value estimates, beat explicit modelling, a single static exploitative strategy, UCB selection, and a 13-strategy portfolio. It would have won the 2011 ACPC limit total bankroll. In small parameter spaces (Kuhn), explicit Beta-parameter learning beat Exp3. For 1,000-hand three-player matches, Alberta shipped a static response to pooled population data and won by 84%. At 200 hands, a static population-exploitative baseline plus a 3-4-arm portfolio is the evidence-backed design.

### Findings
- **[Exp] Online implicit modelling (Bard, Johanson, Burch & Bowling, AAMAS 2013; 3,000-hand heads-up limit matches; 95% CI ±7 mbb/h).**
  - Portfolio: DBR responses to 2010 ACPC agents (13 agents, ≥8.4M full-information hands each), each tuned to be exploitable for only about 100 mbb/h. A 4-response portfolio was chosen greedily (a submodular, 1 − 1/e approximation).
  - Selector: Exp4 with temperature η = 0.025 and a 2% minimum probability per expert. "Performance was largely insensitive to these parameter choices."
  - Off-policy importance sampling plus imaginary observations, over all private cards and early folds, scored every arm on every hand. This needs the mixture to keep every arm's support, which UCB, playing one arm at a time, cannot do.
  - Results: against 4 known mimics, nearly double the equilibrium's winnings and ≥19.9% over any single response. Against the 13-agent field, about 65% over equilibrium. The small portfolio beat the big one against known mimics and tied it against the field. UCB had higher variance (±13 mbb/h).
  - Replayed on the 2011 ACPC benchmark: the small portfolio scored 317 ± 5 mbb/h, against the winner Calamari's 276 ± 4. Alberta's actual 2011 entry scored 224.
  - — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **[Exp] Static responses to the population won the short multiplayer matches.** 2013 and 2014 ACPC three-player limit (1,000-hand matches in 2013):
  - Alberta deliberately shipped a static DBR to aggregate data of all 2011-2012 entrants, since "the shorter 1,000 hand matches ... would provide even less time for an adaptive agent to learn."
  - It won by 84.3% (2013) and 40.1% (2014) over second place, and averaged 33.8% and 35.2% more than Alberta's own larger equilibrium-style entry.
  - Caveat: in head-to-head internal tests it lost to the equilibrium entries at 10 ± 2 mbb/g. — [Bard PhD thesis 2016, §6.2.2](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Exp] Portfolios fail when coverage is thin.** In 2013-2014 heads-up limit the portfolio agent placed 3rd. It under-exploited chump9 (272 vs Slugathorus's 984 mbb/g) and liacc/slugathorus, which the author reads as "insufficient coverage over the space of opponent strategies." — [Bard PhD thesis 2016](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Exp] Earlier portfolios.**
  - UCB1 over 4 RNR experts beat equilibrium against unseen bots in 1,000-hand matches; FBR experts did not. — [Johanson et al. 2007](https://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf)
  - Portfolios of expert imitators (Rubin & Watson, IJCAI 2011) gave "negative or statistically insignificant" results, and opponent-type adaptation for case-based strategies gave "a marginal improvement" (as summarised by Bard et al. 2013). — [Bard et al. 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)
- **[Exp] Kuhn reverses the ranking.** Parameter learning beat Exp3 strategy selection in all but one of six opponents over 200 hands. — [Hoehn et al. 2005](https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf)
- **[Exp] Cluster by response, not by behaviour.** Grouping opponents by which response works best gave "dramatically improved clusterings" over k-means on behaviour, judged by the utility of responding to the clusters (toy poker games). — [Bard et al., AAMAS 2015](https://poker.cs.ualberta.ca/publications/2015-AAMAS-response-clustering.pdf)

### Inferences
- Short horizons favour a few arms. Bandit regret grows with the number of arms. Bard's 4-arm portfolio beat the 13-arm one, and Exp4 needed a 2% floor plus off-policy scoring to learn within 3,000 hands. At 200 hands, where we sit in each position relative to each seat only about 25 times, use 3 or 4 arms: baseline, value-heavy/no-bluff (vs stations), pressure (vs folders), and tight-call-down (vs maniacs). Score every arm on every hand off-policy.
- Off-policy scoring is cheap if each arm is a parameter offset on the same baseline (thresholds on equity, bluff ratio, sizing). Score an arm by asking "would this arm have taken the same action here?" combined with luck-adjusted outcomes. That stays well under 1 ms.
- Explicit or implicit? A hybrid. Use explicit Beta-shrunk counts for the 4-6 pooled stats that converge (Kuhn-like, few parameters). Use implicit arm selection where we cannot model (river behaviour, sizing reactions).

---

## 5. Multi-player tables: targeting the weakest seat without leaking to strong seats

### Takeaway
No study measures, in multiway no-limit, how exploiting a weak seat shifts EV to the strong seats. The evidence that exists points one way:
- In 3-player limit, a style that "beat up on chumps" ranked first on total winnings but was "exploited by the IR16 agents" once only one chump remained.
- The 6-player 2008 runner-up won mostly by exploiting one weak opponent while losing to 3 of 6.
- Equilibrium gives no protection in 3+ player games.

Operational rule: exploit inside pots that are heads-up against the target. Keep the baseline whenever a strong seat is still in the hand. Iso-raise the weak seat, tighter as more (or more aggressive) players remain behind. No pure bluffs multiway.

### Findings
- **[Exp] Farming chumps leaks to strong players (Abou Risk MSc, 3-player limit, 7 agents, 35 matchups of 1.2M duplicate hands).**
  - Multi2 "is clearly the best exploitative player ... able to really beat up on chumps". But "when only one chump (Probe) remains, Multi2 is exploited by the IR16 agents and falls behind" in the runoff.
  - Total-bankroll and runoff rankings disagreed.
  - — [Abou Risk MSc 2010](https://poker.cs.ualberta.ca/publications/abourisk.msc.pdf)
- **[Exp] Win by targeting one weak seat (6-player limit, ACPC 2008, runner-up AKI-RealBot).**
  - A player counted as "weak" if it had "lost money to AKI-RealBot over the course of the last 500 hands". AKI-RealBot then folded less preflop against it, even when folding was the EV choice.
  - "Its success was largely due to its ability to exploit one weak opponent ... while it lost to 3 out of the 6 agents."
  - — [Rubin PhD 2013, §2](https://www.cs.auckland.ac.nz/research/gameai/dissertations/Rubin_PhD_13.pdf)
- **[Exp] A static population response won 3-player limit** (84.3% and 40.1% margins), as covered in §4. — [Bard PhD thesis 2016](https://poker.cs.ualberta.ca/publications/bard.phd.pdf)
- **[Exp] Multiplayer Bayesian best response works with an equilibrium-centred prior** (+48 vs +37 for the best Nash agent; −54 with a flat prior), as covered in §1b. The paper does not measure effects on the other seats. — [Ganzfried, Wang & Chiswick](https://arxiv.org/pdf/2212.06027v4)
- **[Theory] Utility transfer at no cost.** In three-player Kuhn equilibria, one player "completely controls an amount of utility, κβ, that can be transferred from P1 to P3". Equilibria are not interchangeable. — [Szafron, Gibson & Sturtevant, AAMAS 2013](https://poker.cs.ualberta.ca/publications/AAMAS13-3pkuhn.pdf)
  - GTO Wizard restates this: multiway equilibrium does "not guarantee protection against exploitation". They found no realistic hold'em example of large transfers. [Solver/Opinion] — [GTO Wizard multiway quirks](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/)
- **[Exp] Pluribus does not adapt, by design.** "Pluribus plays a fixed strategy that does not adapt to the observed tendencies of the opponents." Moving to an exploitative strategy "opens oneself up to exploitation because the opponent could also change strategies at any moment." It won 48 mbb/game (SE 25) with 5 humans plus 1 AI, and 32 (SE 15) with 1 human plus 5 AIs. — [Brown & Sandholm, Science 2019](https://par.nsf.gov/servlets/purl/10119653)
- **[Solver] Multiway defence and bluffing.**
  - Required defence per player falls with more players. Against a 10%-pot bet: about 91% defence heads-up, about 26% each with 8 defenders.
  - "Pure bluffs are ineffective multiway ... almost never bluff without solid drawing equity."
  - When a second caller is in, the preflop raiser's pot-sized c-bet frequency drops from 18% to 1.3%.
  - — [GTO Wizard multiway tips](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/); [GTO Wizard vs two callers](https://blog.gtowizard.com/playing-in-position-against-two-callers/)
- **[Opinion] Isolation sizing and range.**
  - Iso-raise to 4bb + 1bb per limper (+1bb out of position). Upswing online: 3bb + 1bb per limper, stepping to 6-7bb against snap-callers.
  - Iso the top ~50% of hands in position and ~40% out of position.
  - Tighten iso ranges with more players behind, or with "looser, more aggressive players behind".
  - With a strong regular on your left, "just leave the table".
  - — [PokerStrategy sizing](https://www.pokerstrategy.com/strategy/weekly-no-limit/bet-raise-sizes-preflop/); [Upswing via PokerNews](https://www.pokernews.com/strategy/10-tips-that-will-help-you-destroy-limpers-32206.htm); [Baker via CardPlayer](https://www.cardplayer.com/?p=1091927); [BlackRain79 isolating fish](https://www.blackrain79.com/2015/11/isolating-fish-complete-how-to-guide.html)
- **[Opinion] Seat geometry.** Pros want the fish on their right and strong players not on their left. In limit, avoid the seat directly left of a maniac; sit 3-4 seats left with weak callers between. Seats are fixed in a bot SNG, but position relative to each seat is known from hand 1. — [CardPlayer Head Games](https://www.cardplayer.com/?p=1036752); [Slotboom, CardPlayer](https://www.cardplayer.com/cardplayer-poker-magazines/59-howard-lederer-16-7/articles/13174-choosing-the-best-seat-versus-a-maniac)
- **[Solver] ICM changes which seat to target.**
  - Bubble factors average about 1.6 on the money bubble. Medium stacks against the chip leader reach 2.06, i.e. 67% equity needed to call. A 9bb stack on the money bubble is at 2.06.
  - Chip leaders "can call all-ins much more liberally". "Taking on the big stack is often ICM suicide."
  - ICM "underestimates the chip leaders' advantage". Real players: "big stacks often under-push, short stacks over-call or over-fold."
  - — [GTO Wizard bubble factor](https://blog.gtowizard.com/what-is-the-bubble-factor-in-poker-tournaments/); [GTO Wizard money vs final-table bubble](https://blog.gtowizard.com/money-bubble-vs-final-table-bubble/); [GTO Wizard ICM basics](https://blog.gtowizard.com/icm-basics/); [ICMIZER](https://blog.icmizer.com/high-cost-of-not-being-aggressive-enough/)
- **[Exp] 3-player jam/fold equilibrium versus ICM.** ICM differs from equilibrium tournament values by $0.37 per $100 on average, at most $2.99. Tournament strategies "differ substantially" from single-hand strategies. — [Ganzfried & Sandholm, AAMAS 2008](https://www.cs.cmu.edu/~sandholm/3-player%20jam-fold.AAMAS08.pdf)

### Inferences
- **Keep a per-seat model, but apply exploits per pot.** If every other live player in the hand is a "gift" or weak seat, use the exploit offsets. If any seat classed strong or unknown is live, play the baseline. This keeps the strong seats' view of us close to the baseline, so they have less to adapt to, while weak seats still get punished in the pots they enter.
- **Isolate rather than limp along.** An iso-raise against a station or limper denies the strong seats a cheap multiway pot and creates the heads-up pot where our exploit is safe.
- **Do not let one seat crowd out survival.** Under ICM scoring, chips taken from a weak seat are worth less than chips lost to a strong seat. Prefer exploits with low variance (thin value against stations) over high-variance ones (hero calls against maniacs) when we are a medium stack facing a big stack.

---

## Testable for a bot

Twelve mechanisms, ranked by expected gain against a strong, adaptive field. The ranking and the gain estimates are judgement built on the evidence cited above, not measurements in this format. All mechanisms are O(1) table lookups and counter updates, well inside 1 ms.

**Suggested harness.** One test field, used for every mechanism:
- gift bots: always-call, always-shove, always-fold/timeout, uniform-random-legal, min-bet spammer;
- styles: station, maniac, nit;
- a "rigid prepared" bot (CFR-like, 2 bet sizes, hard translation to nearest size);
- two copies of our baseline;
- an **adaptive exploiter** that tracks our pooled fold-to-bet, bluff-to-value ratio per size, and preflop ranges, and best-responds after 30 hands.

Score every variant by mean ICM points over at least 2,000 duplicate-seeded tables. Report separately how much we gain against the gift bots and how much we lose to the exploiter. That second number is the price of each exploit.

1. **Gift detectors with hard counters** (largest gain, nearly zero risk; RWYWE-safe because these are dominated or "gift" plays).
   - **Trigger.** At least 8-10 of a seat's decisions with zero contrary actions. The archetype simulation in §1 resolves always-call or always-raise in 5 hands. The rule-of-three bound after 10 clean observations is under 26%. CMU's 2nd-place bot used ≥10 hands with >98% all-in.
   - **Exit.** One contrary action drops the seat back to the normal model.
   - **Counters:**
     - Shove-bot: call when equity ≥ the pot-odds threshold, adjusted by ICM. Equity needed = BF/(1+BF), i.e. 54% at a bubble factor of 1.18. Reference points: MIT's worked chip-EV case 0.4975; IIT used 0.52.
     - Always-call: zero bluffs; value-bet anything ahead of its range; check-call early and put the big bet in on the river. LBR got almost the whole 50 BB/h this way, against 33 BB/h for betting big early.
     - Fold/timeout bot: smallest legal bet into it whenever it must act. Under [Sequoia rules](https://pokerbot.sequoiacap.com/rules.html) a timeout checks when it can, so the gift only appears when it faces a bet.
     - Uniform-random: pot or all-in bets on turn and river with ≥50% equity. It folds half its hands to an all-in; LBR measured 80.7 BB/h.
     - Min-bet spammer: switch to a min-bet-aware response once min-bets are ≥1% of its hands (Hyperborean IRO's trigger).
2. **Baseline that strong bots cannot read** (avoided loss; the main defence against the strong half of the field).
   - **Mixing.** Drop actions under 15% probability and renormalise the rest (GS6's least-exploitable setting). Never fully purify: that cost +86% exploitability for Hyperborean.
   - **Sizing.** Never let size encode strength. Use one size per spot for value and bluffs, or two sizes each holding both. MIT 2025 winners read hidden cards from sizing; IIT added 0-12% pot noise.
   - **Defence with no read.** Continue (call or raise) at about 1/(1+x) against a pot-fraction bet x.
   - **Off-grid opponent bets.** Translate them with the pseudo-harmonic mapping f = (B−x)(1+A)/((B−A)(1+x)), randomised. Never map a tiny bet up to ½ pot.
   - **Test:** our loss to the adaptive exploiter with and without each item.
3. **Probe and punish rigid sizing** (high gain against prepared CFR bots, low risk).
   - **Probe.** In hands 1 to about 24 (three orbits), make about 15% of our bets at off-grid sizes {0.2, 0.45, 0.8, 1.3}×pot. Log each seat's fold/call/raise per size bucket.
   - **Rigidity flag.** A seat that bets with 2 or fewer distinct sizes over ≥10 bets is an abstraction bot.
   - **Exploit.** Once a bucket has ≥5 responses and fold rates differ by ≥30 points between buckets, bluff with the highest-fold size and value-bet with the highest-call size against that seat. Against abstraction bots, also use sizes geometrically between their sizes and tiny 0.1-0.2 pot bluffs.
   - **Evidence.** Hyperborean-BR 1.42 vs 0.27 sb/h; PokeMinn +42.06 sb/h against GS3; 2012 ACPC bots did not exploit sizes; MIT 2026 winners pushed opponents "into unfamiliar spots".
4. **Population-tuned static baseline** (high gain if pooled logs of the actual field exist, e.g. from practice tables in the build window; otherwise skip).
   - Refit the baseline's thresholds (call equity, bluff ratio, c-bet frequency, preflop opening and calling ranges) to pooled field data once per submission cycle. Cap the shift at "Pmax 0.25"-like strength: move each threshold at most a quarter of the way to the pooled-data best response.
   - **Evidence.** Static DBR to pooled data won 3-player limit by 84.3% and 40.1%; static imitators (Marv Andersen) topped total bankroll repeatedly; MIT's SPAM tuned to scrimmage logs.
   - **Cost to watch.** Alberta's pooled-data DBR lost 10 ± 2 mbb/g head-to-head to equilibrium entries.
5. **Shrunk, pooled per-seat stats with a DBR trust schedule** (the core read).
   - **Counts.** Beta/Dirichlet counts per seat for 5 pooled cells:
     - preflop fold/call/raise;
     - fold to a bet ≤ pot (all streets);
     - fold to a bet > pot or all-in;
     - raise when facing a bet;
     - bet when checked to.
   - **Prior.** Mean = our baseline's own frequency in that cell (or the population's), strength s = 4 (s = 2-5 in Hoehn, Ganzfried et al. and DBBR). Never a flat prior: it gave −54 vs +48 in 3-player Kuhn.
   - **Trust.** w = n/(n + 4), forced to 0 while n < 10 in that cell (DBR's 10-Step and 0-10 Linear schedules).
   - **Exploit offset.** w × (full archetype counter), computed from the posterior mean, not from the most likely archetype (EBBR beat MAP and Thompson).
   - **Context.** Condition on previous action and amount to call (Poki's best predictors).
   - **Scope.** Classify only the extremes (station, maniac/random, folder). Leave nit, TAG and LAG on the baseline: they do not separate within 200 hands (§1 simulation).
6. **Per-pot exploit gating in multiway pots** (protects against the strong seats).
   - **Gate.** Apply exploit offsets only when every live opponent is classed gift or weak with w ≥ 0.5. Otherwise play the baseline. No pure bluffs with 2 or more opponents live.
   - **Isolate the target.** Iso-raise limpers or stations to 4bb + 1bb per limper (+1bb out of position), with roughly top 50% of hands in position and 40% out of position. Tighten when an unknown or strong seat, or a seat that raises a lot, is still to act.
   - **Evidence.** Multi2 was "exploited by the IR16 agents" once the chumps were gone; AKI-RealBot won by targeting one weak seat.
7. **Per-seat exploitation budget on a luck-adjusted ledger** (RWYWE and RNR ε).
   - **Ledger.** All-in EV in place of realised outcome; equity at showdown where available. AIVAT-style adjustment cuts SD about 3×.
   - **Rule.** Deviation intensity against a seat = min(w, budget). The budget lets a fully adapted opponent recover at most about **0.1 bb/hand** (the ≈100 mb/h ε at which RNR kept most of the gain and lost only 11-45 mb/h to equilibrium), plus whatever we are already up against that seat. Against gift seats the budget is uncapped.
8. **Behavioural counter-exploitation alarm** (cheap insurance against the adaptive half).
   - **Alarm.** For each active exploit, snapshot the targeted seat's response rate in the stat the exploit leans on, e.g. its raise rate against our c-bets once we start c-betting wider. If the rate moves ≥2 SE after the exploit started (with the 10-observation floor), revert that seat to the baseline and halve its trust weight.
   - **Results backstop.** A luck-adjusted loss of ≥1 bb/hand over ≥30 hands to that seat. Raw results need about 278 hands to see that, so do not rely on raw results.
   - **Evidence.** Unsafe best response lost −0.121 vs −0.020 for RWYWE against a switching opponent; Poki's committal model was "more easily deceived"; the stationary particle-filter model lost money against switchers.
9. **3-4-arm portfolio with Exp3/Exp4 selection and off-policy scoring** (modest gain at this horizon).
   - **Arms.** Parameter offsets of one baseline: baseline; value-heavy with no bluffs; pressure (more and smaller bets, more c-bets); tight call-down.
   - **Weights.** ∝ exp(η·G) with η ≈ 0.06 on rewards scaled to [0, 1]. This is the standard √(2 ln K/(T K)) for K = 4, T = 200 (computed). Floor every arm at **2%** (Bard's floor; he found results insensitive to η).
   - **Off-policy scoring.** Score each arm every hand with weight Π P_arm(a)/P_mix(a) over our actions in the hand, times the luck-adjusted outcome. This is a simplified version of Bard's importance-sampling estimator; the 2% floor keeps P_mix > 0.
   - **Evidence.** A 4-arm portfolio beat 13 arms, UCB, and the best single response by ≥19.9% over 3,000 hands. Expect a smaller edge in 200 hands.
10. **Forgetting and regime reset** (small gain, protects against bots that switch).
    - Multiply all counts by **0.99 per hand** (Bard & Bowling's best fixed switch rate, 0.01).
    - If a cell's latest 10 observations sit more than 3 SE from its posterior, zero that cell's trust weight and restart its counts from the prior.
11. **ICM-aware target selection** (moderate gain in the late, short-stacked phase).
    - Point the pressure exploit at medium stacks, whose bubble factors run 1.6-2.06.
    - Avoid marginal confrontations with the covering big stack ("often ICM suicide").
    - Call shoves tighter than chip-EV, except against seats flagged as shove-bots.
    - Near the 200-hand cap, if our stack comfortably covers the remaining blinds, test folding everything but premiums. This is the MIT winners' "check-fold the last ~100 hands" trick, which was built for chip-lead scoring. Gate it by a check that the blinds still to come cannot cost us a finishing place.
12. **Exploratory baseline in the first ~25 hands** (small gain, cheap).
    - Among near-equal lines, prefer those that make each seat reveal a decision: small, frequent c-bets and min-raises in position. More exploratory equilibria learned faster in Kuhn, and the 50-hand switch point was robust across 50-400-hand horizons.
    - Keep these lines inside the baseline's own mixed support, so they leak nothing new.
