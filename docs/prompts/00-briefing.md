# Prompt 00: briefing (paste as the agent's first message, minute 0)

You are helping me build a poker bot in a 60-minute window for a tournament. Read this fully before
doing anything, then restate the constraints in one paragraph and wait for my next message.

Hard constraints from the organizers:
- The bot is Python and implements the Agent interface in the starter kit I will give you.
- Every decision must return within ONE MILLISECOND. An exception or a timeout is scored as a fold.
  Therefore: no Monte Carlo, no search, no solving, no big allocations at decision time. Lookups and
  arithmetic only. Anything expensive runs at import or at the start of a table.
- No network. Submission under 100 MB. Only the standard library is guaranteed; treat any other
  import as forbidden unless the kit itself imports it.
- Format: eight-player sit-and-go tables, 2,000 starting chips, blinds 10/20 rising every 25 hands,
  table ends at bust-out or 200 hands, points by finishing position with ICM splitting remaining
  points among survivors. Scores average over 10,000 tables, so variance is not our friend and
  survival is worth a lot. Our opponents are other teams' one-hour bots.
- The poker variant is a twist on hold'em that I will paste next. Do not assume standard rules.

How we work:
- I have a prepared repository at the path I give you (if I do not give one, we build from scratch
  using the specification I paste). Strategy code never imports the kit. One Adapter translates the
  kit's state into our Observation and our Action back. You write that adapter; you do not rewrite
  strategy.
- Priority order, non-negotiable: (1) a bot that never crashes and never returns an illegal action,
  submitted within 15 minutes; (2) the prepared Hero wired through the adapter and verified in our
  simulator in strict 1 ms mode; (3) the smallest strategy change the variant forces. Nothing else.
- Verify with commands, not by reading code. After every change run the kit's local simulator and
  our test suite and show me the output. If a check fails, fix it before moving on.
- Ask me at most one question at a time, and only when the rules or kit are genuinely ambiguous.
  Otherwise pick the conservative option (fold, check, smaller bet) and tell me what you picked.
- Keep a running file `NIGHT.md` with: the rule sheet, every command that verified something, the
  hash of each file we submitted, and the time.

Restate the constraints now in one paragraph. Do not write code yet.
