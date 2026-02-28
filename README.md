# Godot Natural Outdoor Map Generator

A Python utility that procedurally generates 3D outdoor scenes for Godot Engine 4.x with high-quality 4K trees and mountain backdrop.

## Features

- Procedural terrain generation with winding paths
- High-quality tree models (island tree + pine tree)
- Mountain backdrop with 8K textures
- Poisson disc sampling for natural object placement
- Fly camera for scene exploration
- PBR terrain shaders with grass, dirt, rock, and snow blending

## Requirements

- Python 3.8+
- Godot Engine 4.3+
- Blender 4.0+ (for re-exporting tree models)

## Quick Start

```bash
# Generate the map
python generate_map.py

# Open in Godot
cd godot_project
godot --editor generated_map.tscn
```

## Project Structure

```
projectgodot/
├── generate_map.py          # Main map generator script
├── godot_project/
│   ├── generated_map.tscn   # Generated outdoor scene
│   ├── test_4k_tree.tscn    # 4K tree test scene
│   ├── assets/nature/
│   │   ├── island_tree_4k.glb   # 4K island tree (108MB)
│   │   ├── pine_tree_4k.glb     # 4K pine tree (149MB)
│   │   ├── mountain.obj         # Mountain mesh
│   │   └── mountain_*.png       # Mountain textures
│   ├── scripts/
│   │   ├── player.gd            # Player controller
│   │   └── fly_camera.gd        # Fly camera for exploration
│   ├── shaders/                 # PBR terrain shaders
│   └── textures/                # Terrain textures
└── 4k/                          # Source 4K Blender files
```

## Controls

### Main Map (generated_map.tscn)
- **WASD** - Move
- **Space** - Jump
- **Mouse** - Look around

### Test Scene (test_4k_tree.tscn)
- **WASD** - Fly movement
- **Mouse** - Look around
- **Shift** - Move faster
- **Space/Ctrl** - Up/Down
- **Esc** - Quit

## Tree Models

The 4K trees are exported from high-quality Blender models:

- **Island Tree** - Full detail, 108MB GLB
- **Pine Tree** - LOD1 quality (medium-high detail), 149MB GLB

## Configuration

Key settings in `generate_map.py`:

```python
PATH_LENGTH = 200.0          # Length of the winding path
TREE_SCATTER_OUTER = 60.0    # How far trees spread from path
USE_HQ_TREES = True          # Enable 4K tree models
```

## License

Tree models from Poly Haven (CC0)
