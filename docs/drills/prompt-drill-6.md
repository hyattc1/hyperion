# Prompt drill 6: Track A on kit A, hidden variant toss_or_holdem (information axis)

Date 2026-11-01. T0 01:18:08 EDT; the agent role ended at 01:52:42 EDT, before the 02:00 EDT daylight-saving change
(operator runs after it are stamped EST). The repo was pinned with `git archive` at **`857dbe9`**, the commit that
added kit A's toss mode for this drill, and copied twice into the session scratchpad: `drill6/hyperion/`, the
agent's copy with its own venv (`uv venv` plus `uv pip install -e ".[dev]"`, Python 3.12.12), and `drill6/pristine/`,
an untouched copy for baselines. Another agent was changing `hyperion/strategy/*` in the live tree throughout, and
neither copy saw it.

**Protocol.** Operator protocol as in drills 3 and 4 (the operator keeps the clock and pastes `docs/prompts/00` to
`05` in PLAYBOOK order, filling only the placeholders). New this time: the agent role was played by a **separate
subagent** (same model, Opus 5.5, default effort), not by the operator in a second role. The subagent saw only
the pinned copy, the kit and the prompts. It was told:
- never touch `/home/connor` or git;
- not to read `docs/drills/`, `docs/decisions.md`, `HANDOFF.md` or any `RUBRIC.md`;
- to run at most 2 processes at once, because other agents' sweeps were using the box. So `gen_tables` ran with
  `--workers 2`, and prompt 04's load generator was skipped.

Scratch is `drill6/` in the session scratchpad:
- `hyperion/`: the agent's `NIGHT.md`, `submission/`, `dist/` and `frozen/`;
- `operator/`: the rules text, the prompts as pasted, `clock.log`, `simcompare6.py` (which plays the shipped kit-A
  Agent in the real sim), every sim, kit and diagnostic output, and the unpacked shipped zip.

The box carried other sessions' work the whole time: load 5 to 15 on 8 cores.

**Hidden variant.** The catalog's `toss_or_holdem`:
- three hole cards;
- once the flop is dealt and before anyone bets on it, every player still in tosses one card face up, starting
  left of the button; the card is dead and is not a community card;
- showdown uses the two kept cards plus the board.

Everything else is the standard 8-max SNG: 2,000 chips, 10/20 blinds rising every 25 hands over eight levels, a
200-hand cap, points 10/7/5/4/3/2/1/0 and ICM at the cap. The rules text is in the appendix.

**Kit set-up (operator, committed before pinning).** Kit A's dealer had no discard. `runner --toss` now:
- deals three cards and asks each player still in once, with `legal_moves == ["DISCARD"]`;
- takes `"DISCARD:<i>"`, i an index into `state.hand`, as the answer;
- puts the tossed card face up in `state.discards` and the action log;
- plays showdown as two kept cards plus the board.

A missing or illegal toss is counted and the dealer tosses for you. This mirrors the engine's `TossHooks` and
MIT 2026's `DiscardAction`. The agent was told the kit is `kit.py` plus `runner.py`.

## Key numbers

| Score | Result | Drill 3 (Track B) | Drill 4 (Track A) | Target |
|---|---|---|---|---|
| Rule sheet + axis + FIT VERDICT | **minute 3** (01:22:01) | 1 | 3 | 5 |
| Legal upload-ready package (kit runner PASS, `pack.py` sha256) | **minute 12** (01:30), `68ffc925…ba37` | 4 | 6 | 12 (hard 15) |
| Stage 3 tables | **minute 21** (01:39:29), regeneration over its box, catalog set kept | 9 (step 2) | 8 | 25 |
| Hero wired, strict gate, zip | **minute 29** (01:47), `787c70a6…eec0` | 17 (step 3) | 13 gate / 16 zip | 40 |
| Stage 5 patch measured and decided | **minute 34** (01:52:42), reverted, override `{}` | 19 (step 4) | 20 | 50 |
| Agent questions needing a human | **0** | 0 | 1 | 0 |
| Rule sheet and FIT VERDICT correct | **yes** (below) | | | |
| Kit-runner legality, shipped zip, `--toss --hands 2000` seeds 11 and 12 | **5,868 decisions, 0 exceptions, 0 illegal**, 7 timeouts (0.12%) at load 8–10, max 2.4 / 4.1 ms; every toss legal | | | 0 exc, 0 ill |
| **Shipped Agent in the real sim** (300 tables, seed 11, realistic, `--variant toss_or_holdem`, tonight's payouts) | **3.389 ± 0.304 measure, 3.299 ± 0.303 strict, 5th of 8, bust 91%** | | | Hero's level |
| Pinned Hero, same command | **5.901 ± 0.328 measure, 5.864 ± 0.320 strict, 1st** | | | |
| Shipped Agent after the adapter fix (below) | **5.806 ± 0.322 measure, 5.933 ± 0.314 strict, 1st** | | | |

Minute to each checkpoint against drill 3's 4/9/17/19: **12 / 21 / 29 / 34**. That is 8 to 15 minutes slower, and
every playbook box was still met. The time went to the full test suite (185 s at load 15), two packs (the first
left out the variant tables), a 5-minute regeneration that could not finish on 2 workers, and four 300-table sims
on a loaded box.

## Timeline

| Prompt | Minute | Notes |
|---|---|---|
| 00 | 0 (01:18:39) | restated in one paragraph; read PLAYBOOK §3, §4, §7, CHALLENGE.md, CONTRACTS.md |
| 01 | 3 (01:22:01) | Information axis only; `rules_tonight.json` = `hole_cards` 3, payouts, the preset's `extras`; found `tables/variants/toss_or_holdem` through `tables_for`; named the discard-only decision as the most dangerous thing |
| 02 | 12 (01:30) | subclassed `KitAAdapter` and added the toss path: `bot.variant_decide` with `default_discard` as fallback, plus a `native_safe` that returns a legal `DISCARD`. Kit runner 60 hands PASS, 0/0/0; conformance flagged 26 `hole_len` false positives after the toss (repo finding 4). Suite 508 passed in 185 s. First pack (`330fcb57…`) left out `tables/variants/`, caught, repacked with `--tables-dir tables`. Latency: 1 call in 200 over 1 ms at load 15.8 (load clause) |
| 03 | 21 (01:39:29) | `--variant-check` projected 697 s on 2 workers; a boxed run timed out at 300 s; catalog set kept (338 classes, `source disk`). Refused `--out tables/`, which would have overwritten the 2-card set (prompt edit 5) |
| 04 | 29 (01:47) | strict 300: hero 5.993 ± 0.320 (inside the Verifier's 5.942 ± 0.329), exc 0, ill 0, p99 231 µs, tmo 0.65% at load 14.6 (load clause); rotate 40 first; `latency.py` p99 276 µs, with 468 SafeBot errors from its 2-card generator (repo finding 5); `cheap` measured at 4.68, so it did not revert |
| 05 | 34 (01:52:42) | `preflop.open_step` 1: +0.022 against the +0.164 needed, reverted. Discard: Hero's `variant_decide` already did better than the prompt's rule. Final strict run 5.828, errors 0 |

## Did the rule sheet and FIT VERDICT classify the twist correctly?

Yes, on every line.

- **Axis.** Information moved: three hole cards and a face-up dead toss before flop betting. Strength, payoff and
  betting did not move. The point table went to the ASSUMPTION DIFF and `Rules.payouts`.
- **FIT VERDICT.**

| Layer | Verdict | Reason |
|---|---|---|
| evaluator | KEEP | 7 cards after the toss |
| preflop tables | REGENERATE | the 169 classes do not cover three cards |
| push/fold | KEEP | label tables |
| postflop | KEEP | every postflop decision comes after the toss |
| profiler | KEEP | |
| ICM | KEEP | reads `Rules.payouts` |

  So the path was Stage 3, as it should be.
- **Most dangerous thing.** Every safety net (`native_safe`, SafeBot, `Action.clamp`) falls back to check or fold,
  which is illegal when DISCARD is the only legal move. That was the right call, and the adapter it then wrote
  handled it. In 5,868 kit decisions and about 2,300 sim tosses there were 0 illegal tosses and 0 fallbacks.
- **Engine gap.** In the kit a later seat sees earlier tosses when it chooses; the sim's toss prompt does not
  show them. The agent captioned every sim line with this gap.
- **Caveat.** The operator's prompt-01 message gave the Verifier's Stage 0 line with `--variant toss_or_holdem` in
  it, so the catalog name was not discovered blind. The agent also found it on its own, through
  `variants --list` and `tables_for`.

## The comparison against pinned Hero, and why the shipped bot lost 2.5 points

The gate the prompts run (prompt 04 step 2, prompt 05) is `python -m hyperion.sim`. That plays the bestiary's
Hero, which is fed the engine's own Observation. It never runs the shipped entry point. So the operator played
the shipped zip itself.

`operator/simcompare6.py` is the inverse of kit A. It:
- turns each engine Observation into a kit A `GameState` with `kit.to_state`;
- calls the shipped `Agent.act` and parses its string;
- turns the engine's discard prompt into a DISCARD-only state.

The shipped `hyperion/` and `tables/` are byte-identical to the pinned copy (`diff -r`), so the only difference
from pinned Hero is the kit interface and the agent's adapter.

```
300 tables, seed 11, realistic field, --variant toss_or_holdem, payouts 10/7/5/4/3/2/1/0
shipped Agent, measure  drill6  300  3.389 0.304    9  7  8 12 20 19 18  7  90.7% bust   (5th of 8)
pinned Hero,   measure  hero    300  5.901 0.328   24 23 17 13 10  7  3  2  69.7% bust   (1st)
shipped Agent, strict   drill6  300  3.299 0.303   tmo 199  exc 0  ill 0                  (5th)
pinned Hero,   strict   hero    300  5.864 0.320   tmo 267  exc 0  ill 0                  (1st)
```

Diagnosis, in order:

1. **The observation round trip is exact on every scalar field.** Engine Observation → kit state → the agent's
   `to_observation` matched on hole, board, street, seats, stacks, bets, in_hand, pot, to_call, min/max raise,
   legal, hand_no and blinds in 961 of 961 decisions.
2. **`obs.history` was empty.** It was empty in 109 of 123 decisions where the engine's was not. None of the four
   reference adapters passed history (`make_observation(..., history=None)`), and kit A's rubric called the
   action log "optional; parse lazily or skip".
3. **Hero reads who raised from history alone.** That covers `Spot.n_raises`, `Spot.raiser`, `Preflop._opened` and
   the shove-context read, so every raised pot looks unopened to it. Bestiary Hero with the history stripped
   (100 tables, measure):
   - standard hold'em: **3.21 ± 0.54**, against 5.50 with history;
   - toss: **3.32 ± 0.55**.

   Replacing `act` with a direct `bot.act(obs)` behind the same wrapper restores 5.75; passing the full HandResult
   at hand end changes nothing (3.34). The history is the whole gap.
4. **Every Track A drill so far shipped this.** Drills 1, 2 and 4 built on the reference adapters (drill 4
   subclassed `KitDAdapter` unchanged), and `KitBAdapter`, `KitCAdapter` and `KitDAdapter` pass no history
   either. Their "Hero first" lines were the bestiary Hero's, not the shipped bot's.

**Fixed in this pass (`hyperion/drills/adapter.py`, 4f5ad79):**
- `KitAAdapter` parses `action_log` into history, skipping discards.
- `make_observation` rebuilds the current street's raises from the bets when a kit gives no history: one RAISE per
  bet level above the street's base, credited to the first seat in acting order; a short all-in below the top
  level counts as a call. Bestiary Hero on rebuilt history scores 5.20 against 5.50 with the real one.
- The template gained TODO 7b.

With the fix, the same shipped Agent scores **5.806 ± 0.322 measure and 5.933 ± 0.314 strict, first of 8**,
level with pinned Hero.

**Not fixed here (strategy is another agent's file):** `Spot` should fall back to the bets when history is empty
(`max(bets) > base` means at least one raise), so Hero is safe behind any adapter.

## Repo and protocol findings (not prompt problems)

1. **Adapters dropped history, and Hero needs it.** Explained above. Adapter side fixed; Hero side open for the
   strategy owner.
2. **The sim gate never runs the shipped bot.** Prompt 04's 300 tables measure the bestiary Hero with the
   engine's history, so any information lost in the adapter is invisible. This is drill 5's finding 5 again:
   `hyperion/drills/` needs `shipped_sim.py --kit a|b|c|d --entry dist/submission/submission.py` (the inverse of
   each kit, as in `simcompare6.py` here and drill 5's kit B script), so prompt 04 can gate the shipped entry
   itself. Until then, prompt 04 asks for an `obs.history` print (edit 7).
3. **`pack.py` vendors only `tables/*.json`.** Without `--tables-dir tables` the zip leaves out
   `tables/variants/<name>/`. Hero then falls back to label tables and plays differently from the bot that was
   verified. The agent caught it by diffing behaviour. The prompts now pass `--tables-dir tables`. The tool should
   include `tables/variants/<extras.variant>` itself when a rules JSON is among the extras (`tools/` is not this
   pass's file).
4. **Conformance knew nothing about the toss.** `hole_len` flagged every post-toss observation (26 in 60 hands).
   Fixed: after `extras.discard_street` it expects `extras.keep` cards. Test added.
5. **`tools/latency.py` deals 2-card observations under 3-card rules.** That produced 468 SafeBot `KeyError`s
   on 2-card classes in a 3-card table set. Harmless to p99, but noise in a gate. Prompt 04 now says so; the tool
   should honour `rules.hole_cards`.
6. **Regenerating a 3-card set on 2 workers projects 697 s**, and the boxed run did not finish its preflop stage.
   On the night's 7 idle workers it is about 3 minutes (tables/README). The catalog already holds tables for this
   game, so prompt 03 now keeps a matching catalog set instead of regenerating (edit 5).
7. **Load, fifth drill running.** Load was 5 to 15 throughout. Strict timeouts of 0.6% applied equally to pinned
   Hero (267 per 300 tables) and to trivial bots (tag 27 to 43). The load clause did its job.
8. **The separate-subagent agent role worked.** The agent never read the live tree or the drill reports, which
   makes this the cleanest information boundary of the six drills. Its reports came back as messages and the
   operator kept the clock from them and from `NIGHT.md`.

## Questions the agent would have needed a human to answer

None were asked. Guesses recorded in `NIGHT.md`:
- the import and `new_game` time limits, and the dealer's own toss choice, are UNSPECIFIED: keep import cheap,
  start lazily, never let the dealer toss;
- the Stage 2 latency miss and the Stage 4 timeout rate went under the load clause;
- it generated into `scratch/` instead of `tables/`;
- `--tables-dir tables` on every pack;
- the one `Config` candidate for Stage 5 was `preflop.open_step`, because the label fallback's one-step tightening
  is inactive when variant tables load.

The operator added one instruction mid-drill: no gc change at Stage 2 ("do not optimize").

## Prompt edits (applied to `docs/prompts/*` in 4f5ad79)

1. **02 step 1:** pass the kit's action log as `history`. Hero reads raises from it alone (an empty history cost
   2.5 points); with no log, `make_observation` rebuilds the raises from the bets.
2. **02 step 2:** a variant decision the kit asks for (discard, swap, buy) goes to `bot.variant_decide({...})`,
   never through `act`.
3. **02 step 3:** `native_safe` returns a legal default when the only legal move is a variant move, because fold
   is illegal there.
4. **02 steps 5–6:** the suite takes 2 to 3 minutes and never imports `submission/`, so run it while packing.
   `pack.py --tables-dir tables`.
5. **03 step 2:** if `tables_for(rules)` already loads a catalog `tables/variants/<name>/` from disk, keep it and go
   to step 5. When the hole-card count or the deck changes, never use `--out tables/`; write
   `tables/variants/<name>/` with `extras.variant` set.
6. **04 step 4:** with hole cards other than 2, `latency.py` still deals two; read p99 and ignore SafeBot errors.
7. **04 step 2:** print `obs.history` on a state after a raise; it must hold the RAISE, because the sim's Hero gets
   the engine's history and the shipped one gets only what the adapter passes.
8. **04 step 5:** `pack.py --tables-dir tables`.
9. **05, Information, extra hole cards:** with a variant table set loaded, no bonus and no one-step tightening
   (`preflop.open_step` 1 measured +0.02).
10. **05, Information, discards:** Hero already decides through `variant_decide`; the patch is the adapter's
    routing. No new rule.

Code changes that came with the drill (also in 4f5ad79):
- `hyperion/drills/adapter.py`: history from kit A's log, and a bets-based fallback;
- `hyperion/drills/adapter_template.py`: TODO 7b;
- `hyperion/drills/conformance.py`: the toss's `keep`;
- tests for each.

The kit toss mode itself is 857dbe9.

## Appendix: the operator's rules text as pasted to the agent

```
SEQUOIA POKER BOT NIGHT -- OFFICIAL RULES, FINAL (issued 19:30)

1. THE GAME: TOSS OR HOLD'EM
   No-limit Texas Hold'em with one change: every player is dealt THREE hole cards and must throw one
   away after the flop.
   - Standard 52-card deck, standard hand rankings, one board of five community cards dealt
     flop (3) / turn (1) / river (1).
   - Preflop: each player holds three hole cards. Betting as usual.
   - The toss: once the flop is dealt and before anyone bets on the flop, every player still in the
     hand discards exactly one of their three hole cards, FACE UP. Players toss one at a time,
     starting with the first player to the left of the dealer button and going clockwise. A tossed
     card is dead: it is out of play, it is NOT a community card, and every player can see it for
     the rest of the hand. Players who folded preflop do not toss.
   - After the toss, flop betting begins as usual; then turn and river.
   - Showdown: the best five-card hand from your TWO remaining hole cards and the five community
     cards, using any combination (two, one or none of your hole cards).
   - If you do not toss in time, or your toss is invalid, the dealer tosses for you and it counts
     against you as an illegal action.

2. TABLE FORMAT
   Eight (8) players per table, sit-and-go. Every player starts with 2,000 chips. A table ends
   when seven players have busted OR after hand 200, whichever comes first. Your module is
   imported once per table and told its seat; it may keep memory between hands at that table.
   Nothing persists between tables.

3. BLINDS
   Blinds rise every 25 hands and stay at the last level until the cap:
       Level 1  hands   1-25     10 /  20      Level 5  hands 101-125    75 / 150
       Level 2  hands  26-50     15 /  30      Level 6  hands 126-150   100 / 200
       Level 3  hands  51-75     25 /  50      Level 7  hands 151-175   150 / 300
       Level 4  hands  76-100    50 / 100      Level 8  hands 176-200   200 / 400
   No antes, no straddles. Betting is no-limit. The minimum raise is the size of the last raise
   this street, or one big blind if there has been none. Raises are expressed as the TOTAL you
   are raising to this street, as in the starter kit.

4. SCORING
   Points are awarded by finishing position at each table:
       1st 10    2nd 7    3rd 5    4th 4    5th 3    6th 2    7th 1    8th 0
   If the table reaches the 200-hand cap with more than one player alive, the points still on the
   table for the unfilled positions are split among the survivors by ICM (Malmuth-Harville) on
   their chip counts after hand 200. Players who busted keep the points for the position they
   busted in. Two players who bust on the same hand are ordered by chips at the start of that
   hand; ties split the points. Your tournament score is your average points over all tables you
   play (we expect about 10,000).

5. YOUR BOT
   Python 3. Your module defines `class Agent` as documented in the starter kit's `kit.py`
   (subclass `kit.Agent`, implement `act(state) -> str`; `new_game` and `hand_over` are optional).
   The toss is a decision like any other: your `act` is called with a state whose legal moves are
   exactly ["DISCARD"], and you answer as documented in `kit.py`. One millisecond of wall clock
   per `act` call, measured around the call. An exception, an illegal action or a slow reply is
   scored as a fold (a check when a check is legal; a dealer toss on the discard) and is counted
   against you. Standard library only; you may also import the kit's own `kit` module. No network,
   no threads, no subprocesses.

6. SUBMISSION
   Upload a single zip under 100 MB through the portal. The zip must contain `submission.py` at
   its top level defining `class Agent`; the server imports it from the directory the zip unpacks
   into, so other files in the zip may be imported relative to that directory. You may resubmit
   as often as you like until the freeze, at most one upload per five minutes; the last accepted
   upload plays.

7. STARTER KIT
   `kit.py` (the interface) and `runner.py` (a local simulator: four seats, three house bots, your
   Agent in seat 0). Tonight's game runs locally with:
       python -m <kit package>.runner submission.py --toss [--hands N] [--seed S]
```

The blind table is reflowed into two columns here; the agent received it as one column, as in `operator/rules.txt`.
