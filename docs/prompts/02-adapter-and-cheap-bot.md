# Prompt 02: adapter and cheap bot (minute 7; hard stop at minute 15 with a submission)

Using the rule sheet, write the adapter and submit our cheap bot. Time box: 8 minutes. If at minute
6 of this box the adapter is not clean, submit the kit's own example bot instead and tell me.

Track A (repo present):
1. Read `hyperion/drills/adapter.py` (the `Adapter` base class and the three reference adapters)
   and `hyperion/core/types.py` (`Observation`, `Action`, `Rules`). Create `submission/adapter.py`
   with a subclass that translates the kit's native state into `Observation` and our `Action` back
   into the kit's action format. Pay attention to: raise amounts as raise-to totals (ours) versus
   increments (theirs); whether their pot includes the current street's bets (ours excludes them);
   card encoding (we use rank*4+suit with 2=0 ... A=12, suits c,d,h,s = 0..3); seat numbering and
   the button; how legal actions are exposed.
2. Create the kit's entry point so that it instantiates `hyperion.strategy.hero.Hero.cheap()` wrapped
   in the adapter, with everything imported and warmed at module import, not on the first decision.
3. Make the adapter's `native_safe` return the kit's representation of check-else-fold. Every kit
   call must be wrapped so that any exception returns that.
4. Vendor what the submission needs: copy `hyperion/` and `tables/` into `submission/` so it has no
   dependency on the repo path. Confirm the import works from a fresh Python process started in a
   different directory.
5. Run the kit's local simulator for at least 50 hands against its built-in opponents. Show me the
   output. Required: zero exceptions, zero illegal actions, max decision time under 0.5 ms after the
   first call, and the bot folds, calls and raises at least once each.
6. Run our test suite (`python -m pytest -q`) from the repo root; it must stay green.
7. Package what the rules say to submit. If the rules and kit are silent on layout, zip `submission/`
   with the entry point at the top level and say so. Record the sha256 and the time in `NIGHT.md`,
   and tell me to submit.

Track B (blank directory): do steps 1 to 7 but with the cheap bot from the from-scratch spec I
pasted: a tight hand list preflop, push or fold under 12 big blinds, check-call with top pair or
better postflop, fold otherwise, no bluffs. It must be under 150 lines and have no imports beyond
the standard library.

Do not optimize anything. Do not touch strategy. Report with the command outputs, not prose.
