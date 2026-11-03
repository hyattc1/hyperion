# V-f: carry the hold'em-gated gains into the likely twists

Branch climb/vf-twist-carry, from main 782b0f5, rebased onto e28f0dd (ffb1e62's `r3.v3_bvb_holdem_only`). Worker for
the variants and strength tracks.

**Why.** On the night a real twist is almost certain (variants-ranked.md: about 10% for plain hold'em or a
structure-only change). The recent strength gains are gated to plain hold'em (`hero.holdem_table`), so under any twist
they switch off. The likeliest twist families still play ordinary hold'em after one twist step: deal-extra-then-discard
(~20%), bounty (11%), buy a card (7%), swap or redraw (6%), one card exposed (4%).

## 1. The dials (84d22e8)

`hero.twist_family(rules)` names the family of a table that is hold'em but for one twist, from Rules alone:
structure as hold'em (52 cards, board 3/4/5, no-limit, rank order as dealt, no must-use; two hole cards, three only for
a face-up discard down to two), the extras hold that family's keys and nothing else, and the variant name, when given,
is one of the family's catalog entries. Anything else is no family and every gate stays shut. On the catalog it names
exactly the nine entries:

| family | entries |
|---|---|
| discard | toss_or_holdem, three_card_blind_discard |
| bounty | bounty |
| knockout | knockout_bounty |
| buy | bonus_card, auction |
| swap | swap_holdem, swap_one_turn |
| exposed | exposed_card |

One dial per gain lists the families it reaches, off ("") by default, so F and every gain as gated today play as before:

| dial | gain | what it opens on a listed family |
|---|---|---|
| `hero.postflop.size_read_twists` | S12's size read (D3) | the size read, past `size_read_holdem_only` |
| `hero.postflop.s11_twists` | S11's postflop part (Z3) | the probe read and the one bet size, past `s11_holdem_only` |
| `r3.v3_bvb_twists` | S11's blind-vs-blind 3-bet prior (Z3) | the prior in rival 3's core, past `r3.v3_bvb_holdem_only` |
| `strong_route_twists` (composite) | S9's strong-table route | the hold'em-only members (elite1) may play their routed sections |

**The twist's information, respected.** On a family's table the size read and the probe read skip a bettor whose bet
the twist itself explains (`Postflop._twist_read_off`):
- `buy`: a seat holding a bought card (bonus_card's `bought`, the auction's `auction_winners`): a three-card range the
  hold'em size model does not describe;
- `bounty`: a seat whose bounty rank shows on the board (any pot it wins pays it 1.5x + 10, so it bets for the pot, not
  for its hand); bounties kept private: no test;
- `knockout`: a bet that puts me all-in (the bettor bets for the knockout point too).
- `discard`, `swap`, `exposed`: no skip. After the discard the hand is two cards on a normal board; Hero already removes
  the tossed cards from its outs (`hero.toss_dead`) and reads its hand `toss_call_shift` lower facing a bet, and the read
  uses that same shifted tier. A swapped or exposed hand still bets its current strength.

**Where each gain plausibly holds, decided before any screen:**

| family | D3 size read | S11 postflop (probe, one size) | S11 BvB prior (core) | strong route (elite1) |
|---|---|---|---|---|
| discard | yes: same game after the toss | yes | n/a: Hero plays the table whole | no: three cards preflop, elite1 cannot play them |
| bounty | yes, skipping bettors whose bounty shows | yes | H9 already lost a little here: measured apart | yes: the base's core is bounty-blind too (`r3.bounty` 0) |
| knockout | yes, skipping knockout shoves | yes | measured apart | yes: the core ignores knockout points too |
| buy | yes, skipping buyers | yes | H9 lost a little here: measured apart | yes: preflop is plain hold'em |
| swap | yes | yes | H9 lost a little on swap_holdem: measured apart | yes: preflop is plain hold'em |
| exposed | yes | yes | n/a: Hero plays the table whole | no: Hero's opens read the exposed cards (steals shrink with a high card showing behind); elite1 sees none |

The strong route's dial lets an elite member play only where the base's core plays the table (the composite's existing
`plain` test), so listing discard or exposed changes nothing: their sections stay F's own (the base's fallback Hero).

**One base for all three.** Each gain as gated today plays every one of the nine entries exactly as F (test
`test_each_gain_gated_to_hold_em_plays_every_family_exactly_as_f`, every gain on each entry with its hooks: same
decisions as F). So on the twist cells "F with the gain on, hold'em-only" is F, and one F run is the base of every
extension: the candidate minus F there is exactly the extension.

## 2. Screens (16:53-18:48; code 84d22e8 from the detached goal/wt_vf_m; seeds 10000-10199 x 8 rotations)

`tools/climb_accept.py --set screen --stages aware,variants --workers 2` under `nice -n 10`, two processes at a time,
load 12-16. Aware cells: `generic:<entry>` (V-d's generic aware field) for the nine entries, plus the hand-built
`toss_or_holdem_aware` and `bounty_aware`; variants cells: the realistic field under each entry. Base F
(`{"dials": {}}`) for every pair (section 1: identical there to F with the gain on, hold'em-only). Candidates, each
the gain plus its dial listing every family it can reach:
- D3c = D3 + `size_read_twists` "discard,bounty,knockout,buy,swap,exposed";
- Z3c = Z3 (both gates, ffb1e62) + `s11_twists` "discard,bounty,knockout,buy,swap,exposed" (the postflop part; the
  BvB prior stays hold'em only, below);
- SRc = strong_route + `strong_route_twists` "bounty,knockout,buy,swap" (the families where the core plays).
Zero timeouts and zero errors in every cell of every spec (model mode). Each cell is one entry, so a cell of the
all-families candidate is exactly that family's extension.

### D3c - F (the size read)

| family | entry | generic aware | hand-built aware | variants (realistic) |
|---|---|---|---|---|
| discard | toss_or_holdem | +0.006 ± 0.025 | -0.003 ± 0.015 | +0.005 ± 0.015 |
| discard | three_card_blind_discard | -0.002 ± 0.023 | - | +0.008 ± 0.017 |
| bounty | bounty | +0.006 ± 0.031 | +0.001 ± 0.032 | +0.013 ± 0.029 |
| knockout | knockout_bounty | **+0.069 ± 0.058 UP** | - | **+0.087 ± 0.048 UP** |
| buy | bonus_card | +0.004 ± 0.013 | - | identical |
| buy | auction | -0.014 ± 0.051 | - | -0.035 ± 0.048 |
| swap | swap_holdem | **+0.042 ± 0.032 UP** | - | +0.030 ± 0.032 |
| swap | swap_one_turn | **+0.045 ± 0.031 UP** | - | +0.007 ± 0.030 |
| exposed | exposed_card | **+0.031 ± 0.025 UP** | - | +0.002 ± 0.024 |

climb_accept verdict ACCEPT (nothing down). bonus_card on realistic is identical because the twist-blind seats there
all buy (the hook's default), and the buy gate skips every bettor holding a bought card: the read never fires. The
auction leans down in both cells; nothing found yet explains it (one guess, not tested: when I hold the third card,
a two-card bettor betting into me is stronger than its hold'em sizes say).

### Z3c - F (S11's probe read and one size)

| family | entry | generic aware | hand-built aware | variants (realistic) |
|---|---|---|---|---|
| discard | toss_or_holdem | -0.018 ± 0.049 | -0.023 ± 0.029 | -0.006 ± 0.030 |
| discard | three_card_blind_discard | +0.025 ± 0.042 | - | +0.004 ± 0.028 |
| bounty | bounty | -0.017 ± 0.059 | -0.001 ± 0.050 | -0.007 ± 0.053 |
| knockout | knockout_bounty | -0.036 ± 0.088 | - | +0.047 ± 0.084 |
| buy | bonus_card | +0.039 ± 0.064 | - | -0.022 ± 0.059 |
| buy | auction | +0.022 ± 0.061 | - | -0.019 ± 0.058 |
| swap | swap_holdem | +0.028 ± 0.069 | - | +0.015 ± 0.069 |
| swap | swap_one_turn | +0.023 ± 0.062 | - | +0.014 ± 0.055 |
| exposed | exposed_card | +0.004 ± 0.059 | - | +0.016 ± 0.056 |

Nothing beyond noise either way: S11 was built against the exploiters, and neither field here holds one. Its
intervals are twice D3's, because one bet size changes many decisions.

### SRc - F (the strong-table route)

| family | entry | generic aware | hand-built aware | variants (realistic) |
|---|---|---|---|---|
| bounty | bounty | -0.005 ± 0.019 | -0.006 ± 0.015 | -0.004 ± 0.013 |
| knockout | knockout_bounty | -0.024 ± 0.034 | - | -0.006 ± 0.028 |
| buy | bonus_card | -0.010 ± 0.017 | - | -0.002 ± 0.012 |
| buy | auction | -0.000 ± 0.018 | - | -0.007 ± 0.011 |
| swap | swap_holdem | -0.006 ± 0.022 | - | +0.007 ± 0.020 |
| swap | swap_one_turn | -0.021 ± 0.022 | - | -0.011 ± 0.021 |

Nothing beyond noise, but 12 of 13 point estimates are below zero (mean -0.008). On hold'em the route was level on
realistic too (H6); its gain is at strong tables (mirror +0.10). So these fields do not test what the route is for:
the `mirror` field under each of the six entries does (section 3).

**The BvB prior (`r3.v3_bvb_twists`) was not screened.** H9 (400 held-out seeds) already measured it slightly down on
four of the six entries where the core plays preflop (swap_holdem, bonus_card, auction, bounty: -0.014 to -0.027, and
bounty_aware -0.015). A 200-seed screen (intervals ±0.03-0.06 here) cannot show "clearly not down" at that size, so the
slot went to the mirror and hold'em-identity checks. The dial exists (off) for a later 400-seed test.

**Rule for the recommendation (fixed at 18:48, before the mirror, combined and identity runs):** a family is in a
gain's list when none of its cells is beyond noise down and the mean of its cells' point estimates is at least 0.
- D3: discard (mean +0.003), bounty (+0.007), knockout (+0.078), swap (+0.031), exposed (+0.017) in; buy (-0.011) out.
- S11 postflop: knockout (+0.006), buy (+0.005), swap (+0.020), exposed (+0.010) in; discard (-0.004) and bounty
  (-0.008) out. Bounty also has a mechanism against it: when my bounty is hit a won pot pays 1.5x, and the one size
  caps big-value bets at 0.5 pot (0.8 otherwise).
- Strong route: decided by the mirror cells.

## 3. The strong route at strong tables under a twist (18:38-19:42)

`--stages aware --aware mirror:bounty,mirror:knockout_bounty,mirror:bonus_card,mirror:auction`, screen seeds, F vs
SRc. The `mirror` field (three copies of F, rival 2, elite1, elite2, hybrid3_x) is where the route was accepted on
hold'em (H6 +0.101 ± 0.040). The two swap entries were dropped to fit the time (mirror cells run at about half the
speed of the others); their F chunks were not finished.

| entry (mirror field) | F | SRc | SRc - F |
|---|---|---|---|
| bounty | 4.644 | 4.692 | +0.048 ± 0.052 |
| knockout_bounty | 5.260 | 5.453 | **+0.194 ± 0.073 UP** |
| bonus_card | 4.534 | 4.604 | **+0.070 ± 0.053 UP** |
| auction | 4.453 | 4.514 | **+0.062 ± 0.045 UP** |

The route keeps its strong-table gain under these twists (hold'em mirror screen: +0.098 ± 0.062), and on the fields
that are not strong it is level, as on hold'em. Strong route: bounty, knockout, buy in; swap out (no strong-table cell,
and its four other cells lean down: mean -0.008).

## 4. The size read and S11 twist dials together (18:49-19:58)

CombRec = F + D3 + Z3 + strong_route (all hold'em-gated as today) + `size_read_twists`
"discard,bounty,knockout,swap,exposed" + `s11_twists` "knockout,buy,swap,exposed" (the lists of section 2's rule; the
strong route's twist dial was not decided yet and is not in this run). Base F (identical to the gated gains on these
tables). climb_accept verdict ACCEPT.

| family | entry | generic aware | hand-built aware | variants (realistic) |
|---|---|---|---|---|
| discard | toss_or_holdem | +0.006 ± 0.025 | -0.003 ± 0.015 | +0.005 ± 0.015 |
| discard | three_card_blind_discard | -0.002 ± 0.023 | - | +0.008 ± 0.017 |
| bounty | bounty | +0.006 ± 0.031 | +0.001 ± 0.032 | +0.013 ± 0.029 |
| knockout | knockout_bounty | +0.004 ± 0.104 | - | +0.071 ± 0.091 |
| buy | bonus_card | +0.039 ± 0.064 | - | -0.022 ± 0.059 |
| buy | auction | +0.022 ± 0.061 | - | -0.019 ± 0.058 |
| swap | swap_holdem | +0.068 ± 0.074 | - | +0.034 ± 0.075 |
| swap | swap_one_turn | +0.035 ± 0.063 | - | +0.038 ± 0.057 |
| exposed | exposed_card | +0.025 ± 0.062 | - | +0.034 ± 0.057 |

Where only one dial reaches an entry the cell repeats that dial's own (discard and bounty: the size read's; buy: S11's,
the read is off for buy). Where both reach it, nothing is down and the mean is +0.039, but the
intervals are S11's (twice the size read's): the size read's knockout gain on generic aware (+0.069 alone) is +0.004
with S11 on top. 0 timeouts, 0 errors.

## 5. Plain hold'em unchanged (19:45-20:05)

Comb = F + D3 + Z3 + strong_route, hold'em-gated; CombAll = Comb + every twist dial at its widest (`size_read_twists`
and `s11_twists` all six families, `r3.v3_bvb_twists` and `strong_route_twists` "bounty,knockout,buy,swap").
`--stages confirm,guards --set 10000:10100` (100 seeds x 8, cut from 200 to fit the time):

| cell | Comb | CombAll | CombAll - Comb |
|---|---|---|---|
| night | 5.977 | 5.977 | +0.000 ± 0.000 (identical) |
| night_hard | 5.500 | 5.500 | identical |
| realistic | 6.324 | 6.324 | identical |
| top | 5.078 | 5.078 | identical |
| night @10/7/5/4/3/2/1/0 | 6.175 | 6.175 | identical |
| night @50/25/12/6/3/2/1/1 | 24.428 | 24.428 | identical |
| night, doubling blinds | 5.841 | 5.841 | identical |

The widest lists are identical on hold'em, so every subset is (each gate's hold'em branch does not read the lists).
With the dials off (the default) every gate is as before: tests/test_vf_twists.py, and section 1's identity on the
twist entries.

## 6. Latency (20:00-20:05, load 9-10)

`tools/latency.py --hand-end --reps 3 --variant NAME --dials <spec>`, 20 realistic tables under each entry, per-call
minimum of 3, µs. Rec = the recommended spec (section 7); Comb = the same gains hold'em-gated (it plays these tables
as F).

| entry | Rec act mean / p99 / max | Comb act mean / p99 / max | Rec hand end mean / p99 / max | Comb hand end mean / p99 / max | Rec first act mean / max |
|---|---|---|---|---|---|
| toss_or_holdem | 49 / 86 / 127 | 48 / 82 / 114 | 64 / 133 / 183 | 63 / 132 / 187 | 101 / 127 |
| three_card_blind_discard | 50 / 93 / 126 | 49 / 88 / 128 | 66 / 137 / 251 | 64 / 132 / 174 | 103 / 126 |
| bounty | 54 / 102 / 143 | 54 / 102 / 149 | 61 / 140 / 181 | 60 / 138 / 180 | 110 / 130 |
| knockout_bounty | 54 / 101 / 140 | 53 / 101 / 139 | 61 / 134 / 199 | 61 / 141 / 190 | 106 / 132 |
| bonus_card | 56 / 107 / 158 | 56 / 110 / 143 | 56 / 111 / 178 | 57 / 111 / 153 | 107 / 158 |
| auction | 58 / 109 / 246 | 57 / 108 / 138 | 59 / 114 / 148 | 58 / 112 / 152 | 111 / 136 |
| swap_holdem | 54 / 99 / 146 | 55 / 104 / 263 | 60 / 136 / 191 | 61 / 138 / 190 | 108 / 142 |
| swap_one_turn | 55 / 104 / 154 | 54 / 102 / 140 | 62 / 138 / 211 | 60 / 139 / 223 | 109 / 144 |
| exposed_card | 47 / 85 / 115 | 46 / 82 / 117 | 66 / 135 / 182 | 65 / 132 / 179 | 92 / 115 |

Decision p99 85-109 µs with the dials, 82-110 without: the same within the run-to-run spread; every p99 under the
protocol's 200 µs. The new work is one family test per table and one dict lookup per read spot.

## 7. Family x gain, and the recommended spec

Screen seeds 10000-10199 x 8, extension minus F (= minus the gain hold'em-gated). "in" / "out" by section 2's rule.

| family (P) | D3 size read | S11 postflop (probe, one size) | S11 BvB prior | strong route |
|---|---|---|---|---|
| discard (~20%) | **in**: generic +0.006 / -0.002, hand-built toss -0.003, realistic +0.005 / +0.008 | out: generic -0.018 / +0.025, hand-built toss -0.023, realistic -0.006 / +0.004 (mean -0.004) | n/a (Hero plays the table) | n/a (three cards preflop) |
| bounty (8%) | **in**: generic +0.006, hand-built +0.001, realistic +0.013 | out: -0.017, -0.001, -0.007 (and the one size caps value when a won pot pays 1.5x) | off: H9 slightly down | **in**: generic -0.005, hand-built -0.006, realistic -0.004, mirror +0.048 |
| knockout (3%) | **in**: generic **+0.069 UP**, realistic **+0.087 UP** | in: generic -0.036, realistic +0.047 | off: not screened | **in**: generic -0.024, realistic -0.006, mirror **+0.194 UP** |
| buy (7%) | out: bonus generic +0.004, realistic identical (every bettor bought); auction -0.014 / -0.035 | in: bonus +0.039 / -0.022, auction +0.022 / -0.019 | off: H9 slightly down | **in**: bonus -0.010 / -0.002, mirror **+0.070 UP**; auction -0.000 / -0.007, mirror **+0.062 UP** |
| swap (6%) | **in**: swap_holdem generic **+0.042 UP**, realistic +0.030; swap_one_turn **+0.045 UP**, +0.007 | in: +0.028 / +0.015, +0.023 / +0.014 | off: H9 slightly down | out: -0.006 / +0.007, -0.021 / -0.011, no mirror cell |
| exposed (4%) | **in**: generic **+0.031 UP**, realistic +0.002 | in: +0.004 / +0.016 | n/a (Hero plays the table) | n/a (Hero's opens read the exposed cards) |

Nothing is beyond noise down anywhere. Intervals: about ±0.015-0.03 for the size read and the route, ±0.05-0.09 for
S11's one size.

**Recommended (on top of the batch-5 gains D3, Z3 and strong_route as gated today):**

    {"hero.postflop.size_read_twists": "discard,bounty,knockout,swap,exposed",
     "hero.postflop.s11_twists": "knockout,buy,swap,exposed",
     "strong_route_twists": "bounty,knockout,buy"}

`r3.v3_bvb_twists` stays "" (hold'em only). The size read and S11 lists were measured together (section 4: nothing
down, mean +0.039 where both reach); the strong route's list alone (sections 2 and 3). Confidence, highest first: the
size read (four UP cells, the rest level, the smallest intervals); the strong route (gains at strong tables under all
four twists measured, level elsewhere, as on hold'em); S11's list lowest (no cell up, wide intervals: it is
exploit-resistance insurance, and nothing here holds an exploiter). If a held-out run shows anything down, drop
`s11_twists` first.

Weighted by variants-ranked.md, the size read alone now plays on about 41% of the twist mass (all of the five
families but buy), the strong route on about 18% (bounty, knockout, buy), S11 on about 20%.

**On the night:** these dials do nothing until the gains themselves are in the ship (batch 5). The family test reads
Rules only: a twist written as tonight's own file reaches a family when its extras use that family's keys (any variant
name except another family's catalog entry); otherwise every gate stays shut, as today. `python -c "from
hyperion.strategy.hero import twist_family; ..."` on tonight's Rules says which.

## 8. Left off, and why

- **S11's blind-vs-blind prior on any twist** (`r3.v3_bvb_twists`, built, off): H9 measured it slightly down on
  bounty, swap_holdem, bonus_card and auction; a 200-seed screen cannot clear an effect that size. Next: 400 held-out
  seeds on those four entries, if anyone wants it.
- **The size read on buy**: its auction cells lean down (-0.014, -0.035) and bonus_card gives nothing. Untested idea:
  skip the read while I hold the bought card too (the bettor bets into a visible three-card hand).
- **S11 on discard and bounty**: both lean down (toss -0.018 / -0.023 / -0.006; bounty -0.017 / -0.001 / -0.007).
- **The strong route on swap**: its four cells lean down and its mirror cells were dropped for time.
- **The strong route on discard and exposed**: structurally out (elite1 cannot hold three cards; on exposed tables
  Hero's opens read the exposed cards and elite1 sees none). Their sections stay F's own (the base's fallback Hero).
- Not measured: the three dials together on the twist cells (the route's list was decided after section 4 ran), the
  `mirror` field under swap, any held-out set (screens only, as asked), the exploit fields under a twist.

## 9. Tests

- tests/test_vf_twists.py (16): the family of every catalog entry; unknown family names fail; dials off keep every
  gain hold'em-only; each dial reaches only its families (the hero member and the base's fallback Hero); the BvB dial
  reaches rival 3's core; elite1 may play only where the core plays the table; the twist read skips a buyer, a bettor
  whose bounty shows, a knockout shove, and nothing on discard, swap or exposed; each gain gated to hold'em plays every
  family's entry exactly as F (with the hooks).
- Full suite at 3898128 (+ docs/packet/CONTRACTS.md regenerated for the new dials, `tools/apicard.py`; it also picks up
  ffb1e62's `r3.v3_bvb_holdem_only`, which main left stale), load 7-10, 6:54: **1239 passed, 2 failed, 1 skipped**.
  The two: test_apicard (CONTRACTS.md stale, fixed by the regeneration) and test_gate's history-dropping package
  (a known load failure); both pass alone.

Runs: detached worktree goal/wt_vf_m at 84d22e8 (the dials; the later commit only widens the variant-name check, which
no catalog entry reaches), cache under its scratch/climb, specs and outputs in goal/vf_runs.
