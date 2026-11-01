# Composite bot: running log

The compose phase (HANDOFF, 13:45): for each section of the game, find whether another bot's decisions beat the base's
(hybrid3_x: rival 3's core + the exploit layer behind Hero's shell), combine the winners, then a guarded hill climb.
Ship only if the composite beats hybrid3_x beyond noise on night and realistic and is not worse on any judge field.
Summary goes to docs/decisions.md, "Composite bot".

## 14:10 ET: the sections (hyperion/compose/sections.py)

Twelve sections, read from the Observation alone in about 1 us (0.87-1.0 us per call on this box, best of five passes
over 20,000 recorded decisions). Axes in the order they are read:

- **street:** preflop is 78% of hybrid3_x's decisions on realistic, and in a 200-hand turbo from 100 bb most of the points
  move there (opens, steals, re-shoves, calling all-ins under ICM).
- **postflop:** by players in the hand. Multiway (3+) is 2-4% of decisions, so it is one section; a heads-up pot splits
  on whether we face a bet, because the exploit layer's bet-when-checked-to acts only when nothing is to call.
- **alive, preflop:** heads-up (2 alive) and three-handed (3) are their own sections: ICM and ranges change most there.
- **what we face, preflop:** unopened (blinds and limps), a raise we can re-raise, or an all-in (the raiser is all-in,
  calling costs my stack, or no raise is legal).
- **effective stack** (min of my chips and the biggest other stack still in the hand, this street's bets included):
  < 10 / 10-20 / 20-40 / 40+ bb for unopened pots, < 20 / 20+ facing a raise.

Shares of hybrid3_x's decisions, model mode, 50 seeds x 8, in Hero's seat (%):

| # | section | realistic | top | strong |
|---|---|---|---|---|
| 0 | pre_open_40 | 23.4 | 19.2 | 20.0 |
| 1 | pre_open_20 | 8.8 | 8.8 | 9.6 |
| 2 | pre_open_10 | 4.4 | 6.8 | 8.2 |
| 3 | pre_open_short | 1.3 | 3.1 | 3.6 |
| 4 | pre_raised_deep | 18.5 | 23.6 | 22.6 |
| 5 | pre_raised_short | 2.8 | 6.2 | 6.5 |
| 6 | pre_allin | 3.1 | 6.6 | 5.4 |
| 7 | pre_3way | 8.7 | 4.8 | 4.6 |
| 8 | pre_hu | 6.9 | 3.2 | 3.5 |
| 9 | post_hu_bet | 6.2 | 4.9 | 5.2 |
| 10 | post_hu_chk | 12.1 | 9.7 | 9.1 |
| 11 | post_mw | 3.7 | 2.9 | 1.8 |

Every section holds at least 1.3% of decisions on every field. Decision share is not points share: a section's weight in
the swap matrix shows up as the size of its paired delta. Tests: tests/test_compose_sections.py.
