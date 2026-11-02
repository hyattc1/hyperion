# NIGHT.md — <regional, date>

Copy this file to `NIGHT.md` at minute 0 (`cp docs/packet/NIGHT-template.md NIGHT.md`). The Verifier owns
it. Keep the T0 line exactly in this form: `tools/pack.py` reads it to stamp each submission's minute.

T0: <HH:MM local, the minute the variant was revealed>
repo: <`git rev-parse --short HEAD`>   kit: <path>   variant (their name): <...>   track: A | B
ship bot: <`python -m hyperion.ship`: SHIP and DIALS>   (`--bot hero` restores Hero)
Stage 0 known-good number: <ship line of `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship`>
Hero's, for the fallback: <hero line of the same with `--field realistic`>

## RULE SHEET (Stage 1, prompt 01)

Where the rules are silent write UNSPECIFIED and the conservative assumption; quote the rule text for
anything non-standard. A filled rehearsal example: `docs/packet/EXAMPLE-rule-sheet.md` (not tonight's rules).

- Hole cards dealt per player: N. Any discards, swaps, exposures, auctions? When, and who chooses?
- Board: cards per street, number of boards, any community cards that change.
- Hand ranking: standard? Any rank permutation, removed ranks, added categories, must-use-two rule?
- Betting: no-limit / pot-limit / fixed. Min raise rule. Raise amounts as raise-to totals or
  increments? Antes? Straddles? A non-standard rule with no `Rules` field in CONTRACTS.md: first check the
  variant hooks (`hyperion/drills/variants.py`: on_deal, on_street, score_hand, score_splits, on_payout, on_bust,
  charges and charges_dead; the shape hooks in `hyperion/sim/engine.py`'s header: forced_bets, after_forced,
  next_card, on_fold, settle). Most twists fit them as a file (`hyperion/drills/variant_file_example.py`): a hand
  the house deals, a pot that carries to the next hand (drill 8's Ghost: on_deal, settle, after_forced). Write
  ENGINE CANNOT REPRESENT, and what the sim will play instead, only if none fits.
- Blind schedule: levels and hands per level. Starting stack. Table size. Hand cap.
- Scoring: points by finish position (table), ICM at the cap, any bounty or side payoff.
- Agent interface: class or function name, method signature, every state field and its type, the
  action format (type, string, dict), legal-action discovery, per-decision time limit, how a table
  start and a hand end are signalled, one instance per table or per tournament, whether state persists.
- Setup budget per table (import + construction + table start) and whether each table gets a fresh module, a
  fresh instance, or one object for the tournament (kit E: 1 s, a fresh module per table).
- Event callbacks (table or hand start, cards, actions, showdown, hand end): timed or not, and what an overrun
  does (skipped, interrupted mid-call, counted as a timeout).
- Submission size cap, zipped and unzipped (kit E's was 10 MB zipped, not 100 MB): tools/pack.py `--max-mb`.
- Tooling: how the local simulator runs, how to submit, what the submission file layout must be,
  allowed imports the kit itself uses.

## AXIS CLASSIFICATION

- Hand strength ordering moved? (permuted ranks, short deck, new categories) -> Y/N, how.
- Information moved? (extra/fewer hole cards, swaps, exposed cards, extra boards) -> Y/N, how.
- Payoff moved? (bounties, auctions, non-standard points) -> Y/N, how.
- Betting structure moved? (limits, sizes, schedule, antes) -> Y/N, how.

Stage 5 patch section: <axis>.

## FIT VERDICT (minute 2; the Verifier holds it for the hour)

| prepared layer | KEEP / REGENERATE / DROP | reason |
|---|---|---|
| evaluator (best hand from 5 to 8 cards, rank remap through `Rules.rank_order`) | | |
| preflop tables (169-class equity and ranks) | | |
| push/fold solution | | |
| postflop rule layer | | |
| opponent profiler | | |
| ICM curve (reads `Rules.payouts`) | | |

Path (mechanical): evaluator AND preflop tables both DROP -> not hold'em underneath: skip Stages 3 to 5,
Track B cheap bot behind the adapter (plus the profiler if KEEP). Any REGENERATE -> Stage 3 runs.
Otherwise Stage 4 as normal. Tonight's path: <...>

## ASSUMPTION DIFF

| Our default | Tonight | Invalidates | Carried by |
|---|---|---|---|
| 2 hole cards, 3/1/1 board | | | `rules_tonight.json`: hole_cards, board_sizes |
| standard rankings | | | rank_order; Stage 3 tables |
| no-limit, raise-to totals | | | adapter (from_action), `Rules.betting` |
| 10/20 rising every 25 hands, 2,000 chips, 8 seats, 200-hand cap | | | blind_levels, hands_per_level, starting_stack, n_players, max_hands |
| no antes | | | ante, ante_from_level, ante_per_level |
| linear payouts 8..1 | | | payouts (Hero's ICM curve reads it) |

ENGINE CANNOT REPRESENT: <none | the rule, and what every sim line is captioned "variant minus ...">

## MOST DANGEROUS THING FOR A 1 ms BOT

<one paragraph>

## Verified (every command whose output decided something)

| minute | stage | command | the line that mattered |
|---|---|---|---|
| | 2 | `HYPERION_CHECK=1 python -m <kit runner> submission/<entry>.py --hands 50` | PASS ... 0 illegal; conformance ... 0 violations |
| | 4 | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --rules rules_tonight.json --field realistic@ship` | ship ... exc 0 ill 0 p99 ... |
| | 4 | `python tools/latency.py --n 2000 --rules rules_tonight.json` | bot <SHIP> ... p99 ... over 1 ms ... |
| | 4 | `python tools/gate.py dist/submission.zip --kit <k> --tables 100 --rules rules_tonight.json` | baseline bot ...; GATE PASS ... |

## Submissions

`python tools/pack.py --entry submission/<entry>.py --out dist/ --note "<what changed>"` (`--bot cheap` at Stage 2)
appends a row whose "what changed" starts with the bot it recorded and its dials;
the Verifier fills "verified by" with the portal's confirmation (time, or the hash the portal shows).

| minute | file | sha256 | size / import | what changed | verified by |
|---|---|---|---|---|---|

Frozen known-good: <sha256>  (`mkdir -p frozen && cp dist/submission.zip frozen/T1.zip`)

## Windows

One change per window, verified before upload, upload by minute 15 or nothing. One upload per five minutes.

| window | standings in at minute | our rank / mean / spread | signal | recipe (and the dials it set) | model sim before -> after | uploaded (sha256 or nothing) |
|---|---|---|---|---|---|---|
| T2 | | | | | | |
| T3 | | | | | | |
| T4 | | | | | | |
| T5 | | | | | | |
| T6 | | | | | | |

## sha256

Linux: `sha256sum dist/submission.zip`   macOS: `shasum -a 256 dist/submission.zip`   (`tools/pack.py` prints the same)
