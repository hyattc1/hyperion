# Batch 8's timing proof (2026-11-04, the freeze staging worker)

The zip's own bot, not the repo's: batch 8's staged zip (sha256 0d07654e...372ba19, 3,692,371 bytes, 8.5 MB unzipped, commit
77c5ea6) beside batch 7's (frozen/B7-038c3f0, 51c37f02), the same tables, the same box, the same hour. The box: Ryzen 7 9850X3D,
16 threads, WSL2. No budget was loosened. Raw runs: goal/b8_stage/timing/.

## What it says

1. **At this box's speed nothing is wrong.** Bot alone: p50 about 120 µs, p99 about 250 µs, timeouts 0.01-0.03%, the same as
   batch 7 within noise, with every thread busy.
2. **At 3x, through a kit's adapter, batch 8 times out on 12% of its decisions (batch 7: 7.2%). This is a real finding.** The bot
   alone at 3x is fine (0.11%; p99 728 µs). The fake kit B's adapter adds about 140 µs at p50 here (253 against 112), and it runs the
   deferred hand end and the history inference inside the timed call. SafeBot's governor times `bot.act` alone, so it never sees
   that time: at k = 3 `act`'s own p99 stays under the governor's 0.8 ms line, and the bot-alone run reached no level in 110
   tables (the gate does not report levels, so that is inferred for the kit path). The margin is thin and the wall is sharp:
   kit path 0.11-0.47% at 1x, 0.36% at 1.5x, 1.1% at 2x, 12% at 3x. Batch 7 has the same wall a little further out (7.2% at 3x); up
   to 2x the two are level. Over 0.3% the gate fails (its load clause aside), so on this adapter the bot is outside the gate's
   limit from about 1.5-2x.
3. **Setup time nearly doubled.** Import + construction + first table, cold, no bytecode cache: 0.63 s against 0.35 s (R6's 3 MB
   table, decoded at construction). At 3x: 1.7-1.9 s against 1.0 s. Pack's default budget (5 s) holds everywhere. Kit H's 2 s
   start budget (the tightest kit we have rehearsed) passes here (1.07 s at load) and **is at the limit at 3x: the dilated clock's
   worst table is 1.90 s (p50 1.72 s), a real third of a CPU's is 2.06 s, launch to first table 2.05-2.14 s, and the gate at k = 3
   saw 2.13 s**. Batch 7: 1.0-1.3 s. The official rules name no start budget (docs/packet/CHALLENGE.md: "per-table init exists outside the budget",
   expected, unconfirmed).
4. **A bot that never sleeps, on a real third of a CPU, loses 3% of its decisions in either batch**, one 8 ms scheduler stall at a
   time. p50 stays 120 µs and p99 goes to 8.2 ms: no bot code can answer that, and batch 8 and batch 7 are level (3.1% against 2.7%).
   It matters only if the organisers' sandbox is a CPU-share slice of a busy host and runs the bot without sleeping.

Not decided here, for the coordinator: whether the governor should count the adapter's time. That changes play on a slow box,
so this worker did not touch it (brief: fixes that can change play are reported, not made).

## The bot alone (tools/zip_timing.py)

One fresh `python -I -B` per table, the zip's package first on sys.path, every shipped setting on (governor, soft deadlines). 110
tables, 15,000 decisions a run: night 30, elite 20, heads-up 30, three-handed 30. Over 1 ms is a timeout and the engine checks or
folds. µs unless marked.

| condition | zip | decisions | p50 | p99 | p99.9 | max | timeouts | governor tables (panic / any level) | setup p50 / max ms | launch-to-table wall p50 / max ms | hand end p99 | workload ms (clock / CPU) | load |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a at the box's load | b8 | 15140 | 121 | 250 | 468 | 1960 | 3 (0.020%) | 0 / 0 of 110 | 628 / 671 | 654 / 697 | 273 | 12.0 / 11.9 | 15.1-15.3 |
| a at the box's load | b7 | 14854 | 118 | 233 | 472 | 4114 | 1 (0.007%) | 0 / 0 of 110 | 351 / 379 | 378 / 406 | 255 | 12.1 / 12.1 | 15.2-15.3 |
| a again | b8 | 15140 | 119 | 239 | 457 | 1604 | 2 (0.013%) | 0 / 0 of 110 | 624 / 694 | 650 / 722 | 268 | 11.9 / 11.9 | 14.8-15.3 |
| a again | b7 | 14813 | 117 | 235 | 449 | 1904 | 1 (0.007%) | 0 / 0 of 110 | 340 / 378 | 365 / 406 | 255 | 11.7 / 11.7 | 14.3-15.1 |
| b + 2 hogs | b8 | 15160 | 118 | 241 | 468 | 1522 | 2 (0.013%) | 0 / 0 of 110 | 631 / 2356 | 657 / 2408 | 270 | 12.3 / 12.2 | 14.8-15.9 |
| b + 2 hogs | b7 | 14855 | 115 | 233 | 460 | 1555 | 2 (0.013%) | 0 / 0 of 110 | 351 / 378 | 378 / 407 | 261 | 12.2 / 12.2 | 15.2-15.4 |
| b sampled | b8 | 15296 | 119 | 263 | 667 | 2752 | 5 (0.033%) | 0 / 0 of 110 | 656 / 1069 | 686 / 1122 | 318 | 12.7 / 12.6 | 15.9-16.9 |
| b sampled | b7 | 14937 | 116 | 240 | 612 | 2860 | 7 (0.047%) | 0 / 0 of 110 | 359 / 379 | 386 / 408 | 269 | 12.4 / 12.4 | 15.1-16.1 |
| b never sleeps, 1 hog | b8 | 15153 | 120 | 240 | 507 | 1243 | 2 (0.013%) | 0 / 0 of 110 | 627 / 691 | 654 / 720 | 269 | 12.1 / 12.1 | 14.9-15.6 |
| b never sleeps, 1 hog | b7 | 15017 | 117 | 245 | 469 | 2544 | 3 (0.020%) | 0 / 0 of 110 | 348 / 370 | 374 / 402 | 260 | 12.2 / 12.2 | 15.0-15.3 |
| c k=3 | b8 | 15182 | 366 | 728 | 1017 | 1611 | 17 (0.112%) | 0 / 0 of 110 | 1716 / 1901 | 597 / 660 | 756 | 33.0 / 11.0 | 13.7-15.0 |
| c k=3 | b7 | 15085 | 353 | 702 | 1084 | 1377 | 25 (0.166%) | 0 / 0 of 110 | 960 / 1036 | 346 / 370 | 730 | 32.2 / 10.7 | 13.2-13.7 |
| c2 pinned, 2 hogs | b8 | 15140 | 122 | 237 | 345 | 481 | 0 (0.000%) | 0 / 0 of 110 | 1785 / 1969 | 1865 / 2049 | 255 | 26.9 / 11.2 | 13.5-15.4 |
| c2 pinned, 2 hogs | b7 | 14826 | 119 | 240 | 426 | 1942 | 2 (0.013%) | 0 / 0 of 110 | 1033 / 1287 | 1114 / 1364 | 258 | 27.7 / 11.6 | 15.1-16.6 |
| c3 pinned, 2 hogs, never sleeps | b8 | 15712 | 121 | 8163 | 8285 | 16124 | 488 (3.106%) | 0 / 8 of 110 | 1892 / 2057 | 1975 / 2145 | 8179 | 35.3 / 11.5 | 15.1-16.2 |
| c3 pinned, 2 hogs, never sleeps | b7 | 15471 | 119 | 8160 | 8290 | 13518 | 423 (2.734%) | 0 / 1 of 110 | 1086 / 1200 | 1170 / 1294 | 8166 | 36.1 / 12.1 | 16.2-17.7 |

| condition | zip | cell | decisions | p50 | p99 | max | timeouts | first decision p50 / max |
|---|---|---|---|---|---|---|---|---|
| a at the box's load | b8 | night | 5742 | 120 | 261 | 1704 | 2 (0.035%) | 238 / 318 |
| a at the box's load | b8 | elite | 3194 | 131 | 268 | 874 | 0 (0.000%) | 243 / 334 |
| a at the box's load | b8 | exploit2_hu | 2721 | 129 | 230 | 1960 | 1 (0.037%) | 179 / 237 |
| a at the box's load | b8 | exploit2_3 | 3483 | 106 | 241 | 580 | 0 (0.000%) | 196 / 324 |
| a at the box's load | b7 | night | 5623 | 118 | 243 | 873 | 0 (0.000%) | 230 / 472 |
| a at the box's load | b7 | elite | 3064 | 125 | 244 | 4114 | 1 (0.033%) | 232 / 281 |
| a at the box's load | b7 | exploit2_hu | 2762 | 125 | 233 | 736 | 0 (0.000%) | 168 / 237 |
| a at the box's load | b7 | exploit2_3 | 3405 | 104 | 216 | 651 | 0 (0.000%) | 185 / 225 |
| a again | b8 | night | 5742 | 119 | 248 | 816 | 0 (0.000%) | 233 / 284 |
| a again | b8 | elite | 3194 | 128 | 242 | 1011 | 1 (0.031%) | 236 / 284 |
| a again | b8 | exploit2_hu | 2721 | 127 | 256 | 1604 | 1 (0.037%) | 190 / 304 |
| a again | b8 | exploit2_3 | 3483 | 106 | 210 | 586 | 0 (0.000%) | 197 / 503 |
| a again | b7 | night | 5588 | 118 | 253 | 1904 | 1 (0.018%) | 233 / 323 |
| a again | b7 | elite | 3058 | 123 | 238 | 559 | 0 (0.000%) | 230 / 303 |
| a again | b7 | exploit2_hu | 2762 | 126 | 220 | 535 | 0 (0.000%) | 157 / 233 |
| a again | b7 | exploit2_3 | 3405 | 103 | 209 | 622 | 0 (0.000%) | 182 / 240 |
| b + 2 hogs | b8 | night | 5725 | 118 | 247 | 1044 | 1 (0.018%) | 242 / 459 |
| b + 2 hogs | b8 | elite | 3194 | 128 | 257 | 519 | 0 (0.000%) | 239 / 352 |
| b + 2 hogs | b8 | exploit2_hu | 2721 | 126 | 234 | 714 | 0 (0.000%) | 172 / 245 |
| b + 2 hogs | b8 | exploit2_3 | 3520 | 104 | 206 | 1522 | 1 (0.028%) | 190 / 247 |
| b + 2 hogs | b7 | night | 5623 | 116 | 238 | 746 | 0 (0.000%) | 230 / 524 |
| b + 2 hogs | b7 | elite | 3058 | 122 | 239 | 594 | 0 (0.000%) | 228 / 351 |
| b + 2 hogs | b7 | exploit2_hu | 2762 | 126 | 246 | 1555 | 1 (0.036%) | 167 / 346 |
| b + 2 hogs | b7 | exploit2_3 | 3412 | 101 | 197 | 1242 | 1 (0.029%) | 192 / 410 |
| b sampled | b8 | night | 5796 | 119 | 260 | 1090 | 1 (0.017%) | 234 / 290 |
| b sampled | b8 | elite | 3296 | 127 | 289 | 2752 | 3 (0.091%) | 250 / 388 |
| b sampled | b8 | exploit2_hu | 2721 | 124 | 238 | 874 | 0 (0.000%) | 177 / 226 |
| b sampled | b8 | exploit2_3 | 3483 | 105 | 250 | 2499 | 1 (0.029%) | 194 / 552 |
| b sampled | b7 | night | 5623 | 116 | 239 | 653 | 0 (0.000%) | 228 / 380 |
| b sampled | b7 | elite | 3108 | 122 | 260 | 2191 | 5 (0.161%) | 228 / 361 |
| b sampled | b7 | exploit2_hu | 2801 | 129 | 240 | 2860 | 2 (0.071%) | 156 / 219 |
| b sampled | b7 | exploit2_3 | 3405 | 100 | 229 | 742 | 0 (0.000%) | 180 / 622 |
| b never sleeps, 1 hog | b8 | night | 5755 | 121 | 245 | 1243 | 2 (0.035%) | 248 / 535 |
| b never sleeps, 1 hog | b8 | elite | 3194 | 129 | 262 | 570 | 0 (0.000%) | 246 / 282 |
| b never sleeps, 1 hog | b8 | exploit2_hu | 2721 | 127 | 240 | 750 | 0 (0.000%) | 181 / 332 |
| b never sleeps, 1 hog | b8 | exploit2_3 | 3483 | 103 | 190 | 390 | 0 (0.000%) | 188 / 241 |
| b never sleeps, 1 hog | b7 | night | 5623 | 116 | 243 | 2201 | 1 (0.018%) | 226 / 452 |
| b never sleeps, 1 hog | b7 | elite | 3145 | 125 | 260 | 1664 | 1 (0.032%) | 232 / 314 |
| b never sleeps, 1 hog | b7 | exploit2_hu | 2762 | 126 | 262 | 452 | 0 (0.000%) | 172 / 235 |
| b never sleeps, 1 hog | b7 | exploit2_3 | 3487 | 103 | 219 | 2544 | 1 (0.029%) | 180 / 266 |
| c k=3 | b8 | night | 5781 | 366 | 738 | 1264 | 3 (0.052%) | 735 / 954 |
| c k=3 | b8 | elite | 3203 | 394 | 782 | 1611 | 8 (0.250%) | 720 / 822 |
| c k=3 | b8 | exploit2_hu | 2715 | 388 | 691 | 1054 | 5 (0.184%) | 511 / 1052 |
| c k=3 | b8 | exploit2_3 | 3483 | 323 | 639 | 1145 | 1 (0.029%) | 570 / 794 |
| c k=3 | b7 | night | 5812 | 351 | 698 | 1377 | 16 (0.275%) | 690 / 1118 |
| c k=3 | b7 | elite | 3085 | 382 | 714 | 1153 | 3 (0.097%) | 725 / 1044 |
| c k=3 | b7 | exploit2_hu | 2716 | 387 | 750 | 1355 | 6 (0.221%) | 512 / 710 |
| c k=3 | b7 | exploit2_3 | 3472 | 319 | 630 | 920 | 0 (0.000%) | 535 / 895 |
| c2 pinned, 2 hogs | b8 | night | 5742 | 121 | 239 | 456 | 0 (0.000%) | 245 / 290 |
| c2 pinned, 2 hogs | b8 | elite | 3194 | 132 | 248 | 460 | 0 (0.000%) | 243 / 298 |
| c2 pinned, 2 hogs | b8 | exploit2_hu | 2721 | 131 | 233 | 481 | 0 (0.000%) | 187 / 271 |
| c2 pinned, 2 hogs | b8 | exploit2_3 | 3483 | 107 | 218 | 376 | 0 (0.000%) | 205 / 350 |
| c2 pinned, 2 hogs | b7 | night | 5623 | 119 | 236 | 398 | 0 (0.000%) | 233 / 288 |
| c2 pinned, 2 hogs | b7 | elite | 3058 | 127 | 250 | 424 | 0 (0.000%) | 230 / 296 |
| c2 pinned, 2 hogs | b7 | exploit2_hu | 2762 | 127 | 262 | 844 | 0 (0.000%) | 189 / 268 |
| c2 pinned, 2 hogs | b7 | exploit2_3 | 3383 | 106 | 227 | 1942 | 2 (0.059%) | 192 / 269 |
| c3 pinned, 2 hogs, never sleeps | b8 | night | 5915 | 121 | 8167 | 12118 | 193 (3.263%) | 240 / 8787 |
| c3 pinned, 2 hogs, never sleeps | b8 | elite | 3536 | 130 | 8182 | 8560 | 124 (3.507%) | 247 / 8346 |
| c3 pinned, 2 hogs, never sleeps | b8 | exploit2_hu | 2592 | 128 | 8174 | 16124 | 77 (2.971%) | 180 / 8236 |
| c3 pinned, 2 hogs, never sleeps | b8 | exploit2_3 | 3669 | 108 | 8131 | 8650 | 94 (2.562%) | 194 / 249 |
| c3 pinned, 2 hogs, never sleeps | b7 | night | 5716 | 118 | 8150 | 13518 | 143 (2.502%) | 237 / 8225 |
| c3 pinned, 2 hogs, never sleeps | b7 | elite | 3207 | 128 | 8181 | 12226 | 95 (2.962%) | 240 / 302 |
| c3 pinned, 2 hogs, never sleeps | b7 | exploit2_hu | 2829 | 131 | 8171 | 12092 | 95 (3.358%) | 183 / 8236 |
| c3 pinned, 2 hogs, never sleeps | b7 | exploit2_3 | 3719 | 105 | 8138 | 9770 | 90 (2.420%) | 185 / 8160 |

**Conditions, and what they are worth.**
- **a**: no hogs of ours. Not quiet: the other runs held the load at 14-15 all session, 13-15 running. There was no quiet window, so
  this is "quiet-ish" only in name; the old box's quiet gate (0.04-0.05%) is not comparable.
- **b**: two hogs on top. The sampled rerun read /proc/loadavg once a second: batch 8's run had 16 or more runnable in every one of
  103 samples (mean 18.6); batch 7's in 60% of 63 (median 17, min 13: another run ended a chunk). Oversubscribing further would have
  broken the brief's 3-worker cap. A bot process that sleeps between calls wakes ahead of the busy ones, so load barely shows.
- **c**: batch 2's method (tools/slowbox.py, `--clock cpu`): every clock in the bot's process reads 3 x its thread's CPU time, from
  before the import. **Verified**: the fixed workload reads 33.0 ms on the bot's clock for 11.0 ms of CPU (3.00), and the batch 7 run
  32.2 / 10.7 (3.01). The governor and the deadlines see it. It has no scheduler stalls and it scales memory-bound work
  as much as CPU work, which a real slow box may not. The base is this box's CPU time at load: a sibling thread inflates it.
- **c2**: the bot and two hogs pinned to one logical CPU (`--pin 15 --hogs 2`). The workload that runs flat out does slow (26.9 ms for
  11.2 of CPU, 2.4x), but a decision does not: p99 237 µs, 0 timeouts, because the bot sleeps on its pipe between calls and each
  wake-up preempts a hog. Setup does slow, as it never sleeps. **So a CPU-share "3x" does not model a slower CPU for decisions**; c2
  is here to say so.
- **c3**: as c2, with the bot's process spinning between calls (`--spin`), as under a runner that plays every seat in one process.
  It really gets a third (35.3 ms for 11.5 of CPU, 3.07x), in scheduler slices.

## Through a kit's adapter (tools/gate.py, kit B, plain hold'em, 40 tables strict)

The package behind the fake kit B's adapter, and the same package with no adapter as the pair (`--baseline package`); `--slow K`
puts both on the K-times clock. One fresh process per table. Load 15-17 throughout.

| clock | zip | kit path: tmo % | p50 | p99 | max | import worst, s | no adapter: tmo % | p50 | p99 | paired points (± 95%) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1x | b8 | 0.11 | 251 | 513 | 12098 | 1.08 | 0.06 | 112 | 265 | -0.375 ± 0.478 |
| 1x | b7 | 0.22 | 241 | 530 | 9072 | 0.63 | 0.06 | 109 | 260 | -0.422 ± 0.511 |
| 1.5x | b8 | 0.36 | 381 | 755 | 4404 | 1.05 | 0.20 | 174 | 395 | +0.134 ± 0.605 |
| 1.5x | b7 | 0.47 | 362 | 769 | 4766 | 0.60 | 0.09 | 168 | 357 | -0.684 ± 0.546 |
| 2x | b8 | 1.12 | 518 | 1036 | 4021 | 1.44 | 0.25 | 233 | 499 | -0.222 ± 0.542 |
| 2x | b7 | 1.10 | 485 | 1023 | 9264 | 0.81 | 0.21 | 226 | 499 | -0.055 ± 0.558 |
| 3x | b8 | **11.96** | 783 | 1528 | 8869 | 2.13 | 0.45 | 348 | 757 | -0.580 ± 0.491 |
| 3x | b7 | 7.20 | 723 | 1354 | 4786 | 1.18 | 0.31 | 334 | 699 | -0.449 ± 0.423 |

Read the timeouts, not the points: 40 tables give ±0.5, and the rows disagree in sign at 1.5x (batch 7's GATE FAIL there is this
noise; the same zip passes at 2x). The first row's point gap is the known cost of a kit with no log (the inference), not time.
Kit B is a fake kit: the real kit's adapter may cost less or more, and we will not know until the build starts.

## Setup against every budget

| budget | where it is checked | batch 8 | batch 7 | |
|---|---|---|---|---|
| zip under 100 MB (the rules) | pack `--max-mb` | 3.69 MB zipped, 8.5 MB unzipped | 1.1 MB, 4.8 MB | holds |
| kit H's 20 MB unzipped, 5 MB zipped | pack `--max-mb 20 --max-zip-mb 5` (exit 0) | 8.5, 3.69 | | holds; the 5 MB cap is 74% used |
| 5 s to import and build (pack's default) | pack `--import-budget` | 0.68 s (load 15-17) | 0.30 s (old box) | holds, 3x too |
| kit H's 2 s from launch to hello | pack `--import-budget 2` | 1.07 s at load (exit 0) | | holds at 1x |
| the same at 3x | this file | p50 1.72-1.89 s, worst 1.90-2.06 s, launch to first table up to 2.14 s | p50 0.96-1.09 s, worst 1.04-1.30 s | **over at the worst table** |
| 1 ms a decision, 0.3% of timeouts (the gate) | gate `--max-tmo-pct` | plain 0.47% and 0.11% (load 15-17, the load clause), auction 0.00%, bonus_card 0.11%, tranche 0.06% | 0.22% (today, load 15-17) | holds at 1x |

short_3b.json is 3.0 MB of base85 and hardly compresses: it is most of the zip's growth. Its decode is most of the setup's.

## Not verified

- **The organisers' sandbox**: its speed, whether it is a CPU quota, whether a bot sleeps between calls, whether it starts a process
  per table. Each changes which row above applies.
- **The real kit's adapter.** Every kit-path number is the fake kit B's.
- **A quiet box**: never available this session. Every 1x number is at load 14-17.
- **Twists at 3x**: only plain hold'em and the bot's four rooms were timed; the gate's twists ran at 1x.

## Commands

    python tools/zip_timing.py <zip> --label X --json X.json                      # a
    python tools/zip_timing.py <zip> --hogs 2                                     # b
    python tools/zip_timing.py <zip> --k 3                                        # c
    python tools/zip_timing.py <zip> --pin 15 --hogs 2 [--spin]                   # c2, c3
    python tools/gate.py <zip> --kit b --entry entry_kitb.py --tables 40 --baseline package --max-tmo-pct 100 [--slow K]
