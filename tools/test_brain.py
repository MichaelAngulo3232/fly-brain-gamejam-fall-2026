"""
test_brain.py - quick look at how a brain file reacts to an input.

Pokes a group of input neurons (from FlyNeuronIDs.h), runs the brain, and prints
how often the movement neurons fired. For PASS/FAIL checks use check_brain.py.

Usage (from the repo root):
    python tools/test_brain.py Content/Brains/dodger.bin --input LOOM_LC4_LEFT --input LOOM_LPLC2_LEFT
    python tools/test_brain.py Content/Brains/sniffer.bin --input SMELL_FRUIT_LEFT --rate 50

The simulation itself lives in brainsim.py (the same math the game will run).
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import brainsim as bs

OUTPUTS = ["GIANT_FIBER", "MOONWALKER", "WALK_FORWARD", "STEER_A", "STEER_B"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brain", help="path to a .bin brain")
    ap.add_argument("--input", action="append", default=[], help="neuron group to poke, e.g. SMELL_FRUIT_LEFT")
    ap.add_argument("--rate", type=float, default=150, help="how fast to poke the inputs (spikes per second)")
    ap.add_argument("--ms", type=float, default=300, help="how long to simulate")
    ap.add_argument("--header", default="Source/fruit_fly_game/FlyNeuronIDs.h")
    args = ap.parse_args()

    brain = bs.load_brain(args.brain)
    names = bs.load_names(args.header)
    movement = (brain["flags"] & 1).astype(bool)
    print(f"{args.brain}: {len(brain['ids']):,} neurons, {len(brain['targets']):,} connections")
    for name in args.input:
        print(f"  input {name}: {len(bs.slots(brain, names, name))} of {len(names.get(name, []))} neurons are in this brain")
    inputs = bs.slots(brain, names, *args.input)

    for label, poke in [("no input", []), ("with input", [(inputs, args.rate, 0, args.ms)])]:
        t0 = time.time()
        fired, _ = bs.simulate(brain, poke, args.ms)
        print(f"\n[{label}]  {args.ms:.0f} ms simulated in {time.time() - t0:.1f} s")
        print(f"  neurons that fired: {int((fired > 0).sum()):,}   "
              f"movement (descending) neurons that fired: {int(((fired > 0) & movement).sum())}")
        for out in OUTPUTS:
            left = int(fired[bs.slots(brain, names, out + "_LEFT")].sum())
            right = int(fired[bs.slots(brain, names, out + "_RIGHT")].sum())
            print(f"  {out:13s} left {left:>5}   right {right:>5}")


if __name__ == "__main__":
    main()
