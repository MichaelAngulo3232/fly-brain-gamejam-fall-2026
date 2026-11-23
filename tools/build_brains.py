"""
build_brains.py — turns the FlyWire Codex CSVs into compact .bin brain files
that the Unreal game loads (one file per enemy type).

Usage (from the repo root):
    pip install pandas numpy
    python tools/build_brains.py --data data --out Content/Brains

Inputs (FAFB v783, from https://codex.flywire.ai/api/download into data/):
    connections_princeton.csv.gz    pre_root_id, post_root_id, neuropil, syn_count, nt_type
                                    ("Connections (Filtered)", 5+ synapses)
    classification.csv.gz           root_id, flow, super_class, class, sub_class, hemilineage, side, nerve
    consolidated_cell_types.csv.gz  root_id, primary_type, additional_type(s)  ("Cell Types")
    coordinates.csv.gz              root_id, position, supervoxel_id  ("Marked Neuron Coordinates")

Output .bin layout (little-endian), one file per brain:
    char[4]   magic "FLYB"
    uint32    version (1)
    uint32    N  number of neurons
    uint32    E  number of connections
    int64[N]  root_id         FlyWire ID of each neuron (index i -> real neuron)
    float[N*3] position xyz   in micrometers (0,0,0 if unknown)
    uint8[N]  flags           bit0 = descending (movement output) neuron
    uint32[N+1] offsets       connections of neuron i are targets[offsets[i]:offsets[i+1]]
    uint32[E] targets         index of the receiving neuron
    int16[E]  weights         synapse count, negative if inhibitory
"""

import argparse
import struct
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Enemy brain definitions. Edit these to change what each enemy "has".
# A neuron is kept if it matches ANY rule in the list.
#   neuropils   -> neuron has a synapse in one of these brain regions
#   super_class -> FlyWire's broad category (e.g. "descending")
#   cell_types  -> specific named cell types
#   all_except_super_class -> every neuron EXCEPT these broad categories
# NOTE: region and cell-type names below should be double-checked against the
# Codex data before relying on them (look them up at codex.flywire.ai).
# ---------------------------------------------------------------------------
BRAINS = {
    # Smell only: antennal lobe + lateral horn, plus movement outputs
    "sniffer": {
        "neuropils": ["AL_L", "AL_R", "LH_L", "LH_R"],
        "super_class": ["descending"],
        "cell_types": [],
    },
    # Danger vision + escape: looming detectors, giant fiber, movement outputs
    "dodger": {
        "neuropils": [],
        "super_class": ["descending"],
        "cell_types": ["LC4", "LPLC2", "DNp01"],  # DNp01 = giant fiber
    },
    # Whole central brain, without the optic lobes (the eye's pixel processing).
    # The game feeds the looming detectors directly, so the optic lobes would sit idle.
    "boss": {
        "all_except_super_class": ["optic", "visual_projection", "visual_centrifugal"],
        "cell_types": ["LC4", "LPLC2"],  # keep our looming inputs (they are visual projection neurons)
    },
}

# Neurotransmitters treated as inhibitory (others count as excitatory)
INHIBITORY = {"GABA", "GLUT"}


def first_existing(data_dir: Path, names):
    for n in names:
        if (data_dir / n).exists():
            return data_dir / n
    raise FileNotFoundError(f"None of {names} found in {data_dir}/")


def load(data_dir: Path):
    # Codex names the filtered (5+ synapse) table connections_princeton.csv.gz
    conn = pd.read_csv(first_existing(data_dir, ["connections_princeton.csv.gz", "connections.csv.gz"]))
    cls = pd.read_csv(data_dir / "classification.csv.gz")
    # Cell types live in their own file (root_id, primary_type, additional_type(s));
    # merge primary_type in as cell_type so the rest of the script can use it.
    types_path = data_dir / "consolidated_cell_types.csv.gz"
    if types_path.exists():
        types = pd.read_csv(types_path)[["root_id", "primary_type"]]
        cls = cls.merge(types.rename(columns={"primary_type": "cell_type"}), on="root_id", how="left")
    elif "cell_type" not in cls.columns:
        print("  WARNING: consolidated_cell_types.csv.gz not found; cell-type rules and the constants file will be empty")
        cls["cell_type"] = None
    coords_path = data_dir / "coordinates.csv.gz"
    coords = pd.read_csv(coords_path) if coords_path.exists() else None
    return conn, cls, coords


def pick_neurons(spec, conn, cls):
    """Return the set of root_ids that belong to this brain."""
    everyone = set(conn["pre_root_id"]) | set(conn["post_root_id"])
    if spec == "ALL":
        return everyone
    keep = set()
    if spec.get("all_except_super_class"):
        for sc in spec["all_except_super_class"]:
            n = int((cls["super_class"] == sc).sum())
            note = "" if n else "   WARNING: none found, check the name on Codex"
            print(f"  removing {n:>7,} '{sc}' neurons{note}")
        dropped = set(cls.loc[cls["super_class"].isin(spec["all_except_super_class"]), "root_id"])
        keep |= everyone - dropped
    if spec.get("neuropils"):
        in_region = conn[conn["neuropil"].isin(spec["neuropils"])]
        keep |= set(in_region["pre_root_id"]) | set(in_region["post_root_id"])
    if spec.get("super_class"):
        keep |= set(cls.loc[cls["super_class"].isin(spec["super_class"]), "root_id"])
    if spec.get("cell_types"):
        keep |= set(cls.loc[cls["cell_type"].isin(spec["cell_types"]), "root_id"])
    return keep


def build(name, ids, conn, cls, coords, out_dir: Path):
    ids = np.array(sorted(ids), dtype=np.int64)
    index = pd.Series(np.arange(len(ids), dtype=np.uint32), index=ids)

    # Keep only connections where both ends are in this brain.
    c = conn[conn["pre_root_id"].isin(index.index) & conn["post_root_id"].isin(index.index)]
    # The same pair can appear once per brain region: add them together.
    c = c.assign(sign=np.where(c["nt_type"].isin(INHIBITORY), -1, 1))
    c = c.assign(w=c["syn_count"] * c["sign"])
    c = c.groupby(["pre_root_id", "post_root_id"], as_index=False)["w"].sum()

    pre = index.loc[c["pre_root_id"]].to_numpy()
    post = index.loc[c["post_root_id"]].to_numpy()
    w = np.clip(c["w"].to_numpy(), -32768, 32767).astype(np.int16)

    # Sort by sender so each neuron's outgoing connections sit together (CSR).
    order = np.argsort(pre, kind="stable")
    pre, post, w = pre[order], post[order], w[order]
    counts = np.bincount(pre, minlength=len(ids))
    offsets = np.zeros(len(ids) + 1, dtype=np.uint32)
    offsets[1:] = np.cumsum(counts)

    # Positions (nanometers in Codex -> micrometers here).
    pos = np.zeros((len(ids), 3), dtype=np.float32)
    if coords is not None:
        first = coords.drop_duplicates("root_id").set_index("root_id")["position"]
        p = first.reindex(ids)  # one position string per neuron, NaN if missing
        xyz = p.astype(str).str.strip("[]").str.replace(",", " ").str.split(expand=True)
        if xyz.shape[1] >= 3:
            vals = xyz.iloc[:, :3].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
            ok = ~np.isnan(vals).any(axis=1)
            pos[ok] = (vals[ok] / 1000.0).astype(np.float32)

    # Flag descending neurons so the game knows where to read movement output.
    desc = cls.loc[cls["super_class"] == "descending", "root_id"].to_numpy()
    flags = np.isin(ids, desc).astype(np.uint8)

    out = out_dir / f"{name}.bin"
    with open(out, "wb") as f:
        f.write(b"FLYB")
        f.write(struct.pack("<III", 1, len(ids), len(post)))
        f.write(ids.astype("<i8").tobytes())
        f.write(pos.astype("<f4").tobytes())
        f.write(flags.tobytes())
        f.write(offsets.astype("<u4").tobytes())
        f.write(post.astype("<u4").tobytes())
        f.write(w.astype("<i2").tobytes())

    mb = out.stat().st_size / 1e6
    print(f"{name:8s} {len(ids):>7,} neurons  {len(post):>10,} connections  {mb:6.1f} MB  -> {out}")
    if mb > 95:
        print(f"  WARNING: {out.name} is close to GitHub's 100 MB limit, use Git LFS for it")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="folder with the Codex CSVs")
    ap.add_argument("--out", default="Content/Brains", help="where to write .bin files")
    ap.add_argument("--header", default="Source/fruit_fly_game/FlyNeuronIDs.h",
                    help="where to write the generated C++ constants file")
    args = ap.parse_args()

    data_dir, out_dir = Path(args.data), Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn, cls, coords = load(data_dir)
    print("super classes in this data:", ", ".join(sorted(cls["super_class"].dropna().unique())))
    for name, spec in BRAINS.items():
        build(name, pick_neurons(spec, conn, cls), conn, cls, coords, out_dir)
    write_constants(cls, Path(args.header))


# ---------------------------------------------------------------------------
# Constants file: the named FlyWire IDs the game code reads.
# Maps a readable name to FlyWire cell type, so C++ can say GIANT_FIBER_LEFT
# instead of an 18-digit number. Add a row here to expose a new neuron type.
# ---------------------------------------------------------------------------
NAMED_TYPES = {
    "GIANT_FIBER": "DNp01",   # escape jump
    "LOOM_LC4": "LC4",        # looming detectors (input)
    "LOOM_LPLC2": "LPLC2",    # looming detectors (input)
    "STEER_A": "DNa01",       # steering
    "STEER_B": "DNa02",       # steering
    "MOONWALKER": "MDN",      # walk backward
    "WALK_FORWARD": "DNp09",  # walk forward
}

# Smell inputs. FlyWire labels smell receptor neurons with class "olfactory";
# their glomerulus name (ORN_DM1, ...) is the type. Side = which antenna.
SMELL_GROUPS = {
    # Glomeruli that respond to fruity esters and vinegar (fermenting fruit):
    # DM1 (ethyl acetate), DM2 (ethyl esters), DM3 (pentyl acetate),
    # DM4 (methyl acetate), VA2 (2,3-butanedione).
    "SMELL_FRUIT": ["ORN_DM1", "ORN_DM2", "ORN_DM3", "ORN_DM4", "ORN_VA2"],
    # Every smell receptor neuron. Useful for testing.
    "SMELL_ALL": None,
}


def write_constants(cls, header: Path):
    """Write a C++ header listing the FlyWire IDs for each named type, per side."""
    header.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "// GENERATED by tools/build_brains.py - do not edit by hand, rerun the script.",
        "// FlyWire root IDs for the neuron types the game reads or writes.",
        "#pragma once",
        "#include \"CoreMinimal.h\"",
        "",
        "namespace FlyNeurons",
        "{",
    ]
    groups = []  # (constant name, label for the comment, matching rows)
    for name, cell_type in NAMED_TYPES.items():
        rows = cls[cls["cell_type"] == cell_type]
        if rows.empty:
            print(f"  WARNING: no neurons found for cell type {cell_type} ({name}); check the name on Codex")
        groups.append((name, cell_type, rows))

    smell = cls[cls["class"] == "olfactory"]
    if smell.empty:
        print("  WARNING: no neurons with class 'olfactory' found; smell inputs will be empty")
    for name, types in SMELL_GROUPS.items():
        rows = smell if types is None else smell[smell["cell_type"].isin(types)]
        if rows.empty:
            print(f"  WARNING: no smell neurons found for {name}; check the type names on Codex")
        groups.append((name, "all olfactory" if types is None else " ".join(types), rows))

    for name, label, rows in groups:
        for side in ("left", "right"):
            ids = sorted(int(x) for x in rows.loc[rows["side"] == side, "root_id"])
            body = ", ".join(f"{i}LL" for i in ids)
            lines.append(f"    // {label}, {side} side: {len(ids)} neuron(s)")
            lines.append(f"    inline const TArray<int64> {name}_{side.upper()} = {{ {body} }};")
        n_left = int((rows["side"] == "left").sum()); n_right = int((rows["side"] == "right").sum())
        print(f"  {name:13s} left {n_left:>5}  right {n_right:>5}")
    lines += ["}", ""]
    header.write_text("\n".join(lines))
    print(f"constants -> {header}")


if __name__ == "__main__":
    main()
