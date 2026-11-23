"""
test_brain.py - quick check that a brain file reacts to an input.

Pokes a group of input neurons (from FlyNeuronIDs.h), runs the brain for a short
time, and prints how often the movement neurons fired. Run it every time you
change build_brains.py, before touching Unreal.

Usage (from the repo root):
    python tools/test_brain.py Content/Brains/dodger.bin --input LOOM_LC4_LEFT --input LOOM_LPLC2_LEFT
    python tools/test_brain.py Content/Brains/sniffer.bin --input SMELL_FRUIT_LEFT

Model: leaky integrate-and-fire neurons with the settings from the 2024
whole-brain fly model (Shiu et al., Nature). Same math the game will run.
"""

import argparse
import re
import struct
import time

import numpy as np

# Neuron settings (millivolts / milliseconds)
V_REST, V_THRESH, V_RESET = -52.0, -45.0, -52.0
TAU_MEMBRANE, TAU_SYNAPSE = 20.0, 5.0
REFRACTORY, DELAY = 2.2, 1.8
MV_PER_SYNAPSE = 0.275           # how much one synapse pushes the target
INPUT_RATE_HZ = 150.0            # how fast poked input neurons are driven
INPUT_KICK = MV_PER_SYNAPSE * 250

OUTPUTS = ["GIANT_FIBER", "MOONWALKER", "WALK_FORWARD", "STEER_A", "STEER_B"]


def load_brain(path):
    """Read a .bin brain (layout documented in build_brains.py)."""
    b = open(path, "rb").read()
    assert b[:4] == b"FLYB", "not a brain file"
    _, n, e = struct.unpack_from("<III", b, 4)
    o = 16
    ids = np.frombuffer(b, "<i8", n, o); o += 8 * n
    o += 12 * n                                   # skip positions
    flags = np.frombuffer(b, "u1", n, o); o += n
    offsets = np.frombuffer(b, "<u4", n + 1, o).astype(np.int64); o += 4 * (n + 1)
    targets = np.frombuffer(b, "<u4", e, o).astype(np.int64); o += 4 * e
    weights = np.frombuffer(b, "<i2", e, o).astype(np.float64)
    return ids, flags, offsets, targets, weights


def load_names(header):
    """Read NAME = { id, id, ... } lists out of FlyNeuronIDs.h."""
    text = open(header).read()
    return {m.group(1): [int(x) for x in re.findall(r"(\d+)LL", m.group(2))]
            for m in re.finditer(r"(\w+)\s*=\s*\{([^}]*)\}", text)}


def run(brain, inputs, ms, dt=0.1, seed=0):
    """Simulate `ms` milliseconds. Returns how many times each neuron fired."""
    ids, _, offsets, targets, weights = brain
    n = len(ids)
    rng = np.random.default_rng(seed)
    v = np.full(n, V_REST)          # membrane voltage
    g = np.zeros(n)                 # incoming synaptic push
    refractory = np.zeros(n)        # time left before a neuron can fire again
    delay_steps = int(round(DELAY / dt))
    pending = [np.zeros(n) for _ in range(delay_steps)]   # spikes still travelling
    fired = np.zeros(n, np.int64)

    for step in range(int(ms / dt)):
        slot = step % delay_steps
        g += pending[slot]
        pending[slot][:] = 0

        if len(inputs):             # random input spikes at INPUT_RATE_HZ
            hit = inputs[rng.random(len(inputs)) < INPUT_RATE_HZ * dt / 1000.0]
            g[hit] += INPUT_KICK

        ready = refractory <= 0
        v[ready] += dt * (V_REST - v[ready] + g[ready]) / TAU_MEMBRANE
        g -= dt * g / TAU_SYNAPSE
        refractory -= dt

        spiking = np.nonzero(v > V_THRESH)[0]
        if len(spiking):
            fired[spiking] += 1
            v[spiking] = V_RESET
            refractory[spiking] = REFRACTORY
            starts, counts = offsets[spiking], offsets[spiking + 1] - offsets[spiking]
            if counts.sum():        # every connection of every spiking neuron
                edges = np.repeat(starts - np.cumsum(counts) + counts, counts) + np.arange(counts.sum())
                np.add.at(pending[slot], targets[edges], MV_PER_SYNAPSE * weights[edges])
    return fired


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brain", help="path to a .bin brain")
    ap.add_argument("--input", action="append", default=[], help="neuron group to poke, e.g. SMELL_FRUIT_LEFT")
    ap.add_argument("--ms", type=float, default=300, help="how long to simulate")
    ap.add_argument("--header", default="Source/fruit_fly_game/FlyNeuronIDs.h")
    args = ap.parse_args()

    brain = load_brain(args.brain)
    ids, flags = brain[0], brain[1]
    names = load_names(args.header)
    slot_of = {int(r): i for i, r in enumerate(ids)}

    def group(name):
        return np.array([slot_of[r] for r in names.get(name, []) if r in slot_of], np.int64)

    print(f"{args.brain}: {len(ids):,} neurons, {len(brain[3]):,} connections")
    inputs = []
    for name in args.input:
        found, total = len(group(name)), len(names.get(name, []))
        print(f"  input {name}: {found} of {total} neurons are in this brain")
        inputs.append(group(name))
    inputs = np.concatenate(inputs) if inputs else np.array([], np.int64)

    for label, poke in [("no input", np.array([], np.int64)), ("with input", inputs)]:
        t0 = time.time()
        fired = run(brain, poke, args.ms)
        moved = int(((fired > 0) & (flags & 1).astype(bool)).sum())
        print(f"\n[{label}]  {args.ms:.0f} ms simulated in {time.time() - t0:.1f} s")
        print(f"  neurons that fired: {int((fired > 0).sum()):,}   movement (descending) neurons that fired: {moved}")
        for out in OUTPUTS:
            left, right = int(fired[group(out + '_LEFT')].sum()), int(fired[group(out + '_RIGHT')].sum())
            print(f"  {out:13s} left {left:>5}   right {right:>5}")


if __name__ == "__main__":
    main()
