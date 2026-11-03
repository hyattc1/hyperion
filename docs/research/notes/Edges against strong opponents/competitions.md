# What won pokerbot competitions that look like ours, and what the winners say made the difference

Researched 2026-11-03. Target format: Sequoia "No Limit" 2026. Teams get a 60-minute build in Python with a 1 ms decision limit; an error or timeout auto-folds, or checks when checking is legal. Each tournament is 10,000 eight-bot sit-and-gos: 2,000 chips, blinds from 10/20 rising every 25 hands, a 200-hand cap with an ICM split, finish-position points, and T1–T6 weighted 1–6. The variant is secret until the build starts ([Sequoia rules](https://pokerbot.sequoiacap.com/rules.html)). No Sequoia round has been played yet: the first regional is Nov 6, 2026.

Scope: these notes add to `../Sequoia poker bot competition prep/competition_lessons.md`, which already covers the MIT variant history, engine clocks, ACPC and CMU. Facts repeated from it are re-cited here, not re-derived. Primary sources were preferred: official final-event slides, competition repos, winners' code and READMEs, and papers. Code was read only to describe approaches; none is reproduced here.

Method caveat: the session's shared web-search budget ran out partway through. Leads that needed fresh searching are listed under Gaps.

---

## 0. Which competitions resemble ours

| Competition (year) | Build window | Twist | Seats | Clock | Scoring | Closeness to ours |
|---|---|---|---|---|---|---|
| Sequoia No Limit (2026) | 60 min | secret until build | 8, SNG | 1 ms/decision | finish points + ICM at cap | target |
| IIT Pokerbots finals (2026, Jane Street) | 4-hour offline hackathon, new variant | Anaconda Hold'em (card exchange) | 2 | 2 s/query, 20 s total | bankroll over 1,000 hands | closest on short build + new twist |
| HPI Showdown (Jan 2025, Potsdam) | ~1 week, variant revealed at kickoff | "Noble Hold'em" | 2 | 60 s / 1,000 hands | bankroll | short build + reveal |
| Fullhouse Quant Poker Bot Hackathon (Jun 2026, UCL finals) | online qualifiers + finals | none (NLHE) | 6–9, no-rebuy SNG | ≤2 s/decision | chip Δ/100 hands, bust locks −10,000 | closest on multi-player elimination |
| MIT Pokerbots (2017, 2020–2026) | ~1 month | new each January | 2 | 30–60 s / 1,000 hands | per-match bankroll, Elo/bracket | richest winner data |
| Build4Good / TACS (Texas A&M, 2025–2026, SIG+HRT) | apparently one-day ("Today you are tasked…") | 3 hole cards (2025); redraw (2026) | 2 | 180 s/match | single-elimination bracket | short build, no results found |
| Husky Hold'em Bench (NeurIPS 2025) | LLM-written bots, 5 refinement rounds | none | 6 | n/a | net money over 1,000 rounds | multi-player, near-equal bots |

Sources: [IIT Pokerbots](https://www.iitpokerbots.in/), [IIT finals problem statement](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/problem-statements/finals-problem-statement.pdf), [HPI Showdown](https://hpi-poker.de/), [HPI engine config](https://github.com/HPI-Poker/competition-2025/blob/main/engine/config.py), [Fullhouse entry README](https://github.com/utsochaudhuri/lomaans-poker-table), [MIT 2026 final event](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf), [Build4Good 2025](https://github.com/MontgomeryBohde/Build4Good-Pokerbots), [Build4Good 2026](https://github.com/MontgomeryBohde/TACS-PokerBots-2026), [Husky Hold'em Bench](https://neurips.cc/virtual/2025/122372), [huskyholdem-bench repo](https://github.com/NousResearch/huskyholdem-bench).

---

## 1. MIT Pokerbots: who won, and the organizers' own analysis of winning bots

### 2026: Toss or Hold'em
Format: heads-up, 3 hole cards, a 2-card flop, then each player tosses one hole card face-up onto the board; 400 stacks reset each hand; 1,000 hands; 60 s clock.
- Field and results: 80 teams (78 non-reference), 2,571 bots submitted, 619,885 tournament games. 1st **heyo999** (David Zhang, Ben Chen, Evan Kim, Rich Wang), 2nd **double crossers**, 3rd **Fruit Ninja**, 4th **horseshoes**, 5th **last brain cell**. The "most time at top of scrimmage server" team (Policy Gradient Is All You Need) was not in the top 5 — [MIT 2026 final event slides](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)
- Organizers' "Structure of Winning Pokerbots": two approaches won. One leveraged ML methods ("CFR and AlphaHoldEm"); the other built "handcrafted strategies grounded in human poker intuition". Both "used scrimmage logs to gather feedback" — same slides, p.14
- Exploitative play the organizers saw winning: inferring opponent playstyle from game history with hand-crafted features; "unconventional bet sizes to push opponents into unfamiliar spots"; and "sacrifice EV to reduce variance against weaker bots" — same slides, p.16
- **Resource management** (verbatim slide): "Understand that the objective is to obtain enough chips to check/fold"; "**Winning bots check folded the last ~100 hands**"; "Use Binomial distribution to simulate auto-folding outcomes" — same slides, p.17
- "What good teams did well". ML teams: heavy performance optimization, variance reduction to speed convergence, and bucketing extended to the discard phase. Hand-crafted teams: intuition-driven opponent features, Monte Carlo to guide actions, and log analysis "to identify leaks in opposing players' strategies" — same slides, p.18
- Variant trends: nutted hands become more common; the discard narrows ranges sharply; position is worth more because the in-position player discards second — same slides, p.15
- Action profiles (approximate, read off the charts): field average fold ≈0.28, call ≈0.21, raise ≈0.15. The **top five** had median fold ≈0.39 (box ≈0.38–0.57), call ≈0.13, raise ≈0.11. Slide title: "Most teams play tight-aggressive… but top teams play more tight-aggressive" — same slides, pp.21–22
- "Games were not all decisive": most final-tournament games ended with margins under ~50 BB/100, followed by a long tail — same slides, p.20
- A CFR failure mode the 2026 CFR lecture flags: "Opponent plays outside our discretized action set — Ex from Last Year: Min Bet on large pot" — [MIT 2026 Lecture 9 (CFR)](https://github.com/mitpokerbots/class-resources-2026/blob/main/Lectures/Lecture%209.pdf)

### 2025: Bounty Hold'em
Format: heads-up; each player has a secret bounty rank that resets every 25 hands; a win that hits the bounty pays 1.5× + 10; 400 stacks; 1,000 hands; 60 s clock ([variant.pdf](https://github.com/mitpokerbots/class-resources-2025/blob/main/variant.pdf)).
- Field and results: 89 non-reference teams, 2,985 bots, 939,661 tournament games. 1st **Pineapple** (Raymond Feng, Samuel Wang, William Yue, Rowechen Zhong), 2nd **could this be, dog?**, 3rd **Encore 1/2 Regs**, which also spent the most time at the top of the scrimmage server, 4th **pink fluffy sheep**, 5th **heyo394** (best strategy report) — [MIT 2025 final event slides](https://github.com/mitpokerbots/class-resources-2025/blob/main/Slides/finalevent.pdf)
- Organizers' "Structure of Winning Pokerbots": "Explored ML methods like CFR", "Analyzed and exploited opponents", "**Implemented resource management techniques**" — same slides, p.15
- Variant trends: larger bets ("up to 10x Pot"), less preflop folding, and bounty cards used as bluffs and bluff-catchers. Exploits: mining scrimmage logs for weak points, inferring the opponent's bounty from bet sizing, and again "sacrifice EV to reduce variance against weaker bots" — same slides, pp.16–17
- The resource-management slide is identical to 2026: get enough chips to check-fold, and winning bots check-folded the last ~100 hands, with a binomial simulation of auto-fold outcomes — same slides, p.18
- What good teams did well: understood how the twist changes bet sizing, studied opponent bots and exploited their flaws, invested in performance optimization, and used human poker expertise — same slides, p.19
- Action profiles (approximate): field fold ≈0.35, call ≈0.12, raise ≈0.14. **Top ten** fold ≈0.49, call ≈0.04, raise ≈0.15. Top teams raised about as often as the field but called about a third as often — same slides, pp.22–23
- Inference: part of the top teams' higher fold rate comes from the end-of-match check-fold lock, worth up to ~10% of hands. Even so, the call-rate gap (≈0.04 vs ≈0.12) points to "raise or fold, rarely call".

### Earlier years
- 2024 (Auction Hold'em). GTO Wizard AI's entry (sponsor exhibition, ~5 days of work; placement not reported) combined depth-limited solving, a crude "all-in values" leaf heuristic, a precomputed "3v2 − 2v3" equity-difference table for the auction, and a time manager splitting the clock by street — [gtowizard-ai/mitpoker-2024](https://github.com/gtowizard-ai/mitpoker-2024). They note an abstraction-plus-MCCFR blueprint "would have almost certainly been" optimal under the clock — same README
- 2024, abh-win (placement not reported). Beta-smoothed opponent stats measured over 40,000 hands with 95% CIs: profiling lifted win rate against a calling station from +1008 to +2861 BB/100 and against an all-in bidder from +61 to +2002, but made "no measurable difference" against nit and TAG baselines. The bot won 120/120 matches against baselines and showed 0 state mismatches on the official engine — [abh-win/auction-poker-bot](https://github.com/abh-win/auction-poker-bot)
- 2022 (Swap Hold'em) participant: a "Maniac" bot beat early bots that folded too often but "had to be abandoned once they became more sophisticated". The final bot bluffs more against over-folders, calls more against over-bluffers and folds more against under-bluffers — [900miles/Pokerbots-2022](https://github.com/900miles/Pokerbots-2022)
- Organizers (2024): "bots that exploit opponent weaknesses, especially those that utilize the most poker theory and heuristics, fare the best". An all-in-every-hand bot was hard to counter in real time until lectures covered it. "Most students struggled with the limitations set by Pokerbots' homemade engine system" — [The Tech, Feb 2024](https://thetech.com/2024/02/08/pokerbots)
- 2017 (Discard Hold'em) champion: CFR with heavy abstraction. Buckets were 169 preflop, then 100 per street under imperfect recall. Bets were limited to 2 sizes (0.66 pot or all-in) and 2 actions per player per street, with off-tree actions mapped by an action-translation formula. Discards used a hand-written outs-count rule rather than anything learned. Training ran six days on a laptop without converging, so actions taken ≤10% of the time were zeroed. The report notes the twist inverted hand values: "pocket twos is among the worst hands of Discard Holdem" — [Fro116 report.pdf](https://github.com/Fro116/Pokerbots/blob/master/report.pdf), [repo](https://github.com/Fro116/Pokerbots)
- 2017 prize winner (SPAM): win-rate lookup tables. They bet smaller for value against CFR bots "which tended to fold to large raises" — [SPAM_pokerbot_2017](https://github.com/sebLopezCot/SPAM_pokerbot_2017)
- Unreliable claim: a third-party blog says the 2025 MIT variant was "three-player with forced board cards". The official 2025 slides show heads-up Bounty Hold'em — [openpoker.ai](https://openpoker.ai/blog/best-ai-poker-platforms) vs [MIT 2025 slides](https://github.com/mitpokerbots/class-resources-2025/blob/main/Slides/finalevent.pdf)

---

## 2. Short-build and hackathon events

### IIT Pokerbots 2026 (Jane Street; pan-IIT; Python only)
Format: a 7-day online prelim on Sneak Peek Hold'em (a post-flop second-price auction to see one opponent hole card), then a **4-hour offline hackathon final on a new variant, Anaconda Hold'em**. Each player gets 7 private cards and no board; players exchange 3, then 2, then 1 cards with the opponent before each betting round. 1,000 rounds, 5,000 chips per round, blinds 10/20, 2 s per query and 20 s total; an invalid bet counts as a fold. The top 15 of 2,000+ registrants played the finals.
- Champion **Single_G_Double_G**, 1st runner-up **Notato** (Anant Jain, Sparsh), 2nd runner-up **All_In_or_Fold** — [iitpokerbots.in](https://www.iitpokerbots.in/), [finals problem statement](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/problem-statements/finals-problem-statement.pdf)
- Notato was 2nd in prelims, **1st in the 4-hour final hackathon** and 2nd overall. Finals bot: card exchange treated "as an optimization problem" (score the retained hand; never pass cards that improve the opponent's known holdings), tracking of every card seen in exchanges, **exact enumeration once the hidden-card space is small**, and "selective trap betting". Six experimental strategies were kept as separate files (blocker, equity, hybrid, meta, opponent, pass-trap) — [repo README](https://github.com/anantjain29/iit-pokerbots-2026), [finals README](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/finals/README.md)
- Notato's prelim bot (1,141 wins / 316 losses):
  - Equity: an O(1) lookup over all 1,326 preflop combos; Monte Carlo after the flop with 90–650 simulations scaled to street and remaining time bank; exhaustive river enumeration when one opponent card is known.
  - Opponent model: recalibrated every 18 hands, blending 65% recent with 35% cumulative behavior.
  - Bet handling: a tiered "confidence punishment" penalizes big bets more the later the street. Against hyper-aggressive opponents a "recovery" term pulls the adjusted equity back toward raw equity, so the bot cannot be bullied off hands.
  - Auction: bids split into an offensive value (seeing a card) and a defensive value (denying it), fitted from self-play logs by regression on expected pot size and K-means equity tiers, then blended with the opponent's observed bid percentiles.
  - Selection: ~120 variants run in round-robin best-of series, chosen "for performance, low variance, and limited overfitting".
  — [strategy deck](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/DominatorBot_Prelims_Strategy_Presentation.pptx), [README](https://github.com/anantjain29/iit-pokerbots-2026)
- 5th place (Travelling_Salesmen): heuristic preflop strength, eval7 Monte Carlo after the flop (750–1,125 iterations, time-adjusted), pot odds with risk factors for large bets, and bidding that adapts to its own auction win/loss history — [Aravind-Ramana/IIT_Pokerbots_2026](https://github.com/Aravind-Ramana/IIT_Pokerbots_2026)
- 49th of ~500: tried XGBoost (too slow per move), precomputed tables (did not handle the conditional auction information), a GP model (too rigid) and a standalone profiler ("overfit to specific opponent styles"). Shipped a rule-based plus Monte Carlo hybrid — [Bhavana-B-del/IITM-Pokerbots-2025](https://github.com/Bhavana-B-del/IITM-Pokerbots-2025)
- Non-placing entrant's post-mortem: "**Simple and fast beat clever and unfinished**". He shipped a ~300-line equity bot with a timeout guard: if equity takes >0.8 s it falls back to preflop equity. A CFR table and neural nets were built but never loaded. His logged passive postflop calls won only 35% of 695 pots, so he moved to raise-or-fold. Bugs found later:
  - logs were never written (the write sat after a `return`);
  - the shove helper folded instead of calling when already all-in;
  - a strong hand facing an all-in folded because raising was illegal;
  - auction bids used preflop equity even though the auction is post-flop.
  — [kartikya2207/poker__bot_engine_kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)

### HPI Showdown 2025 (Hasso Plattner Institute, Potsdam)
Format: Jan 10–17, 2025; teams of 2; Python or C++ on an MIT-derived framework. The variant was "published at the event"; play was heads-up on 100-chip stacks at 1/2 blinds, 1,000 rounds, 60 s total clock. A build or runtime error makes the bot check if possible, otherwise fold.
- The variant name, "Noble Hold'em", comes from the organizers' guide. From the winner's equity code, the rule appears to be that a J/Q/K dealt to the board triggers an extra board card, with best hand from all board cards. The official rule page did not render — [hpi-poker.de](https://hpi-poker.de/), [HPI winners repo](https://github.com/HPI-Poker/competition-2025-winners), [engine config](https://github.com/HPI-Poker/competition-2025/blob/main/engine/config.py)
- Results: 1st **Der Graph von Monte Carlo** (C++), 2nd **Harry** (Python), 3rd **Stockfish_v2** — [winners README](https://github.com/HPI-Poker/competition-2025-winners)
- The champion's decision layer is ~60 lines on top of a **variant-correct equity engine**:
  - Preflop: a 169-hand table precomputed offline under the variant's dealing rule.
  - Postflop: Monte Carlo against a uniform random range, re-implementing the extra-card rule, stopping on a time budget (remaining clock ÷ remaining rounds) or a confidence-interval target.
  - Betting: open-raise preflop from the small blind when equity >0.45; size raises by equity tier when checked to; never reraise; call when equity, slightly penalized by bet size, is ≥0.5.
  - Match logic: **"win by folding"** — once the bankroll lead exceeds the blinds it could lose by folding every remaining hand, fold everything; on the last hand, shove if slightly behind.
  — [graph_von_monte_carlo source](https://github.com/HPI-Poker/competition-2025-winners/tree/main/bots/graph_von_monte_carlo)
- The runner-up also carries a `can_win_by_folding` check, plus a preflop lookup CSV, board "heaviness" scoring and a bluff-probability estimate — [harry/player.py](https://github.com/HPI-Poker/competition-2025-winners/tree/main/bots/harry)

### Fullhouse Quant Poker Bot Hackathon (June 2026; 500+ entries; finals at UCL East)
Format: one `decide(state)` Python file. Tables are 6–9 handed, 10,000 chips, 400–800 hands per match, **no rebuy: a bust locks −10,000**, ranked by chip Δ per 100 hands. Limits: ≤2 s per decision, 0.5 CPU, eval7/numpy only.
- Top-80 finalist (Lomaan; rank #43 then #38):
  - Bust rate 54% against a field median of 68%; "149 of 202 bots lose their whole stack in 60%+ of their matches". Core thesis: "survive first, extract value second."
  - Their **biggest performance jump came from removing timeouts**: an equity routine that occasionally crossed the limit had cost "dozens of forfeited 'timeout' decisions per match". After a 140 ms wall-clock cap it was zero.
  - The stack-off rule "that actually moved the needle": one pair or worse may not commit a big stack, whatever Monte Carlo says, because Monte Carlo against a loose range overrates ace-high and weak pairs once someone bets big.
  - Their stats: fold/call/raise 65/13/22%, aggression factor 1.75.
  - Post-mortem: a per-opponent river exploit table that looked good locally was 46% correct on held-out data and had to be removed.
  — [utsochaudhuri/lomaans-poker-table](https://github.com/utsochaudhuri/lomaans-poker-table)
- **Finals winner "Hyperion", described as GTO-adaptive** (its architecture as relayed by the Lomaan author):
  - Exploits shift the opponent's sampled *range*; "decision thresholds never change".
  - A hard gate: below 20 observed actions it plays pure baseline, with exploits fading in to full weight at 60+.
  - Opponent ranges are rebuilt each hand from that hand's actions.
  - Big-pot discipline is continuous: required equity grows with (stack fraction at risk)², plus SPR-aware commitment.
  - Principle: "the exploit layer adjusts what the bot believes, never what the bot does."
  - The Lomaan author's rebuild on these principles scored +29% in a 400-match local bake-off, and was identical to v1 against pure preflop shovers.
  — same README §11. (Name collision: unrelated to this repo as far as can be told; the winner's own write-up was not located.)
- Another entrant: "Sandbox sims lie cleanly". 200 heads-up hands against reference bots "tells you almost nothing" about serious opponents but catches crash bugs; opponent archetype modeling was "bigger than tuning preflop charts" — [AEdgecombe/Poker-Bot-Hackathon](https://github.com/AEdgecombe/Poker-Bot-Hackathon)

### Others (formats only, no winner write-ups found)
- Build4Good 2025 (Texas A&M; SIG and HRT): apparently a one-day build, "B4G Hold'em" (3 hole cards, 2-card flop, 2-card turn), 5,000 hands, 500 stacks, a 180 s clock per match after which the bot folds every remaining hand, single-elimination bracket. 2026 variant "Hold'em + Redraw": one redraw per hand of a hole or board card, combined with a betting action, the old card revealed — [Build4Good 2025](https://github.com/MontgomeryBohde/Build4Good-Pokerbots), [2026](https://github.com/MontgomeryBohde/TACS-PokerBots-2026)
- Husky Hold'em (UW Algorithmic Trading Club, May 2024): a 1v1 bot round, then a live "roundtable" final; 2025 used a multi-player engine with blind-increase options — [hh.html](https://students.washington.edu/atcuw/hh.html), [pokerden-engine](https://github.com/kipiiler/pokerden-engine)
- CMU DSC AI Poker Tournament (Jump Trading): Python 3.12, heads-up 1,000 hands, variant revealed at kickoff — see prior notes, [cmudsc.com](https://cmudsc.com/pokerai-2026/)

---

## 3. Multi-player sit-and-go and ICM research

- **Ganzfried & Sandholm, AAMAS 2008** (3-player jam/fold SNG, 13,500 chips, 300/600 blinds, 50/30/20 payouts):
  - ICM's average error against equilibrium prize equity was $0.37 of a $100 pool; the worst case was $2.99. In that case a big blind about to post 2/3 of his stack was overvalued, because ICM "does not take into account" the blinds due next hand.
  - **Tournament vs single-hand play: first-in jamming is "fairly similar", but "players should be much more aggressive in a single hand when someone else has already jammed".** Concretely, the BB overcall after two jams is 2.1% in the tournament vs 19.7% in a single hand (9.4×); in the tournament the BB calls only the four highest pairs plus AKs. The BB calls a lone SB jam about half as often in the tournament as in a single hand (0.27 vs 0.47).
  - There is no fixed hand ranking: the jam set changes with stack vector.
  — [AAMAS08 paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf)
- Follow-up (IJCAI 2009): an ex-post check showed no player can gain more than $0.0488 by deviating from the computed 3-player jam/fold strategies, "0.05% of the total prize pool" (as restated in the AAMAS08 text above). The IJCAI search snippet phrases ε as ≈0.5% of the entry fee; not reconciled here — [IJCAI 2009](https://ijcai.org/proceedings/2009/34), [AAMAS08 §7](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf)
- **Miltersen & Sørensen, AAMAS 2007** (heads-up SNG, as summarized by Ganzfried & Sandholm):
  - A jam/fold strategy is near-optimal; no player can gain more than 0.014 by deviating.
  - Win probability is ≈ stack share, the same as gambler's ruin.
  - The optimal strategy randomizes with at most one hand per state, and the tournament strategy is almost identical to cash-game play heads-up.
  — [paper](https://www.itu.dk/~trbj/papers/poker.pdf), [AAMAS08 §3](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf)
- **Gilbert 2009**: under ICM, joining a fair bet against one other player always lowers your expected value, and **a bystander to a fair bet between two others always gains** (not necessarily true for 3+-way bets) — [arXiv 0911.3100](https://arxiv.org/abs/0911.3100)
- **Kim 2025** (IEEE CoG; 10,000+ real tournaments): ICM beats the paper's baseline, but "underestimates players with larger stacks and overestimates short-stacked players" — [arXiv 2506.00180](https://arxiv.org/abs/2506.00180). The **Dependent Chip Model** (2021) finds "the first podium positions usually collect more money than the amount granted by ICM" — [arXiv 2102.07738](https://arxiv.org/abs/2102.07738)
- **Risk & Szafron, AAMAS 2010** (ACPC 2009, 3-player limit):
  - CFR agents placed 1st and 2nd despite having no guarantees in 3-player games; grafting heads-up "experts" after one player folds helped.
  - In their bankroll table, **the most exploitative agent (PR2) ranked first only while chumps were present**: it fell to third once Always-Raise was removed.
  - The elimination (runoff) event went to the least-exploitable agents (IR16L, IR16S).
  — [AAMAS10 preprint](https://poker.cs.ualberta.ca/publications/AAMAS10.pdf)
- **Pluribus (6-max, 2019)**:
  - Blueprint trained ~8 days on 64 cores; depth-limited search with four continuation strategies (blueprint, fold-, call- and raise-biased) so it is not brittle.
  - It "does not adapt its strategy to the observed tendencies of its opponents"; it abandoned limping and used multiple bet sizes and mixed strategies.
  - Authors: in 3+-player games "it is possible to lose even when playing an exact Nash equilibrium strategy."
  — [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/)
- **DeepBot (EPFL master's thesis, 2019)**: GA-evolved LSTM network for 6-max SNGs (1,500 chips, rising blinds, games of 100–200 hands, 1st = 4 tokens, 2nd = 2).
  - ROI was ~230% against passive tables, ~160% against tight-aggressive and ~130% against loose-aggressive: **LAG tables were hardest to exploit**.
  - Its rule-based "Ruler" opponent switched to push/fold below 12 BB.
  - The bot trained only against one opponent type "can not be generalised to other opponents."
  — [deepbot-poker](https://github.com/tamlhp/deepbot-poker), [report](https://github.com/tamlhp/deepbot-poker/blob/master/docs/Deepbot_report.pdf)
- **Husky Hold'em Bench (NeurIPS 2025)**: frontier LLMs wrote Python bots (5 refinement rounds) for 6-player round-robin games of 1,000 rounds scored on net money. Claude 4 Sonnet topped the leaderboard; "top models tended toward balanced or aggressive play, while lower-ranked models played more defensively" — [NeurIPS page](https://neurips.cc/virtual/2025/122372), [repo](https://github.com/NousResearch/huskyholdem-bench). CodeClash later reused the engine as an arena; it found LLM codebases grew "increasingly cluttered and redundant" over rounds and lost every round to expert humans — [arXiv 2511.00839](https://arxiv.org/abs/2511.00839), [CodeClash HuskyBench](https://github.com/CodeClash-ai/HuskyBench)

---

## 4. Failure modes that cost strong teams

- **Timeouts.** These were the single biggest fix for a Fullhouse finalist: dozens of forfeited decisions per match, down to zero after a 140 ms cap ([Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table)). How each event penalizes them:
  - HPI: "My bot keeps folding even though I didn't code that?" covers both failed build/connect and an exhausted 60 s clock ([HPI winners README](https://github.com/HPI-Poker/competition-2025-winners)).
  - IIT: breaching the 20 s total forfeits the round and every later round ([Bhavana README](https://github.com/Bhavana-B-del/IITM-Pokerbots-2025)).
  - MIT: the engine logs "ran out of time" (prior notes).
  - Sequoia: identical auto-fold or check ([rules](https://pokerbot.sequoiacap.com/rules.html)).
- **Illegal or mis-specified actions.**
  - IIT: an invalid bet (negative, fractional, above the stack or above the opponent's chips) counts as a fold ([IIT finals PS](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/problem-statements/finals-problem-statement.pdf)).
  - Real bugs from one entry: the shove helper folded when already all-in, a strong hand facing an all-in folded because raising was illegal, and bid state was stored as −1 ([kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)).
  - Build4Good's skeleton says to always validate against `legal_actions()` ([TACS 2026](https://github.com/MontgomeryBohde/TACS-PokerBots-2026)).
- **Silent tooling bugs that corrupt learning.** Logs were never written and pot sizes mis-parsed, so the networks trained on bad data ([kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)).
- **Misapplying the twist.**
  - Auction bids priced from preflop equity although the auction is post-flop ([kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)).
  - Ordinary hold'em hand values are wrong under a draw or discard twist: "pocket twos is among the worst hands" ([Fro116](https://github.com/Fro116/Pokerbots/blob/master/report.pdf)).
  - The HPI champion's main investment was simulating the variant's dealing rule exactly ([source](https://github.com/HPI-Poker/competition-2025-winners/tree/main/bots/graph_von_monte_carlo)).
- **Overfitting to the local field.**
  - A per-opponent exploit table was a coin flip (46%) on held-out data ([Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table)).
  - A profiler bot "overfit to specific opponent styles" ([Bhavana](https://github.com/Bhavana-B-del/IITM-Pokerbots-2025)).
  - DeepBot's single-opponent agent did not generalize ([report](https://github.com/tamlhp/deepbot-poker/blob/master/docs/Deepbot_report.pdf)).
  - "Sandbox sims lie cleanly" ([AEdgecombe](https://github.com/AEdgecombe/Poker-Bot-Hackathon)).
  - Field drift: a maniac bot beat early folders, then stopped working ([900miles](https://github.com/900miles/Pokerbots-2022)), and the all-in bot faded after lectures ([The Tech](https://thetech.com/2024/02/08/pokerbots)).
- **Off-tree actions against abstraction bots.** A min-bet on a large pot broke CFR bots ([MIT 2026 L9](https://github.com/mitpokerbots/class-resources-2026/blob/main/Lectures/Lecture%209.pdf)). The 2017 champion needed an action-translation mapping ([report](https://github.com/Fro116/Pokerbots/blob/master/report.pdf)). Winners exploited the same weakness: "unconventional bet sizes" ([MIT 2026 slides](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)).
- **Unfinished ambition.** CFR and neural nets were built but never wired in, and the submitted bot was the simple one ([kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)). GTO Wizard swapped its learned value net for a weak heuristic because of the clock ([README](https://github.com/gtowizard-ai/mitpoker-2024)).
- **Wrong ICM.** No source documents a team knocked out by an ICM error. The research shows plain ICM misprices stacks facing imminent blinds by up to ~3% of the pool ([Ganzfried & Sandholm 2008](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf)) and is biased against big stacks in real finishes ([Kim 2025](https://arxiv.org/abs/2506.00180)). Note that Sequoia's 200-hand split *is* ICM, so ICM is exact for capped tables and only approximate for tables that play out.

---

## 5. Adapting fast to a rule change: what carried over, what was rebuilt

- **Carried over in every case**: the equity engine (lookup plus Monte Carlo), time-budgeted computation, the fail-safe wrapper, the opponent stat counters, the test harness, and scoring-aware match logic. All appear unchanged across IIT's prelim→final variant switch: the same tournament harness and equity core, with only the exchange logic new ([IIT README](https://github.com/anantjain29/iit-pokerbots-2026)). The MIT "resource management" slide is word-for-word identical across two different variants ([2025](https://github.com/mitpokerbots/class-resources-2025/blob/main/Slides/finalevent.pdf), [2026](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)).
- **Rebuilt each time**:
  1. the deal or evaluation model and the precomputed preflop table under the new rule ([HPI champion](https://github.com/HPI-Poker/competition-2025-winners/tree/main/bots/graph_von_monte_carlo); MIT 2021 lecture: precompute the 169 classes once to a CSV, [L4](https://github.com/mitpokerbots/class-resources-2021/blob/main/Lecture%20Slides/Lecture%204%20-%20Performance.pdf));
  2. the twist's extra decision (bid, discard, exchange or toss) ([IIT finals](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/finals/README.md), [GTO Wizard auction table](https://github.com/gtowizard-ai/mitpoker-2024), [Fro116 discard rule](https://github.com/Fro116/Pokerbots/blob/master/report.pdf));
  3. bet sizing and hand-value priors: 2025 bounty meant bigger bets and less preflop folding; 2026 toss meant more nutted hands, narrower ranges and more value in position ([MIT slides](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)).
- **Pattern for the twist decision**: value it as an EV difference by quick simulation, scale by a fudge factor, then calibrate against logs or opponents. Examples: GTO Wizard's 3v2−2v3 equity × 1.8 (best of 0.5–2.5×); Notato's offensive plus defensive value fitted from self-play logs, blended with opponent bid percentiles; abh-win's marginal-EV bid against the opponent's empirical bid distribution ([GTO Wizard](https://github.com/gtowizard-ai/mitpoker-2024), [Notato deck](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/DominatorBot_Prelims_Strategy_Presentation.pptx), [abh-win](https://github.com/abh-win/auction-poker-bot)).
- **Hand-written beats learned for the twist when time is short**: the 2017 CFR champion still used an outs-count discard rule ([report](https://github.com/Fro116/Pokerbots/blob/master/report.pdf)). In the 4-hour IIT final the winner of the hackathon round fielded heuristics plus exact enumeration, not training ([IIT](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/finals/README.md)).

---

## 6. Tables of near-equals: who takes first, and does aggression or survival pay?

- **Top bots fold more and call much less, and raise about as often as the field.** This holds in MIT 2025 (call ≈0.04 vs ≈0.12) and 2026 (call ≈0.13 vs ≈0.21) ([2025](https://github.com/mitpokerbots/class-resources-2025/blob/main/Slides/finalevent.pdf), [2026](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)). Also: Fullhouse finalist fold/call/raise 65/13/22 ([Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table)); IIT entrant's passive calls won 35% of pots ([kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)).
- **In elimination formats most bots beat themselves**: the Fullhouse median bust rate was 68%. A survive-first bot reached the top 80, and the winner paired a GTO-style baseline with a continuous risk² commitment penalty ([Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table)).
- **Without elimination, aggression ranks higher**: Husky Bench's 6-max net-money games favored balanced or aggressive LLM bots ([NeurIPS](https://neurips.cc/virtual/2025/122372)). Inference: the scoring rule decides whether aggression or survival pays.
- **Theory for finish-position payouts.** Aggression as the *opener* is roughly chip-EV-correct, but *calling* should be far tighter: BB overcall 9.4× rarer than in a single hand ([Ganzfried & Sandholm](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf)). Both players in a fair heads-up confrontation lose ICM equity and the bystanders gain ([Gilbert](https://arxiv.org/abs/0911.3100)). So the edge sits on the side that applies pressure: steals, re-jams and folds by others. Getting it in as the caller is where you lose it.
- **Who takes 1st among equals**: heads-up, win probability ≈ chip share ([Miltersen & Sørensen via G&S](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf)). Real data says big stacks finish better than ICM predicts and podium spots are worth more than ICM grants ([Kim](https://arxiv.org/abs/2506.00180), [DCM](https://arxiv.org/abs/2102.07738)). Accumulating chips through uncontested pressure is worth a little more than ICM implies in tables that play out. At Sequoia's cap the split *is* ICM, so near hand 200 the ICM risk premium applies exactly.
- **Exploiters win only while there is prey**: PR2 fell from 1st to 3rd once one chump was removed, and least-exploitable agents won the runoff ([Risk & Szafron](https://poker.cs.ualberta.ca/publications/AAMAS10.pdf)). Profiling gains are huge against stations and shovers and roughly zero against TAG or nit bots ([abh-win](https://github.com/abh-win/auction-poker-bot)). LAG tables gave the lowest ROI to an exploiting SNG agent ([DeepBot](https://github.com/tamlhp/deepbot-poker/blob/master/docs/Deepbot_report.pdf)). Inference for Sequoia: exploits pay most in T1–T2, when many submissions are hasty. As fields converge in T4–T6, which carry most of the weight, the robust baseline matters more.
- **"Variance is a feature" is wrong here.** A Fullhouse entrant argued high variance helps because "in a tournament you only need to win once" ([AEdgecombe](https://github.com/AEdgecombe/Poker-Bot-Hackathon)). Sequoia scores *average* points over 10,000 tables per tournament ([rules](https://pokerbot.sequoiacap.com/rules.html)), so only expected points count, and ICM-concave payouts penalize chip variance. MIT winners did the opposite: "sacrifice EV to reduce variance against weaker bots" ([MIT slides](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)).

---

## 7. Gaps and unreliable items

- No write-ups found for the MIT 2025 and 2026 winners (Pineapple, heyo999); the IIT 2026 champion (Single_G_Double_G); the Fullhouse winner "Hyperion" (its architecture is known only second-hand via [Lomaan §11](https://github.com/utsochaudhuri/lomaans-poker-table)); MIT 2019–2024 final placements; or the ACPC 2018 six-player winner (PokerBot5). The web-search budget ran out before targeted searches for these could run.
- Trading-firm or Kaggle-style poker contests with short builds (beyond the sponsor-backed student events above), theaigames.com heads-up SNG bots, and Sequoia's own (unplayed) regionals were not covered.
- MIT action-profile numbers were read off bar charts and are approximate. The fold-rate gap is partly the check-fold endgame (my inference).
- The HPI "Noble Hold'em" rule is inferred from the winner's code, not from an official rule text.
- A secondary blog's claim that MIT 2025 was three-player conflicts with the official slides ([openpoker.ai](https://openpoker.ai/blog/best-ai-poker-platforms)).

---

## Testable for a bot

Ranked by how much each seemed to matter to winners.

1. **Zero forfeited decisions.** Wrap every decision in a hard wall-clock budget well under 1 ms, with fallback order: cached table answer, then legal check, then fold. Fuzz legality in all-in, short-stack, side-pot and min-raise states. Biggest single fix for a Fullhouse finalist; universal auto-fold rules; real "fold instead of call when all-in" bugs. Test: 10⁶ decisions on the slowest hardware with 0 timeouts and 0 illegal actions ([Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table), [kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya), [rules](https://pokerbot.sequoiacap.com/rules.html)).
2. **Rebuild a variant-correct equity core first.** In the first minutes after the reveal, regenerate the preflop table (169 classes, or 1,326 combos) by simulating the twist's exact dealing rule. Use exact enumeration when few cards are hidden. This was essentially the HPI champion and the IIT hackathon-round winner, and it fixes "deuces are the worst hand" inversions. Test: drill the regeneration on 5 mock twists in under 15 minutes each ([HPI](https://github.com/HPI-Poker/competition-2025-winners/tree/main/bots/graph_von_monte_carlo), [IIT](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/finals/README.md), [Fro116](https://github.com/Fro116/Pokerbots/blob/master/report.pdf)).
3. **Score-aware endgame ("resource management").** MIT winners in both 2025 and 2026 check-folded the last ~100 hands once a lead was safe, using a binomial simulation of auto-fold outcomes; HPI's top two "won by folding". SNG version: each hand, compare the points value of folding to the cap (blind attrition simulated per seat) with playing on, and exploit laddering when other stacks are near-dead. Test: points/table with and without the module from hand 150 on ([MIT 2026](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf), [MIT 2025](https://github.com/mitpokerbots/class-resources-2025/blob/main/Slides/finalevent.pdf), [HPI](https://github.com/HPI-Poker/competition-2025-winners)).
4. **Raise-or-fold; cut calls.** Target a call share well below the field's. MIT top teams called ~1/3 to ~2/3 as often as the field at the same raise rate. Test: A/B a call-heavy version against a raise-or-fold version in the 8-max harness ([MIT 2025](https://github.com/mitpokerbots/class-resources-2025/blob/main/Slides/finalevent.pdf), [kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya)).
5. **Continuous stack-off discipline.** Make required equity rise with (fraction of stack at risk)² and with low SPR, and stop one-pair hands from committing a big stack against large bets. This came from the Fullhouse winner, and the finalist cited it as the bust-rate fix. Test: bust rate and points against archetype tables ([Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table), [Notato deck](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/DominatorBot_Prelims_Strategy_Presentation.pptx)).
6. **ICM-correct push/fold: open wide, call narrow.** Keep first-in jam ranges near chip-EV, but make calling and overcalling ranges much tighter (BB overcall ~9× rarer in the 3-handed SNG equilibrium). Use the starter-kit ICM calculator with the actual payout table, and adjust for blinds about to be posted. Test: ICM-aware vs chip-EV calling thresholds at ≤15 BB ([Ganzfried & Sandholm](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf), [Gilbert](https://arxiv.org/abs/0911.3100)).
7. **Bounded, gated exploitation.** Use Beta-smoothed per-seat counters (VPIP, PFR, fold-to-steal, shove frequency). Reads shift the opponent's *range*, not the decision thresholds. Give zero weight below ~20 observations and full weight around 60. Prioritize detecting shovers and calling stations, where profiling gains are 3–30× and are near zero against TAG bots. Test: gain against a shover/station table and no loss against a TAG table ([Lomaan §11](https://github.com/utsochaudhuri/lomaans-poker-table), [abh-win](https://github.com/abh-win/auction-poker-bot)).
8. **Twist decision as value of information.** Price the new action (bid, toss, exchange, redraw) as an EV or equity difference by quick simulation, include the denial value, then scale by one tuned multiplier. Test: sweep the multiplier from 0.5 to 2.5× in the harness ([GTO Wizard](https://github.com/gtowizard-ai/mitpoker-2024), [Notato deck](https://github.com/anantjain29/iit-pokerbots-2026/blob/main/DominatorBot_Prelims_Strategy_Presentation.pptx)).
9. **Pre-built 8-max SNG harness with archetypes and held-out checks.** Stock it with nit, TAG, LAG, station, maniac, shover, random and copies of self. Rank candidates by mean points with confidence intervals, and reject anything that only wins against one archetype. Notato ran ~120 variants and chose for low variance; a Fullhouse exploit table looked good locally but was 46% on held-out data. Test: harness throughput (target ≥1,000 SNGs per minute) and CI width ([IIT](https://github.com/anantjain29/iit-pokerbots-2026), [Lomaan](https://github.com/utsochaudhuri/lomaans-poker-table), [abh-win](https://github.com/abh-win/auction-poker-bot)).
10. **Ship a simple legal bot first, then iterate.** "Simple and fast beat clever and unfinished". Sequoia weights T1 at 1× and T6 at 6×, so a T1 bot only needs to be legal and sane. Test: legal bot submitted within 15 minutes in drills ([kartikya](https://github.com/kartikya2207/poker__bot_engine_kartikya), [rules](https://pokerbot.sequoiacap.com/rules.html)).
11. **Bet-size robustness both ways.** Map any opponent size, including min-bets into big pots, onto sane responses. Consider odd sizes that fall off typical abstraction trees: MIT 2026 winners used "unconventional bet sizes". Test: run against a bot that min-bets large pots and a bot that overbets 10× pot ([MIT 2026 L9](https://github.com/mitpokerbots/class-resources-2026/blob/main/Lectures/Lecture%209.pdf), [MIT 2026 slides](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf)).
12. **Mine logs between submissions if the kit exposes them.** Every MIT winning approach "used scrimmage logs to gather feedback". With 20 minutes between Sequoia tournaments, a ready log parser (field VPIP/PFR, bust causes, shove ranges) could turn T1 data into T2–T6 adjustments. The rules do not say whether logs are provided, so check the starter kit ([MIT 2026 slides](https://github.com/mitpokerbots/class-resources-2026/blob/main/Final%20Presentation.pdf), [rules](https://pokerbot.sequoiacap.com/rules.html)).
