"""Reference kit C submission: a script that speaks the line protocol on stdin/stdout."""
import sys

from hyperion.drills.adapter import KitCAdapter, _default_bot

if __name__ == "__main__":
    KitCAdapter(_default_bot()).serve(sys.stdin, sys.stdout)
