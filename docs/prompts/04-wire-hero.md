# Prompt 04: wire Hero and verify in strict mode (minute 25; box 15 minutes)

Replace `Hero.cheap()` in the submission entry point with `hyperion.strategy.hero.make_bot()` using
the default Config, behind the same adapter. Then verify, in this order, and paste every output:

1. Kit's local simulator, 100 hands. Zero exceptions, zero illegal actions, max decision time after
   the first call under 0.5 ms.
2. Our simulator through the adapter in strict mode:
   `python -m hyperion.sim --tables 300 --seed 11 --mode strict --rules rules_tonight.json
    --bots hero,tag,nit,naive,station,maniac,random,allin`
   (omit `--rules` if no rules file was needed). Before reading the table, print one Hero decision
   on a remapped flop through the adapter to prove strategy sees canonical cards. Required: hero
   exceptions 0, illegal 0, p99 under 300 µs, strict-mode timeouts under 0.3% of hero decisions
   (timeouts are OS jitter proportional to time spent in act(); compare rates, never counts against
   a 1 µs bot), hero points at least equal to tag's minus the confidence interval. If the engine
   cannot represent the variant, run the standard game and say so.
3. The same with `--rotate --tables 40` so seating luck cancels. Hero must not be last among tag, nit,
   hero.
4. Latency under load: run the strict sim while a second process runs the table generator, and
   report hero's p99 and max. If timeouts exceed 0.3% of decisions, first check the load (another
   sim or the generator running), then try `Config.use_profiler=False`; `Config.cheap=True` is a last
   resort because it costs about a point.
5. Start a fresh Python process in a different directory, import the submission entry point, and
   time the import. If it exceeds 5 seconds, move table loading from import time to the table-start
   callback and re-measure. Importing must never do Monte Carlo.

If 1 or 2 fails and the fix is not obvious inside 5 minutes, fall back: keep the cheap bot's preflop
and push/fold, enable only the profiler and its dead-seat and station flags, and verify again. Record
which configuration is in the submission in `NIGHT.md` with its sha256.
