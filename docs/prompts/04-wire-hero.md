# Prompt 04: wire Hero and verify in strict mode (minute 25; box 15 minutes)

Swap `Hero.cheap()` in the entry point for `hyperion.strategy.hero.make_bot()` (default Config), same
adapter and `rules_tonight.json`. Verify in this order, pasting every output:

1. Kit's local simulator, 100 hands, `HYPERION_CHECK=1`: zero exceptions, illegal actions and
   conformance violations (`history_raise` and `history_prefix` included: Hero reads raises from the
   history), under 0.3% of decisions over 1 ms.
2. Print one Hero flop decision through the adapter on remapped cards (state built from a round start,
   or the pot reads 0). Then `python -m hyperion.sim --tables 300 --seed 11 --mode strict
   --field realistic --rules rules_tonight.json` (and `--variant <name>` if the catalog has tonight's
   twist). Required: hero exc 0, ill 0, p99 under 300 µs, tmo under 0.3% of hands as printed
   (if the box load average exceeds the core count, re-run on a quiet box before failing the gate; the
   rate is 0.3% at normal load), points within hero's own ±95% of the Verifier's re-measured Stage 0
   number (else the plain one; say so). Hero vs tag is not the gate. Unrepresentable rule: caption
   every line "variant minus <rule>".
3. Same with `--rotate --tables 40`; hero not last among the field's chart bots (tag, pushfold).
4. Latency under load: in a second terminal `python tools/gen_tables.py --rules rules_tonight.json --out
   /tmp/load --workers 4` (not the real `tables/`; skip if load is over one per core), then
   `python tools/latency.py --bot hero --n 2000 --rules rules_tonight.json` (add `--adapter
   submission.adapter:TonightAdapter --native kit_<a|b|c|d>`; real kit: `module:build`, see
   `latency.py`'s kit_d builder; it deals the rules' hole cards and board). Required: exit 0 (p99 under
   500 µs), over 1 ms under 0.3%; if not,
   `Config.use_profiler=False`, then `Config.cheap=True` (a point). Kill the generator.
5. `python tools/pack.py --entry submission/<entry>.py --out dist/ --extra submission/adapter.py
   submission/rules_tonight.json --note "hero, default Config"`: fails on a fresh-process import over
   5 s (then load tables at table start), vendors the variant set the rules name, zips, writes the
   sha256 row: the submission.
6. Gate the zip itself, the step 2 sim measured in-sim Hero: `python tools/gate.py dist/submission.zip
   --kit <same as Stage 2> --tables 100 --rules rules_tonight.json` (plus `--variant <name>`; about
   2 minutes). Required: `GATE PASS` (0 exceptions, 0 illegal, and the package not behind in-sim Hero
   beyond the paired interval; drill 6's upload was 2.5 points behind and would have failed). Paste the
   last four lines. FAIL: do not upload. Run it on every zip before every upload, tonight's later ones
   included (a window may use `--tables 40`).

If 1, 2 or 6 fails and the fix is not obvious in 5 minutes, resubmit the Stage 2 `Hero.cheap()`
package unchanged; no intermediate bot. Record the shipped config and sha256 in `NIGHT.md`.
