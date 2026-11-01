# Skill profile: what each bot is best at, section by section

The owner asked to see what each bot is good at, not just one score. Every bot sat in Hero's seat of the same
duplicate deals against the same opponents (`<field>@<bot>`, seed 7, all eight rotations, mode `model`, fixed-speed so
every run replays exactly). Each of its decisions was booked to one of the compose agent's twelve sections of the game
(hyperion/compose/sections.py). Tool: `python tools/skill_profile.py run|report`; the module doc has every
definition. Code at `00efa2c`, `night` at 200 seeds and `realistic` at 100.

**How to read it.**
- **bb/dec** is chips won per decision, in big blinds of the hand. A hand's net result is split over the decisions
  that put chips into it, in proportion to the chips each put in, and the posted blinds take the rest. Folds and
  checks score 0, so a section's figure is "what the chips this bot put in here earned". Compare bots within a section,
  not sections with each other: pots are won after the flop, so the postflop sections collect most of the winnings.
- **±** is a 95% interval with the seed as the unit. A gap inside it is noise.
- **This is descriptive, not causal.** Each bot reaches different spots. A tight opener sees fewer flops, and a bot
  that loses chips early lives in the short-stack sections. "Best at short-stack play" means its decisions there earned
  the most chips per decision in the spots it reached. Whether another bot's play in a section would help ours is
  answered by the compose agent's swap test (docs/drills/compose-log.md), which replaces one section's decisions on the
  same deals.
- **Tuning caveat.** Hero was tuned against rival 1, rival 2 and most of the bestiary (tag, pushfold, loose_aggro,
  the Monte Carlo and timeout bots). Rival 3 was its holdout until the core comparison. The hybrids carry Hero's shell
  and its exploit layer, which was screened against the same bestiary. Nobody tuned anything on the persona bots
  (agent_*), the Track B bots (trackb3, trackb5) or the judges (rivals 4 and 5). So on `night`, about 40% of the
  opponent seats are untuned for every candidate, and the rest favour Hero's tuning set.
- **Groups** in the summary lists: *deep preflop* covers opening at 20+ bb and facing a raise at 20+ bb. *Short stack*
  covers opening under 20 bb, facing a raise under 20 bb, and facing an all-in. *Endgame* covers three-handed and
  heads-up preflop. *After the flop* covers every postflop section.

## Headline

**Points on `night`** (uniform 4.50; each bot in Hero's seat, the same 200 deals):
1. Hero 5.75
2. hybrid3_x 5.75
3. hybrid_x 5.60
4. rival3 5.54
5. rival2 5.47
6. rival1 5.41
7. agent_pushfold 5.28
8. trackb3 5.11
9. trackb5 5.10
10. agent_charts 4.94
11. agent_default 4.75
12. agent_montecarlo 4.29

**On `realistic`** (100 deals):
1. hybrid3_x 6.09
2. Hero 5.98
3. rival3 5.91
4. rival1 5.80
5. hybrid_x 5.71
6. rival2 5.41
7. trackb5 5.39
8. agent_pushfold 5.28
9. trackb3 5.27
10. agent_charts 5.21
11. agent_default 5.07
12. agent_montecarlo 4.31

**Best at, on `night`** (chips won per decision; the full lists with intervals are below):
- *Deep preflop:* 1. hybrid3_x, 2. agent_montecarlo, 3. hybrid_x. Hero is 10th of 12.
- *Short stack:* 1. rival1, 2. agent_montecarlo (wide interval), 3. rival2, 4. hybrid_x. Hero is 7th.
- *Endgame:* 1. hybrid3_x, 2. rival1, 3. rival3, 4. Hero.
- *After the flop:* 1. rival2, 2. hybrid_x, 3. agent_pushfold. Hero is 6th.

**Each bot's firsts and lasts on `night`** (sections where it ranks 1st or last of 12):
- Hero:
  - first: opening at 10-20 bb, heads-up preflop;
  - last: facing a raise at 20+ bb, facing an all-in.
- hybrid3_x:
  - first: opening deep (40+ bb), opening at 20-40 bb, three-handed preflop;
  - last: none.
- hybrid_x: first heads-up postflop facing a bet.
- rival2: first in three sections: facing a raise under 20 bb, heads-up postflop with nothing to call, and multiway
  postflop.
- rival1: first at push or fold under 10 bb; last in multiway pots.
- agent_pushfold: first facing a raise at 20+ bb.
- agent_montecarlo:
  - first facing an all-in (its equity calls, wide interval);
  - last heads-up postflop facing a bet: −1.9 bb a decision, it calls too much.
- agent_default: last in four sections (both opening bands at 10-40 bb, three-handed, heads-up postflop checked to).

**The plainest leak:** Hero facing a raise with 20+ bb. It is last on both fields: −0.11 ± 0.05 bb a decision on
`night` and −0.17 on `realistic`, in 17-19% of its decisions. hybrid3_x is at +0.02 there, and agent_pushfold
leads at +0.13. Whether swapping that section helps is the compose agent's question.

## Where the points come from on the night fields (Hero, hybrid3_x, hybrid_x)

On `night`, hybrid3_x ties Hero (−0.01 ± 0.12 points, paired, 200 seeds). On `night_hard` it is behind beyond noise
(**−0.17 ± 0.13**). On `realistic` it is ahead (+0.11 ± 0.18 here; +0.10 ± 0.09 in the final comparison at 400 seeds).

To see which opponents cause that, each hand's net chips for the bot in Hero's seat were split over the opponents on
the other side: a win goes to the seats that lost chips in the hand, pro rata to their losses; a loss goes to the
seats that gained, pro rata to their gains. The figures are bb won per table from each group, summed over its seats,
from the same deals (scratch script, exact to the profile's points seed for seed).

`night` (seats a table: agent builds 2.83, weak or broken 2.11, decent 1.01, strong 1.05):

| from | Hero | hybrid3_x | hybrid_x | hybrid3_x − Hero | hybrid_x − Hero |
|---|---|---|---|---|---|
| one-hour agent builds | +15.0 | +12.0 | +12.1 | **−3.0 ± 2.4** | **−2.9 ± 2.4** |
| weak or broken | +15.2 | +18.4 | +17.7 | **+3.2 ± 2.7** | +2.5 ± 2.7 |
| decent | +6.0 | +5.6 | +5.0 | −0.4 ± 1.5 | −1.0 ± 1.4 |
| strong teams (rivals 1-3) | +0.6 | +2.0 | +2.0 | +1.4 ± 1.7 | +1.4 ± 1.7 |
| all | +36.8 | +37.9 | +36.7 | | |

`night_hard` (seats a table: agent builds 3.26, weak or broken 0.74, decent 1.08, strong 1.92):

| from | Hero | hybrid3_x | hybrid_x | hybrid3_x − Hero | hybrid_x − Hero |
|---|---|---|---|---|---|
| one-hour agent builds | +14.6 | +12.2 | +12.7 | −2.4 ± 2.8 | −1.9 ± 2.7 |
| weak or broken | +6.1 | +4.6 | +7.3 | −1.5 ± 1.3 | +1.2 ± 1.5 |
| decent | +5.7 | +6.1 | +5.0 | +0.4 ± 1.3 | −0.8 ± 1.3 |
| strong teams (rivals 1-3) | +1.7 | −3.2 | +1.2 | **−4.9 ± 2.0** | −0.5 ± 1.9 |
| all | +28.1 | +19.7 | +26.1 | | |

Per strong bot on `night_hard`, hybrid3_x − Hero at the tables where each one sits: rival1 −2.4 ± 1.8, rival2
−2.9 ± 1.7, rival3 −2.3 ± 1.6 bb a table. On `night` the same three are +0.8, +2.0 and +1.0, all inside noise.

Points by the number of strong seats at the table (hybrid3_x − Hero, paired):

| strong seats | `night` tables | `night` | `night_hard` tables | `night_hard` |
|---|---|---|---|---|
| 0 | 68 | −0.23 ± 0.22 | 21 | −0.15 ± 0.31 |
| 1 | 70 | −0.01 ± 0.18 | 44 | −0.30 ± 0.33 |
| 2 | 45 | +0.30 ± 0.26 | 66 | −0.17 ± 0.22 |
| 3 | 17 | +0.07 ± 0.53 | 69 | −0.09 ± 0.21 |

What it says:
1. **On `night`, Hero and hybrid3_x get their chips from different seats.** hybrid3_x takes about 3 bb a table more
   from the broken bots, mostly the two Monte Carlo bots (+3.6, +3.4). Hero takes about 3 bb a table more from the
   one-hour agent builds, mostly trackb3 (−2.8 ± 1.6). The two cancel. hybrid_x has the same pattern.
2. **On `night_hard`, hybrid3_x's gap comes from the strong teams, and from all three equally.** It is not a rival 1
   and 2 effect: Hero was tuned against those two but never against rival 3, and hybrid3_x gives up as much to rival 3
   (whose core it runs) as to rivals 1 and 2. Against the persona and Track B bots, which nobody tuned on, the gap is
   −2.4 ± 2.8, inside noise. Split by strong seats, the points gap shows up in every bucket, so no single table type
   explains it.
3. **hybrid_x keeps up in the strong rooms.** It is level with Hero on `night_hard` (−0.01) and ahead at tables with all
   three rivals (+0.27 ± 0.22). That is the final comparison's pattern again: rival 2's core is the strong-room bot.
   It is behind on `night` (−0.16 ± 0.12) and `realistic`.
4. **Chips are not points.** The flow is chip EV. Points also depend on when chips move (ICM), so the two tables need
   not add up the same way. Here they point the same direction.

## The owner's other bot (numbers only)

It was played as a black box from a snapshot (dist md5 `07f2f6ed`), in Hero's seat of the same deals, through the
sealed grader's adapter. Its own clock guard reads the wall clock, and these runs were at load 35-60, so its numbers
lean pessimistic. It does not enter the repo; its full profile is in the session scratchpad.
- Points: `night` 4.86 ± 0.12 (11th of 13; Hero − it +0.90 ± 0.14); `realistic` 4.85 ± 0.16 (12th of 13).
- Group ranks on `night` (of 13): deep preflop 10th, short stack 7th, endgame 8th, after the flop 11th.
- Its best section on `night` is facing an all-in, where it is 3rd (+0.60 ± 0.28 bb a decision). Its weakest is
  heads-up postflop facing a bet (−0.60 ± 0.19), and it is last at push or fold.

## Full profile, `night`: 200 seeds x 8 rotations, mode model, seed 7

Overall, by points (uniform 4.50):

1. **hero** 5.75 ± 0.11 (1st 36%, bust 60%)
2. **hybrid3_x** 5.75 ± 0.12 (1st 36%, bust 61%)
3. **hybrid_x** 5.60 ± 0.11 (1st 32%, bust 65%)
4. **rival3** 5.54 ± 0.12 (1st 32%, bust 66%)
5. **rival2** 5.47 ± 0.11 (1st 25%, bust 69%)
6. **rival1** 5.41 ± 0.11 (1st 27%, bust 67%)
7. **agent_pushfold** 5.28 ± 0.10 (1st 19%, bust 73%)
8. **trackb3** 5.11 ± 0.10 (1st 11%, bust 79%)
9. **trackb5** 5.10 ± 0.11 (1st 11%, bust 78%)
10. **agent_charts** 4.94 ± 0.12 (1st 16%, bust 80%)
11. **agent_default** 4.75 ± 0.11 (1st 12%, bust 83%)
12. **agent_montecarlo** 4.29 ± 0.12 (1st 15%, bust 83%)

Best at, by chips won per decision (bb) in the spots each bot reached, ± 95% (the seed is the unit):

- **deep preflop play**: 1. hybrid3_x +0.127 ± 0.021, 2. agent_montecarlo +0.116 ± 0.026, 3. hybrid_x +0.112 ± 0.019, 4. agent_pushfold +0.109 ± 0.029, 5. rival3 +0.105 ± 0.020, 6. agent_charts +0.095 ± 0.015, 7. agent_default +0.089 ± 0.019, 8. rival2 +0.088 ± 0.019, 9. rival1 +0.070 ± 0.016, 10. hero +0.054 ± 0.022, 11. trackb5 +0.049 ± 0.014, 12. trackb3 +0.047 ± 0.014
- **short-stack play**: 1. rival1 +0.369 ± 0.058, 2. agent_montecarlo +0.350 ± 0.143, 3. rival2 +0.349 ± 0.061, 4. hybrid_x +0.335 ± 0.053, 5. rival3 +0.277 ± 0.050, 6. hybrid3_x +0.275 ± 0.043, 7. hero +0.261 ± 0.038, 8. trackb3 +0.257 ± 0.056, 9. trackb5 +0.255 ± 0.060, 10. agent_pushfold +0.232 ± 0.038, 11. agent_default +0.212 ± 0.093, 12. agent_charts +0.212 ± 0.075
- **endgame (three-handed and heads-up preflop)**: 1. hybrid3_x +0.303 ± 0.038, 2. rival1 +0.284 ± 0.030, 3. rival3 +0.274 ± 0.039, 4. hero +0.273 ± 0.032, 5. hybrid_x +0.267 ± 0.030, 6. rival2 +0.249 ± 0.026, 7. agent_pushfold +0.241 ± 0.033, 8. agent_montecarlo +0.166 ± 0.036, 9. trackb5 +0.157 ± 0.023, 10. agent_default +0.139 ± 0.035, 11. agent_charts +0.132 ± 0.026, 12. trackb3 +0.115 ± 0.024
- **play after the flop**: 1. rival2 +0.964 ± 0.097, 2. hybrid_x +0.962 ± 0.106, 3. agent_pushfold +0.789 ± 0.087, 4. hybrid3_x +0.711 ± 0.083, 5. rival3 +0.701 ± 0.083, 6. hero +0.690 ± 0.064, 7. trackb3 +0.677 ± 0.091, 8. trackb5 +0.668 ± 0.094, 9. rival1 +0.629 ± 0.078, 10. agent_charts +0.545 ± 0.086, 11. agent_default +0.379 ± 0.100, 12. agent_montecarlo +0.101 ± 0.089

Per section (bb per decision ± 95%; the bot's share of its decisions in brackets):

- *opening deep (unopened pot, 40+ bb)* (`pre_open_40`): 1. hybrid3_x +0.165 ± 0.014 (20%), 2. rival3 +0.162 ± 0.014 (21%), 3. rival1 +0.146 ± 0.012 (20%), 4. agent_montecarlo +0.130 ± 0.013 (22%), 5. hero +0.125 ± 0.017 (19%), 6. hybrid_x +0.121 ± 0.016 (22%), 7. rival2 +0.101 ± 0.017 (22%), 8. agent_charts +0.100 ± 0.010 (22%), 9. agent_default +0.095 ± 0.009 (22%), 10. agent_pushfold +0.073 ± 0.014 (22%), 11. trackb3 +0.064 ± 0.013 (21%), 12. trackb5 +0.062 ± 0.014 (21%)
- *opening at 20-40 bb* (`pre_open_20`): 1. hybrid3_x +0.312 ± 0.026 (8%), 2. hero +0.289 ± 0.023 (7%), 3. rival3 +0.282 ± 0.025 (8%), 4. rival1 +0.229 ± 0.017 (8%), 5. hybrid_x +0.210 ± 0.021 (8%), 6. agent_charts +0.175 ± 0.012 (9%), 7. agent_montecarlo +0.175 ± 0.021 (6%), 8. rival2 +0.168 ± 0.019 (8%), 9. agent_pushfold +0.156 ± 0.019 (9%), 10. trackb5 +0.154 ± 0.020 (9%), 11. trackb3 +0.146 ± 0.016 (9%), 12. agent_default +0.121 ± 0.012 (8%)
- *opening at 10-20 bb* (`pre_open_10`): 1. hero +0.261 ± 0.034 (4%), 2. hybrid_x +0.255 ± 0.045 (4%), 3. rival3 +0.246 ± 0.038 (4%), 4. hybrid3_x +0.245 ± 0.038 (4%), 5. rival1 +0.230 ± 0.033 (4%), 6. agent_pushfold +0.216 ± 0.041 (5%), 7. agent_charts +0.208 ± 0.042 (4%), 8. agent_montecarlo +0.194 ± 0.055 (2%), 9. trackb3 +0.187 ± 0.032 (5%), 10. rival2 +0.176 ± 0.035 (4%), 11. trackb5 +0.164 ± 0.035 (6%), 12. agent_default +0.119 ± 0.014 (5%)
- *push or fold (unopened, under 10 bb)* (`pre_open_short`): 1. rival1 +0.500 ± 0.137 (1%), 2. agent_charts +0.377 ± 0.112 (1%), 3. agent_montecarlo +0.364 ± 0.142 (1%), 4. agent_pushfold +0.344 ± 0.080 (1%), 5. trackb3 +0.332 ± 0.090 (1%), 6. agent_default +0.319 ± 0.077 (2%), 7. hybrid_x +0.310 ± 0.068 (1%), 8. rival3 +0.307 ± 0.095 (1%), 9. hybrid3_x +0.302 ± 0.077 (1%), 10. trackb5 +0.287 ± 0.072 (2%), 11. hero +0.272 ± 0.061 (1%), 12. rival2 +0.213 ± 0.066 (1%)
- *facing a raise, 20+ bb* (`pre_raised_deep`): 1. agent_pushfold +0.127 ± 0.066 (22%), 2. agent_montecarlo +0.084 ± 0.060 (21%), 3. agent_default +0.069 ± 0.044 (22%), 4. hybrid_x +0.065 ± 0.043 (22%), 5. agent_charts +0.059 ± 0.033 (22%), 6. rival2 +0.044 ± 0.042 (22%), 7. hybrid3_x +0.018 ± 0.042 (20%), 8. trackb5 -0.003 ± 0.026 (22%), 9. trackb3 -0.009 ± 0.028 (22%), 10. rival3 -0.019 ± 0.040 (21%), 11. rival1 -0.070 ± 0.035 (20%), 12. hero -0.110 ± 0.045 (19%)
- *facing a raise under 20 bb (re-shove or fold)* (`pre_raised_short`): 1. rival2 +0.481 ± 0.082 (3%), 2. hybrid_x +0.360 ± 0.101 (3%), 3. rival1 +0.324 ± 0.067 (3%), 4. hero +0.256 ± 0.054 (3%), 5. hybrid3_x +0.203 ± 0.089 (3%), 6. rival3 +0.181 ± 0.094 (3%), 7. agent_pushfold +0.155 ± 0.046 (4%), 8. agent_default +0.098 ± 0.029 (5%), 9. trackb3 +0.093 ± 0.030 (5%), 10. trackb5 +0.052 ± 0.020 (5%), 11. agent_montecarlo +0.037 ± 0.079 (2%), 12. agent_charts -0.092 ± 0.050 (3%)
- *facing an all-in* (`pre_allin`): 1. agent_montecarlo +0.725 ± 0.407 (3%), 2. trackb5 +0.610 ± 0.228 (4%), 3. rival1 +0.550 ± 0.182 (3%), 4. trackb3 +0.544 ± 0.218 (4%), 5. agent_charts +0.520 ± 0.276 (3%), 6. agent_default +0.469 ± 0.418 (3%), 7. rival2 +0.455 ± 0.179 (4%), 8. hybrid_x +0.397 ± 0.143 (4%), 9. rival3 +0.375 ± 0.128 (4%), 10. hybrid3_x +0.351 ± 0.104 (4%), 11. agent_pushfold +0.314 ± 0.137 (4%), 12. hero +0.261 ± 0.106 (4%)
- *three-handed preflop* (`pre_3way`): 1. hybrid3_x +0.325 ± 0.033 (7%), 2. rival1 +0.298 ± 0.029 (8%), 3. hybrid_x +0.298 ± 0.037 (8%), 4. rival3 +0.287 ± 0.034 (7%), 5. rival2 +0.277 ± 0.033 (8%), 6. agent_pushfold +0.262 ± 0.045 (8%), 7. hero +0.254 ± 0.029 (7%), 8. agent_montecarlo +0.171 ± 0.034 (6%), 9. trackb5 +0.170 ± 0.025 (8%), 10. agent_charts +0.148 ± 0.031 (7%), 11. trackb3 +0.148 ± 0.022 (8%), 12. agent_default +0.133 ± 0.018 (7%)
- *heads-up preflop* (`pre_hu`): 1. hero +0.295 ± 0.065 (6%), 2. hybrid3_x +0.278 ± 0.064 (7%), 3. rival1 +0.267 ± 0.060 (6%), 4. rival3 +0.259 ± 0.073 (6%), 5. hybrid_x +0.229 ± 0.052 (7%), 6. agent_pushfold +0.214 ± 0.047 (6%), 7. rival2 +0.213 ± 0.042 (6%), 8. agent_montecarlo +0.160 ± 0.065 (5%), 9. agent_default +0.150 ± 0.089 (4%), 10. trackb5 +0.137 ± 0.044 (5%), 11. agent_charts +0.112 ± 0.043 (6%), 12. trackb3 +0.057 ± 0.056 (5%)
- *heads-up pot after the flop, facing a bet* (`post_hu_bet`): 1. hybrid_x +0.748 ± 0.294 (5%), 2. agent_pushfold +0.728 ± 0.201 (4%), 3. rival2 +0.690 ± 0.286 (5%), 4. hero +0.445 ± 0.144 (7%), 5. rival3 +0.203 ± 0.204 (6%), 6. hybrid3_x +0.154 ± 0.204 (6%), 7. rival1 +0.066 ± 0.198 (6%), 8. trackb3 +0.062 ± 0.188 (5%), 9. trackb5 +0.017 ± 0.203 (5%), 10. agent_charts -0.087 ± 0.213 (6%), 11. agent_default -0.615 ± 0.215 (5%), 12. agent_montecarlo -1.907 ± 0.275 (8%)
- *heads-up pot after the flop, nothing to call* (`post_hu_chk`): 1. rival2 +1.090 ± 0.100 (13%), 2. hybrid_x +1.058 ± 0.099 (13%), 3. rival1 +0.932 ± 0.074 (15%), 4. hybrid3_x +0.920 ± 0.074 (15%), 5. trackb5 +0.891 ± 0.083 (12%), 6. rival3 +0.886 ± 0.071 (16%), 7. trackb3 +0.884 ± 0.084 (12%), 8. agent_pushfold +0.834 ± 0.082 (12%), 9. agent_charts +0.789 ± 0.065 (14%), 10. hero +0.782 ± 0.049 (17%), 11. agent_montecarlo +0.756 ± 0.072 (20%), 12. agent_default +0.725 ± 0.089 (13%)
- *multiway pot after the flop* (`post_mw`): 1. rival2 +0.904 ± 0.254 (3%), 2. hybrid_x +0.903 ± 0.242 (3%), 3. trackb3 +0.836 ± 0.336 (3%), 4. trackb5 +0.815 ± 0.389 (2%), 5. agent_montecarlo +0.778 ± 0.269 (4%), 6. rival3 +0.756 ± 0.285 (3%), 7. hybrid3_x +0.722 ± 0.287 (3%), 8. hero +0.709 ± 0.183 (5%), 9. agent_pushfold +0.685 ± 0.294 (2%), 10. agent_charts +0.676 ± 0.280 (3%), 11. agent_default +0.590 ± 0.346 (3%), 12. rival1 +0.457 ± 0.181 (5%)

Where the busts come from (the section of the last decision that put chips in, top three):

- hero: pre_allin 24%, pre_raised_short 17%, post_hu_bet 13%
- hybrid3_x: pre_raised_short 29%, post_hu_bet 17%, pre_3way 13%
- hybrid_x: pre_raised_short 22%, post_hu_bet 20%, pre_hu 14%
- rival3: pre_raised_short 30%, post_hu_bet 17%, pre_3way 10%
- rival2: post_hu_bet 20%, pre_raised_short 18%, pre_hu 13%
- rival1: post_hu_bet 22%, pre_raised_short 15%, pre_open_short 14%
- agent_pushfold: pre_3way 17%, pre_open_short 16%, pre_raised_deep 14%
- trackb3: pre_open_short 20%, post_hu_bet 15%, pre_allin 14%
- trackb5: pre_open_short 28%, pre_3way 15%, post_hu_bet 14%
- agent_charts: post_hu_bet 36%, pre_open_short 13%, pre_allin 10%
- agent_default: pre_allin 38%, post_hu_bet 15%, pre_open_short 13%
- agent_montecarlo: post_hu_bet 36%, post_hu_chk 13%, pre_allin 11%

Finish distribution (% of seats, 1st .. 8th):

| bot | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | bust |
|---|---|---|---|---|---|---|---|---|---|
| hero | 36 | 12 | 11 | 12 | 10 | 9 | 7 | 4 | 60 |
| hybrid3_x | 36 | 10 | 11 | 12 | 10 | 9 | 6 | 4 | 61 |
| hybrid_x | 32 | 14 | 10 | 11 | 12 | 10 | 8 | 4 | 65 |
| rival3 | 32 | 11 | 11 | 11 | 13 | 11 | 7 | 4 | 66 |
| rival2 | 25 | 17 | 13 | 12 | 11 | 10 | 8 | 5 | 69 |
| rival1 | 27 | 14 | 11 | 12 | 11 | 11 | 8 | 5 | 67 |
| agent_pushfold | 19 | 16 | 15 | 14 | 12 | 10 | 8 | 5 | 73 |
| trackb3 | 11 | 19 | 17 | 16 | 13 | 12 | 9 | 4 | 79 |
| trackb5 | 11 | 18 | 17 | 16 | 14 | 11 | 9 | 4 | 78 |
| agent_charts | 16 | 11 | 15 | 14 | 14 | 13 | 10 | 5 | 80 |
| agent_default | 12 | 12 | 15 | 14 | 15 | 13 | 12 | 6 | 83 |
| agent_montecarlo | 15 | 8 | 10 | 10 | 14 | 17 | 16 | 11 | 83 |

<details><summary>hero: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 19% | 41% | 40% | 25.13 | 0% | +0.125 | 71% | 0 |
| pre_open_20 | 7% | 56% | 55% | 52.08 | 0% | +0.289 | 66% | 0 |
| pre_open_10 | 4% | 61% | 60% | 192.37 | 0% | +0.261 | 71% | 0 |
| pre_open_short | 1% | 35% | 34% | 33.80 | 25% | +0.272 | 48% | 79 |
| pre_raised_deep | 19% | 32% | 4% | 0.15 | 1% | -0.110 | 52% | 85 |
| pre_raised_short | 3% | 20% | 13% | 1.96 | 13% | +0.256 | 48% | 168 |
| pre_allin | 4% | 17% | 0% | 0.00 | 4% | +0.261 | 51% | 227 |
| pre_3way | 7% | 49% | 42% | 5.64 | 8% | +0.254 | 49% | 76 |
| pre_hu | 6% | 67% | 60% | 9.34 | 12% | +0.295 | 46% | 109 |
| post_hu_bet | 7% | 31% | 2% | 0.08 | 3% | +0.445 | 59% | 121 |
| post_hu_chk | 17% | 48% | 48% | inf | 1% | +0.782 | 58% | 67 |
| post_mw | 5% | 23% | 19% | 3.91 | 1% | +0.709 | 38% | 26 |
| blinds | - | - | - | - | - | -24466 total | 48% | 7 |

288815 decisions; net +58833 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 274 us.
</details>

<details><summary>hybrid3_x: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 20% | 40% | 38% | 22.36 | 0% | +0.165 | 62% | 0 |
| pre_open_20 | 8% | 62% | 62% | 290.22 | 0% | +0.312 | 68% | 0 |
| pre_open_10 | 4% | 70% | 70% | inf | 0% | +0.245 | 74% | 0 |
| pre_open_short | 1% | 44% | 43% | 46.36 | 40% | +0.302 | 48% | 93 |
| pre_raised_deep | 20% | 22% | 6% | 0.34 | 1% | +0.018 | 53% | 55 |
| pre_raised_short | 3% | 28% | 23% | 4.75 | 23% | +0.203 | 39% | 280 |
| pre_allin | 4% | 12% | 0% | 0.02 | 2% | +0.351 | 57% | 51 |
| pre_3way | 7% | 71% | 65% | 10.53 | 10% | +0.325 | 45% | 127 |
| pre_hu | 7% | 75% | 67% | 8.17 | 14% | +0.278 | 44% | 101 |
| post_hu_bet | 6% | 40% | 5% | 0.14 | 4% | +0.154 | 44% | 169 |
| post_hu_chk | 15% | 55% | 55% | inf | 2% | +0.920 | 53% | 80 |
| post_mw | 3% | 25% | 20% | 3.72 | 1% | +0.722 | 48% | 11 |
| blinds | - | - | - | - | - | -21247 total | 46% | 6 |

264517 decisions; net +60691 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 1275 us.
</details>

<details><summary>hybrid_x: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 33% | 31% | 14.06 | 0% | +0.121 | 68% | 3 |
| pre_open_20 | 8% | 40% | 39% | 51.51 | 0% | +0.210 | 65% | 3 |
| pre_open_10 | 4% | 42% | 41% | 65.42 | 10% | +0.255 | 56% | 36 |
| pre_open_short | 1% | 44% | 43% | 32.18 | 27% | +0.310 | 51% | 74 |
| pre_raised_deep | 22% | 21% | 7% | 0.51 | 2% | +0.065 | 54% | 106 |
| pre_raised_short | 3% | 29% | 26% | 9.23 | 26% | +0.360 | 40% | 227 |
| pre_allin | 4% | 11% | 0% | 0.00 | 2% | +0.397 | 58% | 61 |
| pre_3way | 8% | 48% | 42% | 7.14 | 11% | +0.298 | 48% | 108 |
| pre_hu | 7% | 61% | 52% | 5.79 | 16% | +0.229 | 45% | 145 |
| post_hu_bet | 5% | 41% | 8% | 0.23 | 6% | +0.748 | 54% | 206 |
| post_hu_chk | 13% | 58% | 58% | inf | 2% | +1.058 | 50% | 62 |
| post_mw | 3% | 17% | 12% | 2.15 | 1% | +0.903 | 44% | 10 |
| blinds | - | - | - | - | - | -24727 total | 49% | 5 |

245783 decisions; net +58731 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 3093 us.
</details>

<details><summary>rival3: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 21% | 39% | 38% | 22.31 | 0% | +0.162 | 71% | 0 |
| pre_open_20 | 8% | 60% | 60% | 280.30 | 0% | +0.282 | 68% | 0 |
| pre_open_10 | 4% | 67% | 67% | inf | 0% | +0.246 | 74% | 1 |
| pre_open_short | 1% | 45% | 44% | 80.38 | 44% | +0.307 | 46% | 85 |
| pre_raised_deep | 21% | 23% | 6% | 0.34 | 1% | -0.019 | 51% | 77 |
| pre_raised_short | 3% | 31% | 26% | 5.52 | 26% | +0.181 | 36% | 314 |
| pre_allin | 4% | 13% | 0% | 0.02 | 2% | +0.375 | 57% | 74 |
| pre_3way | 7% | 68% | 62% | 9.74 | 10% | +0.287 | 44% | 109 |
| pre_hu | 6% | 72% | 63% | 7.51 | 13% | +0.259 | 45% | 103 |
| post_hu_bet | 6% | 40% | 5% | 0.13 | 4% | +0.203 | 45% | 181 |
| post_hu_chk | 16% | 43% | 43% | inf | 2% | +0.886 | 56% | 77 |
| post_mw | 3% | 23% | 17% | 3.12 | 1% | +0.756 | 46% | 15 |
| blinds | - | - | - | - | - | -22203 total | 49% | 12 |

257354 decisions; net +54087 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 202 us.
</details>

<details><summary>rival2: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 31% | 28% | 12.48 | 0% | +0.101 | 72% | 4 |
| pre_open_20 | 8% | 34% | 33% | 35.22 | 0% | +0.168 | 70% | 4 |
| pre_open_10 | 4% | 29% | 26% | 8.99 | 9% | +0.176 | 55% | 37 |
| pre_open_short | 1% | 31% | 28% | 10.08 | 28% | +0.213 | 45% | 103 |
| pre_raised_deep | 22% | 21% | 7% | 0.50 | 2% | +0.044 | 53% | 98 |
| pre_raised_short | 3% | 28% | 26% | 9.61 | 26% | +0.481 | 47% | 200 |
| pre_allin | 4% | 12% | 0% | 0.00 | 2% | +0.455 | 57% | 77 |
| pre_3way | 8% | 39% | 32% | 4.67 | 12% | +0.277 | 49% | 129 |
| pre_hu | 6% | 51% | 42% | 4.99 | 17% | +0.213 | 45% | 141 |
| post_hu_bet | 5% | 42% | 7% | 0.21 | 6% | +0.690 | 52% | 221 |
| post_hu_chk | 13% | 47% | 47% | inf | 2% | +1.090 | 52% | 73 |
| post_mw | 3% | 14% | 9% | 1.50 | 1% | +0.904 | 45% | 12 |
| blinds | - | - | - | - | - | -29072 total | 50% | 7 |

244625 decisions; net +50581 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 4073 us.
</details>

<details><summary>rival1: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 20% | 30% | 30% | inf | 0% | +0.146 | 84% | 0 |
| pre_open_20 | 8% | 40% | 40% | inf | 0% | +0.229 | 76% | 0 |
| pre_open_10 | 4% | 45% | 45% | inf | 6% | +0.230 | 46% | 44 |
| pre_open_short | 1% | 70% | 69% | 56.15 | 69% | +0.500 | 45% | 154 |
| pre_raised_deep | 20% | 27% | 4% | 0.16 | 1% | -0.070 | 59% | 40 |
| pre_raised_short | 3% | 25% | 18% | 2.38 | 17% | +0.324 | 45% | 162 |
| pre_allin | 3% | 13% | 2% | 0.15 | 4% | +0.550 | 58% | 63 |
| pre_3way | 8% | 49% | 42% | 6.53 | 10% | +0.298 | 48% | 103 |
| pre_hu | 6% | 52% | 45% | 6.56 | 12% | +0.267 | 47% | 106 |
| post_hu_bet | 6% | 46% | 5% | 0.13 | 4% | +0.066 | 49% | 230 |
| post_hu_chk | 15% | 43% | 43% | inf | 3% | +0.932 | 60% | 115 |
| post_mw | 5% | 13% | 8% | 1.62 | 1% | +0.457 | 42% | 36 |
| blinds | - | - | - | - | - | -27161 total | 45% | 13 |

259936 decisions; net +45233 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 139 us.
</details>

<details><summary>agent_pushfold: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 29% | 29% | inf | 0% | +0.073 | 77% | 0 |
| pre_open_20 | 9% | 33% | 32% | 420.06 | 1% | +0.156 | 69% | 12 |
| pre_open_10 | 5% | 25% | 24% | 44.47 | 14% | +0.216 | 53% | 134 |
| pre_open_short | 1% | 46% | 45% | 48.12 | 38% | +0.344 | 44% | 190 |
| pre_raised_deep | 22% | 12% | 6% | 0.97 | 2% | +0.127 | 51% | 168 |
| pre_raised_short | 4% | 20% | 11% | 1.11 | 10% | +0.155 | 45% | 115 |
| pre_allin | 4% | 17% | 0% | 0.01 | 2% | +0.314 | 52% | 70 |
| pre_3way | 8% | 37% | 33% | 9.91 | 12% | +0.262 | 47% | 199 |
| pre_hu | 6% | 42% | 37% | 7.24 | 11% | +0.214 | 51% | 131 |
| post_hu_bet | 4% | 28% | 2% | 0.07 | 3% | +0.728 | 65% | 57 |
| post_hu_chk | 12% | 29% | 29% | inf | 2% | +0.834 | 61% | 65 |
| post_mw | 2% | 21% | 15% | 2.45 | 2% | +0.685 | 42% | 28 |
| blinds | - | - | - | - | - | -35256 total | 45% | 5 |

241100 decisions; net +29885 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 167 us.
</details>

<details><summary>trackb3: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 21% | 27% | 27% | inf | 0% | +0.064 | 80% | 0 |
| pre_open_20 | 9% | 31% | 31% | inf | 0% | +0.146 | 71% | 0 |
| pre_open_10 | 5% | 34% | 34% | inf | 7% | +0.187 | 48% | 115 |
| pre_open_short | 1% | 44% | 42% | 37.55 | 43% | +0.332 | 46% | 250 |
| pre_raised_deep | 22% | 14% | 3% | 0.23 | 0% | -0.009 | 80% | 0 |
| pre_raised_short | 5% | 16% | 5% | 0.52 | 4% | +0.093 | 59% | 72 |
| pre_allin | 4% | 19% | 0% | 0.00 | 5% | +0.544 | 55% | 179 |
| pre_3way | 8% | 30% | 25% | 4.97 | 8% | +0.148 | 48% | 170 |
| pre_hu | 5% | 25% | 17% | 2.19 | 9% | +0.057 | 52% | 127 |
| post_hu_bet | 5% | 31% | 0% | 0.00 | 3% | +0.062 | 52% | 186 |
| post_hu_chk | 12% | 31% | 31% | inf | 2% | +0.884 | 58% | 99 |
| post_mw | 3% | 26% | 19% | 2.65 | 2% | +0.836 | 36% | 44 |
| blinds | - | - | - | - | - | -37105 total | 56% | 18 |

241298 decisions; net +14122 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 217 us.
</details>

<details><summary>trackb5: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 21% | 30% | 30% | inf | 0% | +0.062 | 65% | 0 |
| pre_open_20 | 9% | 41% | 41% | inf | 0% | +0.154 | 72% | 0 |
| pre_open_10 | 6% | 45% | 45% | inf | 7% | +0.164 | 52% | 112 |
| pre_open_short | 2% | 53% | 52% | 39.63 | 36% | +0.287 | 46% | 346 |
| pre_raised_deep | 22% | 11% | 3% | 0.32 | 0% | -0.003 | 86% | 1 |
| pre_raised_short | 5% | 8% | 2% | 0.47 | 1% | +0.052 | 75% | 15 |
| pre_allin | 4% | 10% | 0% | 0.00 | 4% | +0.610 | 63% | 146 |
| pre_3way | 8% | 32% | 29% | 9.22 | 8% | +0.170 | 47% | 191 |
| pre_hu | 5% | 27% | 21% | 3.46 | 8% | +0.137 | 57% | 107 |
| post_hu_bet | 5% | 32% | 0% | 0.00 | 3% | +0.017 | 52% | 178 |
| post_hu_chk | 12% | 29% | 29% | inf | 2% | +0.891 | 57% | 80 |
| post_mw | 2% | 27% | 20% | 2.60 | 2% | +0.815 | 39% | 36 |
| blinds | - | - | - | - | - | -40205 total | 44% | 35 |

244700 decisions; net +12011 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 172 us.
</details>

<details><summary>agent_charts: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 23% | 22% | 22.69 | 0% | +0.100 | 59% | 0 |
| pre_open_20 | 9% | 26% | 26% | 46.97 | 0% | +0.175 | 74% | 0 |
| pre_open_10 | 4% | 31% | 28% | 12.74 | 10% | +0.208 | 49% | 82 |
| pre_open_short | 1% | 53% | 52% | 56.53 | 52% | +0.377 | 45% | 163 |
| pre_raised_deep | 22% | 14% | 3% | 0.27 | 0% | +0.059 | 69% | 17 |
| pre_raised_short | 3% | 38% | 4% | 0.12 | 3% | -0.092 | 63% | 20 |
| pre_allin | 3% | 27% | 2% | 0.06 | 6% | +0.520 | 50% | 129 |
| pre_3way | 7% | 36% | 26% | 2.65 | 7% | +0.148 | 45% | 106 |
| pre_hu | 6% | 57% | 42% | 2.82 | 8% | +0.112 | 43% | 90 |
| post_hu_bet | 6% | 53% | 4% | 0.09 | 6% | -0.087 | 44% | 456 |
| post_hu_chk | 14% | 28% | 28% | inf | 2% | +0.789 | 63% | 94 |
| post_mw | 3% | 23% | 13% | 1.26 | 3% | +0.676 | 41% | 87 |
| blinds | - | - | - | - | - | -29666 total | 44% | 31 |

235919 decisions; net +22186 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 61 us.
</details>

<details><summary>agent_default: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 18% | 16% | 6.85 | 0% | +0.095 | 55% | 0 |
| pre_open_20 | 8% | 21% | 18% | 6.83 | 0% | +0.121 | 54% | 0 |
| pre_open_10 | 5% | 23% | 20% | 5.95 | 0% | +0.119 | 70% | 0 |
| pre_open_short | 2% | 35% | 31% | 10.02 | 32% | +0.319 | 49% | 169 |
| pre_raised_deep | 22% | 14% | 3% | 0.24 | 0% | +0.069 | 62% | 45 |
| pre_raised_short | 5% | 13% | 4% | 0.43 | 3% | +0.098 | 62% | 42 |
| pre_allin | 3% | 17% | 2% | 0.11 | 14% | +0.469 | 51% | 503 |
| pre_3way | 7% | 28% | 18% | 2.00 | 4% | +0.133 | 49% | 65 |
| pre_hu | 4% | 46% | 33% | 2.66 | 5% | +0.150 | 47% | 87 |
| post_hu_bet | 5% | 59% | 1% | 0.03 | 3% | -0.615 | 45% | 201 |
| post_hu_chk | 13% | 35% | 35% | inf | 3% | +0.725 | 59% | 161 |
| post_mw | 3% | 24% | 13% | 1.28 | 2% | +0.590 | 48% | 52 |
| blinds | - | - | - | - | - | -31482 total | 50% | 5 |

222948 decisions; net +7468 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 117 us.
</details>

<details><summary>agent_montecarlo: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 32% | 29% | 7.78 | 0% | +0.130 | 75% | 0 |
| pre_open_20 | 6% | 38% | 33% | 6.60 | 0% | +0.175 | 79% | 0 |
| pre_open_10 | 2% | 46% | 40% | 6.30 | 5% | +0.194 | 46% | 46 |
| pre_open_short | 1% | 64% | 57% | 7.86 | 42% | +0.364 | 42% | 144 |
| pre_raised_deep | 21% | 24% | 7% | 0.44 | 1% | +0.084 | 56% | 88 |
| pre_raised_short | 2% | 35% | 10% | 0.40 | 8% | +0.037 | 50% | 79 |
| pre_allin | 3% | 19% | 3% | 0.16 | 8% | +0.725 | 54% | 153 |
| pre_3way | 6% | 56% | 35% | 1.72 | 4% | +0.171 | 45% | 58 |
| pre_hu | 5% | 76% | 40% | 1.14 | 3% | +0.160 | 55% | 48 |
| post_hu_bet | 8% | 64% | 4% | 0.07 | 6% | -1.907 | 31% | 485 |
| post_hu_chk | 20% | 24% | 24% | inf | 2% | +0.756 | 45% | 167 |
| post_mw | 4% | 20% | 13% | 1.97 | 2% | +0.778 | 34% | 42 |
| blinds | - | - | - | - | - | -16592 total | 46% | 21 |

205646 decisions; net +11367 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 407 us.
</details>

## Full profile, `realistic`: 100 seeds x 8 rotations, mode model, seed 7

Overall, by points (uniform 4.50):

1. **hybrid3_x** 6.09 ± 0.16 (1st 45%, bust 51%)
2. **hero** 5.98 ± 0.13 (1st 44%, bust 52%)
3. **rival3** 5.91 ± 0.16 (1st 43%, bust 53%)
4. **rival1** 5.80 ± 0.14 (1st 36%, bust 57%)
5. **hybrid_x** 5.71 ± 0.16 (1st 40%, bust 56%)
6. **rival2** 5.41 ± 0.14 (1st 30%, bust 64%)
7. **trackb5** 5.39 ± 0.11 (1st 12%, bust 70%)
8. **agent_pushfold** 5.28 ± 0.13 (1st 22%, bust 68%)
9. **trackb3** 5.27 ± 0.11 (1st 14%, bust 71%)
10. **agent_charts** 5.21 ± 0.11 (1st 21%, bust 74%)
11. **agent_default** 5.07 ± 0.13 (1st 17%, bust 74%)
12. **agent_montecarlo** 4.31 ± 0.14 (1st 16%, bust 83%)

Best at, by chips won per decision (bb) in the spots each bot reached, ± 95% (the seed is the unit):

- **deep preflop play**: 1. agent_charts +0.131 ± 0.028, 2. hybrid3_x +0.126 ± 0.027, 3. agent_default +0.124 ± 0.032, 4. hybrid_x +0.120 ± 0.031, 5. agent_pushfold +0.117 ± 0.049, 6. agent_montecarlo +0.104 ± 0.040, 7. rival3 +0.099 ± 0.030, 8. rival1 +0.090 ± 0.027, 9. rival2 +0.087 ± 0.030, 10. hero +0.067 ± 0.029, 11. trackb5 +0.054 ± 0.016, 12. trackb3 +0.053 ± 0.017
- **short-stack play**: 1. hybrid_x +0.336 ± 0.067, 2. rival1 +0.304 ± 0.068, 3. hybrid3_x +0.288 ± 0.040, 4. hero +0.281 ± 0.058, 5. rival3 +0.281 ± 0.050, 6. rival2 +0.234 ± 0.074, 7. trackb3 +0.221 ± 0.048, 8. trackb5 +0.212 ± 0.034, 9. agent_default +0.174 ± 0.048, 10. agent_montecarlo +0.152 ± 0.149, 11. agent_pushfold +0.151 ± 0.041, 12. agent_charts +0.139 ± 0.078
- **endgame (three-handed and heads-up preflop)**: 1. hybrid3_x +0.419 ± 0.042, 2. hybrid_x +0.391 ± 0.034, 3. rival3 +0.379 ± 0.037, 4. hero +0.352 ± 0.029, 5. rival1 +0.321 ± 0.027, 6. rival2 +0.277 ± 0.036, 7. agent_pushfold +0.223 ± 0.029, 8. agent_charts +0.185 ± 0.026, 9. trackb5 +0.165 ± 0.020, 10. trackb3 +0.162 ± 0.022, 11. agent_default +0.155 ± 0.020, 12. agent_montecarlo +0.133 ± 0.036
- **play after the flop**: 1. hybrid_x +1.026 ± 0.145, 2. rival2 +0.956 ± 0.134, 3. agent_pushfold +0.866 ± 0.121, 4. hybrid3_x +0.858 ± 0.127, 5. trackb5 +0.842 ± 0.106, 6. rival1 +0.822 ± 0.108, 7. rival3 +0.812 ± 0.126, 8. hero +0.728 ± 0.073, 9. trackb3 +0.706 ± 0.094, 10. agent_charts +0.592 ± 0.094, 11. agent_default +0.450 ± 0.127, 12. agent_montecarlo +0.126 ± 0.137

Per section (bb per decision ± 95%; the bot's share of its decisions in brackets):

- *opening deep (unopened pot, 40+ bb)* (`pre_open_40`): 1. hybrid3_x +0.180 ± 0.017 (23%), 2. rival1 +0.165 ± 0.014 (22%), 3. rival3 +0.162 ± 0.016 (23%), 4. hero +0.153 ± 0.015 (21%), 5. hybrid_x +0.130 ± 0.022 (25%), 6. agent_montecarlo +0.126 ± 0.016 (23%), 7. rival2 +0.115 ± 0.023 (24%), 8. agent_charts +0.107 ± 0.012 (24%), 9. agent_default +0.103 ± 0.011 (23%), 10. trackb3 +0.098 ± 0.012 (24%), 11. agent_pushfold +0.092 ± 0.016 (24%), 12. trackb5 +0.080 ± 0.014 (23%)
- *opening at 20-40 bb* (`pre_open_20`): 1. hybrid3_x +0.375 ± 0.031 (9%), 2. hero +0.351 ± 0.028 (8%), 3. rival3 +0.335 ± 0.028 (9%), 4. hybrid_x +0.296 ± 0.034 (9%), 5. rival1 +0.267 ± 0.020 (9%), 6. rival2 +0.217 ± 0.031 (9%), 7. agent_montecarlo +0.208 ± 0.028 (6%), 8. agent_pushfold +0.205 ± 0.030 (9%), 9. agent_charts +0.189 ± 0.019 (9%), 10. trackb5 +0.187 ± 0.027 (9%), 11. trackb3 +0.164 ± 0.023 (9%), 12. agent_default +0.113 ± 0.018 (8%)
- *opening at 10-20 bb* (`pre_open_10`): 1. rival3 +0.409 ± 0.035 (5%), 2. hybrid3_x +0.403 ± 0.042 (5%), 3. hero +0.382 ± 0.042 (5%), 4. hybrid_x +0.331 ± 0.059 (4%), 5. rival1 +0.290 ± 0.039 (5%), 6. trackb5 +0.283 ± 0.039 (6%), 7. rival2 +0.248 ± 0.048 (4%), 8. agent_charts +0.237 ± 0.047 (4%), 9. agent_pushfold +0.237 ± 0.056 (5%), 10. trackb3 +0.215 ± 0.039 (6%), 11. agent_montecarlo +0.210 ± 0.065 (3%), 12. agent_default +0.144 ± 0.019 (6%)
- *push or fold (unopened, under 10 bb)* (`pre_open_short`): 1. rival1 +0.546 ± 0.139 (1%), 2. rival3 +0.482 ± 0.136 (1%), 3. hybrid_x +0.481 ± 0.101 (1%), 4. hybrid3_x +0.415 ± 0.115 (1%), 5. agent_charts +0.412 ± 0.145 (1%), 6. trackb3 +0.395 ± 0.102 (2%), 7. trackb5 +0.390 ± 0.079 (2%), 8. rival2 +0.329 ± 0.100 (1%), 9. agent_montecarlo +0.313 ± 0.157 (1%), 10. hero +0.308 ± 0.091 (2%), 11. agent_pushfold +0.294 ± 0.104 (1%), 12. agent_default +0.293 ± 0.081 (2%)
- *facing a raise, 20+ bb* (`pre_raised_deep`): 1. agent_default +0.157 ± 0.085 (18%), 2. agent_charts +0.133 ± 0.076 (19%), 3. agent_pushfold +0.106 ± 0.128 (19%), 4. agent_montecarlo +0.037 ± 0.108 (18%), 5. hybrid_x +0.030 ± 0.074 (20%), 6. rival2 -0.008 ± 0.076 (20%), 7. trackb5 -0.043 ± 0.037 (19%), 8. trackb3 -0.056 ± 0.041 (19%), 9. hybrid3_x -0.058 ± 0.067 (19%), 10. rival3 -0.089 ± 0.075 (19%), 11. rival1 -0.096 ± 0.069 (18%), 12. hero -0.174 ± 0.074 (17%)
- *facing a raise under 20 bb (re-shove or fold)* (`pre_raised_short`): 1. hybrid_x +0.453 ± 0.178 (2%), 2. rival2 +0.272 ± 0.208 (2%), 3. rival1 +0.241 ± 0.107 (3%), 4. hybrid3_x +0.237 ± 0.106 (3%), 5. hero +0.218 ± 0.086 (3%), 6. rival3 +0.139 ± 0.136 (3%), 7. agent_pushfold +0.119 ± 0.069 (3%), 8. agent_default +0.081 ± 0.049 (4%), 9. trackb3 +0.050 ± 0.052 (4%), 10. trackb5 +0.001 ± 0.028 (4%), 11. agent_montecarlo -0.024 ± 0.171 (2%), 12. agent_charts -0.200 ± 0.071 (3%)
- *facing an all-in* (`pre_allin`): 1. trackb3 +0.370 ± 0.248 (2%), 2. agent_default +0.302 ± 0.278 (2%), 3. rival1 +0.295 ± 0.276 (2%), 4. agent_charts +0.253 ± 0.420 (2%), 5. trackb5 +0.225 ± 0.154 (3%), 6. hybrid_x +0.189 ± 0.164 (3%), 7. hero +0.155 ± 0.202 (3%), 8. agent_montecarlo +0.145 ± 0.538 (2%), 9. rival2 +0.134 ± 0.206 (3%), 10. rival3 +0.124 ± 0.128 (3%), 11. hybrid3_x +0.105 ± 0.109 (3%), 12. agent_pushfold -0.075 ± 0.151 (2%)
- *three-handed preflop* (`pre_3way`): 1. hybrid3_x +0.467 ± 0.050 (8%), 2. rival3 +0.422 ± 0.045 (9%), 3. hybrid_x +0.393 ± 0.044 (9%), 4. hero +0.343 ± 0.033 (9%), 5. rival1 +0.331 ± 0.035 (9%), 6. rival2 +0.272 ± 0.041 (10%), 7. agent_pushfold +0.258 ± 0.033 (9%), 8. trackb5 +0.204 ± 0.026 (10%), 9. agent_charts +0.195 ± 0.034 (8%), 10. trackb3 +0.195 ± 0.026 (10%), 11. agent_montecarlo +0.175 ± 0.039 (7%), 12. agent_default +0.148 ± 0.021 (9%)
- *heads-up preflop* (`pre_hu`): 1. hybrid_x +0.388 ± 0.056 (6%), 2. hero +0.368 ± 0.051 (6%), 3. hybrid3_x +0.359 ± 0.053 (7%), 4. rival3 +0.321 ± 0.051 (6%), 5. rival1 +0.307 ± 0.044 (6%), 6. rival2 +0.287 ± 0.060 (5%), 7. agent_default +0.170 ± 0.046 (4%), 8. agent_charts +0.169 ± 0.043 (5%), 9. agent_pushfold +0.166 ± 0.049 (6%), 10. trackb3 +0.089 ± 0.041 (4%), 11. trackb5 +0.078 ± 0.036 (4%), 12. agent_montecarlo +0.068 ± 0.067 (5%)
- *heads-up pot after the flop, facing a bet* (`post_hu_bet`): 1. hybrid_x +0.810 ± 0.409 (6%), 2. agent_pushfold +0.776 ± 0.341 (5%), 3. rival2 +0.698 ± 0.378 (6%), 4. hero +0.543 ± 0.214 (7%), 5. rival1 +0.528 ± 0.268 (7%), 6. hybrid3_x +0.503 ± 0.337 (6%), 7. rival3 +0.456 ± 0.313 (7%), 8. trackb5 +0.250 ± 0.255 (5%), 9. trackb3 +0.100 ± 0.215 (6%), 10. agent_charts +0.091 ± 0.260 (7%), 11. agent_default -0.139 ± 0.315 (6%), 12. agent_montecarlo -1.611 ± 0.379 (9%)
- *heads-up pot after the flop, nothing to call* (`post_hu_chk`): 1. hybrid_x +1.249 ± 0.133 (11%), 2. rival2 +1.229 ± 0.127 (11%), 3. rival1 +1.108 ± 0.105 (12%), 4. trackb5 +1.054 ± 0.103 (11%), 5. hybrid3_x +1.029 ± 0.107 (12%), 6. rival3 +1.019 ± 0.109 (12%), 7. trackb3 +0.913 ± 0.104 (11%), 8. hero +0.889 ± 0.065 (14%), 9. agent_pushfold +0.871 ± 0.103 (11%), 10. agent_charts +0.848 ± 0.088 (13%), 11. agent_montecarlo +0.820 ± 0.093 (19%), 12. agent_default +0.780 ± 0.114 (12%)
- *multiway pot after the flop* (`post_mw`): 1. trackb5 +1.100 ± 0.346 (3%), 2. trackb3 +1.007 ± 0.299 (4%), 3. agent_pushfold +0.968 ± 0.306 (4%), 4. hybrid3_x +0.887 ± 0.248 (4%), 5. rival3 +0.785 ± 0.238 (4%), 6. hybrid_x +0.745 ± 0.219 (5%), 7. agent_montecarlo +0.704 ± 0.313 (6%), 8. agent_charts +0.668 ± 0.250 (5%), 9. rival2 +0.650 ± 0.225 (5%), 10. rival1 +0.574 ± 0.229 (5%), 11. hero +0.573 ± 0.146 (6%), 12. agent_default +0.345 ± 0.276 (4%)

Where the busts come from (the section of the last decision that put chips in, top three):

- hybrid3_x: pre_raised_short 22%, post_hu_bet 19%, post_hu_chk 15%
- hero: post_hu_bet 19%, pre_raised_short 18%, pre_allin 17%
- rival3: pre_raised_short 28%, post_hu_bet 19%, post_hu_chk 11%
- rival1: post_hu_bet 23%, pre_raised_short 15%, pre_open_short 13%
- hybrid_x: post_hu_bet 23%, pre_raised_short 18%, pre_raised_deep 17%
- rival2: post_hu_bet 24%, pre_raised_short 21%, pre_raised_deep 12%
- trackb5: pre_open_short 22%, post_hu_bet 19%, pre_3way 16%
- agent_pushfold: pre_raised_deep 22%, pre_open_short 16%, pre_3way 12%
- trackb3: post_hu_bet 21%, pre_open_short 20%, pre_allin 12%
- agent_charts: post_hu_bet 37%, pre_open_short 13%, pre_allin 9%
- agent_default: pre_allin 29%, post_hu_bet 16%, pre_open_short 15%
- agent_montecarlo: post_hu_bet 39%, pre_open_short 11%, pre_allin 10%

Finish distribution (% of seats, 1st .. 8th):

| bot | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | bust |
|---|---|---|---|---|---|---|---|---|---|
| hybrid3_x | 45 | 12 | 8 | 10 | 10 | 7 | 6 | 3 | 51 |
| hero | 44 | 9 | 9 | 11 | 8 | 8 | 6 | 4 | 52 |
| rival3 | 43 | 9 | 7 | 10 | 13 | 9 | 6 | 4 | 53 |
| rival1 | 36 | 12 | 10 | 13 | 11 | 7 | 6 | 4 | 57 |
| hybrid_x | 40 | 9 | 7 | 10 | 12 | 10 | 6 | 6 | 56 |
| rival2 | 30 | 12 | 9 | 13 | 13 | 10 | 8 | 6 | 64 |
| trackb5 | 12 | 23 | 19 | 16 | 12 | 8 | 6 | 4 | 70 |
| agent_pushfold | 22 | 16 | 13 | 12 | 13 | 10 | 8 | 6 | 68 |
| trackb3 | 14 | 20 | 16 | 16 | 13 | 10 | 7 | 5 | 71 |
| agent_charts | 21 | 11 | 14 | 16 | 14 | 11 | 8 | 4 | 74 |
| agent_default | 17 | 12 | 16 | 18 | 14 | 10 | 8 | 6 | 74 |
| agent_montecarlo | 16 | 8 | 8 | 12 | 14 | 14 | 16 | 12 | 83 |

<details><summary>hybrid3_x: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 23% | 38% | 34% | 9.74 | 0% | +0.180 | 58% | 0 |
| pre_open_20 | 9% | 58% | 58% | 91.19 | 0% | +0.375 | 74% | 0 |
| pre_open_10 | 5% | 68% | 68% | inf | 0% | +0.403 | 65% | 1 |
| pre_open_short | 1% | 55% | 54% | 35.24 | 50% | +0.415 | 46% | 32 |
| pre_raised_deep | 19% | 23% | 6% | 0.37 | 1% | -0.058 | 54% | 31 |
| pre_raised_short | 3% | 25% | 20% | 3.95 | 20% | +0.237 | 42% | 92 |
| pre_allin | 3% | 13% | 0% | 0.01 | 1% | +0.105 | 54% | 11 |
| pre_3way | 8% | 74% | 68% | 11.61 | 12% | +0.467 | 50% | 46 |
| pre_hu | 7% | 79% | 72% | 9.63 | 21% | +0.359 | 43% | 48 |
| post_hu_bet | 6% | 43% | 6% | 0.17 | 4% | +0.503 | 47% | 77 |
| post_hu_chk | 12% | 61% | 61% | inf | 2% | +1.029 | 55% | 61 |
| post_mw | 4% | 30% | 23% | 3.53 | 1% | +0.887 | 49% | 6 |
| blinds | - | - | - | - | - | -8375 total | 49% | 4 |

130675 decisions; net +37382 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 4061 us.
</details>

<details><summary>hero: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 21% | 39% | 36% | 11.80 | 0% | +0.153 | 72% | 0 |
| pre_open_20 | 8% | 57% | 55% | 27.56 | 0% | +0.351 | 71% | 0 |
| pre_open_10 | 5% | 63% | 62% | 120.06 | 0% | +0.382 | 68% | 0 |
| pre_open_short | 2% | 41% | 40% | 42.62 | 30% | +0.308 | 47% | 40 |
| pre_raised_deep | 17% | 33% | 5% | 0.16 | 1% | -0.174 | 59% | 39 |
| pre_raised_short | 3% | 19% | 12% | 1.64 | 11% | +0.218 | 48% | 76 |
| pre_allin | 3% | 22% | 0% | 0.00 | 4% | +0.155 | 47% | 72 |
| pre_3way | 9% | 54% | 48% | 7.53 | 8% | +0.343 | 52% | 33 |
| pre_hu | 6% | 73% | 67% | 11.53 | 17% | +0.368 | 43% | 32 |
| post_hu_bet | 7% | 33% | 2% | 0.08 | 3% | +0.543 | 58% | 78 |
| post_hu_chk | 14% | 53% | 53% | inf | 2% | +0.889 | 56% | 34 |
| post_mw | 6% | 26% | 21% | 4.82 | 0% | +0.573 | 37% | 5 |
| blinds | - | - | - | - | - | -10044 total | 47% | 3 |

142480 decisions; net +34394 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 350 us.
</details>

<details><summary>rival3: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 23% | 37% | 33% | 9.25 | 0% | +0.162 | 59% | 0 |
| pre_open_20 | 9% | 55% | 55% | 91.81 | 0% | +0.335 | 65% | 0 |
| pre_open_10 | 5% | 64% | 64% | inf | 0% | +0.409 | 66% | 1 |
| pre_open_short | 1% | 57% | 56% | 82.45 | 56% | +0.482 | 47% | 34 |
| pre_raised_deep | 19% | 23% | 6% | 0.37 | 1% | -0.089 | 54% | 43 |
| pre_raised_short | 3% | 29% | 24% | 4.36 | 23% | +0.139 | 36% | 120 |
| pre_allin | 3% | 15% | 0% | 0.01 | 1% | +0.124 | 54% | 14 |
| pre_3way | 9% | 71% | 65% | 11.06 | 12% | +0.422 | 46% | 39 |
| pre_hu | 6% | 77% | 69% | 9.52 | 20% | +0.321 | 39% | 37 |
| post_hu_bet | 7% | 43% | 6% | 0.15 | 4% | +0.456 | 45% | 79 |
| post_hu_chk | 12% | 48% | 48% | inf | 3% | +1.019 | 57% | 46 |
| post_mw | 4% | 24% | 18% | 2.82 | 1% | +0.785 | 47% | 3 |
| blinds | - | - | - | - | - | -9169 total | 47% | 10 |

128562 decisions; net +32660 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 229 us.
</details>

<details><summary>rival1: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 22% | 27% | 27% | inf | 0% | +0.165 | 61% | 0 |
| pre_open_20 | 9% | 38% | 38% | inf | 0% | +0.267 | 65% | 0 |
| pre_open_10 | 5% | 43% | 43% | inf | 6% | +0.290 | 52% | 18 |
| pre_open_short | 1% | 70% | 69% | 58.12 | 69% | +0.546 | 45% | 61 |
| pre_raised_deep | 18% | 28% | 4% | 0.17 | 1% | -0.096 | 62% | 22 |
| pre_raised_short | 3% | 26% | 17% | 2.13 | 16% | +0.241 | 43% | 70 |
| pre_allin | 2% | 15% | 2% | 0.13 | 4% | +0.295 | 55% | 28 |
| pre_3way | 9% | 51% | 45% | 7.81 | 12% | +0.331 | 50% | 59 |
| pre_hu | 6% | 55% | 49% | 8.58 | 16% | +0.307 | 45% | 27 |
| post_hu_bet | 7% | 46% | 5% | 0.12 | 4% | +0.528 | 53% | 103 |
| post_hu_chk | 12% | 43% | 43% | inf | 3% | +1.108 | 60% | 48 |
| post_mw | 5% | 14% | 8% | 1.27 | 1% | +0.574 | 39% | 15 |
| blinds | - | - | - | - | - | -12625 total | 40% | 2 |

134656 decisions; net +31459 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 150 us.
</details>

<details><summary>hybrid_x: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 25% | 34% | 30% | 7.23 | 0% | +0.130 | 67% | 2 |
| pre_open_20 | 9% | 42% | 41% | 28.04 | 0% | +0.296 | 68% | 2 |
| pre_open_10 | 4% | 47% | 46% | 52.89 | 11% | +0.331 | 49% | 17 |
| pre_open_short | 1% | 52% | 50% | 31.28 | 30% | +0.481 | 54% | 35 |
| pre_raised_deep | 20% | 23% | 8% | 0.56 | 3% | +0.030 | 52% | 77 |
| pre_raised_short | 2% | 34% | 30% | 6.89 | 30% | +0.453 | 43% | 79 |
| pre_allin | 3% | 15% | 0% | 0.00 | 1% | +0.189 | 52% | 23 |
| pre_3way | 9% | 57% | 51% | 8.85 | 13% | +0.393 | 48% | 34 |
| pre_hu | 6% | 71% | 62% | 6.98 | 21% | +0.388 | 46% | 42 |
| post_hu_bet | 6% | 44% | 9% | 0.26 | 7% | +0.810 | 51% | 103 |
| post_hu_chk | 11% | 62% | 62% | inf | 2% | +1.249 | 51% | 27 |
| post_mw | 5% | 18% | 14% | 2.90 | 1% | +0.745 | 37% | 6 |
| blinds | - | - | - | - | - | -9672 total | 50% | 2 |

121670 decisions; net +36291 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 768 us.
</details>

<details><summary>rival2: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 24% | 31% | 27% | 6.58 | 0% | +0.115 | 67% | 3 |
| pre_open_20 | 9% | 35% | 33% | 18.76 | 0% | +0.217 | 72% | 4 |
| pre_open_10 | 4% | 30% | 27% | 7.62 | 10% | +0.248 | 61% | 15 |
| pre_open_short | 1% | 36% | 31% | 7.02 | 31% | +0.329 | 50% | 43 |
| pre_raised_deep | 20% | 23% | 8% | 0.53 | 3% | -0.008 | 54% | 64 |
| pre_raised_short | 2% | 35% | 31% | 7.74 | 31% | +0.272 | 34% | 110 |
| pre_allin | 3% | 17% | 0% | 0.00 | 2% | +0.134 | 49% | 34 |
| pre_3way | 10% | 40% | 33% | 4.69 | 12% | +0.272 | 45% | 43 |
| pre_hu | 5% | 54% | 46% | 5.47 | 23% | +0.287 | 42% | 39 |
| post_hu_bet | 6% | 45% | 8% | 0.22 | 6% | +0.698 | 50% | 124 |
| post_hu_chk | 11% | 48% | 48% | inf | 2% | +1.229 | 55% | 24 |
| post_mw | 5% | 12% | 7% | 1.42 | 1% | +0.650 | 37% | 5 |
| blinds | - | - | - | - | - | -12504 total | 37% | 6 |

120579 decisions; net +26532 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 4070 us.
</details>

<details><summary>trackb5: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 23% | 29% | 29% | inf | 0% | +0.080 | 71% | 0 |
| pre_open_20 | 9% | 39% | 39% | inf | 0% | +0.187 | 66% | 0 |
| pre_open_10 | 6% | 44% | 44% | inf | 7% | +0.283 | 54% | 46 |
| pre_open_short | 2% | 51% | 50% | 45.35 | 37% | +0.390 | 45% | 126 |
| pre_raised_deep | 19% | 11% | 3% | 0.30 | 0% | -0.043 | 62% | 0 |
| pre_raised_short | 4% | 8% | 2% | 0.34 | 1% | +0.001 | 68% | 8 |
| pre_allin | 3% | 9% | 0% | 0.00 | 4% | +0.225 | 65% | 60 |
| pre_3way | 10% | 33% | 29% | 9.18 | 9% | +0.204 | 47% | 92 |
| pre_hu | 4% | 27% | 21% | 3.95 | 8% | +0.078 | 51% | 49 |
| post_hu_bet | 5% | 34% | 0% | 0.00 | 3% | +0.250 | 54% | 104 |
| post_hu_chk | 11% | 30% | 30% | inf | 2% | +1.054 | 57% | 43 |
| post_mw | 3% | 25% | 18% | 3.01 | 1% | +1.100 | 34% | 16 |
| blinds | - | - | - | - | - | -20571 total | 47% | 17 |

128791 decisions; net +11089 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 311 us.
</details>

<details><summary>agent_pushfold: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 24% | 30% | 30% | inf | 0% | +0.092 | 55% | 0 |
| pre_open_20 | 9% | 34% | 34% | 306.58 | 1% | +0.205 | 59% | 6 |
| pre_open_10 | 5% | 28% | 28% | 37.46 | 14% | +0.237 | 51% | 59 |
| pre_open_short | 1% | 48% | 47% | 34.43 | 36% | +0.294 | 43% | 86 |
| pre_raised_deep | 19% | 13% | 6% | 1.00 | 3% | +0.106 | 51% | 119 |
| pre_raised_short | 3% | 20% | 10% | 1.00 | 9% | +0.119 | 49% | 35 |
| pre_allin | 2% | 24% | 0% | 0.00 | 2% | -0.075 | 48% | 27 |
| pre_3way | 9% | 39% | 35% | 10.29 | 10% | +0.258 | 51% | 65 |
| pre_hu | 6% | 45% | 40% | 8.55 | 11% | +0.166 | 42% | 60 |
| post_hu_bet | 5% | 30% | 2% | 0.09 | 3% | +0.776 | 63% | 45 |
| post_hu_chk | 11% | 29% | 29% | inf | 2% | +0.871 | 59% | 29 |
| post_mw | 4% | 20% | 14% | 2.73 | 1% | +0.968 | 43% | 12 |
| blinds | - | - | - | - | - | -15355 total | 45% | 5 |

118885 decisions; net +18445 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 117 us.
</details>

<details><summary>trackb3: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 24% | 28% | 28% | inf | 0% | +0.098 | 79% | 0 |
| pre_open_20 | 9% | 32% | 32% | inf | 0% | +0.164 | 72% | 0 |
| pre_open_10 | 6% | 34% | 34% | inf | 8% | +0.215 | 49% | 59 |
| pre_open_short | 2% | 46% | 45% | 56.45 | 45% | +0.395 | 47% | 112 |
| pre_raised_deep | 19% | 15% | 3% | 0.23 | 0% | -0.056 | 78% | 0 |
| pre_raised_short | 4% | 15% | 6% | 0.56 | 4% | +0.050 | 55% | 30 |
| pre_allin | 2% | 21% | 0% | 0.00 | 6% | +0.370 | 56% | 70 |
| pre_3way | 10% | 32% | 27% | 5.62 | 9% | +0.195 | 49% | 65 |
| pre_hu | 4% | 26% | 19% | 2.52 | 10% | +0.089 | 50% | 39 |
| post_hu_bet | 6% | 32% | 0% | 0.00 | 3% | +0.100 | 51% | 118 |
| post_hu_chk | 11% | 32% | 32% | inf | 2% | +0.913 | 58% | 40 |
| post_mw | 4% | 25% | 18% | 3.07 | 1% | +1.007 | 35% | 20 |
| blinds | - | - | - | - | - | -18165 total | 40% | 18 |

124262 decisions; net +10105 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 279 us.
</details>

<details><summary>agent_charts: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 24% | 24% | 22% | 12.00 | 0% | +0.107 | 67% | 0 |
| pre_open_20 | 9% | 28% | 26% | 16.94 | 0% | +0.189 | 81% | 0 |
| pre_open_10 | 4% | 32% | 29% | 9.50 | 12% | +0.237 | 53% | 37 |
| pre_open_short | 1% | 56% | 55% | 81.70 | 55% | +0.412 | 43% | 80 |
| pre_raised_deep | 19% | 15% | 3% | 0.29 | 0% | +0.133 | 74% | 10 |
| pre_raised_short | 3% | 39% | 4% | 0.10 | 2% | -0.200 | 59% | 9 |
| pre_allin | 2% | 39% | 2% | 0.04 | 7% | +0.253 | 46% | 55 |
| pre_3way | 8% | 37% | 28% | 2.98 | 8% | +0.195 | 47% | 42 |
| pre_hu | 5% | 59% | 45% | 3.14 | 12% | +0.169 | 39% | 34 |
| post_hu_bet | 7% | 53% | 5% | 0.10 | 5% | +0.091 | 47% | 222 |
| post_hu_chk | 13% | 28% | 28% | inf | 3% | +0.848 | 63% | 45 |
| post_mw | 5% | 22% | 12% | 1.21 | 2% | +0.668 | 37% | 40 |
| blinds | - | - | - | - | - | -14145 total | 47% | 20 |

122523 decisions; net +16977 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 70 us.
</details>

<details><summary>agent_default: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 23% | 19% | 16% | 4.78 | 0% | +0.103 | 69% | 0 |
| pre_open_20 | 8% | 22% | 18% | 5.26 | 0% | +0.113 | 70% | 0 |
| pre_open_10 | 6% | 24% | 20% | 5.22 | 0% | +0.144 | 71% | 1 |
| pre_open_short | 2% | 36% | 34% | 11.65 | 34% | +0.293 | 44% | 92 |
| pre_raised_deep | 18% | 15% | 3% | 0.26 | 1% | +0.157 | 68% | 27 |
| pre_raised_short | 4% | 13% | 4% | 0.45 | 3% | +0.081 | 62% | 25 |
| pre_allin | 2% | 18% | 2% | 0.10 | 14% | +0.302 | 52% | 171 |
| pre_3way | 9% | 28% | 19% | 2.21 | 5% | +0.148 | 48% | 40 |
| pre_hu | 4% | 48% | 37% | 3.52 | 7% | +0.170 | 51% | 23 |
| post_hu_bet | 6% | 60% | 1% | 0.02 | 3% | -0.139 | 47% | 96 |
| post_hu_chk | 12% | 33% | 33% | inf | 3% | +0.780 | 60% | 82 |
| post_mw | 4% | 25% | 15% | 1.47 | 1% | +0.345 | 40% | 31 |
| blinds | - | - | - | - | - | -15558 total | 46% | 7 |

120174 decisions; net +9727 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 89 us.
</details>

<details><summary>agent_montecarlo: per-section table</summary>

| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |
|---|---|---|---|---|---|---|---|---|
| pre_open_40 | 23% | 34% | 29% | 6.33 | 0% | +0.126 | 57% | 0 |
| pre_open_20 | 6% | 42% | 35% | 4.87 | 0% | +0.208 | 71% | 0 |
| pre_open_10 | 3% | 50% | 42% | 5.05 | 5% | +0.210 | 37% | 28 |
| pre_open_short | 1% | 67% | 58% | 6.54 | 35% | +0.313 | 42% | 73 |
| pre_raised_deep | 18% | 24% | 8% | 0.48 | 1% | +0.037 | 53% | 63 |
| pre_raised_short | 2% | 35% | 10% | 0.38 | 8% | -0.024 | 45% | 35 |
| pre_allin | 2% | 25% | 2% | 0.10 | 8% | +0.145 | 45% | 66 |
| pre_3way | 7% | 58% | 37% | 1.81 | 3% | +0.175 | 48% | 18 |
| pre_hu | 5% | 81% | 43% | 1.17 | 3% | +0.068 | 39% | 21 |
| post_hu_bet | 9% | 67% | 4% | 0.07 | 6% | -1.611 | 34% | 257 |
| post_hu_chk | 19% | 24% | 24% | inf | 2% | +0.820 | 44% | 63 |
| post_mw | 6% | 19% | 13% | 2.07 | 1% | +0.704 | 30% | 27 |
| blinds | - | - | - | - | - | -6998 total | 46% | 10 |

100928 decisions; net +4942 bb over the run; engine: 0 exceptions, 0 illegal, 0 timeouts, p99 566 us.
</details>

