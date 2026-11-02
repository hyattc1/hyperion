"""tools/latency.py --native submission.latency_native:build: an Observation -> the snapshot dict player.py
hands the adapter (kit-style: street = board length, pot includes this street's bets, string cards)."""
_R, _S = "23456789TJQKA", "cdhs"


def _cs(c):
    return _R[c >> 2] + _S[c & 3]


def build(obs):
    n = len(obs.stacks)
    me = obs.seat
    opts = {}
    for k in ("fold", "check", "call", "raise"):
        if any(a.value == k for a in obs.legal):
            opts[k] = {"move": k}
    if "call" in opts:
        opts["call"] = {"move": "call", "amount": obs.bets[me] + obs.to_call, "cost": obs.to_call}
    if "raise" in opts:
        opts["raise"] = {"move": "raise", "min": obs.min_raise, "max": obs.max_raise}
    return {"n": n, "seat": me, "button": obs.button, "hand": obs.hand_no + 1, "sb": obs.blinds[0],
            "bb": obs.blinds[1], "street": len(obs.board), "board": [_cs(c) for c in obs.board],
            "hole": [_cs(c) for c in obs.hole], "stacks": {s: obs.stacks[s] for s in range(n)},
            "bets": {s: obs.bets[s] for s in range(n)}, "in_hand": {s for s in range(n) if obs.in_hand[s]},
            "pot": obs.pot + sum(obs.bets), "options": opts,
            "log": [(s, len(obs.board), a.kind.value, a.amount) for s, a in obs.history]}
