# Fly Game

A banana fights off fruit flies on a kitchen counter. The enemy flies run on real
fruit fly brain wiring from the FlyWire adult brain connectome.

## Brain data setup (each teammate, once)

1. Go to https://codex.flywire.ai/api/download (free Google login), pick **FAFB v783**,
   and tick the citation-guidelines box.
2. Download these four into a `data/` folder at the repo root (only the brain team needs to):
   - `connections_princeton.csv.gz` ("Connections (Filtered)", 68 MB)
   - `classification.csv.gz` ("Classification / Hierarchical Annotations")
   - `consolidated_cell_types.csv.gz` ("Cell Types")
   - `coordinates.csv.gz` ("Marked Neuron Coordinates")
3. Build the brain files:
   ```
   pip install pandas numpy
   python tools/build_brains.py --data data --out Content/Brains
   ```
   This writes `sniffer.bin`, `dodger.bin` and `boss.bin` into `Content/Brains/`,
   plus the constants file `Source/fruit_fly_game/FlyNeuronIDs.h` (named lists of FlyWire IDs,
   e.g. `FlyNeurons::GIANT_FIBER_LEFT`, so code never hard-codes 18-digit numbers).
   If your Unreal module folder isn't `Source/fruit_fly_game/`, pass `--header` with the right path.

`data/` is ignored by git. The `.bin` files ARE committed, so teammates who only
work on gameplay or art don't need to run the script.

To change what an enemy's brain contains, edit `BRAINS` at the top of
`tools/build_brains.py`, rerun it, and commit the new `.bin` files.

## Brain file format

See the comment at the top of `tools/build_brains.py`.

## Credits

Brain connectivity data: FlyWire Consortium (Dorkenwald et al., 2024; Schlegel et al., 2024).
