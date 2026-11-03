# Poker AI literature: what the strongest bots do, and what survives 1 ms, offline precompute and 8-max ICM

Researched 2026-11-03 for Hyperion: 8-max no-limit hold'em sit-and-go, CPython standard library, a hard 1 ms per
decision, finishing-position points with ICM, 200-hand tables, anonymous opponents reset every table, a few MB of
tables built offline. Companion to `../Sequoia poker bot competition prep/algorithms_sota.md`, which already covers CFR
variants, hobby blueprints against Slumbot, the full LBR table and the basic pseudo-harmonic formula; numbers from there
are repeated here only where an argument needs them.

Tags on every claim: **[paper]** peer-reviewed or an arXiv paper by the authors; **[author]** an author's informal
statement (AMA, talk, blog post); **[tool]** a vendor's own doc or blog (HRC, ICMIZER, GTO Wizard, PrimeDope);
**[secondary]** press, Wikipedia, forums, third-party summaries; **[computed]** computed in this pass from Hyperion's
tables and code (method stated; not literature, reproduce before relying on it). Units: mbb/g = thousandths of a big
blind per hand; 10 mbb/g = 1 bb/100; folding every hand loses 750 mbb/g heads-up. Where a source's PDF could not be
fetched, the bullet says which copy was read.

---

## 0. Bottom line

- **Every superhuman bot is a blueprint plus real-time search, and the ablations say search was the decisive part.**
  Libratus against Baby Tartanian8 (the 2016 ACPC winner): raw blueprint -8 ± 15 mbb/g, with post-processing +18 ± 21,
  with nested subgame solving +63 ± 28 [paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf). Modicum:
  blueprint -57 ± 13, with depth-limited search +6 ± 5 [paper](https://arxiv.org/pdf/1805.08195). Brown: "advances in the
  search algorithm were the biggest factor" for Pluribus
  [author](http://web.archive.org/web/20240912182811/https://www.reddit.com/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/),
  and 20 s of thinking per hand "got the same boost in performance" as a 100,000x larger model and training run
  [author](https://www.ted.com/talks/noam_brown_ai_won_t_plateau_if_we_give_it_time_to_think). **A 1 ms Python bot has no
  search.** It is in the class of the 2015 Claudico blueprint, which decided "in about 10 milliseconds"
  ([talk summary](https://pod.wave.co/podcast/ted-talks-daily/ai-wont-plateau-if-we-give-it-time-to-think-noam-brown-c9e6fd2a))
  and lost 9.16 bb/100 to pros [paper](https://arxiv.org/pdf/1510.08578). The edge has to come from pieces that are pure
  precompute.
- **Pure-precompute pieces with measured value:** table post-processing (purification, thresholding, fold-biased
  meta-purification: Tartanian7 averaged +71 mbb/h against the two strongest 2013 bots with it, against +20 raw
  [paper](http://www.cs.cmu.edu/~sandholm/hierarchical.aamas15.pdf)); randomized pseudo-harmonic translation keyed on the
  true pot (Claudico's biggest leak was misreading the pot after translation [paper](https://arxiv.org/pdf/1510.08578));
  size jitter and range thresholding against tells; offline hole-filling where opponents actually bet (by the end of the
  Libratus match roughly half of all hands used self-improver strategies
  [paper, Science first-release supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth)).
- **Multiplayer has no guarantees, but equilibrium-style play works empirically.** Pluribus in 6-max; CFR agents placed
  first and second in the first ACPC 3-player events [paper](https://poker.cs.ualberta.ca/publications/AAMAS10.pdf); an
  exact Nash agent beat realistic opponents in 3-player Kuhn [paper](https://arxiv.org/abs/1804.04789). Pluribus "plays a
  fixed strategy that does not adapt" [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
- **The tournament endgame is the one place where a solver fits in a table.** Heads-up jam/fold at ≤7 bb is within 1.4
  percentage points of the unrestricted optimum, and chip-EV hand-for-hand play costs under 0.1 pp
  [paper](http://web.archive.org/web/20240429153436/https://www.itu.dk/~trbj/papers/poker.pdf). The 3-player ICM jam/fold
  equilibrium is solvable by fictitious play plus value iteration; **under ICM open-jams barely move but calls shrink 2-9x**
  [paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf).
- **The points tables make this format satellite-like, not winner-take-all.** On a coin flip at eight equal stacks you
  need 67% equity under the brief's 10/7/5/4/3/2/1/0 (bubble factor 2.04) and 70% under linear points (Hyperion's default
  `Rules.payouts` is 8..1; BF 2.33) [computed]. Calls are where chip-EV play bleeds: a bad bubble call costs about $2,
  a bad chip-leader shove $0.18 [tool](https://blog.gtowizard.com/high-cost-of-not-being-aggressive-enough/).
- **Lite strategies keep most head-to-head strength and lose worst-case robustness.**
  - A dynamically chosen single river size keeps 99.7% of an 8-size tree's EV
    [tool](https://blog.gtowizard.com/dynamic-sizing-benchmarks/).
  - A 2-bucket CFR-BR strategy small enough for a floppy disk was less exploitable than most 2010 ACPC bots
    [paper](https://poker.cs.ualberta.ca/publications/AAAI12-cfrbr.pdf).
  - Purified, pure-strategy tables won ACPC bankroll events [paper](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf).
  - What tables lose is robustness to an adaptive prober: LBR beats every 2016 ACPC bot by more than 3,180 mbb/g, and
    off-tree sizes alone win 1,849-2,403 mbb/g against a bot exploitable for only 90 inside its tree
    [paper](https://arxiv.org/pdf/1612.07547).
- **Opponent modelling within 200 hands works only as selection among precomputed responses, with priors.** Full models
  do not converge: "two hundred hands does not provide enough information" in Texas hold'em
  [paper](https://poker.cs.ualberta.ca/publications/UAI05.pdf). What has paid is portfolio selection (Hyperborean's implicit
  modelling [paper](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf)) and safe exploitation, which risks
  only what the opponent has already given away [paper](https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf).
- **Evaluation.**
  - AIVAT cuts the standard deviation about 3x heads-up, so 10x fewer hands [paper](https://arxiv.org/pdf/1612.06915),
    and needed about 12x fewer hands on Pluribus' data [paper](https://arxiv.org/pdf/2605.14261).
  - Corrections for chance events alone barely help multiway.
  - Duplicate deals help a lot in limit, little in no-limit, and can hurt in 3-player six-way
    [paper](https://www.ifaamas.org/Proceedings/aamas2013/docs/p1005.pdf).
  - For SNG points, a 3% edge needs roughly 1,800-8,700 SNGs at 95% depending on payout spread (section 11).

---

## 1. The lineage at a glance

| Agent (year) | Game | Blueprint | Abstraction | Real-time step | Headline result | What the authors credit |
|---|---|---|---|---|---|---|
| Tartanian7 → Claudico (2014-15) | HUNL 200 bb | distributed external-sampling MCCFR; T7 1,200 h × 961 cores = 1.15M core-h | 169 preflop; 60 public flop buckets × 500 private per postflop round; hand-made sizes 0.1 pot to all-in | river LP endgame solver, ~8 s per river hand | T7 won ACPC 2014 (avg +479 mbb/h). Claudico lost 9.16 bb/100 over 80k hands (significant at 90%, not 95%) | Polk: the endgame solver was "the strongest part"; translation and pot misperception the biggest weakness |
| Libratus (2017) | HUNL 200 bb | ES-MCCFR with sampled regret-based pruning (3x speedup); ~3M or ~6M core-h depending on the tally | no card abstraction preflop and flop; turn 2.5M, river 1.25M buckets; asymmetric (more opponent sizes) | nested safe subgame solving from the turn, CFR+ 1,000-1,900 iterations, 13 s per hand; overnight self-improver | +147 mbb/g over 120k hands, p = 0.0002 | ablation against BT8: blueprint -8 → nested solving +63 |
| DeepStack (2017) | HUNL 200 bb | none; counterfactual value nets (turn: 10M solved spots, 175 core-years) | 1,000 buckets for range inputs; lookahead F, C, ½P, P, (2P), A | continual re-solving at every action, 1,000-2,000 iterations, 3.0 s mean on a GTX 1080 | +486 mbb/g (AIVAT) over 44,852 hands against 33 non-specialist pros; LBR loses to it | no translation needed; immune to LBR |
| Modicum (2018) | HUNL | MCCFR, 700 core-h, 5 GB | — | depth-limited search, 4 opponent continuation strategies, 4 cores, 20 s per hand | +6 ± 5 vs BT8, +11 ± 9 vs Slumbot | search lifts the blueprint from -57 to +6 |
| Pluribus (2019) | 6-max NL 100 bb | Linear ES-MCCFR plus pruning, 12,400 core-h, <512 GB | lossless preflop with 1-14 raise sizes; 200 buckets per postflop round; later streets {½P, P, A} then {P, A} | search from round 2 (round 1 only if a bet is >$100 off-tree and ≤4 players remain), 1-33 s; k = 4 continuation strategies with a ×5 bias | +48 ± 25 mbb/g (AIVAT) over 10k hands vs 5 pros; +32 ± 15 as 5 copies vs 1 | depth-limited search "the biggest factor" |
| ReBeL (2020) | HUNL | self-play value and policy nets over public belief states, 90 DGX-1s | no information abstraction; ≤8-9 actions; sizes perturbed ±0.1 pot in training | CFR to the end of the round, <2 s per hand | +45 ± 5 vs Slumbot, +9 ± 4 vs BT8, +165 ± 69 vs Dong Kim (7,500 hands) | general self-play plus search |
| Student of Games (2023) | HUNL and others | growing-tree CFR plus sound self-play, TPU scale | fold, call and **one** bet size drawn U(0.5, 1.0) × pot per hand | GT-CFR search | +7 ± 3 vs Slumbot2019 | one random size per hand is enough |
| AlphaHoldem (2022) | HUNL | end-to-end PPO self-play, 1 PC, 3 days | network on the raw state | **none**: 2.9 ms per decision on a TITAN V GPU | +111.56 vs Slumbot, +16.91 vs its own DeepStack reimplementation | Trinal-Clip PPO, K-best self-play |
| Slumbot (2013-2018) | HUNL 200 bb | disk-based Public Chance Sampling CFR; 2016: 3.9e11 infosets, ~250k core-h, 2 TB | 2013: 3,904 / 3,602 / 2,173 buckets; 11 opening sizes from 0.25 to 50 pot | **none**, a pure lookup table | won ACPC 2018 heads-up; lost 36 ± 12 to BT8 | Jackson: "the ability to understand the difference between various bet sizes is vital" |
| Baby Tartanian8 (2016) | HUNL | ~2M core-h, 16 TB of doubles | asymmetric (more actions for the opponent); purified to ⌈log₂\|A\|⌉ bits, preflop kept mixed (170 KB) | not documented in the sources read | ACPC 2016 total-bankroll winner (3rd in instant run-off) | post-processing, asymmetric abstraction |
| Hyperborean (Alberta, 2009-14) | limit HU, 3p limit, HUNL | CFR family; 3p: 16 imperfect-recall buckets, 64 GB, 43M iterations | — | implicit modelling: Exp4 over a portfolio of robust responses | 3p: won 6 of 7 events 2010-13; HUNL 2013 total bankroll winner uncapped | portfolio selection; CFR works empirically at 3 players |

Sources, row by row:
- Tartanian7 and Claudico: [T7 paper](https://www.cs.cmu.edu/~sandholm/hierarchical.aamas15.pdf); [Claudico paper](https://arxiv.org/pdf/1510.08578); [endgame solver paper](https://www.cs.cmu.edu/~sandholm/endgame.aamas15.fromACM.pdf).
- Libratus: [Science paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf); [supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth); [IJCAI demo](https://www.ijcai.org/proceedings/2017/0772.pdf).
- DeepStack: [paper](https://arxiv.org/pdf/1701.01724).
- Modicum: [paper](https://arxiv.org/pdf/1805.08195).
- Pluribus: [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf); [supplement (Wayback)](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
- ReBeL: [paper](https://arxiv.org/pdf/2007.13544).
- Student of Games: [paper](https://arxiv.org/pdf/2112.03178).
- AlphaHoldem: [AAAI page](https://ojs.aaai.org/index.php/AAAI/article/view/20394); [lab page](https://pi.cs.tsinghua.edu.cn/lab/people/jlxing/zh/publication/featured02-aaai-2022/). The paper text says 200,000 hands, the abstract 100,000.
- Slumbot: [2013 paper](https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf); [Compact CFR (2016)](https://cdn.aaai.org/ocs/ws/ws0231/12647-57457-1-PB.pdf); [ACPC](http://www.computerpokercompetition.org/).
- Baby Tartanian8: [demo paper](http://www.cs.cmu.edu/~sandholm/BabyTartanian8.ijcai16demo.pdf).
- Hyperborean: [Gibson thesis](https://poker.cs.ualberta.ca/publications/gibson.phd.pdf); [implicit modelling](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf); [Bard thesis](https://poker.cs.ualberta.ca/publications/bard.phd.pdf).

---

## 2. Heads-up, CMU line: Claudico (2015) to Libratus (2017)

**Claudico.**
- **Match.** 80,000 duplicate hands (4 pros × 20,000), blinds 50/100, stacks reset to 20,000 each hand. Humans won by
  732,713 chips, i.e. 9.16 bb/100, "statistically significant at the 90% confidence level, though it was not
  statistically significant at the 95% level" [paper](https://arxiv.org/pdf/1510.08578).
- **Blueprint.** "An improved version of … Tartanian7", computed for months on 961 Blacklight cores. Hand-made action
  abstraction "ranging from 0.1 pot in certain situations to all-in", with pseudo-harmonic translation of opponent bets.
  The rounding threshold differed by street, "more aggressive (i.e., larger) … for the later betting rounds"
  [paper](https://arxiv.org/pdf/1510.08578).
- **River endgame solver.** Bayes-rule ranges from the trunk, hands bucketed by equity, an LP solved in Gurobi, "around 8
  seconds per hand". In the predecessor paper it measured +87 ± 50 vs Hyperborean and +29 ± 25 vs Slumbot on hands that
  reached the river [paper](https://www.cs.cmu.edu/~sandholm/endgame.aamas15.fromACM.pdf).
- **The leaks the pros found:**
  - **Pot misperception after translation**, which Polk "views … as Claudico's biggest weakness". It folded A4s preflop
    after putting in over half its stack because translation "mapped the opponent's raise down" and it "thought we had
    invested around 7,000 when we had actually invested close to 10,000". It folded top pair plus a flush draw after a
    flop raise just under its smallest size was read as a call [paper](https://arxiv.org/pdf/1510.08578).
  - **Overbet bluffs without card removal.** Its endgame buckets merged 3c2c with 3s2c; CMU removed its own large endgame
    bets partway through [paper](https://arxiv.org/pdf/1510.08578).
  - **A pure-action tell created by thresholding**, reported by the Libratus authors as seen in Claudico. With limp
    frequencies of 6% for bad hands and 4% for good ones, a 5% threshold leaves the bot "only limping with bad hands,
    which would be extremely exploitable!"
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth)
  - Style: Claudico limped about 10% of hands and appeared to profit from them; it made 10%-pot bets and bet 20,000 into
    500 [paper](https://arxiv.org/pdf/1510.08578).
- Transfer: everything except the endgame LP. Above all, after translating an opponent's bet, every downstream decision
  must read the **true** pot and stacks, not the translated history.

**Libratus.**
- **Match.** 120,000 hands over 20 days against Les, Kim, McAulay and Chou. +147 mbb/g, "99.98% statistical significance
  and a P value of 0.0002" (hands treated as i.i.d.); it beat each human individually
  [paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf).
- **Blueprint.** External-sampling MCCFR with sampled regret-based pruning: actions below a negative regret threshold are
  sampled with probability K/(K+C-R(a)), with a 2% floor, during the last half of iterations, "a speedup of MCCFR by a
  factor of three". Separate blueprints by position and by how the humans opened
  [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
- **Card abstraction.** None preflop or flop. The turn's 55M hands into 2.5M buckets and the river's 2.4B into 1.25M,
  10^161 → 10^12 decision points [paper](https://www.ijcai.org/proceedings/2017/0772.pdf).
- **Action abstraction.**
  - Mostly "nice fractions or multiples of the pot"; early-tree sizes from a parameter optimiser that converged to "a
    locally optimal set of bet sizes" [paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf).
  - Asymmetric: "more actions for the opponent, to better reduce the error resulting from action translation"
    [paper](https://www.ijcai.org/proceedings/2017/0772.pdf).
  - Exact counts per node are not published.
- **Compute, two tallies:**
  - ~25M core-hours: ~6M blueprint, ~3M nested solving, ~3M self-improver, ~13M exploration and evaluation
    [paper](https://www.ijcai.org/proceedings/2017/0772.pdf).
  - ~12M: the same split counting only the 14 cores per node actually used. "No GPUs were used"
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
- **Search.**
  - Blueprint on rounds 1-2, with off-tree bets rounded to nearby sizes. From the turn, a finer subgame with no card
    abstraction, re-solved "every time the opponent bets" [paper](https://www.ijcai.org/proceedings/2017/0772.pdf).
  - CFR+ for 1,000 iterations (pot ≤ $1,600) or 1,900; 13.0 s per hand on average
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
  - Its own bet sizes in each subgame were jittered "by a percentage chosen uniformly at random between 0 and 8%"
    [paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf).
- **Self-improver** (preflop only):
  - Each night it added the pseudo-harmonic midpoint (A+B+2AB)/(A+B+2) of the two gaps [A, B] that scored highest on
    Σ min{x-A, B-x} over the humans' sizes x, solved together with a default sibling size so the new branch stays
    balanced.
  - Type 1 (copy the day's most common size) needed the same size "for each of the last eight times". The humans
    "changed the bet sizes they used almost every day", so it "played little role".
  - Type 2 ended up deciding "roughly half of all the hands"; k = 3 holes fixed per 24 h
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
- **Anti-tell design.**
  - Range thresholding: an action is zeroed only "if every hand has a probability below that threshold", 4% on rounds 1-2.
  - Timing independent of private cards.
  - The pros "coordinated how they explored the AI's potential weaknesses via using different bet sizes", with hot keys
    for unusual pot fractions [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
- **Ablation against BT8 (mbb/g):**

  | Variant | mbb/g |
  |---|---|
  | Raw blueprint | -8 ± 15 |
  | Blueprint + post-processing | +18 ± 21 |
  | On-tree nested solving | +59 ± 28 |
  | Full nested solving | +63 ± 28 |

  BT8 had beaten the next two ACPC bots by only 12 ± 10 and 24 ± 20. Off-tree response exploitability in a smaller game:
  action translation 1,465 against nested unsafe 148 and nested safe 119 mbb/h
  [paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf).
- **Safe and nested subgame solving (NeurIPS 2017 best paper)**, large no-limit flop hold'em at 30,000 buckets
  [paper](https://arxiv.org/pdf/1705.02955):

  | Method | mbb/h |
  |---|---|
  | Trunk alone | 41.41 |
  | Unsafe solving | **396.8**, against 65.59 at 200 buckets: "exemplifies its variability" |
  | Best safe variant | 8.777 |

  Nested solving beats translation "if there is sufficient time to solve the subgame".
- Transfer:
  - Transfers: unabstracted preflop tables, regret-pruned MCCFR offline, ±0-8% size jitter, range thresholding,
    card-independent timing, a denser opponent-side size grid, and an offline Type 2 hole-filling loop.
  - Does not transfer: nested solving, about four orders of magnitude over budget, with two-player zero-sum guarantees
    that do not hold at 8-max or under ICM.

---

## 3. Learned-value and learned-policy line: DeepStack, Modicum, ReBeL, Student of Games, AlphaHoldem

- **DeepStack.**
  - Continual re-solving at every decision, keeping its own range and the opponent's counterfactual values, so no
    translation is needed.
  - Lookahead actions "fold (if valid), call, 2 or 3 bet actions, and all-in". 1,000 CFR iterations per round (2,000 on
    the river), under 5 s on one GTX 1080; median 2.3 s, mean 3.0 s per action. Preflop median 0.04 s because "we cache
    the re-solving result for every observed pre-flop situation".
  - Value nets of 7 × 500 PReLU layers: the turn net took 10M solved situations and "over 175 core years"; the flop net
    half a GPU-year.
  - Result: 44,852 hands, +486 mbb/g with AIVAT (492 raw), against pros who were not heads-up specialists. LBR "fails to
    exploit DeepStack at all — itself losing by over 350 mbb/g" [paper](https://arxiv.org/pdf/1701.01724).
- **DeepStack on how few actions are needed:** "the F, C, P, A, actions provide an excellent tradeoff". A 61k-node tree
  had L2 error 1.272 against 0.891 for an 11-action, 555k-node tree. Replacing P with ½P raised the error to 3.426: "a
  single betting action that is not one pot … causes a substantial error increase"
  [paper](https://arxiv.org/pdf/1701.01724).
- **Modicum (depth-limited solving)** [paper](https://arxiv.org/pdf/1805.08195):
  - 700 core-hours, 16 GB, a 5 GB blueprint, a 240 MB table of end-of-preflop values, 4 cores, 20 s per hand.
  - Ablation:

    | Variant | vs Baby Tartanian8 | vs Slumbot |
    |---|---|---|
    | Blueprint alone | -57 ± 13 | -11 ± 8 |
    | Naïve depth-limited solving | -10 ± 8 | -1 ± 15 |
    | Depth-limited solving | +6 ± 5 | +11 ± 9 |

  - Opponent continuation strategies bias fold/call/raise by ×10. A 2-hidden-layer × 64 leaf net on 34 features is an
    alternative.
- **ReBeL** [paper](https://arxiv.org/pdf/2007.13544):
  - Search over public belief states; nets of 6 × 1,536; data from 90 DGX-1s; "faster than 2 seconds per hand".
  - Results: +45 ± 5 vs Slumbot, +9 ± 4 vs BT8, +165 ± 69 vs Dong Kim over 7,500 hands.
  - Training sizes perturbed ±0.1 pot so the nets generalise to nearby bets; off-tree bets are added to the subgame at
    test time.
- **Student of Games:** a single bet size per hand, drawn uniformly from 0.5-1.0 pot, plus fold and call, was enough to
  beat Slumbot2019 by 7 ± 3 mbb/g [paper](https://arxiv.org/pdf/2112.03178).
- **AlphaHoldem (AAAI 2022): the closest thing to a constant-time strong policy.**
  - End-to-end self-play RL with a pseudo-siamese net, one PC, 3 days, 2.9 ms per decision on a TITAN V GPU, ">1,000
    times faster than DeepStack".
  - +111.56 mbb/h vs Slumbot and +16.91 vs the authors' own DeepStack reimplementation; hand count 100k in the abstract,
    200k in the text [paper](https://ojs.aaai.org/index.php/AAAI/article/view/20394);
    [lab page](https://pi.cs.tsinghua.edu.cn/lab/people/jlxing/zh/publication/featured02-aaai-2022/).
  - The comparison is weakened because a separate DeepStack reimplementation **lost** 63 ± 40 to Slumbot
    [paper](https://arxiv.org/abs/2007.10442).
- **Interpretable and distilled policies:**
  - Bertsimas & Paskov combined optimal classification trees on a compact feature set with CFR self-play; the abstract
    says the bot beats Slumbot, but its numbers were not retrievable here
    [paper, abstract only](https://dspace.mit.edu/handle/1721.1/142962.2).
  - Ganzfried & Yusuf fitted decision trees to 80,000 solved river-like games (10 private hands, 31 sizes from 0 to 3 pot)
    and extracted the "80-20 Rule": "If your hand beats between 20% and 80% of the opponent's distribution of hands, then
    you should always check (or make an extremely small bet)". And an "All-In Rule": beat 95% of the opponent's
    distribution while it holds at least 10% strong hands → all-in. They also proposed k-nearest-neighbour lookup into
    presolved games [paper](https://arxiv.org/abs/1612.06340).
  - SpinGPT (3-player Spin & Go, an LLM) matched a solver on 78% of decisions and beat Slumbot heads-up by
    13.4 ± 12.9 bb/100 over 30,000 hands [paper](https://arxiv.org/abs/2509.22387).
- Transfer:
  - Value nets do not fit: a 7 × 500 forward pass is about 3.5M multiply-adds and ReBeL's about 18M, roughly 100x the
    pure-Python budget before any CFR (estimates from the layer sizes). AlphaHoldem's 2.9 ms is on a GPU.
  - Modicum's 2 × 64 net (~6.5k multiply-adds) is borderline at about 0.3-0.7 ms in pure Python (estimate, unmeasured).
  - What does fit: pot-fraction normalisation, an F/C/P/A-class action set with one jittered size, preflop as a cache, and
    presolved small games keyed by range shape (k-NN or tree rules).

---

## 4. Pluribus and the multiplayer question

**What it did** (Science paper plus supplement; supplement read from a 2020 Wayback copy):
- **Action abstraction.**
  - Preflop raise sizes "between one and 14 depending on the situation", all pot fractions, chosen "by hand based on what
    raise sizes earlier versions of Pluribus decided to use with significant positive probabilities".
  - Rounds 3-4: at most {0.5 pot, 1 pot, all-in} for the first raise and {1 pot, all-in} after.
  - 664,845,654 action sequences, of which 413,507,309 were ever reached
    [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
- **Off-tree bets.** On round 1, search only if a raise is ">$100 off from any raise size in the blueprint … and there are
  no more than four players remaining"; otherwise "randomized pseudo-harmonic action translation" and the blueprint. On
  later rounds the actual bet "is added as a valid action into the subgame model" and the subgame is re-searched from the
  start of the round [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
- **Card abstraction.** Lossless preflop (169); 200 k-means buckets per postflop round in the blueprint; in search, the
  current round lossless and later rounds 500 buckets per flop
  [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
- **Linear MCCFR details** [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf):
  - Linear discounting for the first 400 minutes ("about a factor of 3").
  - Pruning after 200 minutes: in 95% of iterations, skip actions with regret below -300M except on the last round or into
    terminals.
  - 4-byte integer regrets with a -310M floor.
  - The average strategy is kept for round 1 only. Later rounds average snapshots of the *current* strategy, which
    "reduced memory usage by nearly half"; "no theoretical benefit to using the average strategy" with 6 players.
- **Deployment.** Under 128 GB "while storing a compressed form of the blueprint". Continuation strategies are compressed
  by sampling one action per abstract infoset and storing it in "the minimum number of bits"
  [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
- **Search.**
  - "Sort of half-way between safe and unsafe" [author](http://web.archive.org/web/20240912182811/https://www.reddit.com/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/).
  - Solves from the start of the current round. Plays the final CFR iterate, which "helps Pluribus avoid poor actions that
    are not completely eliminated", while updating beliefs with the weighted average.
  - At the leaves every player, the searcher included, chooses among four continuation strategies: the blueprint and
    fold-, call- and raise-biased versions with those probabilities "multiplied by 5". Modicum had let only the opponent
    choose, which made the searcher conservative.
  - No ablation of k exists; CMU's press release says "five" strategies, against k = 4 in the paper
    [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf);
    [secondary](https://www.cmu.edu/news/stories/archives/2019/july/cmu-facebook-ai-beats-poker-pros.html).
- **Resources and what mattered.** 1-33 s per subgame, about 20 s per hand in self-play, two 14-core CPUs
  [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf). Measuring each innovation was "too expensive", so
  there is no blueprint-vs-search number. Depth-limited search cut resources by "probably at least five orders of
  magnitude" [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
  Brown: "advances in the search algorithm were the biggest factor"
  [author](http://web.archive.org/web/20240912182811/https://www.reddit.com/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/).
- **No adaptation.** "Pluribus plays a fixed strategy that does not adapt to the observed tendencies of the opponents"
  [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf). It did not carry knowledge from one hand to the
  next, and kept "one blueprint strategy with six components", one per seat
  [author](http://web.archive.org/web/20240912182811/https://www.reddit.com/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/).
- **Strategic findings.**
  - Limping is "suboptimal for any player except the 'small blind'"; Pluribus experimented with it and "gradually
    discarded this action". It donk-bets "far more often than professional humans do"
    [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
  - Pros: "Its major strength is its ability to use mixed strategies"; it "used multiple raise sizes preflop"
    [secondary](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/).
  - All of this is 100 bb cash evidence. Pluribus never played short-stack ICM.
- **Brown on tournaments:** "if you just use ICM then it would be pretty easy to adapt these techniques to tournaments";
  stack size can be "an input to the network". That CFR finds a competitive 6-player preflop "is surprising and is not
  guaranteed by the existing theory". Adding players "mostly makes the real-time search algorithm faster because the
  ranges … become narrower"
  [author](http://web.archive.org/web/20240912182811/https://www.reddit.com/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/).

**Other multiplayer evidence:**
- **3-player limit (Abou Risk & Szafron, AAMAS 2010).** "For multiplayer … we lose all theoretical guarantees for CFR",
  yet the CFR agents "placed first and second" in both 3-player events of 2009. PR2, which only knew whether its hand was
  "above or below average", still won a 7-agent bankroll test at 530 mb/h. Always-fold loses 500 mb/h in 3-player
  [paper](https://poker.cs.ualberta.ca/publications/AAMAS10.pdf).
- **Gibson's thesis.** Hyperborean3p won 6 of 7 three-player ACPC events in 2010-13. In 3-player hold'em the current
  profile "reaches strong play much sooner than the average profile, which requires about ten times the number of
  iterations". CFR provably removes iteratively strictly dominated actions in multiplayer
  [paper](https://poker.cs.ualberta.ca/publications/gibson.phd.pdf).
- **Strategy stitching** (heads-up "experts" grafted on once a player folds): static experts beat the base strategy,
  +3.06 ± 0.70 vs -6.09, and are "preferred … especially when memory limitations are present"
  [paper](https://poker.cs.ualberta.ca/publications/NIPS11.pdf).
- **3-player Kuhn (Ganzfried et al. 2018).** An exact-Nash agent defeated "a variety of realistic opponents"; Nash agents
  "can be successful in multiplayer games after all" [paper](https://arxiv.org/abs/1804.04789).
- **3-player Kuhn with opponent modelling (Ganzfried, Wang & Chiswick).** 3,000-hand matches over 6 seat permutations.
  Model-plus-best-response (Nash for the first 100 hands) won 48 millichips/hand against 37/35/30 for three Nash agents
  and 34 down to -172 for class bots. With a uniform prior instead of an informed one it scored -54, second to last
  [paper](https://arxiv.org/html/2212.06027v4).
- **Fictitious play vs CFR.** Fictitious play gives a closer Nash approximation than CFR in multiplayer and general-sum
  random games; CFR wins in two-player zero-sum [paper](https://arxiv.org/abs/2001.11165v4). Ganzfried's 3-player ICM
  jam/fold solver is fictitious-play based (section 8).
- Transfer:
  - Pluribus' later-street size menu and its "add the real bet, else randomized psHar" rule map directly onto tables.
  - Its fold/call/raise ×5 biased opponents are a ready-made set of exploit arms to solve for offline (section 10).
  - Current-strategy snapshots and one sampled pure action per infoset are how a multiplayer table gets down to a few MB.
  - Per-seat blueprints are cheap to index.
  - 1,326-combination Bayesian range updates for 7 opponents per action (about 9k updates) are borderline in pure Python;
    use coarse classes (estimate).

---

## 5. Slumbot and the ACPC winners

**Slumbot (Eric Jackson).**
- **2013 build** [paper](https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf):
  - "5.7 billion information sets"; imperfect-recall buckets "3,904 on the flop, 3,602 on the turn, and 2,173 on the
    river".
  - Opening sizes "0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0, 15.0, 25.0, 50.0" pot; raises 0.5-50; 3-bets 0.5, 1, 2; pot
    only after that. Symmetric abstraction, Ganzfried translation, and it "does not adapt to its opponents".
- **What Jackson says mattered:** "we devote most of our capacity to the betting abstraction … a reasonably high quality
  card abstraction can be achieved with relatively few buckets, but the ability to understand the difference between
  various bet sizes is vital" [paper](https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf).
- **Compact CFR (2016)** [paper](https://cdn.aaai.org/ocs/ws/ws0231/12647-57457-1-PB.pdf):
  - Follow-the-leader (argmax over regrets), 1-byte regrets with stochastic rounding, no accumulated strategy, so "only
    1/16 of the memory".
  - The current strategy "generally outperforms the average strategy" head-to-head, though the last checkpoint alone was
    "very poor" on exploitability. Blending 51 checkpoints gave 21.7 against 10.14 mbb/g for the standard average.
  - Slumbot 2016: 3.9 × 10^11 infosets on 11 EC2 instances.
- **Strength and its limits:**
  - About 250k core-hours and 2 TB; BT8 beat it by 36 ± 12 [paper](https://arxiv.org/pdf/1805.08195).
  - It "does not conduct lookahead search; its entire policy is precomputed and used as a lookup table"
    [paper](https://arxiv.org/abs/2007.10442).
  - slumbot.com notes an earlier version was "weak-tight on the river … exploitable by hyper-aggressive play on the final
    street" [author](https://slumbot.com/).
  - In the 2017 ACPC crosstable it lost 1,167 mb/h to ASHE, 760 to PokerBot5 and 58 to Intermission (this pass's parse
    of the raw JSON) [secondary](http://www.computerpokercompetition.org/downloads/competitions/2017/xtable/output/xtable.json).
  - 2018 ACPC heads-up winner [secondary](http://www.computerpokercompetition.org/).
- **slumbot2019 README:** "CFR+ is the preferred algorithm when it is feasible, ideally with no card abstraction".
  Multiplayer is "only supported by MCCFR", and "a reentrant betting tree" is advised because the tree "can explode with
  multiplayer games" [author](https://raw.githubusercontent.com/ericgjackson/slumbot2019/master/README.md).

**CMU entries: post-processing and asymmetric abstraction.**
- **Tartanian7** won the 2014 ACPC, beating every opponent at an average of 479 mbb/h. Post-processing, measured in mbb/h
  against Hyperborean and Slumbot 2013 [paper](http://www.cs.cmu.edu/~sandholm/hierarchical.aamas15.pdf):

  | Post-processing | vs Hyperborean | vs Slumbot | Average |
  |---|---|---|---|
  | None | +30 | +10 | +20 |
  | Purification | +55 | +19 | +37 |
  | Threshold 0.15 | +35 | +19 | +27 |
  | New fold-biased scheme (0.2) | +39 | +103 | +71 |

  The new scheme folds outright if P(fold) > 0.2, otherwise purifies among fold, call and one "bet" meta-action, then
  among bet sizes. The rationale: "Biasing toward conservative actions that reduce variance (e.g., the fold action in
  poker) is helpful in a strong agent".
- **Tartanian4-TBR (purified)** beat its thresholded twin IRO head-to-head by 80 ± 23 mbb/h and won the 2010 no-limit
  total-bankroll event: "opponents … were either not trying or not able to find successful exploitations"
  [paper](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf).
- **Baby Tartanian8** won the 2016 total bankroll [paper](http://www.cs.cmu.edu/~sandholm/BabyTartanian8.ijcai16demo.pdf):
  - "More actions are allowed for the opponent than for ourselves".
  - 16 TB purified to ⌈log|A|⌉ bits to fit 200 GB.
  - "To reduce the possibility of an opponent exploiting our deterministic strategy, we did not purify or compress … the
    preflop, which requires only 170 KB".
- **Asymmetric abstraction (Bard, Johanson & Bowling, AAMAS 2014).** A finer abstraction for yourself than the opponent
  raises one-on-one value but also exploitability: 12-5 had mean 18.97 and exploitability 435.8, against 15.84 and 289.2
  for 12-12. "Designers whose goal is to minimize worst-case performance should assume a pessimistic (i.e., fine-grained)
  abstraction for other agents" [paper](https://poker.cs.ualberta.ca/publications/2014-aamas-asymmetric-abstractions.pdf).

**Alberta: exploiting the field.**
- **Implicit modelling (Bard et al., AAMAS 2013).** A portfolio of robust responses computed offline, chosen online with
  Exp4 (η = 0.025, 2% minimum probability) plus importance-sampling variance reduction
  [paper](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf):
  - About 2x the equilibrium's winnings against its target mimics, and about 65% better than equilibrium against the full
    2010 field.
  - Replayed into the 2011 total bankroll (3,000-hand matches), the small portfolio would have won at 317 ± 5 mbb/h,
    against Calamari's 276 and Alberta's actual 224.
  - UCB was worse; the smaller portfolio beat the larger ("learning cost").
- **2013 heads-up no-limit total bankroll.** The implicit-modelling Hyperborean was second under the 750 mbb/g cap (297 vs
  Slumbot's 312) and the clear winner uncapped (1,474). "Weaker agents generally lost badly against equilibrium-based
  agents … even though a Nash equilibrium does not directly attempt to exploit"
  [paper](https://poker.cs.ualberta.ca/publications/bard.phd.pdf).
- **A disagreement.** Brown in the AMA: "the bots that won the opponent exploitation category didn't do any adaptation,
  they would just play an approximate Nash equilibrium!"
  [author](http://web.archive.org/web/20240912182811/https://www.reddit.com/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/).
  This is true of the CMU winners (2010, 2014, 2016) but not of 2013, per Bard. Both readings hold: equilibrium bots
  collect most of what weak bots give away, and a portfolio adds to it.

**Six-player ACPC (2018)** was the closest precedent to this setting: "only 2 seconds per hand … rather than 7", and a
250 GB submission cap. PokerBot5 won it; there is no write-up of it or of Intermission (2017)
[secondary](http://www.computerpokercompetition.org/). Even that event allowed about 2,000x this budget per hand.

Transfer:
- Spend bytes on bet-size coverage, especially the opponent's side, rather than card buckets.
- Store the postflop as purified, fold-biased action indices and keep the preflop mixed.
- Use current-strategy or checkpoint blends offline.
- Use a reentrant tree to keep an 8-player tree small.
- Audit river and turn fold frequencies against overbets and shoves: hyper-aggression is how fixed-table bots got beaten
  (Slumbot's weak-tight river; LBR's waiting overbets).

---

## 6. Which components matter most: the ablation evidence, ranked

| Component | Strongest measured effect | Survives 1 ms? |
|---|---|---|
| Real-time search / subgame solving | Libratus vs BT8: -8 → +63 mbb/g; Modicum -57 → +6 (vs BT8); off-tree exploitability 1,465 (translation) → 119 (nested solving); "20 s thinking ≈ 100,000x model" | **No.** CFR+ needs 10^3 iterations, 13 s per hand in Libratus |
| Card abstraction quality | LBR: "a large portion of the exploitability … is caused by card abstraction"; feature choice alone (E[HS] vs E[HS²] vs nested) spans ~20% of exploitability at equal size; imperfect recall beats perfect recall head-to-head and in exploitability | Yes: offline buckets and lookups |
| Bet-size coverage, opponent side | 1,849-2,403 mbb/g LBR wins from off-tree sizes against a bot exploitable for 90 inside its tree; Jackson: bet sizes "vital"; Libratus and BT8 gave the opponent more sizes | Yes: a denser opponent grid plus translation |
| Translation method | Clairvoyance game exploitability: Det-Arith 12.37, Det-Geo 2.43, Rand-Geo 1.00, Det-psHar 0.71, Rand-psHar 0.00; Leduc average 0.463 (Rand-psHar) vs 0.574-0.666 | Yes: a few float ops |
| Post-processing (purify, threshold) | Libratus +26 mbb/g (-8 → +18); T7 fold-biased +71 vs +20 average; TBR beat IRO by 80 ± 23 | Yes: offline, zero runtime cost |
| Hole-filling where opponents bet | Libratus Type 2 self-improver decided ~half of all hands by the end | Yes, as an offline loop |
| Opponent exploitation | Implicit modelling ~65% over equilibrium vs the 2010 field; 2013 uncapped winner | Partly: a portfolio switch is a table swap |
| Action menu size for yourself | DeepStack: F, C, P, A "an excellent tradeoff"; GTO Wizard: one river size keeps 99.7% of EV; SoG beat Slumbot with one random size | Yes: fewer sizes, smaller tables |

Sources:
- Search: [Libratus](https://noambrown.github.io/papers/17-Science-Superhuman.pdf); [Modicum](https://arxiv.org/pdf/1805.08195); [TED talk](https://www.ted.com/talks/noam_brown_ai_won_t_plateau_if_we_give_it_time_to_think).
- Card abstraction: [LBR](https://arxiv.org/pdf/1612.07547); [CFR-BR](http://poker.cs.ualberta.ca/publications/AAAI12-cfrbr.pdf); [abstraction evaluation](http://poker.cs.ualberta.ca/publications/AAMAS13-abstraction.pdf).
- Bet-size coverage: [LBR](https://arxiv.org/pdf/1612.07547); [Slumbot 2013](https://cdn.aaai.org/ocs/ws/ws0979/7044-30516-1-PB.pdf); [Baby Tartanian8](http://www.cs.cmu.edu/~sandholm/BabyTartanian8.ijcai16demo.pdf).
- Translation: [pseudo-harmonic mapping](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf).
- Post-processing: [Libratus](https://noambrown.github.io/papers/17-Science-Superhuman.pdf); [Tartanian7](http://www.cs.cmu.edu/~sandholm/hierarchical.aamas15.pdf); [purification](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf).
- Hole-filling: [Libratus supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
- Exploitation: [implicit modelling](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf); [Bard thesis](https://poker.cs.ualberta.ca/publications/bard.phd.pdf).
- Action menu: [DeepStack](https://arxiv.org/pdf/1701.01724); [GTO Wizard](https://blog.gtowizard.com/dynamic-sizing-benchmarks/); [Student of Games](https://arxiv.org/pdf/2112.03178).

**Reading for a 1 ms bot.** The top row is gone. What is left, in order of measured size: bet-size coverage plus
translation (worst-case robustness), post-processing (head-to-head), card or feature quality, and hole-filling. In a
multiplayer tournament one more component matters that none of these heads-up ablations measure: **the terminal utility
(ICM)**. In the only multiplayer tournament equilibrium computed (section 8) it changes calling frequencies by 2-9x,
larger than any of the post-processing effects above.

---

## 7. Off-tree bets, probing and bet-size tells

- **Pseudo-harmonic mapping.** An opponent bets x (as a fraction of the pot) between abstract sizes A < x < B. Map to A
  with probability f(x) = ((B-x)(1+A)) / ((B-A)(1+x)).
  - It is "the only mapping consistent with" the clairvoyance-game rule of calling a bet x with probability 1/(1+x).
  - Its median is x* = (A+B+2AB)/(A+B+2).
  - Only Rand-psHar and Rand-Arith satisfy all of the paper's robustness axioms.
  - Geometric maps never map a bet down to a check (they break at A = 0)
    [paper](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf).
- **History of exploited mappings** [paper](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf):
  - Tartanian1 used deterministic arithmetic and was exploited by bets just under the midpoint.
  - Mapping small bets up to the smallest size "could be significantly exploited by an opponent who makes extremely small
    bets as bluffs".
  - Hyperborean 2009 used "a simple strategy (that did not even look at its own cards) to exploit opponents' betting
    boundaries and came in first place".
  - Paradox: against 2012 ACPC bots "not attempting any exploitation of bet sizes", the exploitable mappings did slightly
    better (Det-Arith 609 vs Rand-psHar 568 mbb/h), and Tartanian5 shipped Det-psHar.
- **Hard vs soft translation (Schnizlein, Bowling & Szafron, IJCAI 2009).** A card-blind "naïvePA" (a large pot bet, then
  a small all-in) beat a hard-translation bot by 27.01 $/h ($1/$2 blinds, about 13.5 bb per hand) but lost 5.66 $/h to
  soft translation. A size-by-strength "+-" strategy beat hard translation by 5.42 and soft by 1.50. Their modelling can
  tell "with high accuracy and within 100 hands" how an agent hard-translates
  [paper](https://www.ijcai.org/Proceedings/09/Papers/055.pdf).
- **Translation is the weak point of tables.** Nested solving beats randomized psHar 119 to 1,465 mbb/h
  [paper](https://arxiv.org/pdf/1705.02955). LBR with only fold, call, min-bet, 2/4/8x pot and all-in wins 1,849 against a
  fold/call/pot/all-in bot [paper](https://arxiv.org/pdf/1612.07547). With no search, **shrink the gaps** (a denser
  opponent-side grid, as Libratus and BT8 did) and **compute downstream decisions from the true pot** (Claudico).
- **Probe sizes.** The psHar medians between common abstract sizes are 0.2 pot (0 to 0.5), 0.714 (0.5 to 1) and 1.4
  (1 to 2). These are the sizes that maximise a translating opponent's confusion [computed from the formula].
- **Bet-size tells in bots:**
  - Libratus guarded against tells with 0-8% jitter, range thresholding (an action is dropped only when *every* hand plays
    it under 4%) and card-independent timing
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
  - Too much rounding "signals too much to the opponent about the agent's private information"
    [paper](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf).
  - Ganzfried & Yusuf: "if we bet one size with a weak hand and a different size with a strong hand, it would be very easy
    for the opponent to exploit us" [paper](https://arxiv.org/abs/1612.06340).
  - Galfond's example: an opponent who bets 75% with AA/AK/KQ/5x and 25% with sets and medium hands makes "you should fold
    your AQ!" trivial; a second size multiplies the ranges to balance (2³ → 3³ lines)
    [author](https://www.philgalfond.com/articles/exploiting-gto-bet-sizing/).
  - GTO Wizard: "betting small with your entire range would be an acceptable strategy"; a hand that mixes is near
    indifferent, so a mixing error costs only against an opponent who adjusts
    [tool](https://blog.gtowizard.com/overchoice-making-sense-of-multiple-sizings/);
    [tool](https://blog.gtowizard.com/the-three-laws-of-indifference/).
  - No paper measures bot bet-size tells directly in mbb/g; this is a gap.
- **The cost of one size per node is small:**
  - Simple vs complex flop sizing is "within one one-hundredth of a big blind" on most flops, worst case 0.02 bb, and
    "multiple sizes matter most on the river" [tool](https://blog.gtowizard.com/do-multiple-sizes-matter/).
  - A dynamically chosen single river size keeps 99.7% of the EV of an 8-bet/5-raise tree (99.95% against the best fixed
    single size). The best fixed river sizes were about 75-100% pot in position and about 50% out of position. Over 150k
    hands against Slumbot the 1-size strategy won 19.4 bb/100 and the complex one 13.1 (CIs overlap)
    [tool](https://blog.gtowizard.com/dynamic-sizing-benchmarks/).
- Transfer:
  - Incoming bets: randomized psHar drawn once per hand (stable across re-asks), a dense opponent grid (min-bet, 0.25,
    0.33, 0.5, 0.75, 1, 1.5, 2, all-in), separate precomputed responses for min-bets and for overbets and shoves, and the
    true pot for everything downstream.
  - Outgoing bets: one size per (street, position, pot type) for the whole range, ±0-8% jitter, and range thresholding
    rather than per-hand rounding.

---

## 8. Push/fold, ICM and endgame solving in sit-and-goes

**Heads-up jam/fold is solved, and chip EV is enough** (Miltersen & Sørensen, AAMAS 2007; read from a Wayback copy):
- **Setup.** SB 300, BB 600, 8,000 chips in total (≤ ~6.7 bb effective), the PartyPoker SNG heads-up endgame.
- **Near-optimality.** Their jam/fold strategy wins "within 1.4 percentage points" of an unrestricted optimal strategy;
  always-jam is within 5.3 pp (Sklansky's revised "System" equals always-jam here).
- **Single hand vs tournament.** Playing each hand with the single-hand chip-EV jam/fold strategy costs "less than 0.1
  percentage points": heads-up P(win) ≈ s1/(s1+s2), so heads-up ICM is chip share.
- **Structure.** At most one hand ever needs mixing. No fixed hand ranking works: the SB folds 43s and jams J2o at 1,800
  and does the reverse at 3,600.
- [paper](http://web.archive.org/web/20240429153436/https://www.itu.dk/~trbj/papers/poker.pdf)

**Three-player ICM jam/fold equilibrium (Ganzfried & Sandholm, AAMAS 2008; IJCAI 2009).**
- **Setup.** 13,500 chips at 300/600 (7.5 bb each at equal stacks), 50/30/20 payouts; stack vectors in multiples of 300,
  946 non-terminal states.
- **VI-FP algorithm.** ICM-initialised state values; fictitious play per state over the button's 169, the SB's 2 × 169
  and the BB's 3 × 169 information sets; value iteration outside. 21 outer iterations of "several hours".
- **Equilibrium quality.** No player gains more than $0.0488 by deviating (<0.05% of the pool)
  [paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf).
- **ICM vs equilibrium values.** Mean absolute deviation $0.37 per $100 pool across 2,838 player-states; only 3.8% are
  off by more than $1. The worst error ($28.85 ICM vs $25.86 equilibrium) is a BB with 900 chips about to post 600:
  ICM "does not take into account" the blinds a short stack must post next
  [paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf).
- **Tournament (ICM) vs single-hand (chip EV) frequencies at equal 4,500 stacks**
  [paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf):

  | Spot | ICM | Chip EV |
  |---|---|---|
  | BTN jam | 0.376 | 0.355 |
  | SB jam after a fold | 0.652 | 0.633 |
  | SB call of a BTN jam | 0.088 | 0.234 |
  | BB call, jam then fold | 0.145 | 0.308 |
  | BB call, fold then jam | 0.273 | 0.466 |
  | BB call after two jams | **0.021** | 0.197 |

  With two jams in, the tournament BB calls only "the four highest pocket pairs and AKs".
- **Hand orderings.** First-in jam ranges contradict Karlson-Sklansky rankings (the SB folds Q5o but jams 52s); ranges
  after a jam "agree pretty closely" with them; randomisation is rare.
- **Precompute cost.** The 3-way all-in equity table took "a month using 16 processors" and collapsed to about 11M entries
  [paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf).
- **IJCAI 2009** [paper](https://www.ijcai.org/Proceedings/09/Papers/034.pdf):
  - VI-FP can converge to a non-equilibrium. PI-FP (policy iteration outside) is an equilibrium whenever it converges, and
    reached ε < 0.05 fastest; VI-FP took "almost three times as long".
  - The ex-post check found ε ≤ $0.049. Terminal states with ≤2 players are valued by ICM "since previous two-player
    results showed that ICM payoffs very closely approximate equilibrium payoffs".

**How good is ICM?**
- Malmuth-Harville gives "misleading probabilities" for later places but "adequately approximate[s] the expected payout";
  the largest relative equity error in a finite-element comparison was 1.42%
  [secondary](https://en.wikipedia.org/wiki/Independent_Chip_Model).
- Melcher's TU Wien thesis (the HRC author's): Malmuth-Harville and Roberts have "similar accuracy", both underestimate
  big stacks, and FGS is a significant improvement [paper](https://repositum.tuwien.at/handle/20.500.12708/79991).
- On 33,478 real WSOP and PokerNews players, ICM beats a chip-rank baseline (MSE 4.30e-3 vs 6.77e-3), but short stacks
  underperform it and large stacks outperform it (skill confounds this) [paper](https://arxiv.org/html/2506.00180v2).
- Gilbert: under ICM a fair 2-player bet always lowers both participants' EV and raises every bystander's
  [paper](https://ar5iv.arxiv.org/html/0911.3100).
- **FGS** (future game simulation) values each outcome by simulating the next hand(s) under Nash with rotated positions.
  In ICMIZER's short-stack example UTG's push range goes 6% → 45% and the SB's 39% → 12%. It matters most at "6 or less
  players" and below 10 bb, and "doesn't affect HU preflop decisions at all"
  [tool](https://www.icmizer.com/en/blog/icm-to-fgs-future-game-simulations/). HRC's developer claims FGS is worth
  "roughly +0.3% ROI against ICM over large samples", self-reported with no CI
  [secondary](https://www.pokerstrategy.com/news/content/65746/).
- **In this game the terminal utility at the 200-hand cap is ICM itself** (the rules split the remaining points by ICM),
  so the model's known biases matter only before the cap, mostly through blinds about to be posted.

**Charts and regimes.**
- **HRC heads-up chip-EV chart** (ranges computed from its threshold grid by this pass's researcher) [tool](https://www.holdemresources.net/hune):

  | Effective stack | SB push | BB call |
  |---|---|---|
  | 5 bb | 72.2% | 62.3% |
  | 10 bb | 58.4% | 37.3% (61.4/41.2 with 10% antes) |
  | 15 bb | 45.7% | 28.8% |
  | 20 bb | 40.3% | 21.7% |

  - HRC: push-or-fold is "typically only recommended up to around 10bb"; ">20bb is almost certainly a bad idea".
  - Raw equilibrium data from 1 to 200 bb in 0.05 bb steps is an 86 KB zip
    [tool](https://www.holdemresources.net/hrdata/holdemresources_hu_equilibrium.zip).
- **HRC 9-max chip-EV first-in shoves at 7.5 bb with 10% antes, without and with card bunching**
  [tool](https://www.holdemresources.net/blog/card-bunching-effects/):

  | Seat | No bunching | With bunching |
  |---|---|---|
  | UTG | 18.3% | 17.3% |
  | HJ | 32.6% | 29.9% |
  | CO | 37.9% | 32.8% |
  | BU | 47.2% | 41.3% |
  | SB | 77.3% | 69.3% |
  | BB call vs SB | 62.3% | 52.5% |

  Folded to the SB, all four aces remain 72% of the time; about 24% of the unbunched SB push combos become unprofitable,
  the worst (75o) losing up to 0.5 bb. In 6-max the effects are "just smaller".
- **GTO Wizard 8-max MTT solves with antes** [tool](https://blog.gtowizard.com/short-stacked-play-in-mtts/):
  - 4 bb UTG shoves 30.3% (chip EV) vs 28.2% (ICM), "exclusively shove or fold".
  - 10 bb UTG: chip EV shoves 11.4% and min-raises 4.2%; ICM shoves 8% and min-raises 7.1%.
  - 13 bb BTN: ICM moves weight from shoves to min-raises (shoves 25% → 20.6%).
  - Push/fold at 10 bb "appears largely correct" under chip EV.
- **Harrington zones by M = stack / (SB + BB + antes):** red 1-6 is all-in or fold, orange 6-10 "be first-in"
  [secondary](https://en.wikipedia.org/wiki/M-ratio). If the blinds double every 25 hands, the 2,000 starting stack is
  6.25 bb at level 5 (hands 101-125); the real schedule comes in the kit.

**ICM vs chip EV: bubble factors and the cost of errors.**
- Bubble factor = EV lost if you lose ÷ EV gained if you win; required equity = BF/(BF+1)
  [tool](https://blog.gtowizard.com/what-is-the-bubble-factor-in-poker-tournaments/). PokerStrategy's 9-max 50/30/20
  values: early 1.2, 4-handed bubble 1.9, double-or-nothing bubble 5.1
  [secondary](https://www.pokerstrategy.com/strategy/sit-and-go/bubble-factor-sng-forms/).
- **Bubble factor for a coin flip at equal 2,000 stacks** [computed: `hyperion/core/icm.py`, exact Malmuth-Harville]:

  | Alive | Brief's 10/7/5/4/3/2/1/0 | Linear (Hyperion default 8..1) | 50/30/20 | Winner-take-all |
  |---|---|---|---|---|
  | 8 | **2.04 (67.1%)** | 2.33 (70%) | 1.25 | 1.00 |
  | 6 | 1.79 (64.2%) | 2.14 | 1.39 | 1.00 |
  | 4 | 1.50 (60.0%) | 1.80 | 1.88 | 1.00 |
  | 3 | 1.40 (58.3%) | 1.50 | 1.33 | 1.00 |
  | 2 | 1.00 (50%) | 1.00 | 1.00 | 1.00 |

  The 50/30/20 and linear columns are from this pass's researcher's own Malmuth-Harville code, checked against
  PokerStrategy's 9-man 1.2/1.9. Points that fall with every elimination make the whole table a bubble from hand 1.
- **Required call equity, BB facing a 10 bb SB shove at 2,000 stacks** [computed]: chip EV 45.0%; linear points 65.8%
  with 8 alive, 59.9% with 4, 55.4% with 3.
- **The asymmetry by opponent** [computed]. At 4 alive (6,000/4,000/4,000/2,000, linear points): a 4,000 stack against the
  6,000 has BF 2.24; the 6,000 against a 4,000 has 1.53, and against the 2,000 has 1.17. GTO Wizard agrees: big stacks
  should target medium stacks [tool](https://blog.gtowizard.com/what-is-the-bubble-factor-in-poker-tournaments/). A
  one-dimensional value curve of your own stack cannot represent who you double through or bust.
- **Errors are cheap on shoves and expensive on calls.**
  - ICMIZER's 90-man SNG bubble: a bad AJs call costs -$2.09 and a bad AKo call -$1.82, but a bad 32o chip-leader shove
    only -$0.18; a covered player's bad call is "devastating"
    [tool](https://blog.gtowizard.com/high-cost-of-not-being-aggressive-enough/).
  - GTO Wizard: 8 bb HJ on a bubble, "In ChipEV world we shove 30% of the time, in ICM world we shove 12%"; risk premiums
    of 18.9% (8 bb HJ bubble) and 1.6% (13 bb UTG1 at a final table)
    [tool](https://blog.gtowizard.com/playing-under-10bb-part-2-icm/).
  - "The bigger error was using a cEV preflop range in an ICM spot even though postflop play was optimal"
    [tool](https://blog.gtowizard.com/what-happens-when-playing-chip-ev-and-icm-is-significant/).
  - No controlled study of the ROI gain of ICM Nash over chip-EV Nash in SNGs was found; the only number is an unreviewed
    video's +3.3% ROI in a 200-player MTT simulation [secondary](https://sozai.app/transcript/playing-tournaments-wrong-reasons/).

**Exploitative push/fold and the flat EV near equilibrium** [computed by this pass's researcher: fictitious play on
Hyperion's `tables/hu_matrix.json`, heads-up 10 bb chip EV; Nash came out at SB 58.6% / BB 37.2%, against HRC's
58.4/37.3]:
- **The pusher's EV is flat.** Pushing the top 40/50/75/100% instead of Nash loses only 0.022/0.013/0.034/0.088 bb per
  hand.
- **Calls are less forgiving.** Calling the top 25/55/70% against a Nash pusher loses 0.071/0.087/0.271 bb per shove; at
  15 bb, calling 55% loses 0.39 bb.
- **Best response against fixed callers:**

  | Caller calls | Best push width | Gain over Nash (bb/hand) |
  |---|---|---|
  | Top 15% | 100% | +0.29 |
  | Top 25% | 100% | +0.11 |
  | Top 37% (≈Nash) | 54% | +0.001 |
  | Top 55% | 43% | +0.06 |
  | Top 75% | 49% | +0.10 |

  **Exploiting tight callers pays about 3x more than exploiting loose ones.**
- **Ordering matters about as much as width.** A top-58% range ordered by heads-up equity loses 0.015 bb against Nash's
  own set, which includes suited trash over offsuit gappers.
- **Sklansky-Chubukov** is a lower bound that pushes 40.6% at 10 bb against Nash's 58.6%; S-C numbers assume the caller
  sees your cards [secondary](https://www.pokerlistings.com/a-fail-safe-profitable-strategy-for-some-parts-of-poker-tournaments).
- **Practitioners:**
  - "one of the biggest general population leaks is too tight calling ranges"; players near final tables are "grossly
    overfolding to shoves" [secondary](https://www.tournamentpokeredge.com/forum/mtt-poker-strategy/adjusting-nash-ranges-as-exploits/).
  - Under ICM, "lean towards lower-variance exploits in spots with lots of ICM pressure"
    [tool](https://blog.gtowizard.com/the-limitations-of-nash-equilibrium-in-icm-spots/).
  - With 3+ players a third player can shift EV between the other two within a family of equilibria; restricting yourself
    to jam/fold limits what colluders can do (Ganzfried, conjecture)
    [tool](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/).

**ICM cost in CPython** [computed on this WSL box, which was under load 13 on 8 cores from the running climb, so these are
upper bounds]:

| Call | Time |
|---|---|
| Hyperion's exact Malmuth-Harville (`icm_equity`, subset recursion, all seats), 8 alive, 8 paid places | 445-495 µs |
| Same, top-3 payouts | 116 µs |
| Same, winner-take-all | 9.5 µs |
| Same, 6 / 4 / 3 alive | 103 / 33 / 4 µs |
| `icm_cached` hit (stacks rounded to the big blind) | 1.2 µs |
| Hero-only subset DP with a cached transition plan (this pass's researcher), 8 / 7 / 6 / 5 / 4 alive | ~44 / ~20 / 10-18 / ~5 / ~2.5 µs |
| Naive 8! permutation sum | ~35,600 µs |

A push or call needs hero's equity for fold and for win or lose against each possible caller, at most 1 + 2 × 7 = 15
evaluations. That is about 0.3-0.7 ms at 8 alive with the hero-only DP, and far less below 6 alive. Precompute it per
hand, cache it by rounded stacks, evaluate only the likeliest callers, and keep a bubble-factor table as the fallback.

**Transfer summary for section 8.**
- **Heads-up:** chip-EV tables are essentially optimal (ICM is linear in chips there).
- **3-5 alive:** solve ICM jam/fold (and min-raise/fold in the 10-20 bb band) offline with PI-FP over coarse stack
  classes, with the cap's ICM as terminal value. Store open-jams as per-hand 169-bit masks and calls as cutoffs on one
  ranking (post-jam ranges follow K-S order).
- **6-8 alive:** chip-EV multiway Nash with card bunching, plus an exact ICM check on every call.
- **A cheap FGS-style correction:** subtract the blinds a stack must post before its next button before evaluating ICM.
  This is this pass's heuristic, motivated by Ganzfried's worst-case error; it is not from the literature.

---

## 9. What a constant-time policy (tables plus rules) captures of a solver

**Small strategies can be strong.**
- **Tiny CFR-BR strategies.** 2- and 3-bucket perfect-recall limit abstractions (96,056 and 476,934 infosets, small
  enough "to fit on a single 1.44 MB floppy disk") are 218.5 and 175.8 mbb/g exploitable: "less exploitable than most of
  the 2010 [ACPC] strategies". But "they lose to the CFR strategies that share their abstraction" head-to-head
  [paper](https://poker.cs.ualberta.ca/publications/AAAI12-cfrbr.pdf).
- **Deep CFR.** A 98,948-parameter network reaches the exploitability of a 3.6M-cluster abstraction on flop hold'em
  [paper](https://arxiv.org/pdf/1811.00164).
- **A 2-bucket 3-player agent.** PR2 (only "above or below average" per round) won a 7-agent 3-player limit bankroll test
  at 530 mb/h [paper](https://poker.cs.ualberta.ca/publications/AAMAS10.pdf).
- **Head-to-head vs exploitability.** In heads-up limit, 2010 ACPC bots ranged from 135 to 464 mb/g exploitable, yet the
  top five were within 9 mb/g of each other head-to-head against Rockhopper. One-on-one results "do[] not indicate how far
  away from optimal a strategy is" [paper](https://www.ijcai.org/Proceedings/11/Papers/054.pdf).
- **Abstraction quality is about features, not size:**
  - At equal size the feature choice spans about 20% of exploitability
    [paper](http://poker.cs.ualberta.ca/publications/AAAI12-cfrbr.pdf).
  - "Every imperfect recall agent … outperformed every perfect recall agent" head-to-head
    [paper](http://poker.cs.ualberta.ca/publications/AAMAS13-abstraction.pdf).
  - Public-board features helped in limit (flop.turn.14 beat pr.14 by about 7 mb/h)
    [paper](http://poker.cs.ualberta.ca/publications/sara09.pdf).
- **Finer abstractions can be worse:**
  - Refining both players' card abstractions in Leduc raised exploitability from 272 to 360
    [paper](https://poker.cs.ualberta.ca/publications/AAMAS09-abstraction.pdf).
  - CFR overfits its abstraction: full-game exploitability falls, then drifts up (277 → 305 for a 10-bucket strategy)
    [paper](http://poker.cs.ualberta.ca/publications/AAAI12-cfrbr.pdf).

**Mixing versus pure strategies.**
- **Purification often wins head-to-head.**
  - In Leduc against an exact equilibrium, the best mixed abstract strategy loses 43.8 mb/h and the best purified 1.86;
    19 of 24 improved.
  - In random 4 × 4 games purification helped in 17.4%, hurt in 11.5% and tied otherwise.
  - The rationale: low-probability actions are "likely due to abstraction coarseness, overfitting, or failure of the
    equilibrium-finding algorithm to fully converge"
    [paper](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf).
- **The worst case is the price.** Hyperborean limit exploitability by threshold: none 235, then 244, 259 and 278, and
  purified 437. GS6 was best at an intermediate threshold, 318 at 0.15 against 464 unthresholded
  [paper](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf).
- **The professionals' compromise:**
  - BT8 purified everything except the preflop [paper](http://www.cs.cmu.edu/~sandholm/BabyTartanian8.ijcai16demo.pdf).
  - Libratus range-thresholded at 4%
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
  - Pluribus stored one sampled pure action per abstract infoset for its continuation strategies
    [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
  - "Changing mixtures between indifferent actions cannot lose value against a fixed strategy"
    [tool](https://blog.gtowizard.com/the-three-laws-of-indifference/).
  - GTO Wizard solves only to 0.2-0.3% of the pot from Nash, and flags actions under 3.5% frequency as noise
    [tool](https://blog.gtowizard.com/understanding-nash-distance/).
- **Current vs average strategy.** In 3-player and 6-player games current-strategy snapshots are as good as averages or
  better and are cheaper to store [paper](https://poker.cs.ualberta.ca/publications/gibson.phd.pdf);
  [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
  Jackson found the current strategy "generally outperforms the average strategy" head-to-head
  [paper](https://cdn.aaai.org/ocs/ws/ws0231/12647-57457-1-PB.pdf).

**Constant-time stand-ins for search:**
- **River indifference rules.**
  - The clairvoyance-game solution calls a bet of x pot with probability 1/(1+x)
    [paper](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf).
  - Minimum defence is pot/(pot+bet). A balanced polarised bettor bluffs bet/(pot+2·bet) of its betting range: 25% at
    half pot, 33% at pot, 40% at 2x [secondary](https://www.pokerskill.com/poker-glossary/minimum-defense-frequency/).
  - Ganzfried & Yusuf's 80-20 and All-In rules (section 3) [paper](https://arxiv.org/abs/1612.06340).
- **Presolved small games looked up by k-nearest neighbour** on range-CDF features
  [paper](https://arxiv.org/abs/1612.06340).
- **Simple-bot benchmark.** OpenHoldem's rule bot beat Slumbot by +57 mbb/h over 100,000 hands
  [paper](https://arxiv.org/pdf/2012.06168), already in `algorithms_sota.md`. It is the one published heads-up case of a
  hand-built bot beating a strong blueprint.

**Simple bots are very exploitable, and that bounds what an exploiter can win:**
- **Heads-up limit best-response values (mb/g):** always-fold 750, always-call 1,163, always-raise 3,698, 50/50
  call/raise 2,407 [paper](https://www.ijcai.org/Proceedings/11/Papers/054.pdf).
- **No-limit 200 bb.** The best response to always-call is to wait for the river and shove when ahead, about 50 bb per
  hand. LBR wins 34-49 bb/h against always-call and 80.7 against a random legal action. Against always-call LBR "always
  uses only the largest" bet, and betting all-in "as soon as the probability of winning is higher than 0.5" is worse than
  waiting [paper](https://arxiv.org/pdf/1612.07547).
- **Equilibria leave money on the table.** An equilibrium collects only 48-63% of what a simple modeller collects
  against chumps (this pass's arithmetic). DBBR's limit numbers, equilibrium GS5 → DBBR, sb/h: AlwaysCall 0.582 → 0.930,
  AlwaysRaise 0.791 → 1.391, Random 0.854 → 1.769 [paper](https://www.cs.cmu.edu/~sandholm/opponentModeling.aamas11.pdf).
- **Vexbot.** The adaptive bot reached about 90% and 81% of the maximum against always-call and always-raise, against
  about 41% and 37% for the equilibrium-style Sparbot [paper](http://poker.cs.ualberta.ca/publications/billings.phd.pdf).

Transfer:
- Against non-adaptive, resetting opponents, tables plus rules keep most of a solver's head-to-head value.
- Spend the bytes on (a) a strong preflop by depth and seat, kept mixed; (b) good current-street hand-strength and
  board-texture features; (c) one bet size per node; (d) purified postflop indices.
- Mix only at genuine indifference points, the river bluff/value boundary and preflop.
- The biggest single lever against weak bots is a value-only line against stations; against strong bots it is not giving
  away tells or translation errors.

---

## 10. Exploits of fixed strategies, and how competition bots defended

**How fixed strategies get beaten:**
- **Patient probing by a human.**
  - "thecount" (Gautam Rao) was -200 sb after 3,700 hands against PsOpti, then +600 sb over the next 1,100 by becoming
    less aggressive. He used "his knowledge that the computer player did not do any opponent modeling … to systematically
    probe for weaknesses".
  - His prediction: "Once you add opponent modeling to it, it will kill everyone"
    [paper](https://poker.cs.ualberta.ca/publications/IJCAI03.pdf).
  - The Libratus pros probed sizes as a team every day
    [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
- **Waiting, then betting big.** LBR checks or calls early and bets big late. Betting large from preflop on wins almost an
  order of magnitude less (Hyperborean 2013: 619 vs 5,062 mbb/g) [paper](https://arxiv.org/pdf/1612.07547).
- **Off-tree sizes and boundary bets** (section 7).
- **Hyper-aggression on the river** (Slumbot's earlier version; 2017's ASHE and PokerBot5 beat it by 0.76-1.17 bb/hand)
  [author](https://slumbot.com/);
  [secondary](http://www.computerpokercompetition.org/downloads/competitions/2017/xtable/output/xtable.json).
- **Frequentist best responses are brittle.** They need "5 million hands of training data … reasonable responses … with
  as few as 1 million". A best response to bot A60 beat it by over 2,000 mb/h yet "every FBR strategy besides the one
  trained on it, loses to it" [paper](http://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf).

**Defences and safe exploitation:**
- **Restricted Nash response (RNR)** trades exploitation against exploitability along a "highly concave" curve.
  - Against PsOpti4 (figure-read): about 89% of the maximum exploitation at about 7% of the maximum exploitability.
  - Tuned to about 100 mb/h exploitability, RNR-A80 won 293 against A80 (FBR 1,048, equilibrium 41).
  - Across the field RNRs scored +43 to +78, the equilibrium +56 and FBRs -148 to +3
    [paper](http://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf).
- **Data-biased response.** RNR with "less than 100 thousand observed games" is "both more exploitable and less
  exploitive". DBR (confidence ramping from 0 to 1 over 10 observations per infoset) works from 100 observations up
  [paper](http://poker.cs.ualberta.ca/publications/AISTATS09.pdf).
- **DBBR (Ganzfried & Sandholm, AAMAS 2011).** 1,000 equilibrium hands first, then the model rebuilt every 50 hands with
  a prior worth 5 fictitious hands. Against AlwaysRaise and GUS2, "the win rate decreases significantly for the first
  several hundred hands" after exploitation starts. The authors suggest exploiting "only … if a win rate above some
  threshold is attained" [paper](https://www.cs.cmu.edu/~sandholm/opponentModeling.aamas11.pdf).
- **Safe exploitation** (deviate only by what the opponent has "gifted" in expectation), Kuhn poker, 1,000-hand matches,
  $/hand [paper](https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf):

  | Opponents | Safe exploitation (RWYWE) | Full best response | Equilibrium |
  |---|---|---|---|
  | Random | 0.3636 | 0.4700 | 0.1450 |
  | Opponents who switch to best-responding after 100 hands | -0.0204 | -0.1209 | — |

- **Implicit modelling** (section 5) is the competition-proven form: precomputed robust responses chosen online. It won
  or would have won ACPC bankroll events.
- **Sample sizes in short matches:**
  - Bayes' Bluff, 200-hand trials: in Leduc the posterior concentrates "within less than 20 hands"; in Texas "two hundred
    hands does not provide enough information". Frequentist models can lock into folding and "never make the observations
    required to correct" [paper](https://poker.cs.ualberta.ca/publications/UAI05.pdf).
  - Kuhn: exploiting "is typically better than … Nash" after as few as 50 hands
    [paper](http://poker.cs.ualberta.ca/publications/AAAI05.pdf).
  - Vexbot needed "several thousand games" against Sparbot but showed "a marked increase in its win rate after the first
    200-400 games" against humans [paper](http://poker.cs.ualberta.ca/publications/billings.phd.pdf).
  - Poki (ring games): no modelling was about break-even; the enhanced model made +0.22 sb/h
    [paper](https://poker.cs.ualberta.ca/publications/ICAI00.pdf).
- **The table-reset structure is itself a defence.** Every opponent sees each bot for at most 200 hands and
  then forgets, so no adaptive opponent can run the 1,000-5,000-hand learning that FBR, DBBR or thecount needed. What a
  strong bot *can* do inside 200 hands is react to coarse, high-frequency signals (fold to steals, fold to c-bets,
  over-folding to shoves, bet-size→strength) [inference from the sample-size results above].

Transfer:
- Keep 3-5 precomputed arms per role, for example baseline; against a station (value-only, no bluffs); against an
  over-folder (steal and shove wider); against a maniac (call down wider, never bluff). These echo Pluribus' fold-, call-
  and raise-biased continuation strategies.
- Switch per seat on prior-shrunk counters with about 5-10 pseudo-observations.
- Gate any deviation by an evidence threshold and a "gift" budget, i.e. never stake more than the opponent has given you.
- Under ICM prefer low-variance exploits (wider shoves against over-folders) to high-variance ones (bluff-catching
  maniacs).

---

## 11. Evaluation methodology: duplicate deals, AIVAT, and how many SNGs it takes

**Duplicate deals:**
- **ACPC.** Heads-up duplicate: play k hands, reset memories, swap seats, replay the same cards; "some form of this
  mechanism has been used since the first competition in 2006". 3-player: all 6 seatings of the same cards
  [secondary](http://web.archive.org/web/20150312174917/http://www.computerpokercompetition.org:80/index.php/competitions/rules/76-duplicate-poker).
- **Heads-up limit: a big gain.** The raw standard deviation is about 6 sb/g; duplicate brings it to 1.6 (about 14x less
  variance) and duplicate plus DIVAT to 1.18 (about 26x). Bot-vs-bot matches used 5M duplicate hands for a ±2 mb/g CI
  [paper, Johanson MSc thesis citing Billings & Kan](http://johanson.ca/publications/theses/2007-johanson-msc-thesis/2007-johanson-msc-thesis.pdf).
  Duplicate still leaks luck when the two seats' decisions diverge, for example one player folds preflop where the other
  calls and flops a set.
- **No-limit: a small gain, and multiplayer can be worse** (Davidson, Archibald & Bowling, AAMAS 2013)
  [paper](https://www.ifaamas.org/Proceedings/aamas2013/docs/p1005.pdf):
  - In the 2011 heads-up no-limit ACPC, duplicate cut standard errors by only 2-33%.
  - In 3-player limit it "actually increased the size of the sample standard error in over half of the summaries", while
    their Baseline method cut it 22-50% for all nine agents.
  - "The number of samples needed for one data point is factorial in the number of agents."
- **Brains vs AI.** Claudico and Libratus used mirrored duplicate pairs (one pro in isolation got the AI's cards from the
  other room) [secondary](https://www.cmu.edu/piper/news/archives/2017/january/poker-pros-vs-AI.html). Pluribus used no
  duplicate with humans, only AIVAT, and in the 1-human formats replayed each hand with a Pluribus "Control" in the
  human's seat
  [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).

**Variance-reduction estimators:**
- **DIVAT (AAAI 2006):** an unbiased advantage sum against a hand-designed bet-for-value policy. 5.7-7.2x fewer hands;
  ruling out break-even took about 800 hands with money and about 100 with DIVAT. Needs all hole cards
  [paper](https://cdn.aaai.org/AAAI/2006/AAAI06-092.pdf).
- **MIVAT (IJCAI 2009):** a learned value function at chance nodes only. Heads-up no-limit standard deviation
  42.3 → 32.4, and in 6-player limit "only a modest 20% variance reduction"
  [paper](https://www.ijcai.org/proceedings/2009/0326.pdf).
- **AIVAT (AAAI 2018):**
  - What it adds: control variates at chance nodes **and** at the decisions of every player whose strategy is known, from
    any fixed value function, unbiased whatever that function is.
  - Heads-up no-limit with one known strategy: standard deviation 25.96 → 8.10 chips, "ten times less data". Leduc with
    both strategies known: "a little less than 99.9%" [paper](https://arxiv.org/pdf/1612.06915).
  - DeepStack: "an impressive 85% reduction in standard deviation", 486 ± 40 against 492 ± 220 raw
    [paper](https://arxiv.org/pdf/1701.01724).
  - Pluribus: "by about a factor of 9" in variance
    [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
    A 2026 re-analysis of the public hands: raw -70 ± 88 against AIVAT 48 ± 25 (about 12x fewer hands), while the
    chance-only correction gave about 1.07x, i.e. almost nothing in 6-max [paper](https://arxiv.org/pdf/2605.14261).
- **Cautions (2026 papers, read by this pass's researcher):**
  - Tuning the value function on the evaluation data can "p-hack" a result, so it "should be fixed prior to observing the
    evaluation data" [paper](https://arxiv.org/pdf/2605.14261).
  - Optional stopping with ordinary CIs "invalidates the stated level"; use confidence sequences
    [paper](https://arxiv.org/pdf/2608.06362).
  - GTO Wizard's benchmark reports a threefold standard-deviation reduction and gives pros' win rates as "around 5 bb/100"
    [paper](https://arxiv.org/pdf/2603.23660).

**Hands needed in cash-game units** (n = (1.96·SD/50)² for a ±50 mbb/g CI; standard deviations derived by this pass's
researcher from the published CIs):

| Setting | SD per hand | Hands for ±50 mbb/g |
|---|---|---|
| Heads-up no-limit, raw, 100 bb | ≈13 bb | ≈259k |
| Heads-up no-limit, raw, 200 bb (DeepStack) | ≈23.8 bb | ≈868k |
| Heads-up no-limit, AIVAT | ≈4 bb | 25-29k |
| 6-max, raw (Pluribus) | ≈8.8 bb | ≈119k |
| 6-max, AIVAT (Pluribus) | ≈2.5 bb | ≈9.6k, matching Pluribus' 10,000-hand design (SE 25) |

Published anchors for these derivations: [DeepStack](https://arxiv.org/pdf/1701.01724);
[AIVAT](https://arxiv.org/pdf/1612.06915); [Pluribus](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
"Professional poker players consider 50 mbb/g a sizable margin" [paper](https://arxiv.org/pdf/1701.01724).

**SNG units: points per table** (worked by this pass's researcher; n = (z·CV/e)², CV = σ/μ of points per SNG, uniform
finishing places for a break-even bot):
- **Spread of points per SNG.** Linear 7..0 points: μ 3.5, σ 2.29, CV 0.655. Top-3 50/30/20 of an 8-unit pool: σ 1.43,
  CV 1.43. Brief's 10/7/5/4/3/2/1/0: μ 4.0, σ ≈ 3.08, CV ≈ 0.77 [computed]. ICM splits at the cap lower σ.
- **SNGs needed at 95% (z = 1.96, CI half-width equal to the edge):**

  | Edge in mean points | Linear 7..0 | 50/30/20 |
  |---|---|---|
  | 1% | ≈16,500 | ≈78,400 |
  | 3% | ≈1,830 | ≈8,700 |
  | 5% | ≈660 | ≈3,140 |

  For 80% power multiply by 2.04; for an unpaired A/B test, double again per arm. The brief's table sits near the linear
  column (about 1.4x it).
- **The competition itself.** 10,000 SNGs give a 95% CI of about ±1.3% (linear) to ±2.8% (top-heavy) on a bot's mean, so
  edges over the field below about 1-3% will not reliably separate ranks in one scored tournament.
- **Rotation (8 cyclic seatings of one deal against the same 7 bots).** Var(block mean) = (σ²/8)(1 + 7ρ̄), where ρ̄ is the
  mean pairwise correlation of the bot's points across rotations. The researcher's bracketing from the no-limit and
  3-player data is f = 1 + 7ρ̄ ≈ 0.5-0.9, i.e. 1.1-2x fewer SNGs; this is unverified and should be measured.
  [analysis](https://www.ifaamas.org/Proceedings/aamas2013/docs/p1005.pdf)
- **Hyperion's own number.** The documented "realistic 5.94 ± 0.04 at 1,000 duplicate seeds" (PLAYBOOK §6) implies a
  standard deviation of about 0.65 points per 8-rotation block. Running one field with and without `--rotate` would
  measure f directly.
- **Paired common random numbers** (the Baseline idea: both versions on identical seeds, seats and opponent RNG streams,
  each bot's RNG seeded by (seed, seat, hand, decision)) give Var(diff) = 2σ²(1-ρ_AB); ρ_AB = 0.8 means 5x fewer SNGs
  than unpaired [analysis](https://www.ifaamas.org/Proceedings/aamas2013/docs/p1005.pdf).
- **AIVAT is unusually available locally**, because in the simulator every bot's strategy is known, which is AIVAT's best
  case.
  - Cheapest unbiased terms first: (1) an all-in runout term, E over remaining boards of V(after) - V(realised), with V
    the ICM points of the post-hand stacks; (2) a term at each of our own mixed decisions,
    Σ_a π(a)·V(after a) - V(after the observed a).
  - Freeze V before the run. Chance-only terms buy little multiway; the action terms are where the gain is.
- **Judging against a field:**
  - Head-to-head results do not measure strength: Act1 and Slumbot were within 20 mbb/g head-to-head, but Act1 was 1,300
    mbb/g less exploitable [paper](https://arxiv.org/pdf/1701.01724).
  - ACPC split total bankroll (rewards exploitation) from instant run-off (rewards not being exploited)
    [secondary](http://web.archive.org/web/2015/http://www.computerpokercompetition.org:80/index.php/competitions/rules/82-winner-determination-bankroll-instant-run-off).
  - Pluribus' "5 copies + 1 challenger" format; α-Rank and Nash averaging rank a pool without being biased "by the
    incorporation of easy tasks or weak agents" [paper](https://arxiv.org/abs/1903.01373);
    [paper](https://arxiv.org/abs/1806.02643).
  - Report the mean over a realistic field, the worst case across fields, and a meta-game rank including old versions.
    Do not promote a change on one archetype field.

---

## 12. What does not transfer to a 1 ms, offline-precompute, 8-max ICM bot, and why

- **Real-time subgame solving of any kind.** Libratus ran 1,000-1,900 CFR+ iterations for 13 s per hand on 50 nodes;
  DeepStack 1,000-2,000 iterations per action, 3 s on a GPU; Modicum and Pluribus about 20 s per hand. One CFR+ iteration
  over even a small river subgame costs more than 1 ms in CPython. The ceiling is a lookahead of one action evaluated from
  tables (sections 2-4).
- **Value and policy networks.** DeepStack's 7 × 500 (about 3.5M multiply-adds), ReBeL's 6 × 1,536 (about 18M) and
  AlphaHoldem (2.9 ms on a GPU) are out. Only something like Modicum's 2 × 64 leaf net (about 6.5k multiply-adds) is in
  range, and that is unmeasured (section 3).
- **Two-player zero-sum guarantees.** Safe subgame solving, exploitability bounds, CFR convergence and LBR as an
  evaluation tool all assume two players and zero sum. The ICM objective at 8-max is constant-sum across the table but
  not two-player zero-sum, and Pluribus' authors call their own approach empirical
  [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
- **Full Bayesian range tracking.** Pluribus tracked 1,326 combinations per player. For 7 opponents that is about 9k
  updates per observed action, borderline in Python (estimate), and as noregrets found, range tracking that assumes
  opponents play *your* blueprint concentrates on the wrong hands against bots that do not (`algorithms_sota.md`, Q7).
- **Long-horizon opponent modelling.** FBR needed millions of hands, DBBR 1,000 equilibrium hands first and then "several
  hundred" hands of losses, Bard's portfolio 3,000-hand matches, thecount about 4,000 hands. At most 200 hands per
  anonymous opponent leaves only coarse counters and portfolio selection (section 10).
- **Online self-improvement.** Libratus' self-improver ran on 196 nodes overnight between sessions. The same idea works
  as an offline loop over arena logs between events, not inside a table.
- **Blueprint scale.** Pluribus' 664M action sequences and Libratus' 10^12 decision points have no route into a few MB.
  The tables must be per-spot (preflop by depth and seat, push/fold by stack class, a few postflop contexts), not a
  full-game blueprint. The slumbot2019 README's warning that multiplayer trees "explode" applies with 8 players and
  varying stacks.
- **100 bb cash conclusions applied to short stacks.** Pluribus' limp and donk findings, GTO Wizard's sizing benchmarks
  and every ACPC number are deep-stack cash. Below about 15 bb the game is push/fold plus ICM, and only the Miltersen &
  Sørensen and Ganzfried & Sandholm results apply.
- **Duplicate's limit-poker power.** The 14x variance cut was heads-up limit with chips reset every hand. No-limit
  tournaments with carried-over stacks diverge quickly, so expect tens of percent, and measure it.
- **AIVAT in the real event.** It needs known strategies; in the competition no opponent's strategy is known, so it is
  a local evaluation tool only.

---

## 13. Testable for a bot

Ranked by expected gain against **strong** bots: tuned, ICM-aware, aggressive opponents of the "exploiter 2" or rival
2 kind, not weak or broken seats. Each item gives the evidence, the expected size, and what Hyperion already has (from
the module docstrings read on 2026-11-03). "Expected gain" is this pass's judgement from the cited evidence, not a
measurement.

1. **Exact two-stack ICM on every all-in call and shove** (hero-only subset DP, about 44 µs per evaluation at 8 alive,
   memoised per hand), replacing a one-dimensional value curve of hero's own stack.
   - *Evidence:*
     - Under ICM, calling frequencies shrink 2-9x while open-jams move ≤2 points
       [paper](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf).
     - Bad calls cost about 10x bad shoves [tool](https://blog.gtowizard.com/high-cost-of-not-being-aggressive-enough/).
     - Bubble factor depends on *whom* you play: 2.24 against the cover stack vs 1.17 against the short stack [computed].
     - Coin-flip BF is 2.04 at 8 alive under the brief's points [computed].
   - *Expected gain:* the largest available. Strong bots shove a lot at 10-25 bb. The HANDOFF records an earlier Hero folding 93%
     to rival 2's 13-25 bb shoves while the calls it made won 63%, which points to miscalibrated calling. The fix works in
     both directions.
   - *Hyperion:* the `pushfold.py` ICM gate uses a per-hand curve V(my stack) and the Nash caller frequency.
   - *Test:* swap in exact two-stack ICM, run paired on `top`, `top2`, `night_hard`, then compare bust rates and
     points.
2. **ICM-equilibrium jam/fold tables for 3-5 alive, solved offline with PI-FP**, with card bunching and an FGS-style
   blind correction. Store open-jams as 169-bit masks per (alive, seat, stack class) and calls as cutoffs on one ranking;
   add a min-raise/fold branch at 10-20 bb.
   - *Evidence:*
     - Ganzfried & Sandholm's 946-state solve reached ε < $0.05 [paper](https://www.ijcai.org/Proceedings/09/Papers/034.pdf).
     - Card bunching moves the BU 47.2% → 41.3% and the SB 77.3% → 69.3% at 9-max
       [tool](https://www.holdemresources.net/blog/card-bunching-effects/).
     - FGS can swap ranges at ≤6 alive and <10 bb [tool](https://www.icmizer.com/en/blog/icm-to-fgs-future-game-simulations/);
       its developer claims +0.3% ROI [secondary](https://www.pokerstrategy.com/news/content/65746/).
     - ICM preflop errors cost more than postflop ones
       [tool](https://blog.gtowizard.com/what-happens-when-playing-chip-ev-and-icm-is-significant/).
   - *Expected gain:* large in the phase every table reaches.
   - *Hyperion:* `multiway.py` is chip-EV with card removal "pairwise only" (shover against each responder), so the
     bunching effect of seats that folded before the shove is absent; S13 has a 3-handed ICM table (`short_3.json`) and
     is off by default.
3. **Shove wider against seats that over-fold to shoves**, gated by a per-seat calls/shoves-faced counter with a Nash
   prior. Never widen calls without evidence.
   - *Evidence:* heads-up 10 bb best response gains +0.29 bb/hand against a top-15% caller and +0.11 against top-25%,
     about 3x the gain against loose callers; pusher EV is flat near Nash [computed]. Populations over-fold to shoves
     near the money [secondary](https://www.tournamentpokeredge.com/forum/mtt-poker-strategy/adjusting-nash-ranges-as-exploits/).
     It is the low-variance exploit GTO Wizard recommends under ICM
     [tool](https://blog.gtowizard.com/the-limitations-of-nash-equilibrium-in-icm-spots/).
   - *Expected gain:* medium-high against strong ICM-aware bots, which *should* call tightly and so over-fold relative to
     chip EV.
   - *Hyperion:* the exploit layer steals on fold reads; extend it to shove width by caller class (precompute
     best-response push masks for 3-5 caller widths per depth).
4. **Off-tree robustness: randomized pseudo-harmonic translation, the true pot downstream, and a denser opponent-side
   grid** (min-bet, 0.25, 0.33, 0.5, 0.75, 1, 1.5, 2, all-in), with dedicated responses to min-bets and to overbets and
   shoves.
   - *Evidence:*
     - Rand-psHar exploitability 0.00 against Rand-Geo 1.00 and Det-Arith 12.37 (clairvoyance game)
       [paper](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf).
     - Claudico's biggest leak was pot misperception [paper](https://arxiv.org/pdf/1510.08578).
     - Off-tree LBR wins 1,849-2,403 mbb/g [paper](https://arxiv.org/pdf/1612.07547).
     - Pluribus used Rand-psHar preflop [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
   - *Expected gain:* medium. It is mostly insurance against strong bots that probe with odd sizes or lead and stab
     often.
   - *Hyperion:* S13 maps "a raise between the tree's size and all-in … by a log-scale split drawn once per hand", which
     is geometric and so never maps down. Test the psHar split there and in every table lookup keyed on bet size.
5. **Bet-size hygiene: one size per (street, position, pot type) for the whole range, ±0-8% jitter, range thresholding
   (drop an action only if every hand plays it under about 4%), card-independent compute time.**
   - *Evidence:*
     - A single river size keeps 99.7% of EV [tool](https://blog.gtowizard.com/dynamic-sizing-benchmarks/).
     - Student of Games beat Slumbot with one random size per hand [paper](https://arxiv.org/pdf/2112.03178).
     - Libratus' jitter and range thresholding, and Claudico's thresholding-made limp tell
       [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
     - The size-by-strength "+-" strategy beat translating bots [paper](https://www.ijcai.org/Proceedings/09/Papers/055.pdf).
   - *Expected gain:* medium against strong bots that read sizes (Hyperion's own batch 5 has "the bet-size read", so
     others may too); near zero against weak ones.
   - *Hyperion:* S13 heads-up postflop already uses one size per street "so a size names nothing". Audit F's multiway
     and preflop paths for strength-dependent sizes.
6. **Fold-biased meta-purification of any postflop solver table** (fold if P(fold) > 0.2, else purify among fold, call
   and one bet meta-action, then among sizes), keeping preflop and river bluff/value boundaries mixed.
   - *Evidence:* Tartanian7 averaged +71 against +20 raw and +37 purified [paper](http://www.cs.cmu.edu/~sandholm/hierarchical.aamas15.pdf);
     Libratus -8 → +18 from post-processing [paper](https://noambrown.github.io/papers/17-Science-Superhuman.pdf);
     TBR beat IRO by 80 ± 23 [paper](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/3E_4.pdf). Against
     that, purifying raised Hyperborean's exploitability from 235 to 437.
   - *Expected gain:* small-medium; it applies only where Hyperion has solver tables (S13 heads-up and 3-handed, future
     postflop tables). Saves bytes too (⌈log₂|A|⌉ bits per entry).
7. **A portfolio of 3-5 precomputed response tables per role, chosen per seat by prior-shrunk counters, with a safe
   exploitation budget.** Arms: baseline; against a station (no bluffs, thin value); against an over-folder; against a
   maniac (call down, never bluff); best responses to fold-, call- and raise-biased (×5) versions of the baseline, as in
   Pluribus' continuation strategies.
   - *Evidence:* implicit modelling would have won the 2011 total bankroll (317 vs 224) and won 2013 uncapped
     [paper](https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf);
     [paper](https://poker.cs.ualberta.ca/publications/bard.phd.pdf). RNR's concave tradeoff gives about 89% of the
     exploitation for about 7% of the exploitability [paper](http://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf).
     Safe exploitation holds up against opponents who adapt (-0.02 vs -0.12)
     [paper](https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf).
   - *Caveats:* a uniform prior made the 3-player Kuhn modeller second to last [paper](https://arxiv.org/html/2212.06027v4),
     and 200 hands is too few to model Texas hold'em fully [paper](https://poker.cs.ualberta.ca/publications/UAI05.pdf).
   - *Expected gain:* medium against mixed fields, small against strong bots (they are near equilibrium, so arms add
     little); its main value is not losing while switching.
   - *Hyperion:* the composite already routes sections by table reads; this formalises it with offline-solved arms and
     a gift budget.
8. **Read each opponent's size→strength map** from showdowns and all-ins (counter per seat, size bucket and street), and
   fold or raise accordingly.
   - *Evidence:* boundaries of a hard-translating agent can be learned "within 100 hands"
     [paper](https://www.ijcai.org/Proceedings/09/Papers/055.pdf); Galfond's example
     [author](https://www.philgalfond.com/articles/exploiting-gto-bet-sizing/). No paper measures bot size tells in
     mbb/g (gap).
   - *Expected gain:* medium against hand-built strong bots that size by strength; nil against solver bots.
   - *Hyperion:* batch 5 has a bet-size read; check its sample threshold against the 100-hand figure.
9. **Probe translating opponents with psHar-median sizes** (0.2, 0.714 and 1.4 pot) and small card-blind boundary bets.
   - *Evidence:* Hyperborean 2009 won with a strategy that "did not even look at its own cards" to exploit betting
     boundaries [paper](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf); naïvePA beat hard translation
     by about 13.5 bb/hand but lost to soft [paper](https://www.ijcai.org/Proceedings/09/Papers/055.pdf).
   - *Expected gain:* high against abstraction bots with hard translation, near zero against equity/pot-odds rule bots,
     which treat sizes continuously. Most of the field is the latter, so overall small-medium.
   - *Test:* a probe-size dial against a hard-translating archetype added to the bestiary.
10. **An unabstracted preflop table by stack depth and seat, solved offline with MCCFR at ICM terminal values**,
    kept mixed (BT8's preflop was 170 KB), with open-raise-or-fold except a mixed SB complete (Pluribus' limp finding)
    and mixed preflop sizes.
    - *Evidence:* Pluribus and Libratus play preflop from the blueprint
      [paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf); "the bigger error was using a cEV preflop
      range in an ICM spot" [tool](https://blog.gtowizard.com/what-happens-when-playing-chip-ev-and-icm-is-significant/).
    - *Cost:* an 8-player tree with varying stacks explodes. Use a reentrant tree and current-strategy snapshots
      [author](https://raw.githubusercontent.com/ericgjackson/slumbot2019/master/README.md).
    - *Expected gain:* medium, uncertain; high build cost.
    - *Hyperion:* rival 3's preflop charts, plus S13's heads-up (5-100 bb) and 3-handed CFR+ tables.
11. **Closed-form and presolved river play beyond heads-up**: minimum defence pot/(pot+bet), bluff share bet/(pot+2·bet)
    of the betting range, the 80-20 check rule and the All-In rule, and k-NN lookup into presolved river games keyed by
    (our range CDF, opponent range CDF, bet/pot).
    - *Evidence:* [paper](https://arxiv.org/abs/1612.06340); [paper](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf).
    - *Expected gain:* small-medium, mainly against strong bots that bluff the river at sensible frequencies.
    - *Hyperion:* S13 uses minimum defence heads-up; multiway rivers are Hero's rules.
12. **An offline self-improver loop between events.** From arena logs, score each gap [A, B] in our size grid by
    Σ min{x-A, B-x} over the sizes x opponents used, add the psHar midpoints of the top 2-3 gaps, and re-solve the
    affected tables.
    - *Evidence:* Libratus' Type 2 self-improver ended up deciding about half of all hands; copying exact sizes (Type 1)
      did little because opponents changed sizes
      [paper, supplement](https://www.aeaweb.org/conference/2018/preliminary/paper/h9Bs5dth).
    - *Expected gain:* small-medium; it raises coverage exactly where real opponents bet. A process, not a runtime
      change.
13. **A biased-continuation check on close decisions.** Where two lines are within a small EV margin, prefer the one
    whose table EV holds up against all four of {baseline, fold×5, call×5, raise×5} opponent responses.
    - *Evidence:* Pluribus' k = 4 leaves; letting only the opponent choose made Modicum "defensive/conservative"
      [paper, supplement](http://web.archive.org/web/20200630233143/https://science.sciencemag.org/content/sci/suppl/2019/07/10/science.aay2400.DC1/aay2400-Brown-SM.pdf).
      There is no ablation of k and no constant-time precedent.
    - *Expected gain:* small, speculative; test only after items 1-7.

**Not a bot change, but it decides how many of the above can be validated in time:** run every candidate paired (common
seeds, seats and RNG streams) over 8-rotation duplicate blocks, add the all-in runout term and our own mixed-decision
AIVAT terms with V = ICM points frozen in advance, and report realistic-field mean, worst field and a meta-game rank
(section 11). A 3% edge needs about 1,800 SNGs at 95% under linear-like points before these cuts.
