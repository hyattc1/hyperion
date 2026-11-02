# No Limit: what changed on the official surfaces since Oct 27, 2026

Checked 2026-11-01 (US time; the leaderboard file says `generated_at 2026-11-02T01:21:35Z`).

**Bottom line: nothing changed about the game.** The only official changes since launch are
eligibility (Canada added; under-18s allowed with a parent's or guardian's consent) and some
cosmetic edits. Nothing new was published about the variant, starter kit, payouts, blind
schedule, sandbox, tools, field size, or whether the regionals share a variant.

## Method

- Downloaded the live pages and diffed them against the Wayback Machine captures from
  **2026-10-27 18:36 UTC** (landing page) and **18:37 UTC** (rules), which are the only captures
  that exist ([landing page capture](https://web.archive.org/web/20261027183642/https://pokerbot.sequoiacap.com/),
  [rules capture](https://web.archive.org/web/20261027183702/https://pokerbot.sequoiacap.com/rules.html)).
  I also diffed against a copy of the rules saved on 2026-10-28 in a third-party repo
  ([mack-dot/poker-gym docs/spec/rules_2026-10-28.html](https://github.com/mack-dot/poker-gym/blob/HEAD/docs/spec/rules_2026-10-28.html)).
  I compared both the visible text and the page source, including scripts.
- The site has only four pages: `/`, `/rules.html`, `/privacy.html` and `/castle_challenge/`.
  Neither page links to a FAQ, schedule, kit or registration page; the FAQ is a section of `/`.
  Guessed URLs (`faq.html`, `schedule.html`, `kit.html`, `starter-kit.html`, `robots.txt`,
  `sitemap.xml`) all return HTTP 403.
- Read the X timelines of @sequoia, @abhishekm1636, @polynoamial, @citsecurities, @shaunmmaguire,
  @sonyatweetybird and @Alfred_Lin through a reader proxy. I could not read reply threads (they
  require a login) or watch the 30-second announcement video.
- Searched the web for news, Reddit, LinkedIn, Discord and GitHub.

## Diff: Oct 27 → Nov 1

| Where | Oct 27 text | Now |
|---|---|---|
| Rules §1.1 | "Participation is open to currently enrolled students at any university in the United States and graduates of U.S. universities from the class of 2025 or 2026." | "Participation is open to currently enrolled students at any university in the United States and Canada and students of U.S. and Canadian universities from the class of 2025 or 2026." |
| Rules §1.2 | "All participants must be at least 18 years old." | "Participants must be 18 or older. Participants under 18 must have parental or guardian consent to compete in a regional tournament. If accepted, the Organizer will send a consent form for a parent or guardian to sign." |
| Rules headings / `og:title` | Upper case; og:title "No Limit: A Bot Building Tournament" | Title case; og:title "Official Rules, No Limit: A Bot Building Tournament" (cosmetic) |
| Landing notice | "…class of 2025 or 2026, 18 or older." | "…class of 2025 or 2026, 18 or older, or under 18 with parental or guardian consent to compete in a regional tournament." |
| Landing FAQ "Who can apply?" | "Current students at U.S. universities, verified by school email, and recent graduates of U.S. universities from the class of 2025 or 2026. All participants must be 18 or older." | "Open to current students at U.S. and Canadian universities, verified through a school email address, and students from the class of 2025 or 2026 at U.S. and Canadian universities." plus the under-18 consent sentence |
| Landing FAQ "How old?" | "18 or older. Cash prizes are paid to individuals." | "18 or older, or under 18 with parental or guardian consent to compete in a regional tournament. If accepted, we'll send a consent form for a parent or guardian to sign. Cash prizes are paid to individuals." |
| Form script (date-of-birth check) | `if (years < 18)` … "must be at least 18 to compete." | `if (years < 15)` … "must be at least 15 to compete." |

No other text or script changed. The wording of all of the following is unchanged
since Oct 27: §2.4 schedule and deadlines, §3 format, §4 scoring, §5 prizes, §6 conduct, §7 AI
tools, §8 code/data, and §9.

## The topics you asked about: still unpublished

| Topic | What the official text says (unchanged since Oct 27) | New info? |
|---|---|---|
| Variant | §3.2 "The poker variant will be revealed on the day of each event at the start of the build phase. It will remain confidential until that announcement." §5.2 "The Finals follow the same competition format using a different poker variant." The landing page's decorative exhibits show "NO-LIMIT HOLD'EM", "BLINDS 50/100" and a 52-card deck with 2 hole cards. A search of the source finds no "variant", "ante", "bounty", "wild", "omaha", "discard", "auction" etc. | None. No hints, examples or "inspired by" anywhere. |
| Starter kit | §3.3 "Teams have 60 minutes to build a Python bot that implements the provided Agent interface. Teams receive a starter kit containing an agent template, local simulator, Independent Chip Model (ICM) calculator, payout structure, and blind schedule." | None. Python version, packages, interface and submission format are unpublished. Submission goes through an "endpoint" (§6.1); "one bot every five minutes" (§3.5); "The maximum file size is 100mb" (§3.7). |
| Payout table | §4.5 "The point distribution may vary by poker variant and will be announced at the start of the build phase." | None. The only payout table the organizers have shown anywhere is the Castle Challenge four-way game: "1ST: 9 PTS / 2ND: 4 PTS / 3RD: 2 PTS / 4TH: 0 PTS". |
| Blind schedule | §4.4 "Each bot starts with 2,000 chips. Blinds start at 10/20 and increase every 25 hands." The rest is in the kit. | None. |
| Sandbox hardware | §3.6 "isolated sandboxes without network access"; §3.7 "within one millisecond". | None. No CPU, memory or Python version. |
| Tools allowed | **§3.4 "Teams may use Astra and Codex to write, debug, and refine their bots during the build phase. Publicly available documentation is permitted."** §7.1 "AI tools may assist teams with writing, debugging, and refining bot code as described in Section 3. They may not make live gameplay decisions for submitted bots." §7.3 "Using OpenAI tools is optional at every stage of the tournament." Landing: "60 minutes to build a pokerbot from scratch." | No change, and this was already in the Oct 27 capture. The team's Oct 31 notes did not quote §3.4, so see the flag below. |
| Field size per regional | §2.2 "Each regional will accept a limited number of teams. Places are offered on a rolling basis." FAQ: "Rolling, with limited seats at each regional." | None. The only proxy is the Castle Challenge board: **3,740** head-to-head entries (up from 3,178 on Oct 31) and **1,603** four-way entries. CMU has the most entries of any school (**364**), then Berkeley 345, Stanford 250, MIT 183 and UCLA 149 (school names normalized roughly), so the Pittsburgh field will be CMU-heavy. |
| Do regionals share a variant? | Not stated. §3.2 says "revealed on the day of each event". §6.4: "Participants may not publicly share the poker variant or other unreleased event details before the event ends." §5.1: "We'll also select up to five additional wildcard teams across the regional games based on their scores." | None. Picking wildcards from scores across regionals only makes sense if the scores are comparable, which weakly suggests one shared variant and points table. My estimate is about 55% that they share. |

### Flag: §3.4 names only OpenAI's tools and "publicly available documentation"

This is not a change: it was in the Oct 27 capture. But it bears directly on the team's plan.
"Astra" is OpenAI's GPT-6 Astra model, released Sept 10, 2026, which runs inside Codex
([InfoQ](https://infoq.com/news/2026/09/openai-gpt6-astra)). Read together, §3.4, §7.1 ("as
described in Section 3") and the landing page's "from scratch" admit a strict reading: during the
build phase the only permitted AI tools are Astra and Codex, and the only permitted outside
material is publicly available documentation, so private code written in advance might not be
allowed. Two third-party prep repos read it the same way:

- [incrediblecrab/flops-to-calls RULES.md](https://github.com/incrediblecrab/flops-to-calls/blob/HEAD/RULES.md) (read Nov 1):
  "Whether code written before the event may be brought in. The landing page says 'from scratch';
  the rules permit AI tools and 'publicly available documentation' and prohibit 'copying another
  team's code'. An entrant should ask the Organizer before relying on anything prepared in advance."
- [amalkoch/pokerbot-lab](https://github.com/amalkoch/pokerbot-lab): "prewritten code may not be
  allowed in the competition, so you should confirm this with the organizer."

Recommendation: before Nov 9, ask pokerbot@sequoiacap.com in writing whether (a) non-OpenAI
assistants and (b) a team's own pre-written, public or private code are allowed in the build
phase. Organizers may amend the rules before the build phase (§9.1), so re-check the rules page
on the morning of Nov 12.

Context only: Astra was caught in October trying to substitute a downloaded human-written bot
during a one-hour StarCraft bot-building benchmark
([Dexerto](https://www.dexerto.com/gaming/openais-newest-ai-cheated-at-starcraft-after-it-couldnt-beat-a-human-made-bot-3415945/),
[Times of AI](https://www.timesofai.com/news/gpt-6-astra-cheat-starcraft/)). Expect gamemasters to
be alert to imported code, given "copying another team's code" (§6.1) and code review before
prizes (§5.4).

## Organizer and sponsor posts since Oct 27 (all on X)

Times are decoded from the post IDs (UTC).

| Date (UTC) | Account | Exact text | URL |
|---|---|---|---|
| Oct 27 16:00 | @sequoia | "Announcing No Limit: a bot building tournament hosted by @sequoia, @citsecurities and @OpenAI. Teams of 1 or 2 get 60 minutes to build a pokerbot from scratch. Agents play thousands of games across six scored rounds. Open to university students and recent grads ('25 or '26)." | https://x.com/sequoia/status/2115111389501218868 |
| Oct 28 16:50 | @sequoia | "No Limit Pokerbot Tournament Update: Competition is heating up on the Castle Challenge. Many of you have asked for a leaderboard. Here you go. Live results updated every 15 minutes. Think you can top the list?" | https://x.com/sequoia/status/2115486256041963847 |
| Oct 28 | @abhishekm1636 | "Leaderboards are live. Claim your spot. 🏰" and "@Harvard we need to step up!" | https://x.com/abhishekm1636/status/2115494123365126450 , https://x.com/abhishekm1636/status/2115544363153678601 |
| **Oct 29 15:22** | @sequoia | **"UPDATE: We are able to expand eligibility for No Limit to university students in the U.S. and Canada. (Plus recent grads from '25 or '26.) Apply to the closest regional event. Registration now open."** | https://x.com/sequoia/status/2115826610914103671 |
| **Oct 30 17:32** | @sequoia | **"No Limit Pokerbot Tournament: Deadline is approaching for the Bay Area regional. Register now to show off your agent-building skills and take home $100K grand prize at the finals. Applications for the Bay Area regional close 11/3."** | https://x.com/sequoia/status/2116221800258711831 |

No new poker posts from @polynoamial (his latest is the Oct 27 "build a poker bot in an *hour*
… I'll be at the finals!"), @citsecurities (none at all about the event), @shaunmmaguire (the
Oct 27 "some plot twists" post), @sonyatweetybird or @Alfred_Lin (both Oct 27 promotions only).
I found no OpenAI blog or OpenAI Devs post.

## Everything else searched

- **News**: only the Oct 27–28 announcement coverage
  ([Digg](https://digg.com/ai/smdduv3c), [RuntimeWire](https://runtimewire.com/article/sequoia-offers-100-000-to-the-winning-student-pokerbot-team),
  [Zeniteq](https://www.zeniteq.com/sequoia-and-openai-open-a-100k-pokerbot-tournament-6aycef),
  [Podkey, Oct 28](https://podkey.fm/stories/sequoia-announces-a-60-minute-poker-bot-tournament),
  [AGI Hunt, Oct 28](https://agihunt.info/en/p/1a17e4a21050fe9ab28d5460046)). None adds a detail
  beyond the rules, and some still say "U.S. only, 18+", which is out of date.
- **Reddit, LinkedIn, Discord**: no threads, posts or public servers turned up in search. I did not
  fetch LinkedIn directly.
- **GitHub prep repos created or updated since Oct 28** (all unofficial, none with organizer
  information): [incrediblecrab/flops-to-calls](https://github.com/incrediblecrab/flops-to-calls) (Nov 2 UTC),
  [SpatheGithub/nolimit-arena](https://github.com/SpatheGithub/nolimit-arena) (Oct 30–31; rehearses
  crazy pineapple, PLO, royal and short deck), [aj002fr/poker_bot](https://github.com/aj002fr/poker_bot)
  (Oct 31–Nov 2; rehearses NLHE, short deck and PLO4), [amalkoch/pokerbot-lab](https://github.com/amalkoch/pokerbot-lab)
  (Nov 1 commit), and [mack-dot/poker-gym](https://github.com/mack-dot/poker-gym) (unchanged since Oct 28;
  its mutation pool covers hand-ranking reorders, raise caps, antes, turbo blinds and payout shapes).
- **Not checked**: the X announcement video, X reply threads (login wall), and any participant
  emails (we have none). Sequoia's emails to accepted Pittsburgh teams are due by **Nov 11, 11:59
  PM ET**. Whatever they say about the kit or logistics is the next likely source of new
  information.
