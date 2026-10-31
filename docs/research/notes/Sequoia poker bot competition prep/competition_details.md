# Sequoia "No Limit" poker bot competition (2026): everything publicly knowable as of 2026-10-31

Status note up front: the event is **"No Limit: A Bot Building Tournament"**, organized by Sequoia Capital Operations, LLC and hosted by OpenAI and Citadel Securities. It was announced on **October 27, 2026**. **No round has been played yet.** The first regional (Bay Area, held in Menlo Park, not San Francisco) is Friday **November 6**; Boston (Cambridge, MA) is Monday **November 9**; Pittsburgh is Thursday **November 12**; the Finals are in San Francisco on Sunday **November 15**. So there are no SF results, winning approaches, post-mortems, or leaked prompts to report. The only "live" competitive data so far is the optional **Castle Challenge** (a Colonel Blotto game on the application form), whose public leaderboard is analyzed below.

Official URLs:
- Landing page / application: https://pokerbot.sequoiacap.com/
- Official rules: https://pokerbot.sequoiacap.com/rules.html
- Castle Challenge leaderboard: https://pokerbot.sequoiacap.com/castle_challenge/ (data file: https://pokerbot.sequoiacap.com/castle_challenge/data/leaderboard.json)
- Privacy notice: https://pokerbot.sequoiacap.com/privacy.html
- Contact: pokerbot@sequoiacap.com
- Announcement posts: [Sequoia on X](https://x.com/sequoia/status/2115111389501218868), [Sequoia apply post](https://x.com/sequoia/status/2115126043556319602), [Castle Challenge leaderboard post](https://x.com/sequoia/status/2115486256041963847), [Shaun Maguire](https://x.com/shaunmmaguire/status/2115131879452295182), [Noam Brown](https://x.com/polynoamial/status/2115125429619343609), [Abhishek Malani "Over $250K in prizes"](https://x.com/abhishekm1636/status/2115113318893670464), [Sonya Huang](https://x.com/sonyatweetybird/status/2115113467078463783)

## Key question 1: What is the exact format and rule set, and what was the SF round's actual prompt/engine if public?

### Takeaway
The format is fully specified in the official rules: a 60-minute build of a **Python** bot against a provided Agent interface, then six scored tournaments (T1–T6, 20 minutes apart) of **10,000 simulated eight-bot sit-and-gos** each, with position-based points, ICM for unfinished tables, and later tournaments weighted more heavily. The **poker variant is secret until the build phase starts**, the Finals use a *different* variant, and nothing from any round is public yet because the first regional is November 6.

### Cited Findings

**Organizer, hosts, people**
- The Competition is "Organized by Sequoia Capital Operations, LLC and Hosted by OpenAI and Citadel Securities"; OpenAI OpCo, LLC and Citadel Securities are "Hosts"; Sequoia is solely responsible for the platform, scoring, winner selection and prize payment. The page is styled as the "Department of Algorithmic Play, 2800 Sand Hill Road, Menlo Park, CA 94025". — [Official rules](https://pokerbot.sequoiacap.com/rules.html)
- Sequoia's announcement: "Announcing No Limit: a bot building tournament hosted by @Sequoia, @citsecurities and @OpenAI. Teams of 1 or 2 get 60 minutes to build a pokerbot from scratch. Agents play thousands of games across six scored rounds. Open to university students and recent grads ('25 or '26)." — [Sequoia on X, Oct 27 2026](https://x.com/sequoia/status/2115111389501218868)
- Shaun Maguire (Sequoia): "Sequoia is running an experiment. We're hosting a poker bot tournament, with rules for the age of AI. There will be prizes, an incredible guest list (ex @polynoamial), and some plot twists. The brainchild of my partner @abhishekm1636." — [Shaun Maguire on X](https://x.com/shaunmmaguire/status/2115131879452295182)
- Sonya Huang (Sequoia): "casino royale, ai edition... delighted for sequoia, openai, citsec to host this poker bot tournament together... kudos @abhishekm1636 for the spark of inspiration / stewardship and thanks @polynoamial and other friends for teaming with us." — [Sonya Huang on X](https://x.com/sonyatweetybird/status/2115113467078463783)
- Abhishek Malani (Sequoia): "Prove you're the best. Over $250K in prizes. $100K grand prize. No experience needed, just creativity and skill." — [Abhishek Malani on X](https://x.com/abhishekm1636/status/2115113318893670464); he also credited "@polynoamial for pioneering what's possible" — [reply](https://x.com/abhishekm1636/status/2115114170903638282)
- Noam Brown (OpenAI; Libratus/Pluribus author): "Every winter, @MIT has run a 1-month class (6.9630) in which students make poker AIs and compete against each other for cash prizes. Coding agents have accelerated that process so much that it's now possible to build a poker bot in an *hour*. Also, I'll be at the finals!" — [Noam Brown on X](https://x.com/polynoamial/status/2115125429619343609)
- Alfred Lin (Sequoia) also promoted it ("Think you have what it takes to be the pokerbot champion? Apply now."). — [Digg roundup](https://digg.com/ai/smdduv3c)

**Schedule (all 2026)**
- "Friday, November 6 - Menlo Park, CA (deadline to register - Tuesday, November 3 at 11:59 PM PT)"; "Monday, November 9 - Cambridge, MA (deadline to register - Friday, November 6 at 11:59 PM ET)"; "Thursday, November 12 - Pittsburgh, PA (deadline to register - Monday, November 9 at 11:59 PM ET)"; "Sunday, November 15 - Finals in San Francisco, CA (Attendance is by invitation only, with invitations extended to the top-performing teams at each regional event.)" — [Official rules §2.4](https://pokerbot.sequoiacap.com/rules.html)
- "Check-in begins at 5:30 PM, and the regional event runs from 6:00-9:00 PM local time." Participants must attend in person for the full event. — [Official rules §2.3](https://pokerbot.sequoiacap.com/rules.html)
- Finals: "Finals in San Francisco, Nov 15, 12:00–8:00 PM, in person"; "Participants must be able to attend the finals in SF in order to win the final prize. Travel is covered." — [Landing page application form](https://pokerbot.sequoiacap.com/)
- Applications opened Tuesday, October 27; decisions sent on a rolling basis, all applicants notified by 11:59 PM local time on: Bay Area Thursday Nov 5; Boston Sunday Nov 8; Pittsburgh Wednesday Nov 11. "Rolling, with limited seats at each regional." — [Landing page FAQ](https://pokerbot.sequoiacap.com/)
- Specific venues (building/room) are not published anywhere on the official site; only city-level locations (Menlo Park, Cambridge, Pittsburgh, San Francisco). — [Official rules](https://pokerbot.sequoiacap.com/rules.html); [Landing page](https://pokerbot.sequoiacap.com/)

**Build phase and submission mechanics**
- "The poker variant will be revealed on the day of each event at the start of the build phase. It will remain confidential until that announcement." — [Official rules §3.2](https://pokerbot.sequoiacap.com/rules.html)
- "Teams have 60 minutes to build a Python bot that implements the provided Agent interface. Teams receive a starter kit containing an agent template, local simulator, Independent Chip Model (ICM) calculator, payout structure, and blind schedule." — [Official rules §3.3](https://pokerbot.sequoiacap.com/rules.html)
- "Each team may submit one bot every five minutes. The team's most recently accepted submission becomes its active bot." — [Official rules §3.5](https://pokerbot.sequoiacap.com/rules.html)
- "Teams may continue editing and submitting bots after the build phase. At the start of each scored tournament, each team's active bot is frozen for that tournament. Any submissions accepted afterward apply to the next scored tournament." — [Official rules §4.2](https://pokerbot.sequoiacap.com/rules.html)
- "Participants may not publicly share the poker variant or other unreleased event details before the event ends." — [Official rules §6.4](https://pokerbot.sequoiacap.com/rules.html)

**Game structure**
- "There are six scored tournaments, labeled T1-T6. The first begins at the end of the 60-minute build phase, with subsequent tournaments starting 20 minutes apart." — [Official rules §4.1](https://pokerbot.sequoiacap.com/rules.html)
- "Each scored tournament consists of 10,000 simulated eight-bot sit-and-gos. In each iteration, bots are randomly assigned to tables." — [Official rules §4.3](https://pokerbot.sequoiacap.com/rules.html)
- "Each table plays until one bot holds all the chips or 200 hands have been played. Each bot starts with 2,000 chips. Blinds start at 10/20 and increase every 25 hands." — [Official rules §4.4](https://pokerbot.sequoiacap.com/rules.html)
- "Points are awarded based on each bot's finishing position at its table. The point distribution may vary by poker variant and will be announced at the start of the build phase. An eliminated bot receives the points assigned to its finishing position. If a table reaches the 200-hand limit, the remaining points are allocated among the surviving bots using the Independent Chip Model (ICM)." — [Official rules §4.5](https://pokerbot.sequoiacap.com/rules.html)
- "If the number of competing bots is not divisible by eight, empty seats are filled with randomly selected copies of submitted bots. These filler bots earn no points." — [Official rules §4.6](https://pokerbot.sequoiacap.com/rules.html)
- "Bot state resets at the start of each table. Opponents are anonymized so bots cannot identify specific teams." — [Official rules §3.8](https://pokerbot.sequoiacap.com/rules.html)
- "Bots compete exclusively against other bots. No humans play in the bot competition." No real money; no wagering on outcomes by anyone. — [Official rules §3.9–3.10](https://pokerbot.sequoiacap.com/rules.html)
- "The Finals follow the same competition format using a different poker variant." — [Official rules §5.2](https://pokerbot.sequoiacap.com/rules.html)
- The landing page's decorative exhibits are labelled "SIMULATED PLAY" and show "10,000 GAMES, 8 BOTS EACH, NO-LIMIT HOLD'EM" with "BLINDS 50/100", a heads-up duel with "STACKS RESET TO 10,000 EVERY HAND", and fictional bots named CFR-7, NASH and MONTE. The exhibits are JavaScript animations with no real data (counters at 0). — [Landing page](https://pokerbot.sequoiacap.com/). These exhibit numbers (50/100 blinds, heads-up) contradict the rules (10/20 blinds, eight-bot tables); the rules are the binding document.
- Landing page tagline: "Teams of 1 or 2 get 60 minutes to build a pokerbot from scratch. Bots play 10,000 games against each other." — [Landing page](https://pokerbot.sequoiacap.com/)

**Prizes**
- "The top 5 teams at each regional receive $5,000 per team and advance to the Finals. We'll also select up to five additional wildcard teams across the regional games based on their scores." Finals: first $100,000, second $50,000, third $25,000. Prizes are per team, split equally between teammates; paid by Sequoia Capital Operations within 30 days of verification; winners handle taxes. — [Official rules §5](https://pokerbot.sequoiacap.com/rules.html)
- Travel to the Finals is covered "for the top teams from each regional." — [Landing page FAQ](https://pokerbot.sequoiacap.com/)

**Eligibility and team size**
- "Participation is open to currently enrolled students at any university in the United States and Canada and students of U.S. and Canadian universities from the class of 2025 or 2026." 18+, or under 18 with parental consent for a regional. Teams of one or two; each participant may compete in only one regional; teammates need not attend the same school. Free to enter. Employees/contractors/judges/gamemasters of Sequoia, OpenAI, Citadel Securities and their households are excluded. — [Official rules §1](https://pokerbot.sequoiacap.com/rules.html)
- Students verify enrollment via school email; recent grads may use any email. — [Landing page FAQ](https://pokerbot.sequoiacap.com/)
- Several secondary writeups say "U.S. universities" only ([Zeniteq](https://www.zeniteq.com/sequoia-and-openai-open-a-100k-pokerbot-tournament-6aycef); [RuntimeWire](https://runtimewire.com/article/sequoia-offers-100-000-to-the-winning-student-pokerbot-team)); the official rules and FAQ both say U.S. **and Canada**, so the secondary coverage is outdated or wrong.
- Application form collects: name, phone, email, university, degree, graduation year (2025–2032 options), DOB, optional GitHub, LinkedIn, resume (PDF/Word under 5 MB), regional choice, confirmation of in-person attendance at regional and Finals, T-shirt size, solo vs teammate, how you heard (university club / mailing list / social media / friend / other), and an opt-in to share details with Sequoia, OpenAI and Citadel Securities "for developer follow-up and recruiting outreach." — [Landing page](https://pokerbot.sequoiacap.com/)

**Castle Challenge (pre-event, part of the application)**
- "OPTIONAL: THE CASTLE CHALLENGE. Two quick strategy games, about 3 minutes in all. This is optional, but top scorers get priority registration for the tournament. You have 100 soldiers to split across 5 castles, worth 1, 2, 3, 4 and 5 points. Whole numbers only, adding up to exactly 100." Game 1 (head to head): matched against every other applicant; higher count wins the castle, ties split; score = average across matchups. Game 2 (four-way battle): random groups of 4; ranked by total castle points; payouts 1st 9 / 2nd 4 / 3rd 2 / 4th 0, ties split; "We reshuffle the groups thousands of times and average your results." An optional free-text strategy explanation is requested. — [Landing page](https://pokerbot.sequoiacap.com/)
- Leaderboard: "Head to Head scores are average castle points across every one-on-one matchup, out of 15. Four-Way Battle scores are average payout across 1,000,000 randomly drawn groups of four, out of 9. Tied scores share a rank." Updated every 15 minutes; players shown as first name + last initial unless they "claim" their spot. — [Castle Challenge leaderboard](https://pokerbot.sequoiacap.com/castle_challenge/)
- Sequoia: "No Limit Pokerbot Tournament Update: Competition is heating up on the Castle Challenge. Many of you have asked for a leaderboard. Here you go. Live results updated every 15 minutes." — [Sequoia on X](https://x.com/sequoia/status/2115486256041963847); Malani: "@Harvard we need to step up!" — [Abhishek Malani on X](https://x.com/abhishekm1636/status/2115544363153678601)

### Inferences
- **Regional timeline (inferred from §2.3 and §4.1):** if the build starts at 6:00 PM, T1 starts ~7:00, T2 7:20, T3 7:40, T4 8:00, T5 8:20, T6 8:40, finishing by 9:00 PM. That means each 10,000-table tournament must simulate and score in well under 20 minutes, and teams get at most ~100 minutes of post-build iteration spread over five 20-minute windows (one submission per 5 minutes, so at most ~4 submissions per window).
- **Score weighting (inferred from §4.7):** total weight is 21; T5+T6 alone are 11/21 (52%) of the final score. A bot that is weak at T1 but strong by T5 can still win; conversely, breaking a working bot late is very expensive.
- **"Variant" (inferred):** the landing page says "No-Limit Hold'em" everywhere, and the rules say the "poker variant" is secret and the Finals use "a different poker variant." The most plausible reading is that the base game is no-limit hold'em with a twist (rule mutation, altered hand rankings, bounty/extra street, etc.), consistent with how MIT Pokerbots keeps its variant secret each year. The unofficial poker-gym simulator (below) rehearses exactly this with mutations like "flush-beats-full-house" and "pot-limit", but that is a third party's guess, not organizer information.
- **Blind pressure (inferred from §4.4):** 2,000 chips at 10/20 is 100 BB; blinds step every 25 hands with 200 hands max, so there are at most 8 blind levels per table. The blind schedule is in the starter kit, so the exact escalation is unknown until event day; the 200-hand cap plus ICM payout means many tables will end unfinished with survivors paid by ICM, which rewards survival and chip accumulation rather than pure elimination.
- **"Plot twists"** (Maguire) are undefined; the secret variant, the ICM cutoff, and the tie-breaker challenge are the only twist-like mechanics stated in the rules.

### Gaps
- No round has been played, so there is no actual prompt, engine code, starter kit, variant, point distribution, blind schedule, or results from any city. The SF-round post-mortem requested in the brief does not exist yet; the first regional is Nov 6 and the Finals Nov 15.
- The official starter kit (agent template, local simulator, ICM calculator) is **not published** anywhere public; it is distributed on event day.
- Venues (building/room) for all four events are not published.
- X.com posts could not be fetched directly (HTTP 402/451 on x.com and mirrors); quotes above come from search-engine renderings of those posts and from Digg's roundup. Reply threads with organizer Q&A, if any, could not be read.
- No Hacker News, Reddit, or Substack discussion threads were found as of Oct 31. Coverage is limited to Sequoia/partner X posts, Digg, Zeniteq, RuntimeWire, tilt.now, Podkey, AGI Hunt, and a Threads repost.

## Key question 2: What languages/runtimes does the engine support, and is a starter kit published?

### Takeaway
Python only, implementing a provided `Agent` interface, with a hard 1 ms per-decision limit, 100 MB file-size cap, no network, and state reset per table. The starter kit (agent template, local simulator, ICM calculator, payout structure, blind schedule) is handed out at the event and has not been published; three unofficial GitHub rehearsal repos exist and explicitly say they are not the official kit.

### Cited Findings
- Language: "Teams have 60 minutes to build a **Python** bot that implements the provided Agent interface." — [Official rules §3.3](https://pokerbot.sequoiacap.com/rules.html)
- Decision budget: "Each bot must return a decision within one millisecond. The maximum file size is 100mb. If a bot encounters an error or exceeds the time limit, it automatically folds, or checks if checking is available." — [Official rules §3.7](https://pokerbot.sequoiacap.com/rules.html)
- Sandbox: "Submitted bots run in isolated sandboxes without network access. They cannot call OpenAI tools, external APIs, or any other outside service to make gameplay decisions." — [Official rules §3.6](https://pokerbot.sequoiacap.com/rules.html)
- "AI tools may assist teams with writing, debugging, and refining bot code... They may not make live gameplay decisions for submitted bots." — [Official rules §7.1](https://pokerbot.sequoiacap.com/rules.html)
- State: "Bot state resets at the start of each table. Opponents are anonymized." — [Official rules §3.8](https://pokerbot.sequoiacap.com/rules.html)
- Starter kit contents: "an agent template, local simulator, Independent Chip Model (ICM) calculator, payout structure, and blind schedule." — [Official rules §3.3](https://pokerbot.sequoiacap.com/rules.html)
- Submission path is an endpoint: teams are disqualified for "using the submission endpoint in unintended ways." — [Official rules §6.1](https://pokerbot.sequoiacap.com/rules.html)
- Hand logs are retained for disputes; the Organizer may use an AI model post-hoc to pick hands for spectator replay (no effect on scoring). — [Official rules §6.3, §7.2](https://pokerbot.sequoiacap.com/rules.html)
- Code ownership stays with participants; organizers get a license to run/evaluate it and to publish hand logs and anonymized results; "Prizes and advancement remain subject to verification, including code review." Submissions must not contain malware, credentials, or code designed to compromise the platform. — [Official rules §5.4, §8.1, §8.4](https://pokerbot.sequoiacap.com/rules.html)
- Unofficial rehearsal repo #1: `mack-dot/poker-gym` ("fast, verified eight-player poker tournament simulator for No Limit (Sequoia x Citadel Securities x OpenAI) rehearsal"). It states "This is not Sequoia's official starter kit" and "The official kit, secret variant, payouts, and harness arrive only on tournament day." Pure Python (CPython 3.12), no runtime deps, Malmuth-Harville ICM in `pokergym/icm.py`, an `AgentAdapter` enforcing a 1 ms deadline/legality, a `MyBot.act()` example, a 17-rule "arena mutation pool" to rehearse secret variants (e.g., `flush-beats-full-house`, `pot-limit`), a `drills/fake_kit/` exercise for adapting to an unseen kit, and a saved copy of the rules dated 2026-10-28. — [GitHub: mack-dot/poker-gym](https://github.com/mack-dot/poker-gym)
- Unofficial repo #2: `amalkoch/pokerbot-lab` ("Offline pokerbot practice: legal-action checks, seeded matchups, and decision-latency benchmarks"), links the official rules (checked Oct 30, 2026), practices on Kuhn poker rather than the real game, advises stateless policies using the supplied RNG, and notes "prewritten code may not be allowed in the competition, so you should confirm this with the organizer." It recommends fixed seeds for comparisons, studying ICM vs chip-EV divergence, and running a timed 60-minute build drill. — [GitHub: amalkoch/pokerbot-lab](https://github.com/amalkoch/pokerbot-lab)
- Unofficial repo #3: `nischalon10/poker-bot-tournament` covers only the Castle Challenge (C++ Blotto simulators). — [GitHub: nischalon10/poker-bot-tournament](https://github.com/nischalon10/poker-bot-tournament)
- The landing page's "Exhibit D: Message Trace — heads-up: two bots and a dealer on one wire... bot replies, with think time" is a decorative animation; inspection of the page's JavaScript shows only display strings (DEAL, CHECK, CALL, BET, RAISE TO, ALL-IN, FOLD, SHOWDOWN, SPLIT POT) and no actual wire protocol. — [Landing page](https://pokerbot.sequoiacap.com/) (verified by downloading and grepping index.html on 2026-10-31)
- Reference point for the analogous MIT competition: MIT Pokerbots (6.9630) is a one-month IAP class supporting Python, Java and C++, keeps its variant and structure secret until the January kickoff, and lists Citadel as a 2025 Gold sponsor (Sequoia is not a sponsor). — [pokerbots.org](https://pokerbots.org/)

### Inferences
- A 1 ms decision budget in Python rules out per-decision Monte Carlo rollouts of any depth or on-the-fly CFR; practical designs are precomputed lookup tables (preflop ranges by position/stack-in-BB, push/fold charts, ICM-adjusted shove/call thresholds) plus cheap hand-strength heuristics. The 100 MB file cap is large enough to ship substantial precomputed tables or a small model inside the submission.
- The "Agent interface" is almost certainly a class with a single decision method taking an observation (hole cards, board, stacks, pot, legal actions, blind level, seat/position) and returning an action; both unofficial repos model it that way, but the real signature is unknown until the kit is distributed.
- Because state resets per table and opponents are anonymized, opponent modeling is limited to within-table (up to 200 hands against 7 anonymous bots); cross-table learning is impossible by design.
- "Local simulator" in the kit implies teams can self-play test offline during the hour; expect to spend part of the 60 minutes just wiring the template, so a pre-rehearsed mental plan for the first 10 minutes matters more than any specific algorithm.

### Gaps
- Exact Agent method signature, observation format, action encoding, Python version, allowed third-party packages (numpy? treys/pokerkit?), CPU/memory limits, whether a per-bot init/warm-up phase is allowed outside the 1 ms budget, and how the 1 ms is measured (wall clock vs CPU, per call, with or without a grace period) are all unpublished.
- Whether the simulator runs bots in-process or over a dealer protocol (the Exhibit D "wire" imagery hints at the latter, but there is no evidence) is unknown.

## Key question 3: How are matches scored and against whom (other participants, a house bot, Slumbot-like baseline)?

### Takeaway
Scoring is purely against other participants' bots: 10,000 eight-bot sit-and-gos per scored tournament with random seating, points by finishing position (distribution announced at build time), ICM for tables hitting the 200-hand cap, filler seats filled with no-score copies of submitted bots, and a final score weighting T1..T6 by 1..6. There is no house bot, baseline bot, or bracket.

### Cited Findings
- 10,000 simulated eight-bot sit-and-gos per tournament, random seating each iteration. — [Official rules §4.3](https://pokerbot.sequoiacap.com/rules.html)
- Position points, variant-dependent distribution announced at build; eliminated bots get their position's points; ICM allocates remaining points to survivors at 200 hands. — [Official rules §4.5](https://pokerbot.sequoiacap.com/rules.html)
- Filler seats: "randomly selected copies of submitted bots. These filler bots earn no points." — [Official rules §4.6](https://pokerbot.sequoiacap.com/rules.html)
- "A team's score for each scored tournament is its average points per table across the 10,000 iterations. Later tournaments carry greater weight: Final score = (T1 score × 1) + (T2 score × 2) + (T3 score × 3) + (T4 score × 4) + (T5 score × 5) + (T6 score × 6)." — [Official rules §4.7](https://pokerbot.sequoiacap.com/rules.html)
- "Ties are resolved by a tie-breaker challenge to be determined by the Organizer. The Organizer will announce the tie-breaker challenge and its objective skill-based scoring criteria." — [Official rules §4.8](https://pokerbot.sequoiacap.com/rules.html)
- "Competition rankings and prizes depend solely on bot performance under this scoring system." — [Official rules §4.9](https://pokerbot.sequoiacap.com/rules.html)
- Disputes must be raised with a Gamemaster before the next scored tournament; T6 disputes within 5 minutes of results. The technical lead decides timing/delays; the events lead decides rules/conduct. — [Official rules §6.2–6.3](https://pokerbot.sequoiacap.com/rules.html)
- Bots "compete exclusively against other bots. No humans play." — [Official rules §3.9](https://pokerbot.sequoiacap.com/rules.html)

### Inferences
- Because every opponent is another team's fresh bot and the field will skew toward simple, fast-built bots (many will be the starter template lightly modified, or bots that time out and auto-fold), robust exploitative play against weak/passive opponents likely matters more than equilibrium play. Timeouts auto-fold, so a field with many erroring bots rewards simply staying alive and applying pressure.
- The field composition changes between T1 and T6 as teams iterate; a bot tuned to beat T1's field may be mis-tuned for T6's, and the weighting makes T5/T6 performance dominant.
- Average points per table across 10,000 tables gives low variance, so scores will be close; the tie-breaker rule suggests organizers expect ties (possibly many bots scoring identically if the point scale is coarse).

### Gaps
- The point distribution per finishing position (e.g., whether it is top-heavy like the Castle Challenge's 9/4/2/0 or flatter) is unpublished until event day.
- Whether the same 10,000 random seatings are used for all bots within a tournament (common random numbers) and whether card deals are seeded identically across tables is unknown.

## Key question 4: What did winners in SF do, and what did participants say they wished they had prepared?

### Takeaway
Nothing yet: the Bay Area regional is November 6, 2026 and the Finals November 15. The only competitive signal so far is the Castle Challenge application leaderboard (3,178 head-to-head entries and 1,603 four-way entries as of 2026-10-31 06:51 UTC) and two unofficial prep repos.

### Cited Findings
- Castle Challenge leaderboard data file (`generated_at` 2026-10-31T06:51:50Z): Game 1 (head-to-head) has 3,178 ranked entries, top score 9.172/15, median ~7.78; Game 2 (four-way) has 1,603 entries, top score 6.497/9, median ~3.72. Eight entries are tied at or within 0.002 of the Game 1 top score. — [leaderboard.json](https://pokerbot.sequoiacap.com/castle_challenge/data/leaderboard.json) (downloaded and parsed 2026-10-31)
- School counts among Game 1 entries (rough normalization of free-text school names, so treat as approximate): Carnegie Mellon ~324, UC Berkeley ~310, Stanford ~222, MIT ~156, Harvard ~114, Waterloo ~86, Columbia ~77, Penn ~71, Northeastern ~71, UT ~69, Georgia Tech ~57, NYU ~54, UIUC ~52, Purdue ~50, Cornell ~46. — [leaderboard.json](https://pokerbot.sequoiacap.com/castle_challenge/data/leaderboard.json)
- Game 1 top: a three-way tie at 9.172 (Hofstra, UC Berkeley, Boston College entrants); Game 2 top: Yale (6.497), CMU (6.456), UCLA (6.447). Names are shown publicly on the board. — [Castle Challenge leaderboard](https://pokerbot.sequoiacap.com/castle_challenge/)
- One participant's published Castle strategy: Game 1 pick (1,0,21,31,47), chosen for smallest worst-case gap across ten modeled opponent fields; Game 2 pick (0,0,48,52,0), averaging ~8.6/9 in the author's models. — [GitHub: nischalon10/poker-bot-tournament](https://github.com/nischalon10/poker-bot-tournament)
- Prep advice from an unofficial repo author: run a timed 60-minute build drill; keep policies stateless and use the supplied RNG; measure decision latency separately from chip results; study ICM vs chip-EV; adapt to the official interface only once released. — [GitHub: amalkoch/pokerbot-lab](https://github.com/amalkoch/pokerbot-lab)
- Prep approach from poker-gym's author: rehearse against a mutation pool of rule variants and practice wiring a bot to a "fake kit" so adapting to an unseen interface is fast. — [GitHub: mack-dot/poker-gym](https://github.com/mack-dot/poker-gym)
- Public commentary so far is pre-event speculation: commenters asked which tools/APIs will be allowed and one argued bots should click through a UI rather than use an API; one predicted bots would become superhuman. — [Podkey](https://podkey.fm/stories/sequoia-announces-a-60-minute-poker-bot-tournament)

### Inferences
- The scale of the Castle Challenge (3,000+ applicants in four days against "limited seats") implies regionals will be selective and the "top scorers get priority registration" lever is real; the field at each regional will be dominated by CMU/Berkeley/Stanford/MIT/Harvard students.
- The Game 1 scores cluster tightly at the top (eight entries within 0.002), consistent with many applicants converging on the same heavy-top-castles allocations, which is the kind of convergence to expect in the poker rounds too.

### Gaps
- No winning approaches, no post-mortems, no "wish I had prepared" reflections, no released prompt or engine: none exist as of Oct 31, 2026. Re-run this research after Nov 6 (Bay Area), Nov 9 (Boston), Nov 12 (Pittsburgh) and Nov 15 (Finals). Rule §6.4 bars participants from sharing the variant until each event ends, so expect recaps only after each date.

## Key question 5: What are the Boston and Pittsburgh dates, and are they tied to MIT and CMU?

### Takeaway
Boston regional: Monday November 9, 2026, Cambridge, MA, 6:00–9:00 PM ET (register by Nov 6). Pittsburgh regional: Thursday November 12, 2026, 6:00–9:00 PM ET (register by Nov 9). No official source names MIT or CMU as venue or co-host; the tie is circumstantial.

### Cited Findings
- "Monday, November 9 - Cambridge, MA (deadline to register - Friday, November 6 at 11:59 PM ET)"; "Thursday, November 12 - Pittsburgh, PA (deadline to register - Monday, November 9 at 11:59 PM ET)". — [Official rules §2.4](https://pokerbot.sequoiacap.com/rules.html)
- Decision notifications: Boston by Sunday Nov 8; Pittsburgh by Wednesday Nov 11. — [Landing page FAQ](https://pokerbot.sequoiacap.com/)
- Noam Brown explicitly framed the event relative to MIT's 6.9630 Pokerbots class. — [Noam Brown on X](https://x.com/polynoamial/status/2115125429619343609)
- MIT Pokerbots lists Citadel (a co-host here) as a Gold sponsor; Sequoia is not a sponsor. — [pokerbots.org](https://pokerbots.org/)
- The application form's "How you heard" options include "UNIVERSITY CLUB" and "MAILING LIST", consistent with campus-club distribution. — [Landing page](https://pokerbot.sequoiacap.com/)
- CMU is the single most represented school on the Castle Challenge leaderboard (~324 Game 1 entries) and MIT is fourth (~156). — [leaderboard.json](https://pokerbot.sequoiacap.com/castle_challenge/data/leaderboard.json)

### Inferences
- "Cambridge, MA" strongly suggests an MIT (or Harvard) venue; "Pittsburgh, PA" plus Noam Brown's CMU lineage (Libratus/Pluribus) strongly suggests CMU. Both are inferences; neither university is named on the official site, and no MIT Pokerbots or CMU club page mentioning the event was found.
- The Bay Area regional "Menlo Park, CA" is most plausibly Sequoia's own office at 2800 Sand Hill Road, which is the address printed on the event pages.

### Gaps
- No venue names, room numbers, or university co-host announcements found for any city. No MIT Pokerbots, CMU, Stanford or Berkeley club post about the event surfaced in search.

## Key question 6: Is prior preparation (precomputed tables, pre-written code) allowed or prohibited?

### Takeaway
The official rules neither permit nor prohibit bringing pre-written code or precomputed tables; they only prohibit copying another team's code, collusion, platform interference, network calls during play, and sharing the variant. Marketing language says "from scratch", and the secret variant plus the 100 MB cap are the practical constraints. Allowed AI tooling is stated as "Astra and Codex" (OpenAI), with OpenAI tool use "optional at every stage"; whether non-OpenAI assistants are allowed is not stated.

### Cited Findings
- "Teams may use Astra and Codex to write, debug, and refine their bots during the build phase. Publicly available documentation is permitted." — [Official rules §3.4](https://pokerbot.sequoiacap.com/rules.html)
- "Using OpenAI tools is optional at every stage of the tournament." "No purchase of OpenAI services or any other product or service is necessary to enter or win." — [Official rules §7.3, §1.5](https://pokerbot.sequoiacap.com/rules.html)
- "Participants must review and test AI-generated code and remain responsible for their submissions." — [Official rules §7.4](https://pokerbot.sequoiacap.com/rules.html)
- Prohibited conduct: "colluding with other teams, copying another team's code, interfering with the platform, or using the submission endpoint in unintended ways," plus cheating, fraud, malicious code, security abuse, misrepresentation. — [Official rules §6.1](https://pokerbot.sequoiacap.com/rules.html)
- Max submission size 100 MB; no network; 1 ms per decision. — [Official rules §3.6–3.7](https://pokerbot.sequoiacap.com/rules.html)
- "Participants must comply with applicable third-party software and data licenses." Submissions must not include third-party confidential information. — [Official rules §8.4](https://pokerbot.sequoiacap.com/rules.html)
- The Organizer "may amend these rules before the build phase begins. Any changes will be announced to all participants." — [Official rules §9.1](https://pokerbot.sequoiacap.com/rules.html)
- "Astra" refers to OpenAI's GPT-6 Astra model, released September 3, 2026 and available in Codex and GitHub Copilot. — [The New Stack](https://thenewstack.io/openai-gpt6-astra-benchmarks/); [GitHub changelog](https://github.blog/changelog/2026-09-04-gpt-6-astra-is-generally-available-in-github-copilot)
- Sequoia and all secondary coverage use "from scratch" ("60 minutes to build a pokerbot from scratch"). — [Sequoia on X](https://x.com/sequoia/status/2115111389501218868); [Landing page](https://pokerbot.sequoiacap.com/)
- An unofficial prep repo warns "prewritten code may not be allowed in the competition, so you should confirm this with the organizer." — [GitHub: amalkoch/pokerbot-lab](https://github.com/amalkoch/pokerbot-lab)
- Secondary coverage paraphrases the AI-tool rule as "AI coding assistants may be used during development" without naming vendors. — [Zeniteq](https://www.zeniteq.com/sequoia-and-openai-open-a-100k-pokerbot-tournament-6aycef); [RuntimeWire](https://runtimewire.com/article/sequoia-offers-100-000-to-the-winning-student-pokerbot-team)

### Inferences
- The rules are written to constrain the *bot* (offline, 1 ms, 100 MB) rather than the *inputs* to the build; nothing in the text bars a personal library of helper code, hand evaluators, or precomputed preflop/ICM tables, and the 100 MB cap would be odd if only hour-old code were expected. However, "from scratch" is the organizers' framing and §9.1 allows rule amendments before the build; participants should ask pokerbot@sequoiacap.com explicitly and expect an on-the-day clarification.
- The naming of "Astra and Codex" (rather than "any AI assistant") plus the OpenAI host role suggests OpenAI will provision Codex/GPT-6 Astra access on site; whether Claude Code, Cursor, etc. are tolerated is a genuine ambiguity. The safest reading is that OpenAI tools are the sanctioned path and others are unaddressed, not expressly banned.
- Because the variant is secret and may change hand rankings or betting structure, generic infrastructure (fast evaluator parameterized by hand rankings, ICM calculator, push/fold generator, latency-safe action wrapper with a fallback to check/fold) is the preparation most likely to survive contact with the actual rules; pre-solved NLHE-specific tables may be partly invalidated.

### Gaps
- No organizer statement on pre-written code, precomputed tables, bringing your own laptop/environment, or non-OpenAI AI assistants was found. No FAQ entry addresses it.

## Past Sequoia events with a similar one-hour format

### Takeaway
No prior Sequoia event with a one-hour build format was found; the closest analogs are MIT Pokerbots (the explicit inspiration, one month long) and a 72-hour virtual fal x Sequoia video hackathon in July 2026.

### Cited Findings
- fal x Sequoia 72-Hour Video Hackathon: virtual, July 17–19 2026, teams up to four, application-gated, prizes and token budgets, judges TBD. — [Cerebral Valley](https://cerebralvalley.ai/e/fal-x-sequoia-virtual-hackathon)
- Sequoia Arc is a seven-week founder program, not a hackathon. — [Sequoia Arc](https://sequoiacap.com/arc)
- Sequoia is a title sponsor of HackMIT. — [Wikipedia: HackMIT](https://en.wikipedia.org/wiki/HackMIT)
- MIT Pokerbots: one-month class (6.9630), Python/Java/C++, variant secret until kickoff, Citadel sponsor. — [pokerbots.org](https://pokerbots.org/); [Noam Brown on X](https://x.com/polynoamial/status/2115125429619343609)

### Inferences
- The No Limit format reads as MIT Pokerbots compressed to one evening and adapted for coding agents: secret variant, provided engine/template, bots-vs-bots, with the month-long schedule replaced by six 20-minute iteration windows.

### Gaps
- No earlier Sequoia "AI build hour" or timed-build event was found under the phrasings searched ("Sequoia hackathon 60 minutes", "Sequoia AI build", "Sequoia Arc poker", "Base Camp").
