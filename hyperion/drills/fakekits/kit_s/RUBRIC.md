# Kit S rubric: one kit shape at a time (backlog R3)

Kit S is not a kit anyone ships: it is the dealer's decision state (`_table.py`) with one quirk switched on, so an
adapter can be held to every shape a real kit may have. The reference adapter is `KitSAdapter` in
`hyperion/drills/adapter.py`; `tests/test_kit_shapes.py` plays every shape at real tables with the ship bot behind it,
and `tools/gate.py --kit seat.py --kit-module hyperion/drills/fakekits/kit_s/kit.py` gates a packed entry on one
(a seat file is `from kit import Seat as _S` and `class Seat(_S): SHAPE = "raise_by"`).

| shape | what changes | what the adapter does |
|---|---|---|
| `raise_by` | min / max / reply amount are increments over the top bet | `total = amount + max(bets)`, back as `total - max(bets)` |
| `put_in` | ... are the chips this action puts in | `total = amount + my bet`, back as `total - my bet` |
| `log_own` | the log holds only our actions | `history_source = "partial"`: the rebuilt log, merged |
| `log_last3` | only the hand's last three actions | `"partial"` |
| `log_none` | no log | `"bets"`: the log rebuilt from the states |
| `posts` | the log starts with the blinds as bets of 10 and 20 | make_observation drops leading raises to the big blind or less |
| `bounds_swapped` | min and max swapped | make_observation puts them in order |
| `bounds_missing` | no min or max | pass None: derived (max = all-in, min = top bet + last increment) |
| `allin_short` | short of a full raise: min is the full raise, above my stack | min becomes the all-in |
| `seats_from_1` | seats 1..n | subtract 1; the table start's 1-based seat is put right at the first decision |
| `seats_me` | seats numbered from us | nothing: a consistent relabelling plays the same |
| `cards_ten`, `cards_lower`, `cards_unicode`, `cards_suit_first` | "10h", "th", "T♥", "hT" | parse_card reads them all |
| `legal_upper`, `legal_dicts`, `legal_string` | "FOLD", {"type": "raise"}, "fold,call,raise" | make_observation's legal_kinds |
| `legal_words` | "bet" when nobody has bet, "all-in" for an all-in-only raise; the reply must use that word | reply with the kit's word |

Before this kit (main at 98a7259, the template's way: `parse_card` and `make_observation` as they were), the share
of decisions that fell back to the kit's check/fold: `bounds_missing`, `cards_unicode`, `cards_suit_first`,
`legal_dicts`, `legal_string` every decision; `cards_ten` 13% (every hand with a ten); `legal_words` 21%;
`bounds_swapped` none, but every raise became an all-in (the clamp takes the larger bound); `posts` read every
unopened pot as a raise and a re-raise. After: no fallback on any shape, and the same decisions as the plain shape
on every one (docs/drills/climb/r2-log.md).
