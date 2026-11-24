"""
brainsim.py - the fly brain simulation, shared by test_brain.py and check_brain.py.

This is the reference version of the math. The C++ brain component in Unreal
must do exactly the same thing, so what we test here is what the game runs.

Model: leaky integrate-and-fire neurons with the settings from the 2024
whole-brain fly model (Shiu et al., Nature), plus synaptic depression ("ammo"):
every spike uses up part of a neuron's ammo, so a neuron that fires nonstop
gets weaker. Ammo refills over time.
"""

import re
import struct

import numpy as np

# --- Neuron settings (millivolts / milliseconds) -------------------------------
V_REST, V_THRESH, V_RESET = -52.0, -45.0, -52.0
TAU_MEMBRANE, TAU_SYNAPSE = 20.0, 5.0
REFRACTORY, DELAY = 2.2, 1.8
MV_PER_SYNAPSE = 0.275           # how much one synapse pushes the target
INPUT_KICK = MV_PER_SYNAPSE * 250  # how hard a game input spike pushes an input neuron
DT = 0.1                         # simulation step

# --- Ammo (synaptic depression) -----------------------------------------------
# Tuned with check_brain.py: 50% / 300 ms makes the dodger and the boss pass
# (they calm down after input stops and escape on the correct side).
AMMO_USED_PER_SPIKE = 0.5        # fraction of remaining ammo each spike uses (0 = off)
AMMO_REFILL_MS = 300.0           # how fast ammo refills (time constant)


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
    return {"ids": ids, "flags": flags, "offsets": offsets, "targets": targets, "weights": weights,
            "slot": {int(r): i for i, r in enumerate(ids)}}


def load_names(header):
    """Read NAME = { id, id, ... } lists out of FlyNeuronIDs.h."""
    text = open(header).read()
    return {m.group(1): [int(x) for x in re.findall(r"(\d+)LL", m.group(2))]
            for m in re.finditer(r"(\w+)\s*=\s*\{([^}]*)\}", text)}


def slots(brain, names, *groups):
    """FlyWire IDs of the named groups -> slots in this brain (missing IDs skipped)."""
    s = brain["slot"]
    return np.array([s[r] for g in groups for r in names.get(g, []) if r in s], np.int64)


def simulate(brain, inputs, total_ms, window_ms=100, seed=0,
             ammo_used=None, ammo_refill_ms=None):
    """
    Run the brain.
      inputs: list of (slots, rate_hz, start_ms, stop_ms): poke these neurons
              at rate_hz between start_ms and stop_ms.
    Returns (spikes per neuron over the whole run,
             spikes per neuron per window: array [windows, neurons]).
    """
    used = AMMO_USED_PER_SPIKE if ammo_used is None else ammo_used
    refill = AMMO_REFILL_MS if ammo_refill_ms is None else ammo_refill_ms
    offsets, targets, weights = brain["offsets"], brain["targets"], brain["weights"]
    n = len(brain["ids"])
    rng = np.random.default_rng(seed)

    v = np.full(n, V_REST)           # membrane voltage
    g = np.zeros(n)                  # incoming synaptic push
    refractory = np.zeros(n)         # time left before a neuron can fire again
    ammo = np.ones(n)                # 1 = full strength
    last_spike = np.full(n, -1e9)    # when each neuron last fired
    delay_steps = int(round(DELAY / DT))
    pending = [np.zeros(n) for _ in range(delay_steps)]   # spikes still travelling

    steps = int(round(total_ms / DT))
    steps_per_window = int(round(window_ms / DT))
    windows = np.zeros((int(np.ceil(steps / steps_per_window)), n), np.int32)

    for step in range(steps):
        t = step * DT
        slot = step % delay_steps
        g += pending[slot]
        pending[slot][:] = 0

        for inp, rate, start, stop in inputs:        # game input: random spikes at `rate`
            if start <= t < stop and len(inp):
                hit = inp[rng.random(len(inp)) < rate * DT / 1000.0]
                g[hit] += INPUT_KICK

        ready = refractory <= 0
        v[ready] += DT * (V_REST - v[ready] + g[ready]) / TAU_MEMBRANE
        g -= DT * g / TAU_SYNAPSE
        refractory -= DT

        spiking = np.nonzero(v > V_THRESH)[0]
        if len(spiking):
            windows[step // steps_per_window, spiking] += 1
            v[spiking] = V_RESET
            refractory[spiking] = REFRACTORY

            # Ammo: refill since the last spike (only computed now, at the spike),
            # fire at current strength, then use some up.
            strength = np.ones(len(spiking))
            if used > 0:
                since = t - last_spike[spiking]
                a = 1.0 - (1.0 - ammo[spiking]) * np.exp(-since / refill)
                strength = a
                ammo[spiking] = a * (1.0 - used)
                last_spike[spiking] = t

            starts, counts = offsets[spiking], offsets[spiking + 1] - offsets[spiking]
            if counts.sum():                          # every connection of every spiking neuron
                edges = np.repeat(starts - np.cumsum(counts) + counts, counts) + np.arange(counts.sum())
                np.add.at(pending[slot], targets[edges],
                          MV_PER_SYNAPSE * weights[edges] * np.repeat(strength, counts))

    return windows.sum(axis=0), windows
