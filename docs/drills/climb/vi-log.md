# V-i: twist decisions priced as value of information, and the showdown tax read (2026-11-03)

Branch climb/vi-twist-value, from main eecf4d8. Item 14 of docs/research/Edges against strong opponents.md
(competitions §5: value the twist's decision as an EV difference by quick simulation, scale by a fudge factor; GTO
Wizard's MIT 2024 auction entry bid the 3v2 - 2v3 equity difference x 1.8, the best of 0.5-2.5x). Seeds: the screen set
(10000-10199) for every measurement, my own for diagnostics (777 / 50000+ / 2026). No held-out set, judge bot or
held-out variant was run, read or tuned on. Host shared (load 14-18 of 8 cores): `nice -n 5`, at most three worker
processes. Scratch scripts: the session scratchpad, `goal/vi_work/scripts/`.

## Plan, fixed before measuring

- The multiplier `hero.voi` takes three values, fixed now: **0.67, 1.0, 1.5**. At 1.0 the auction bids the
  indifference price, which is F's bid today (d x pot_eff / (1 - d) already prices the dead money the price feeds and
  the betting to come, so it sits at about 1.4-1.7x GTO Wizard's raw equity difference; their best 1.8 is about our
  1.1, their 0.5-2.5 about our 0.3-1.5). No value outside these three is run.
- The multiplier only moves decisions that have a price against them (bid, buy). Keep, discard and swap take the
  option worth most, whatever the multiplier; so the three values are measured on the auction and bonus_card cells,
  the other aware cells once (they play the same at any value).
- The showdown tax's gate margin is fixed now at 0.05 (every catalog twist with hold'em's payoff measures 0.4996-0.5015;
  the Ghost 0.342, bounty 0.569), and its tiers come from a formula (1 / (2f) - 1/2 of TIER_EQUITY above the value
  tier), not a sweep.
