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

## Getting started (everyone, once)

1. Install **Unreal Engine 5.8** from the Epic Games Launcher, and install Git.
2. Install a C++ compiler. This is a C++ project, so Unreal builds our code the first time you open it.
   - **Windows:** Visual Studio 2026 Community (free). In the installer tick **Game development with C++**,
     **Desktop development with C++** and **.NET desktop development**.
   - **Mac:** Xcode from the App Store. Open it once and let it install its components.
3. Clone the repo: `git clone https://github.com/MichaelAngulo3232/fly-brain-gamejam-fall-2026.git`
4. Double-click `fruit_fly_game.uproject`. When it says modules need to be rebuilt, click **Yes**.
   The first open compiles code and shaders and can take a while. Let it finish; it only happens once.
5. Laptop running slow? In the bar above the viewport open **Performance and Scalability**:
   set **Viewport Scalability** to Medium (or Low) and **Screen Percentage** to 50-75%.
6. Make your own branch before you change anything: `git checkout -b yourname/role`.
   Pull main into your branch every day with `git pull origin main`. Michael merges finished work into main.

**If the first open fails to build (Windows):** right-click `fruit_fly_game.uproject` →
**Generate Visual Studio project files**, open the `.sln`, and press Build. Then open the project again.
