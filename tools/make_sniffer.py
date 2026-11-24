"""
make_sniffer.py - builds the sniffer brain by trimming the boss brain.

How: run smell whiffs through the boss (left and right antenna, banana far to
close, a few random seeds) and keep every neuron that fires, plus every named
neuron in FlyNeuronIDs.h. In our model a neuron that never fires has no effect
on any other neuron, so the trimmed sniffer reacts to smell like the boss does,
at a fraction of the size.

Run it after build_brains.py (which calls it automatically), or by itself:
    python tools/make_sniffer.py

Re-run it whenever the boss brain or the neuron rule in brainsim.py changes,
then check the result:
    python tools/check_brain.py Content/Brains/sniffer.bin --reference Content/Brains/boss.bin
"""

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import brainsim as bs

WHIFF_EVERY = (1000, 700, 500)   # banana far / medium / close (ms between whiffs)
WHIFF_MS, WHIFF_HZ = 100, 50
RUN_MS = 3000
SEEDS = (0, 1, 2)


def read_bin(path):
    """Everything in a .bin file, positions included (so we can write it back)."""
    b = open(path, "rb").read()
    _, n, e = struct.unpack_from("<III", b, 4)
    o = 16
    ids = np.frombuffer(b, "<i8", n, o); o += 8 * n
    pos = np.frombuffer(b, "<f4", 3 * n, o).reshape(n, 3); o += 12 * n
    flags = np.frombuffer(b, "u1", n, o); o += n
    offsets = np.frombuffer(b, "<u4", n + 1, o).astype(np.int64); o += 4 * (n + 1)
    targets = np.frombuffer(b, "<u4", e, o).astype(np.int64); o += 4 * e
    weights = np.frombuffer(b, "<i2", e, o)
    return ids, pos, flags, offsets, targets, weights


def write_bin(path, ids, pos, flags, offsets, targets, weights):
    with open(path, "wb") as f:
        f.write(b"FLYB")
        f.write(struct.pack("<III", 1, len(ids), len(targets)))
        f.write(ids.astype("<i8").tobytes())
        f.write(pos.astype("<f4").tobytes())
        f.write(flags.astype("u1").tobytes())
        f.write(offsets.astype("<u4").tobytes())
        f.write(targets.astype("<u4").tobytes())
        f.write(weights.astype("<i2").tobytes())


def build(boss_path, header, out_path):
    brain = bs.load_brain(boss_path)
    names = bs.load_names(header)
    n = len(brain["ids"])

    # 1. Which neurons does smell actually use?
    used = np.zeros(n, bool)
    for side in ("LEFT", "RIGHT"):
        x = bs.slots(brain, names, f"SMELL_FRUIT_{side}")
        for every in WHIFF_EVERY:
            for seed in SEEDS:
                whiffs = [(x, WHIFF_HZ, t, t + WHIFF_MS) for t in range(0, RUN_MS, every)]
                fired, _ = bs.simulate(brain, whiffs, RUN_MS, seed=seed)
                used |= fired > 0
    keep = used.copy()
    keep[bs.slots(brain, names, *names.keys())] = True     # every named input and output

    # 2. Copy those neurons, and the connections between them, into a new file.
    ids, pos, flags, offsets, targets, weights = read_bin(boss_path)
    new_slot = np.full(n, -1, np.int64)
    new_slot[keep] = np.arange(keep.sum())
    sender = np.repeat(np.arange(n), np.diff(offsets))
    kept_edge = keep[sender] & keep[targets]
    s, t, w = new_slot[sender[kept_edge]], new_slot[targets[kept_edge]], weights[kept_edge]
    order = np.argsort(s, kind="stable")                    # keep each neuron's connections together
    s, t, w = s[order], t[order], w[order]
    new_offsets = np.zeros(keep.sum() + 1, np.int64)
    new_offsets[1:] = np.cumsum(np.bincount(s, minlength=keep.sum()))
    write_bin(out_path, ids[keep], pos[keep], flags[keep], new_offsets, t, w)

    mb = Path(out_path).stat().st_size / 1e6
    print(f"sniffer  {keep.sum():>7,} neurons  {kept_edge.sum():>10,} connections  {mb:6.1f} MB  -> {out_path}"
          f"   ({used.sum():,} used by smell + named neurons)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boss", default="Content/Brains/boss.bin")
    ap.add_argument("--header", default="Source/fruit_fly_game/FlyNeuronIDs.h")
    ap.add_argument("--out", default="Content/Brains/sniffer.bin")
    args = ap.parse_args()
    build(args.boss, args.header, args.out)


if __name__ == "__main__":
    main()
