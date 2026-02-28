# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Godot Natural Outdoor Map Generator - a Python utility that procedurally generates 3D outdoor scenes for Godot Engine 4.3. It extracts model files (FBX/GLB/OBJ) from the KayKit Forest Nature Pack and creates `.tscn` scene files with objects placed along winding paths.

## Running the Generator

```bash
python generate_map.py
```

**Prerequisites:** Python 3.8+, KayKit Forest Nature Pack FREE zip in the same directory (download from https://kaylousberg.itch.io/kaykit-forest).

**Output:** Creates `./godot_project/` with extracted assets in `assets/nature/` and the final scene at `generated_map.tscn`.

## Architecture

Single-file script (`generate_map.py`) with a 5-step pipeline:

1. **Asset Detection** - Finds KayKit zip via glob patterns (`find_kaykit_zip`)
2. **Asset Extraction** - Maps model files (FBX/GLB/OBJ) to semantic roles (tree_pine, tree_oak, rock_large, rock_small, bush, fern) using exact + fuzzy matching
3. **Scene Wrapper Generation** - Creates `.tscn` wrapper files for each model
4. **Path & Placement** - Generates winding paths via Catmull-Rom splines, places objects based on distance from path (near/mid/far zones)
5. **Final Scene Writing** - Outputs complete `.tscn` with Transform3D matrices

## Key Configuration (lines 46-64)

- `GODOT_PROJECT_DIR` - Output directory
- `PATH_LENGTH`, `PATH_CONTROL_POINTS`, `PATH_WANDER` - Path generation parameters
- `SCATTER_INNER`, `SCATTER_OUTER` - Object placement distance range from path
- `OBJECTS_PER_SEGMENT` - Placement density
- `SEED` - Random seed for reproducibility

## Code Structure

- Entry point: `main()` at line 358
- Asset role mapping: `KAYKIT_ASSET_ROLES` dict at line 76
- No external dependencies (stdlib only: os, sys, math, random, shutil, zipfile, glob)
