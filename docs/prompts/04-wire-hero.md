# Prompt 04: wire Hero and verify in strict mode (minute 25; box 15 minutes)

Replace `Hero.cheap()` in the entry point with `hyperion.strategy.hero.make_bot()` (default Config)
behind the same adapter and `rules_tonight.json`. Verify in this order and paste every output:

1. Kit's local simulator, 100 hands, `HYPERION_CHECK=1`: zero exceptions, zero illegal actions, zero
   conformance violations, under 0.3% of decisions over 1 ms.
2. The Stage 0 command plus tonight's rules: `python -m hyperion.sim --tables 300 --seed 11 --mode strict
   --field realistic --rules rules_tonight.json`. First print one Hero flop decision through the adapter
   on remapped cards. Required: hero exc 0, ill 0, p99 under 300 µs, tmo under 0.3% of hands as printed,
   and hero's points within its own ±95% of the Stage 0 known-good number in `NIGHT.md` (re-measured with
   `--rules` if payouts or schedule changed). Hero vs tag is not the gate. A rule the engine cannot
   represent: run everything else and caption every line "variant minus <rule>".
3. The same with `--rotate --tables 40`. Hero must not be last among tag, nit, hero.
4. Latency under load: in a second terminal `python tools/gen_tables.py --rules rules_tonight.json --out
   /tmp/load --workers 4` (never the real `tables/`), then `python tools/latency.py --bot hero --n 2000
   --rules rules_tonight.json` (add `--adapter submission.adapter:TonightAdapter --native <module:func>`
   if you wrote an Observation-to-native builder; fake kits: `--native kit_b`). Required: exit 0 (p99
   under 500 µs) and over-1 ms count under 0.3%. If not: check the load, then `Config.use_profiler=False`;
   `Config.cheap=True` last, it costs about a point. Kill the generator.
5. `python tools/pack.py --entry submission/<entry>.py --out dist/ --extra submission/adapter.py --note
   "hero, default Config"`: it times the import from a fresh process in another directory and fails over
   5 s (then move table loading to the table-start callback and re-run), zips, and writes the sha256 row.
   That row is the submission.

If 1 or 2 fails and the fix is not obvious inside 5 minutes, fall back: resubmit the Stage 2 `Hero.cheap()`
package unchanged; there is no intermediate bot. Record the shipped configuration and its sha256 in `NIGHT.md`.
