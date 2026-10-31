# Poker-bot algorithms: state of the art, ranked by practicality for a one-hour build on modest compute

Scope note: research conducted 2026-10-31. Primary sources are the papers (arXiv/AAAI/NeurIPS text), the Pluribus authors' public statements, and GitHub READMEs. Several hobbyist repos are cited because they are the only sources that report *small-compute blueprint vs Slumbot* numbers; treat those as single-run, high-variance evidence (they say so themselves). Units: 1 bb/100 = 10 mbb/hand (mbb/g, mbb/h); always-fold loses 750 mbb/g ([DeepStack](https://arxiv.org/abs/1701.01724)).

Headline ranking (details and citations under each question below):

1. **Equity + rule bot (Monte Carlo equity, pot-odds, position, a few bet sizes).** Zero training, microsecond-to-millisecond decisions, trivially debuggable. Ceiling is low vs equilibrium bots (-1,100 to -1,200 mbb/g vs Slumbot for naive equity bots in one hobby project), but a carefully built one can beat an abstraction blueprint: OpenHoldem's expert rule bot scored **+57 mbb/h vs Slumbot** over 100k hands. The safest thing to ship if the integration hour goes badly.
2. **Precomputed tabular blueprint: external-sampling MCCFR with Linear-CFR discounting (Pluribus-style), small k-means equity-histogram card abstraction, 3–5 pot-fraction bet sizes, pseudo-harmonic action translation at runtime.** Trains in 1–2 h on 16 cores to a 4–16 GB table; decision time is a hash lookup. Measured strength of a ~30-core-hour blueprint: about **-700 mbb/hand vs Slumbot** (10k hands, +/-330). A 700-core-hour blueprint (Modicum's) ties Slumbot (-11 +/- 8). Beats calling stations and naive equity bots comfortably; strength scales with iterations and bucket count up to memory.
3. **Blueprint + river-only (or river+turn) CFR+ re-solving with a 1–3 s budget.** The river subgame can be solved with no card abstraction; Modicum's turn/river CFR+ ran 150–2,000 iterations in 5–10 s on a 4-core CPU and lifted a losing blueprint to +11 vs Slumbot. Hobby reimplementations found flop/turn re-solving *hurt* unless done carefully (over-folding, range-tracking assumes opponent plays your blueprint); river-only is the sweet spot.
4. **Depth-limited search on flop/turn (Modicum/Pluribus style, 4 biased continuation strategies).** Feasible on a laptop in principle (Modicum: 4 cores, 16 GB, 700 core-hour blueprint) but two independent reimplementations report it was a net loss against Slumbot at ≤800 ms budgets without extensive tuning. Only worth it with days of advance prep and a self-play harness to validate.
5. **Deep CFR / DeepStack-style value nets / ReBeL.** Impractical in this window: DeepStack's turn net used >175 core-years plus GPUs; ReBeL trained on up to 90 DGX-1 machines; Deep CFR's own paper does not state wall-clock but trains a 100k-parameter net from scratch for 4,000 SGD steps per CFR iteration. OpenHoldem's PPO-style RL agent took 3 days on 8 GPUs + 64 cores to reach +111 vs Slumbot. Flag as cluster-scale.

---

## Q1. Core approaches and their trade-offs (vanilla CFR, CFR+, DCFR, Linear CFR, MCCFR, Deep CFR, DeepStack re-solving, Libratus/Pluribus blueprint + search, ReBeL, rule bots)

### Takeaway
Every superhuman HUNL/6-max bot since 2017 is "approximate equilibrium via some CFR variant + real-time search"; the cheapest configuration that has beaten Slumbot on commodity hardware is Modicum (MCCFR blueprint, 700 core-hours, 16 GB, 4-core CPU at play time). Neural methods (Deep CFR, DeepStack, ReBeL, deep RL) all required cluster-scale data generation and are not reproducible in hours. For a one-hour build, the realistic choices are a tabular Linear-MCCFR blueprint, a CFR+ river re-solver, and/or an equity-based rule bot.

### Cited Findings

**Vanilla CFR / CFR+ / DCFR / Linear CFR (tabular, full traversal)**
- CFR (Zinkevich et al., NeurIPS 2007) showed that minimizing counterfactual regret minimizes overall regret, so self-play converges to Nash in two-player zero-sum; applied to limit hold'em abstractions with up to 10^12 states — [NeurIPS 2007](https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html)
- Discounted CFR (Brown & Sandholm, 2018/AAAI 2019): DCFR(α,β,γ) multiplies accumulated positive regrets by t^α/(t^α+1), negative regrets by t^β/(t^β+1), and average-strategy contributions by (t/(t+1))^γ; the recommended setting α=3/2, β=0, γ=2 "led to performance that was consistently stronger than CFR+" — [arXiv 1809.04040](https://arxiv.org/abs/1809.04040)
- DCFR(3/2,0,2) matched or beat CFR+ in every tested game (four Libratus HUNL subgames plus Goofspiel), usually by a factor of 2–3; tied CFR+ only on Goofspiel — [arXiv 1809.04040](https://arxiv.org/abs/1809.04040)
- Linear CFR (LCFR) = DCFR(1,1,1): weight iteration t's regret and average-strategy updates by t (equivalently multiply accumulated regret by t/(t+1) each iteration). Theoretical bound only 2/√3 worse than CFR. Toy example: LCFR finds the best action after 970 iterations vs 471,407 for CFR+. But LCFR "appears to do worse in practice than CFR+" asymptotically, and LCFR+ (regret floor at 0) was worse than both — [arXiv 1809.04040](https://arxiv.org/abs/1809.04040)
- Pruning compatibility: with β≤0 regrets of bad actions do not run to -∞, which hampers pruning; β>0 (e.g., DCFR(3/2,1/2,2)) supports temporary pruning, performed similarly on HUNL but noticeably worse on Goofspiel. CFR+ is not compatible with regret-based pruning — [arXiv 1809.04040](https://arxiv.org/abs/1809.04040)
- Slumbot's author: "CFR+ is the preferred algorithm when it is feasible, ideally with no card abstraction"; MCCFR gives "pretty good approximations of equilibrium for large games"; multiplayer support in his code is MCCFR only — [slumbot2019 README](https://github.com/ericgjackson/slumbot2019)
- Modicum's river/turn solver: enhanced CFR+ that ignores the first 50% of iterations when computing the average strategy and discounts regrets for the first 30 iterations; turn 150–1,000 iterations, river 300–2,000 — [arXiv 1805.08195 (PDF, Appendix)](https://arxiv.org/pdf/1805.08195)

**Monte Carlo CFR (external / outcome sampling)**
- Linear-discounted external-sampling MCCFR: scaling accumulated regrets and strategy sums by n/(n+1) after every 10^7 nodes touched beat vanilla MCCFR in HUNL subgames, "most noticeably in Subgame 3"; CFR+'s changes "did not help MCCFR" — [arXiv 1809.04040](https://arxiv.org/abs/1809.04040)
- Pluribus blueprint: Monte Carlo CFR (sampling actions rather than traversing the full tree), 8 days on a 64-core server, 12,400 CPU core-hours, <512 GB RAM, no GPUs, ≈$144 at cloud spot rates — [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/); [Brown AMA (mirror)](https://reddit.rtrace.io/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/eu7b5e3/?context=3); [LessWrong read-through](https://www.lesswrong.com/posts/6qtq6KDvj86DXqfp6/let-s-read-superhuman-ai-for-multiplayer-poker)
- Modicum blueprint: MCCFR for 700 core-hours over a state-of-the-art abstraction; stored as 4-byte floats in 5 GB — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- A 2025 laptop study (MacBook Pro M4 Pro, 24 GB) on synthetic heads-up NLHE states found MCCFR converged closest to a high-iteration reference after 500 iterations (KL 0.015) vs plain CFR (KL 0.196); concludes MCCFR is the most efficient method for approaching equilibrium in two-player settings. Preprint, synthetic states, not full play — [arXiv 2509.23747](https://arxiv.org/abs/2509.23747)
- Hobby reimplementation (noregrets): parallel external-sampling Linear MCCFR with Pluribus-style negative-regret pruning; 400M iterations in 1 h 56 m at 57.2k it/s; 200M iterations in ~79 min on 16 cores (6-max) — [noregrets README](https://github.com/All4Eli/noregrets)
- Hobby reimplementation (MaxSmd/poker-ai, Rust): 3×10^9 MCCFR iterations (3.15×10^12 nodes) in 13.9 h on 32 cores; lock-free atomic updates are faster but non-deterministic; deterministic parallel training is merge-bound at ~7 effective cores — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)

**Deep CFR**
- Network: 7 layers, 98,948 parameters (hidden dim 256); 10,000 traversals per CFR iteration; each iteration retrains the value net from scratch for 4,000 minibatch SGD steps (batch 10,000, Adam lr 1e-3); reservoir buffers up to 40M infosets each. Hardware and wall-clock are not reported; the paper states it spends most wall-clock in SGD — [arXiv 1811.00164](https://arxiv.org/abs/1811.00164)
- Results: on flop hold'em (>10^12 nodes, >10^9 infosets) Deep CFR reached ~37 mbb/g exploitability vs NFSP's ~47; on HULH, head-to-head vs tabular abstractions: +6 ± 2 vs 3.3M buckets, -6 ± 2 vs 33M buckets, -11 ± 2 vs 330M buckets; +43 ± 2 vs NFSP — [arXiv 1811.00164](https://arxiv.org/abs/1811.00164)
- Deep CFR's own Slumbot number: none published (the paper reports exploitability and head-to-head vs abstractions/NFSP, not Slumbot) — [arXiv 1811.00164](https://arxiv.org/abs/1811.00164)

**DeepStack-style continual re-solving**
- DeepStack: feedforward net, 7 hidden layers × 500 units; ranges input over 1,000 hand buckets; turn net trained on 10M random turn situations solved with 1,000 CFR+ iterations (F/C/pot/all-in, no card abstraction) using 6,144 cores and >175 core-years; flop net on 1M situations using 20 GPUs for half a GPU-year — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724)
- Play time: sparse lookahead (fold, call, 2–3 bets, all-in), re-solved trees of ~10^7 decision points solved "in under five seconds using a single NVIDIA GeForce GTX 1080" — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724)
- Results: won 492 mbb/g (486 mbb/g AIVAT-adjusted) vs 33 professionals; LBR could not exploit it under any tested action set (LBR lost ≥350 mbb/g) — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724)
- Reimplementations: a DeepStack reimplementation lost 63 ± 40 mbb/g to Slumbot; Supremus (improved deep CFV nets) won 176 ± 44 over 150k hands — [arXiv 2007.10442](https://arxiv.org/abs/2007.10442). OpenHoldem's DeepStack-like agent spent "several weeks using 120 GPUs" generating training samples and scored +103 mbb/h vs Slumbot (100k hands, AIVAT); with 500 re-solve iterations it *lost* 224 mbb/h, with 1,000 it won 93 — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)

**Libratus / Pluribus / Modicum (blueprint + search)**
- Libratus: >15M core-hours on Bridges to build plus ~4M during the match; beat four pros by 14.7 bb/100 (~147 mbb/g) over ~120,000 hands — [Wikipedia: Libratus](https://en.wikipedia.org/wiki/Libratus) (secondary); Libratus beat Baby Tartanian8 by 63 ± 28 and humans by 147 ± 77 mbb/g — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Baby Tartanian8 (ACPC 2016 winner): ~2M core-hours and 18 TB RAM; Slumbot (ACPC 2018 winner): ~250,000 core-hours and 2 TB RAM; neither uses real-time computation — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Modicum: 700 core-hours, 16 GB RAM, 4-core CPU, ~20 s per full hand. Head-to-head (AIVAT, 95% CI): blueprint alone -57 ± 13 vs Baby Tartanian8 and -11 ± 8 vs Slumbot; naive depth-limited solving -10 ± 8 / -1 ± 15; full depth-limited solving **+6 ± 5 / +11 ± 9**. Built with "less than 0.1% of the computing resources and memory" of Libratus — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Pluribus play-time: two Intel Haswell E5-2695 v3 CPUs, <128 GB RAM; search 1–33 s per decision; ~20 s per hand in 6-player self-play. Results: +48 mbb/g (SE 25, p=0.028) in 5 humans + 1 AI over 10,000 hands; +32 mbb/g (SE 15) in 1 human + 5 AIs — [LessWrong read-through](https://www.lesswrong.com/posts/6qtq6KDvj86DXqfp6/let-s-read-superhuman-ai-for-multiplayer-poker); [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/)

**ReBeL**
- No card abstraction (each infostate gets its own policy); hand-chosen pot-fraction bet sizes, ≤9 actions per decision, perturbed ±0.1 pot in training; data generation on "up to 128 machines with 8 GPUs each", full-game run on 90 DGX-1 (8×V100 32 GB) machines, 1,750 epochs of 2.56M examples; plays <2 s per hand average, never >5 s per decision — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544)
- Results: +45 ± 5 vs Slumbot, +9 ± 4 vs Baby Tartanian8, +165 ± 69 vs Dong Kim, +881 ± 94 vs LBR; Modicum row in the same table: +11 ± 5 vs Slumbot, +6 ± 3 vs BT8 — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544)

**Deep RL end-to-end**
- OpenHoldem's PPO-based agent: 3 days on one server with 8 GPUs + 64 cores; 3.8 ms per decision on a single 2.0 GHz core; +111 mbb/h vs Slumbot (100k hands, AIVAT) — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)
- GTO Wizard AI (ex-Ruse): deep RL self-play over "hundreds of millions of hands" plus search at play time; beat Slumbot by 19.4 bb/100 over 150,000 hands under ACPC rules (≤7 s average acting time, 200 bb reset) — [GTO Wizard blog](https://blog.gtowizard.com/crushing-a-top-hunl-poker-bot/) (vendor source)

**Rule / equity bots**
- OpenHoldem's expert rule bot (≈10^6 scenarios, tens of thousands of lines, written by skilled players) scored **+57 mbb/h vs Slumbot**; their CFR-based static bot scored -20 (authors note Slumbot's abstraction is far finer). The paper attributes the rule-bot win to the known LBR-exploitability of ACPC abstraction bots — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)
- Hobby project (≈10,000 hands each vs Slumbot): always all-in -295.9 BB/100 (≈-2,959 mbb/g); always check/call -123.3 BB/100; naive equity betting -112.0 BB/100; a "more advanced" equity bot -204.3 BB/100 (worse than the naive one) — [Gongsta/Poker-AI](https://github.com/Gongsta/Poker-AI)

### Inferences
- Compute-to-strength curve vs Slumbot for pure blueprints: ~30 core-hours/12 buckets ≈ -700 mbb/g (noregrets); unknown-but-modest compute/coarse abstraction ≈ -20 (OpenHoldem); 700 core-hours ≈ -11 (Modicum); 250k core-hours = Slumbot itself. Search on top of a 700-core-hour blueprint gains ~20 mbb/g vs Slumbot and ~60 vs BT8; a DeepStack/RL agent gains ~100+. Expect a one-day-prep laptop blueprint to land somewhere between -700 and -20 mbb/g against Slumbot, i.e., far above calling stations (-1,233) and naive equity bots (-1,120) but below Slumbot.
- Because OpenHoldem's hand-written rule bot beat Slumbot and their CFR bot did not, a well-engineered equity/rule bot is not a strictly inferior option in a weak field; it is the lowest-risk integration and a strong fallback.
- DCFR(3/2,0,2) is the right default for any full-traversal solving (river re-solve); Linear discounting (periodic n/(n+1) scaling) is the right default for MCCFR blueprints. Do not use CFR+ with MCCFR.

### Gaps
- No published mbb numbers for Deep CFR vs Slumbot or for any Deep CFR run on a laptop.
- The Pluribus Science paper and supplement were not reachable (403 at science.org; the CMU mirror redirects); blueprint internals (bet-size counts, bucket counts, pruning threshold, Linear CFR duration) come from secondary summaries only and are flagged as such below.
- Libratus numbers are from Wikipedia and the Modicum paper's recap, not the Science 2018 text.

---

## Q2. Card and action abstraction techniques and their cost

### Takeaway
Standard practice is: lossless suit isomorphism; preflop 169 canonical hands; postflop k-means on equity histograms (EMD distance for flop/turn to capture potential, plain equity or 1-D clustering on the river), optionally OCHS features; and 3–7 pot-fraction bet sizes with a raise cap. A full-coverage bucket build is ~30 min on 64 cores (≈32 core-hours) in one Rust implementation; with capped board sampling it runs on an 8 GB laptop. LBR analysis shows card abstraction, not bet abstraction, is the dominant source of exploitability in ACPC bots.

### Cited Findings
- Canonical situation counts (suit-isomorphic) per street: flop 1.29M, turn 13.96M, river 123.16M; flop/turn clustered with k-means, river with an exact 1-D DP; equity features offered: scalar, histogram, or OCHS; "full-coverage bucket build: about 30 min on a 64-core box"; laptop (8 GB) runs use capped boards and memory guards — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)
- Suit-isomorphism indexing library (C) by Kevin Waugh maps hands to tight indices (AsKs, KdAd, KhAh share one preflop index); based on "A Fast and Optimal Hand Isomorphism Algorithm" (2013) — [kdub0/hand-isomorphism](https://github.com/kdub0/hand-isomorphism)
- Potential-aware imperfect-recall abstraction with EMD (Ganzfried & Sandholm, AAAI 2014): k-means under earth mover's distance over histograms of next-round bucket outcomes; "improves performance over the previously best approach" in NLHE; a 2025 paper notes this "PAAEMD" method was integrated into DeepStack, Libratus and Pluribus — [AAAI 2014 abstract](https://ojs.aaai.org/index.php/AAAI/article/view/8816); [arXiv 2511.12089](https://arxiv.org/abs/2511.12089)
- Method detail in the same lineage: final street clustered by squared L2 on equity; earlier streets by k-means with EMD between histograms — [arXiv 2510.15094](https://arxiv.org/abs/2510.15094)
- Implementation speedups: Elkan's triangle-inequality k-means and Sinkhorn entropic OT for EMD — [rbp-clustering (Rust crate)](https://docs.rs/rbp-clustering). The parent robopoker project warns "any practical attempt to run this library will require ~1TB of RAM" for its full river-equity pipeline (amortized one-time cost) — [robopoker docs](https://docs.rs/crate/robopoker/0.1.0)
- Bucket counts in practice: noregrets default 12 postflop buckets per street (claims Pluribus used ~200; secondary, unverified here), later 24 buckets + OCHS features for 6-max; "more buckets means fewer visits per infoset. Scaling buckets did not beat baselines once seed noise was counted"; 36 buckets at equal iterations was worse — [noregrets README](https://github.com/All4Eli/noregrets)
- DeepStack encodes ranges over 1,000 buckets "as in traditional abstraction methods" — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724). Deep CFR's tabular comparison points: 3.3M / 33M / 330M buckets; Polaris (2007) used ~3×10^8 — [arXiv 1811.00164](https://arxiv.org/abs/1811.00164)
- Bet abstraction examples: Pluribus coarse postflop menu as reproduced by noregrets: 50%/100%/all-in first-in, pot/all-in raise; chosen because it was ~1.3× faster and 2.5× smaller than a 6–7 size menu — [noregrets README](https://github.com/All4Eli/noregrets). DeepStack lookahead: fold, call, 2–3 bets, all-in — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724). ReBeL: ≤9 actions per decision; its turn-endgame variant used 0.5×/1×/all-in first raise and 0.75×/all-in afterwards — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544). OpenHoldem action set: Fold, Call/Check, Bet Half Pot, Bet Pot, All-In — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)
- Blueprint sizes: noregrets 200M-iteration 6-max run = 128.5M infosets, 4.3 GB; 400M = 521.7M infosets, 16 GB — [noregrets README](https://github.com/All4Eli/noregrets). MaxSmd heads-up 200 bb cap-3 ≈ 299M infosets ≈ 11 GB at 12 B per (infoset, action); 6-max 20 bb cap-2 ≈ 6.8B infosets ≈ 161 GB — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai). Modicum's abstraction: 5 GB as 4-byte floats — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Where exploitability comes from: "considerably more exploitability can be attributed to card abstraction as opposed to betting abstraction"; ACPC bots "are generally well converged within their abstract games" — [LBR, arXiv 1612.07547 (PDF)](https://arxiv.org/pdf/1612.07547)
- Hand-evaluator throughput (for equity computation budgets): ~79M 5-card and ~50M 7-card evaluations/s on one core (Go, author's machine) — [paulhankin/poker](https://github.com/paulhankin/poker); OMPEval (C++) perfect-hash evaluator with ~200 kB table, Monte Carlo/enumeration "2 to 10 times faster per thread than the free version of Equilab" — [zekyll/OMPEval](https://www.github.com/zekyll/OMPEval)
- rlcard reports the no-limit hold'em game at ~10^162 infosets with action size ~10^4 before abstraction — [rlcard README](https://github.com/datamllab/rlcard)

### Inferences
- A pragmatic precompute budget: 169 preflop classes (free); flop/turn k-means on 50-bin equity histograms over a sampled subset of canonical boards (minutes to an hour on a laptop); river bucket by raw equity percentiles (no EMD needed). With ~50M 7-card evals/s per core, exhaustive river equity for one hand/board (990 opponent combos) costs ~20 µs, so Monte Carlo equity at decision time (10k samples) is sub-millisecond — ample for a rule bot or a feature for translation.
- Keep buckets small (12–50 per street) and iterations high; the noregrets negative results say extra buckets without proportionally more iterations do not help.
- Bet abstraction of 3 sizes (≈0.5 pot, pot, all-in) plus a raise cap is the industry-standard minimum and keeps the tree ~2.5× smaller than a 6–7 size menu.

### Gaps
- No primary source gives wall-clock for the Ganzfried–Sandholm EMD clustering itself (the AAAI PDF is bot-blocked); the only runtime figure is MaxSmd's "~30 min on 64 cores".
- Johanson's thesis and "Evaluating state-space abstractions" (2013) were not fetched; E[HS^2] vs distribution-aware comparisons are therefore not cited.

---

## Q3. How strong can a laptop-trained HUNL blueprint get (vs Slumbot, random, calling stations)?

### Takeaway
Published and semi-published data points, all vs Slumbot: naive equity/calling bots lose ~1,100–1,250 mbb/g; a ~30-core-hour, 12-bucket Linear-MCCFR blueprint lost ~715 ± 330 mbb/hand (10k hands); OpenHoldem's coarse CFR bot lost 20 mbb/h (100k hands); Modicum's 700-core-hour blueprint lost 11 ± 8; with search Modicum won 11 ± 9. Expect a well-executed overnight blueprint to sit in the -700 to -20 range vs Slumbot while crushing simple opponents.

### Cited Findings
- noregrets (external-sampling Linear MCCFR, pruning, EMD k-means, 12 buckets/street; heads-up 200 bb, 10,000 hands): blueprint only **-714.5 ± 331.5 mbb/hand**; with 800 ms safe re-solve **-1,771 ± 471.8**; "single seeds swing by hundreds of mbb/hand" — [noregrets README](https://github.com/All4Eli/noregrets)
- Training cost for that blueprint: 200M iterations ≈ 79 min on 16 cores; 400M ≈ 1 h 56 m — [noregrets README](https://github.com/All4Eli/noregrets)
- OpenHoldem CFR-based static bot vs Slumbot: **-20 mbb/h** over 100,000 hands (AIVAT); rule bot +57; DeepStack-like +103; RL +111 — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)
- Modicum blueprint (MCCFR, 700 core-hours, 5 GB): -11 ± 8 vs Slumbot, -57 ± 13 vs Baby Tartanian8 — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Simple baselines vs Slumbot (~10k hands): all-in bot -2,959 mbb/g; check/call -1,233; naive equity -1,120 — [Gongsta/Poker-AI](https://github.com/Gongsta/Poker-AI)
- Slumbot's own ACPC 2016 result: -11.88 ± 10.33 mBB/h vs Baby Tartanian8; Act1 -16.82 ± 14.35 — [LBR, arXiv 1612.07547 (PDF)](https://arxiv.org/pdf/1612.07547). Baby Tartanian8 beat Slumbot 36 ± 12 — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Upper reference points vs Slumbot: ReBeL +45 ± 5; Supremus +176 ± 44; GTO Wizard AI +194 (19.4 bb/100, 150k hands) — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544); [arXiv 2007.10442](https://arxiv.org/abs/2007.10442); [GTO Wizard blog](https://blog.gtowizard.com/crushing-a-top-hunl-poker-bot/)
- DecisionHoldem claims >730 mbb/h vs Slumbot over ~20,000 games with a `play_with_slumbot.py` script (unverified claim from the repo/paper) — [AI-Decision/DecisionHoldem](https://github.com/AI-Decision/DecisionHoldem); [arXiv 2201.11580](https://arxiv.org/abs/2201.11580)
- Slumbot API access for benchmarking: Python adapter with POST `new_hand` / `act` endpoints (client_pos 0 = big blind, 1 = small blind) — [aipoker-bot/slumbot-adapter](https://github.com/aipoker-bot/slumbot-adapter); the maintainer's guidance thread proposes 20–30k hands total, one sequential session, ≥500 ms between requests — [slumbot2019 issue #49](https://github.com/ericgjackson/slumbot2019/issues/49). OpenHoldem notes the website's "poor stability" and sent packets directly — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)
- Variance: Pluribus used AIVAT for ~10× fewer hands needed; 10,000 hands gave SE 25 mbb/g — [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/); 50 mbb/g is "a sizable margin" by pro standards — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724)

### Inferences
- The gap between noregrets (-715) and OpenHoldem/Modicum (-20/-11) is roughly 1.5–2 orders of magnitude of core-hours plus finer abstraction; a team with a few days of unattended training on a 16–32 core box should expect to land in the low hundreds of mbb/g loss vs Slumbot, and to beat any opponent that does not play near-equilibrium by hundreds to thousands of mbb/g.
- In a short-build competition, opponents are likely rule bots or thin blueprints; the measured 1,000+ mbb/g gaps between equilibrium-ish play and naive equity play matter far more than the ~100 mbb/g separating good blueprints from Slumbot.
- Without AIVAT, 10k-hand matches have ±300 mbb/hand CIs; evaluating variants against each other requires duplicate hands and pooled seeds (noregrets' lesson).

### Gaps
- I found no blog or paper reporting a *laptop-trained* HUNL blueprint's result vs a random or calling-station bot in mbb; only vs Slumbot. The Fro116 2017 MIT Pokerbots winner's report.pdf was not readable in this session (repo lists it; game was a discard variant).
- Hobby numbers are single 10k-hand runs without AIVAT; treat as order-of-magnitude.

---

## Q4. Multiway (3+ players): what changes, and what Pluribus did that is cheaply replicable

### Takeaway
Theoretical guarantees vanish beyond two-player zero-sum, but Pluribus showed that the same recipe (Linear MCCFR blueprint + depth-limited search with four biased continuation strategies) works empirically in 6-max at ~$150 of compute; its play-time footprint (2 CPUs, <128 GB) is the part a small team can approximate. Tree size explodes with players: a 6-max 20 bb cap-2 abstraction is 6.8B infosets/161 GB in one reimplementation, so a laptop 6-max blueprint needs tiny bucket counts and aggressive raise caps.

### Cited Findings
- Pluribus authors: techniques "do not have known strong theoretical guarantees on performance outside of the two-player zero-sum setting"; goal was empirical, not a solution concept — [LessWrong read-through](https://www.lesswrong.com/posts/6qtq6KDvj86DXqfp6/let-s-read-superhuman-ai-for-multiplayer-poker)
- Pluribus blueprint: MCCFR self-play, 8 days / 64 cores / 12,400 core-hours / <512 GB / ≈$144; blueprint compressed to fit a 128 GB machine; blueprint used directly only in the first betting round, search thereafter — [LessWrong read-through](https://www.lesswrong.com/posts/6qtq6KDvj86DXqfp6/let-s-read-superhuman-ai-for-multiplayer-poker); [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/)
- Pluribus search: depth-limited (a few moves ahead), at the leaf each player picks among four continuation strategies — blueprint, fold-biased, call-biased, raise-biased; 1–33 s per search; 2 CPUs, <128 GB — [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/)
- Information abstraction used "only to reason about situations on future betting rounds, never the betting round it is actually in" (secondary summary of the paper) — [KDnuggets](https://www.kdnuggets.com/2020/12/remembering-pluribus-facebook-master-difficult-poker-game.html)
- Results: +48 mbb/g (SE 25) vs 5 pros over 10,000 hands; +32 mbb/g (SE 15) as 5 copies vs 1 pro; per-player: Elias -4.0 bb/100, Ferguson -2.5, Loeliger -0.5 — [LessWrong read-through](https://www.lesswrong.com/posts/6qtq6KDvj86DXqfp6/let-s-read-superhuman-ai-for-multiplayer-poker); [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/)
- Modicum's bias approach (the 2-player precursor): opponent fold-bias = multiply fold probabilities by 10 and renormalize; similarly call-bias and raise-bias; leaf values estimated by rollouts of the stored strategies; a 2-hidden-layer × 64 DNN alternative (34-float input, 4 outputs, 180M examples/player) ran on a 4-core CPU but cost ~17 mbb/g vs rollouts — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Slumbot's author's code: multiplayer "MCCFR only, no real-game best response, and reentrant betting trees are advised" — [slumbot2019 README](https://github.com/ericgjackson/slumbot2019)
- Hobby 6-max blueprints: noregrets 200M iterations ≈ 79 min on 16 cores → 4.3 GB; search "cut the leak by -186 ± 98 mbb/hand" in multiway pots, so it is on by default there — [noregrets README](https://github.com/All4Eli/noregrets). MaxSmd 6-max 20 bb cap-2 ≈ 6.8B infosets ≈ 161 GB — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)
- OpenSpiel's ACPC-based hold'em supports 2–10 players and is marked thoroughly tested — [OpenSpiel games.md](https://github.com/google-deepmind/open_spiel/blob/master/docs/games.md)
- Alberta's 3-player limit work notes CFR on the full game "would require hundreds of petabytes of RAM" (context for why abstraction is unavoidable multiway) — [Gibson, U. Alberta thesis](https://ualberta.scholaris.ca/items/99bff73e-7467-4592-bd96-b602c920cea2)

### Inferences
- Cheap, replicable Pluribus ingredients: (a) Linear MCCFR with negative-regret pruning for the blueprint; (b) coarse postflop bet menu; (c) information abstraction only for future streets; (d) four biased continuation strategies for depth-limited search; (e) AIVAT-style evaluation. The expensive ingredient is simply running (a) for 12,400 core-hours with 512 GB; a laptop gets ~1% of that.
- For 3+ players on a laptop: cap raises per street at 2, use ≤24 buckets, short stacks if the format allows, and lean on the blueprint plus a river solver rather than multiway flop search.

### Gaps
- Pluribus's exact bet-size count, bucket counts, pruning schedule and Linear-CFR window were not confirmable from primary text (paper and supplement unreachable); only the compute, hardware, search-time and result figures are confirmed via the authors' blog/AMA.

---

## Q5. Decision-time budgets and how real-time search fits a 1–10 s per-action limit

### Takeaway
Table lookups are microseconds; Monte Carlo equity is sub-millisecond to milliseconds; river CFR+ re-solves with no card abstraction fit in 1–3 s on a few cores; turn re-solving fits ~2–10 s only with a depth limit or value estimates (a full-river turn solve took 798 s in one implementation); flop search needs a value function or rollouts and 10–30 s in Modicum. Iteration count is decisive: a DeepStack-like agent with 500 re-solve iterations lost 224 mbb/h to Slumbot and won 93 with 1,000.

### Cited Findings
- Modicum (4-core CPU): each subgame solve "takes between 5 and 10 seconds depending on the size of the subgame"; preflop MCCFR 30 s (rarely run due to caching); flop MCCFR 10–30 s by pot size; turn 150–1,000 CFR+ iterations; river 300–2,000; ~20 s per full hand — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Pluribus: 1–33 s per search, ~20 s per hand, 2 CPUs — [Meta AI blog](https://ai.meta.com/blog/pluribus-first-ai-to-beat-pros-in-6-player-poker/)
- DeepStack: ~10^7-decision-point sparse trees solved in <5 s on one GTX 1080 — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724)
- ReBeL: <2 s per hand average, never >5 s for a decision — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544)
- OpenHoldem RL agent: 3.8 ms per decision on a single 2.0 GHz core; DeepStack-like agent: 500 iterations → -224 mbb/h vs Slumbot, 1,000 iterations → +93 — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)
- Hobby timings at 16 threads: ~1.9 s per river decision, 1.9 s turn, 2.1 s flop (with runout sampling); flop re-solve was 24.6 s before runout sampling; full-river turn re-solve 798 s per decision, kept offline — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)
- Budget sensitivity: noregrets' search without a value net was "roughly zero at 800ms and harmful at 150ms" in self-play; with its value net +331 ± 213 vs raw blueprint in self-play, but -1,000 mbb/hand worse vs Slumbot — [noregrets README](https://github.com/All4Eli/noregrets)
- Depth-limited solving vs translation for an off-tree 0.75-pot bet (NLFH): with one leaf value, randomized pseudo-harmonic translation is better; with 16 leaf values, exploitability approaches having the size in the abstraction; solving to the end of the game instead would be ~10,000× larger — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- GTO Wizard AI's Slumbot match ran under an ACPC-style cap of 7 s average acting time per hand — [GTO Wizard blog](https://blog.gtowizard.com/crushing-a-top-hunl-poker-bot/)
- Hand evaluation: ~50M 7-card evals/s per core (Go) — [paulhankin/poker](https://github.com/paulhankin/poker)

### Inferences
- With a 1 s budget: blueprint lookup + river CFR+ (a few hundred DCFR iterations on an unabstracted river tree with 3 bet sizes) is achievable in Python+NumPy or Rust; with 5–10 s: turn re-solving with a depth limit at the river and blueprint-derived leaf values becomes possible but is where reimplementations report over-folding bugs.
- Cache preflop decisions (Modicum did) and precompute river equity tables per board at hand start to keep worst-case latency bounded.
- Use a wall-clock guard that falls back to the blueprint action if the solver has not reached a minimum iteration count; under-iterated re-solves are measurably worse than no re-solve.

### Gaps
- No source gives CFR+ iterations/second for a river subgame on a specific laptop CPU; Modicum's 5–10 s figure is the closest.

---

## Q6. Open-source implementations and their maturity

### Takeaway
OpenSpiel is the only actively maintained, thoroughly tested library with full ACPC hold'em plus tabular CFR/CFR+/MCCFR/Deep CFR; slumbot2019 is the reference C++ CFR+/MCCFR solver with k-means bucketing from Slumbot's author; rlcard is good for environments but offers no pretrained NLHE policy; PokerRL and DeepStack-Leduc are stale (PyTorch 0.4.1; Lua/Torch); fedden/poker_ai is archived and 20-card-deck only. Two recent hobby repos (noregrets, MaxSmd/poker-ai) implement the full Pluribus/Modicum stack and publish honest negative results.

### Cited Findings
- OpenSpiel algorithms with poker relevance and status: CFR, CFR-BR, external- and outcome-sampling MCCFR, Deep CFR, NFSP, RCFR, exploitability/best response, sequence-form LP — all thoroughly tested; FSICFR, ESCHER, IS-MCTS, RNR, MMD lightly tested — [OpenSpiel algorithms.md](https://github.com/google-deepmind/open_spiel/blob/master/docs/algorithms.md). Games: Poker (Hold 'em) "implemented via ACPC", 2–10 players, thoroughly tested; Leduc and Kuhn thoroughly tested — [OpenSpiel games.md](https://github.com/google-deepmind/open_spiel/blob/master/docs/games.md)
- slumbot2019 (C++17, gcc 7.3): CFR+, external-sampling MCCFR, Targeted CFR; bucketing via null (lossless isomorphic), rollout features, unique or k-means buckets; parameter files for game/abstraction/CFR; `play` and `head_to_head` binaries; examples use 100M MCCFR iterations; reentrant betting abstractions "TODO"; no runtime or strength figures — [slumbot2019 README](https://github.com/ericgjackson/slumbot2019)
- rlcard: environments leduc-holdem, limit-holdem (~10^14 infosets), no-limit-holdem (~10^162 infosets, action space abstracted); algorithms DMC, DQN, NFSP, CFR; pretrained CFR model for Leduc only, rule models for Leduc/limit; no pretrained NLHE model; ~3.6k stars, 875 commits — [rlcard README](https://github.com/datamllab/rlcard)
- PokerRL: vanilla CFR/CFR+/Linear CFR baselines for small games, best-response/LBR/RL-BR/head-to-head evaluators, Ray-distributed; pinned to Python 3.6 and PyTorch 0.4.1; 14 commits, no releases; Deep CFR/SD-CFR live in separate community repos — [PokerRL README](https://github.com/EricSteinberger/PokerRL)
- DeepStack-Leduc: official-style reimplementation of continual re-solving for heads-up no-limit *Leduc* only; Lua + Torch; 2 commits, no releases — [DeepStack-Leduc README](https://github.com/lifrordi/DeepStack-Leduc)
- fedden/poker_ai: MCCFR self-play with lossy/lossless clustering (`poker_ai cluster` → joblib LUT); only a 20-card deck supported without modification; archived read-only 2024-07-16; no strength results — [fedden/poker_ai README](https://github.com/fedden/poker_ai)
- Gongsta/Poker-AI: HUNL CFR with preflop/postflop split, 169 preflop clusters, postflop k-means incomplete, CFR strategy unfinished; useful mainly for its baseline-vs-Slumbot table — [Gongsta/Poker-AI](https://github.com/Gongsta/Poker-AI)
- noregrets: Linear MCCFR + pruning + EMD k-means + depth-limited resolving, Slumbot API harness with per-street loss autopsy; publishes negative results (3× iterations, exact river bucketing, 36 buckets, VR-MCCFR, snapshot averaging, expert-iteration distillation all failed to help) — [noregrets README](https://github.com/All4Eli/noregrets)
- MaxSmd/poker-ai (Rust): DCFR/MCCFR/CFR+ solvers, k-means + exact river DP bucketing, CFV-gadget re-solving, full-coverage canonical boards; docs/summary.md holds Slumbot results (not read) — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)
- Slumbot API client: `aipoker-bot/slumbot-adapter` (pip-installable, POST new_hand/act) — [slumbot-adapter](https://github.com/aipoker-bot/slumbot-adapter)
- MIT Pokerbots 2017 winner's code: Java bot + C++ helper for hand bucketing, CFR-trained, "report.pdf" included; engine must be requested from MIT — [Fro116/Pokerbots](https://github.com/Fro116/Pokerbots)
- Tutorials: AI Poker Tutorial (sections on CFR, game abstractions, agent evaluation, CFR advances, top agents) — [aipokertutorial.com](https://aipokertutorial.com/); int8.io CFR explainer with Go chance-sampling CFR for Kuhn/Rhode Island — [int8.io](https://int8.io/counterfactual-regret-minimization-for-poker-ai/); Thomas Trenner's "Building a Poker AI" series (part 6 Kuhn CFR, part 7 3-player Kuhn/exploitability, part 8 Leduc with general CFR) — [Part 6](https://ai.plainenglish.io/building-a-poker-ai-part-6-beating-kuhn-poker-with-cfr-using-python-1b4172a6ab2d); curated list — [awesome-poker-ai](https://github.com/PokerBotAI/awesome-poker-ai)
- Hand evaluators: OMPEval (C++, ~200 kB table, equity calculator) — [zekyll/OMPEval](https://www.github.com/zekyll/OMPEval); paulhankin/poker (Go, 50M 7-card/s) — [paulhankin/poker](https://github.com/paulhankin/poker); hand-isomorphism (C) — [kdub0/hand-isomorphism](https://github.com/kdub0/hand-isomorphism)

### Inferences
- For advance prep: use slumbot2019 or a Rust/C++ MCCFR of your own for the blueprint (Python is too slow for 10^8+ iterations), OMPEval or equivalent for equity, hand-isomorphism for indexing, OpenSpiel for unit-testing solver correctness on Kuhn/Leduc, and slumbot-adapter for an external benchmark. Nothing off the shelf yields a competitive NLHE policy without training.

### Gaps
- Could not read MaxSmd's docs/summary.md (Slumbot results) or Fro116's report.pdf.
- Did not check the ACPC archive site for downloadable past agents; whether any ACPC bot binaries are publicly runnable is unknown from this session.

---

## Q7. Known pitfalls (abstraction overfitting, off-tree actions, bet-size translation, blueprint exploitability without search)

### Takeaway
Blueprints are hugely exploitable off-tree: LBR found every top ACPC bot (including Slumbot 2016) exploitable by >3,000 mbb/g — four times worse than folding every hand — with card abstraction the main culprit; translation errors add another ~1,000–2,000 mbb/g. Use randomized pseudo-harmonic translation, keep your own bet sizes inside opponents' likely sizes (fcpa), and be aware that naive search can make things worse (over-folding, range tracking that assumes the opponent plays your blueprint).

### Cited Findings
- LBR lower bounds on exploitability (mbb/g; LBR actions by street): Slumbot 2016: 522 ± 50 (F/C all streets), 4,020 ± 115 (F/C/P/A on turn+river), 3,763 ± 104 (56 bets turn+river), 1,227 ± 79 (56 bets on flop); Hyperborean 2014: 721 / 3,852 / 4,675 / 983; Act1 2016: 407 / 2,597 / 3,302 / 847; Always Fold: 250–750; a no-card-abstraction "Full Cards" fcpa bot (2 TB, 14 CPU-years): -424 / -536 within its tree but 2,403 ± 87 with 56 bets; DeepStack: -428 / -383 / -775 / -602 (unexploited) — [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724); original LBR table with "on-tree" rows — [arXiv 1612.07547 (PDF)](https://arxiv.org/pdf/1612.07547)
- "With 97.5% confidence, exploitability of each evaluated bot is over 3180 mBB/h... folding every hand would cost the bots at least 4 times less money"; LBR must wait (check/call early streets) to exploit, otherwise it finds almost an order of magnitude less; a hard-translation bot loses 1,849 mBB/h to just fold/call/min-bet/2×/4×/8× pot/all-in — [arXiv 1612.07547 (PDF)](https://arxiv.org/pdf/1612.07547)
- Head-to-head vs exploitability disagree: Slumbot beat Act1 head-to-head, yet Act1 was 1,300 mbb/g less exploitable by LBR — [arXiv 1612.07547 (PDF)](https://arxiv.org/pdf/1612.07547); [arXiv 1701.01724 (PDF)](https://arxiv.org/pdf/1701.01724)
- Action translation (Ganzfried & Sandholm, IJCAI 2013): pseudo-harmonic mapping f_{A,B}(x) = ((B − x)(1 + A)) / ((B − A)(1 + x)) is the unique mapping consistent with calling a bet of size x with probability 1/(1+x) (the clairvoyance-game solution); its median is x* = (A + B + 2AB)/(A + B + 2); randomized version (Rand-psHar) had exploitability 0 in the clairvoyance game and the lowest average exploitability in no-limit Kuhn and Leduc (fcpa), while arithmetic mappings are more exploitable than geometric, and deterministic more than randomized; the authors note the practical benefit in large games is modest — [IJCAI 2013 PDF](https://www.cs.cmu.edu/~sandholm/reverse%20mapping.ijcai13.pdf)
- RPAT is "the lowest-exploitability known technique for responding to off-tree actions that does not involve real-time computation"; depth-limited re-solving beats it once ≥2 leaf values are used — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Modicum blueprint without search: -57 ± 13 vs BT8, -11 ± 8 vs Slumbot; with search +6/+11; the search agent "is not vulnerable to off-tree opponent actions on the first two betting rounds" — [arXiv 1805.08195 (PDF)](https://arxiv.org/pdf/1805.08195)
- Range-tracking pitfall: "Range tracking assumes opponents play the blueprint. Against a different opponent, the posterior concentrates on the wrong hands and the resolver best-responds to a fiction"; belief widening (+310) and carried-CFV gadget alternatives on villain-led rivers (+660) partially mitigated; no-net flop re-solves "stacked off at about 18% equity (51 flop all-ins in 10k hands, versus 2 for the blueprint)" — [noregrets README](https://github.com/All4Eli/noregrets)
- Over-folding pitfall: leaf-cut re-solves made 66% of small-blind flop decisions facing a bet folds (Slumbot: 33–37%) and folded 81% of turn leads (Slumbot 43%); flop/turn search therefore disabled by default, river only — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)
- Evaluation pitfalls: in-loop sampled best response is "meaningless at any affordable sample count on a tree this size" and once read negative; bucket maps must come from the same training run as the blueprint — [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai); seeds swing hundreds of mbb/hand, so pool seeds and use paired comparisons — [noregrets README](https://github.com/All4Eli/noregrets)
- Pruning details that mattered: exempting the river and terminal actions from pruning "roughly halved the best-response bound at equal iterations"; stochastic rounding on strategy sums prevents long-run averaging from freezing — [noregrets README](https://github.com/All4Eli/noregrets); [MaxSmd/poker-ai README](https://github.com/MaxSmd/poker-ai)
- ReBeL mitigates translation by perturbing training bet sizes ±0.1 pot — [arXiv 2007.13544](https://arxiv.org/abs/2007.13544)
- Rule bots are exploitable by construction; abstraction bots are exploitable by LBR; OpenHoldem's rule bot still beat Slumbot (+57) — [arXiv 2012.06168 (PDF)](https://arxiv.org/pdf/2012.06168)

### Inferences
- In a field of short-build bots, the opponents most likely to hurt a blueprint are ones that bet odd sizes and bet a lot on later streets (exactly LBR's recipe). Including the common sizes (half-pot, pot, all-in, plus min-raise) in the abstraction and using randomized pseudo-harmonic translation covers most of this at zero runtime cost.
- Ship search only on the river and only after validating fold frequencies against the blueprint; a wrong re-solver costs more than it gains (-1,000 mbb/hand in noregrets).
- Simple opponent-adaptive tweaks (e.g., calling wider vs an opponent whose bet frequencies are far from equilibrium) are the one place a rule layer can add value on top of a blueprint, since the blueprint never exploits.

### Gaps
- No source quantifies how much *overfitting the abstraction* (as opposed to coarse card abstraction) costs on a small blueprint in mbb; the LBR numbers are all for 10^5–10^6 core-hour bots.
- I did not find published, current (2025–2026) exploitability measurements of Slumbot's 2019+ version; the LBR numbers are for the 2016 build.
