"""
check_brain.py - PASS/FAIL checkup for a brain file. Run it before pushing any
change to the brains or to the neuron rule in brainsim.py.

Usage (from the repo root):
    python tools/check_brain.py Content/Brains/dodger.bin
    python tools/check_brain.py Content/Brains/boss.bin
    python tools/check_brain.py Content/Brains/sniffer.bin --reference Content/Brains/boss.bin

Looming is tested with a steady threat (a swatter coming in for 800 ms).
Smell is tested with WHIFFS (100 ms of smell, then a gap, repeated), because
real smell arrives in wisps and the brain reacts to each new whiff.

Checks:
  1. Quiet at rest   - nothing moves with no input
  2. Turns off       - activity dies down after the input stops
  3. Graded          - stronger looming / more frequent whiffs give a stronger response
  4. Right reaction  - smell fires CHASE and never escape; looming escapes and never fires CHASE
  5. Both sides      - looming from the left/right escapes harder on that side
  6. Repeatable      - same result with a different random seed
  7. Faithful        - (only with --reference) a cut brain behaves like its source
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import brainsim as bs

SENSES = {"dodger": ["loom"], "sniffer": ["smell"], "boss": ["loom", "smell"]}
SIDES = ("LEFT", "RIGHT")

# Looming: steady threat, weak / medium / strong (input spikes per second)
LOOM_LEVELS = (10, 30, 100)
LOOM_ON_MS, LOOM_OFF_MS = 800, 500

# Smell: whiffs. Banana far / medium / close = a whiff every 1000 / 700 / 500 ms.
WHIFF_EVERY = (1000, 700, 500)
WHIFF_MS, WHIFF_HZ = 100, 50
WHIFF_PERIOD_MS, WHIFF_OFF_MS = 3000, 600

TURN_OFF_LIMIT = 0.05   # after input stops, activity must fall below 5% of "on"


def group(brain, names, name, side=None):
    return bs.slots(brain, names, *([f"{name}_{side}"] if side else [f"{name}_LEFT", f"{name}_RIGHT"]))


class Trial:
    """One run of the brain. Records movement activity per 100 ms and the output groups."""

    def __init__(self, brain, names, inputs, total_ms, seed=0):
        total, self.windows = bs.simulate(brain, inputs, total_ms, window_ms=100, seed=seed)
        self.movement_mask = (brain["flags"] & 1).astype(bool)
        self.per_window = self.windows[:, self.movement_mask].sum(axis=1)
        self.total = total
        self.brain, self.names = brain, names

    def spikes(self, name, side=None, start_ms=0, stop_ms=None):
        w = self.windows[start_ms // 100:(stop_ms // 100 if stop_ms else None)]
        return int(w[:, group(self.brain, self.names, name, side)].sum())

    def movement_by_id(self):
        ids = self.brain["ids"][self.movement_mask].tolist()
        return dict(zip(ids, self.total[self.movement_mask].tolist()))


def loom_trial(brain, names, side, level, seed=0):
    x = bs.slots(brain, names, f"LOOM_LC4_{side}", f"LOOM_LPLC2_{side}")
    t = Trial(brain, names, [(x, LOOM_LEVELS[level], 0, LOOM_ON_MS)], LOOM_ON_MS + LOOM_OFF_MS, seed)
    t.on = int(t.per_window[3:8].sum()) / 5                 # 300-800 ms: steady response, per 100 ms
    t.off = int(t.per_window[10:].sum()) / 3                # 1000-1300 ms: 200+ ms after it stopped
    t.gf_left = t.spikes("GIANT_FIBER", "LEFT", 0, LOOM_ON_MS)
    t.gf_right = t.spikes("GIANT_FIBER", "RIGHT", 0, LOOM_ON_MS)
    t.chase = t.spikes("CHASE", None, 0, LOOM_ON_MS)
    return t


def whiff_trial(brain, names, side, level, seed=0):
    x = bs.slots(brain, names, f"SMELL_FRUIT_{side}")
    every = WHIFF_EVERY[level]
    onsets = list(range(0, WHIFF_PERIOD_MS, every))
    t = Trial(brain, names, [(x, WHIFF_HZ, s, s + WHIFF_MS) for s in onsets],
              WHIFF_PERIOD_MS + WHIFF_OFF_MS, seed)
    t.on = int(t.per_window[:WHIFF_PERIOD_MS // 100].sum()) / (WHIFF_PERIOD_MS / 100)
    t.off = int(t.per_window[-3:].sum()) / 3                # last 300 ms, 400+ ms after the last whiff
    chase = group(brain, names, "CHASE")
    t.chase_hits = sum(t.windows[s // 100:(s + 200) // 100][:, chase].sum() > 0 for s in onsets) / len(onsets)
    t.chase_per_s = t.spikes("CHASE", None, 0, WHIFF_PERIOD_MS) / (WHIFF_PERIOD_MS / 1000)
    t.gf = t.spikes("GIANT_FIBER", None, 0, WHIFF_PERIOD_MS + WHIFF_OFF_MS)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brain")
    ap.add_argument("--senses", help="comma list, e.g. loom,smell (default: from the file name)")
    ap.add_argument("--reference", help="source brain to compare a cut brain against")
    ap.add_argument("--header", default="Source/fruit_fly_game/FlyNeuronIDs.h")
    ap.add_argument("--ammo-used", type=float, help="override brainsim.AMMO_USED_PER_SPIKE")
    ap.add_argument("--ammo-refill", type=float, help="override brainsim.AMMO_REFILL_MS")
    args = ap.parse_args()
    if args.ammo_used is not None:
        bs.AMMO_USED_PER_SPIKE = args.ammo_used
    if args.ammo_refill is not None:
        bs.AMMO_REFILL_MS = args.ammo_refill

    t0 = time.time()
    brain = bs.load_brain(args.brain)
    names = bs.load_names(args.header)
    senses = args.senses.split(",") if args.senses else SENSES.get(Path(args.brain).stem, ["loom", "smell"])
    print(f"Brain checkup: {args.brain} ({len(brain['ids']):,} neurons), senses: {', '.join(senses)}")
    print(f"  ammo: {bs.AMMO_USED_PER_SPIKE:.0%} used per spike, refill {bs.AMMO_REFILL_MS:.0f} ms\n")

    results = []
    def report(ok, name, detail):
        results.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {name:15s} {detail}")

    rest = Trial(brain, names, [], 500)
    report(int(rest.per_window.sum()) == 0, "Quiet at rest", f"{int(rest.per_window.sum())} movement spikes with no input")

    loom = {(s, l): loom_trial(brain, names, s, l) for s in SIDES for l in range(3)} if "loom" in senses else {}
    smell = {(s, l): whiff_trial(brain, names, s, l) for s in SIDES for l in range(3)} if "smell" in senses else {}

    # 2. Turns off
    rows, ok = [], True
    for label, trials in (("loom", loom), ("smell", smell)):
        if trials:
            worst = max(trials.values(), key=lambda t: t.off / max(t.on, 1))
            ratio = worst.off / max(worst.on, 1)
            ok &= worst.on > 0 and ratio <= TURN_OFF_LIMIT
            rows.append(f"{label}: worst {worst.on:.0f} -> {worst.off:.0f} per 100 ms ({ratio:.0%})")
    report(ok, "Turns off", "   ".join(rows))

    # 3. Graded
    rows, ok = [], True
    if loom:
        v = [sum(loom[(s, l)].on for s in SIDES) for l in range(3)]
        ok &= v[0] <= v[1] <= v[2] and v[0] < 0.8 * v[2]
        rows.append("looming weak/medium/strong = " + "/".join(f"{x:.0f}" for x in v))
    if smell:
        v = [sum(smell[(s, l)].chase_per_s for s in SIDES) for l in range(3)]
        ok &= v[0] <= v[1] <= v[2] and v[0] < 0.8 * v[2]
        rows.append("CHASE per s, banana far/medium/close = " + "/".join(f"{x:.0f}" for x in v))
    report(ok, "Graded", "   ".join(rows))

    # 4. Right reaction
    rows, ok = [], True
    if smell:
        gf = max(t.gf for t in smell.values())
        hits = min(t.chase_hits for t in smell.values())
        ok &= gf <= 2 and hits >= 0.9
        rows.append(f"whiffs -> CHASE on {hits:.0%} of whiffs (want 90%+), escape {gf} (want ~0)")
    if loom:
        gf = min(loom[(s, 2)].gf_left + loom[(s, 2)].gf_right for s in SIDES)
        chase = max(t.chase for t in loom.values())
        ok &= gf >= 5 and chase <= 2
        rows.append(f"strong looming -> escape {gf} (want 5+), CHASE {chase} (want ~0)")
    report(ok, "Right reaction", "   ".join(rows))

    # 5. Both sides (looming)
    if loom:
        rows, ok = [], True
        for l in (1, 2):
            a, b = loom[("LEFT", l)], loom[("RIGHT", l)]
            ok &= a.gf_left > a.gf_right and b.gf_right > b.gf_left
            rows.append(f"{LOOM_LEVELS[l]} Hz: from left {a.gf_left}/{a.gf_right}, from right {b.gf_left}/{b.gf_right}")
        report(ok, "Both sides", "escape L/R   " + "   ".join(rows))

    # 6. Repeatable
    rows, ok = [], True
    if loom:
        a, b = loom[("LEFT", 1)].on, loom_trial(brain, names, "LEFT", 1, seed=1).on
        d = abs(a - b) / max(a, b, 1); ok &= d <= 0.25
        rows.append(f"looming {a:.0f} vs {b:.0f} ({d:.0%} apart)")
    if smell:
        a, b = smell[("LEFT", 1)].chase_per_s, whiff_trial(brain, names, "LEFT", 1, seed=1).chase_per_s
        d = abs(a - b) / max(a, b, 1); ok &= d <= 0.25
        rows.append(f"CHASE {a:.0f} vs {b:.0f} per s ({d:.0%} apart)")
    report(ok, "Repeatable", "seed 0 vs 1:  " + "   ".join(rows))

    # 7. Faithful
    if args.reference:
        ref = bs.load_brain(args.reference)
        rs = []
        for sense, trials, make in (("loom", loom, loom_trial), ("smell", smell, whiff_trial)):
            for s in SIDES if trials else ():
                mine, theirs = trials[(s, 1)].movement_by_id(), make(ref, names, s, 1).movement_by_id()
                common = [i for i in mine if i in theirs]
                x, y = np.array([mine[i] for i in common]), np.array([theirs[i] for i in common])
                rs.append(np.corrcoef(x, y)[0, 1] if x.std() and y.std() else 0.0)
        report(min(rs) >= 0.95, "Faithful", f"movement neurons vs {Path(args.reference).name}: worst r = {min(rs):.3f} (want 0.95+)")

    print(f"\nResult: {sum(results)}/{len(results)} passed   ({time.time() - t0:.0f} s)")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
