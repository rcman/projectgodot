"""
Godot Natural Outdoor Map Generator

Full pipeline:

1. Detects the KayKit Forest Pack zip (free tier, CC0) in the same folder
2. Extracts the model files (FBX/GLB/OBJ) and copies them into your Godot project
3. Generates a lightweight .tscn wrapper scene for each model
4. Generates the final map scene with objects placed along a winding path

HOW TO GET THE ASSET PACK (one-time, free):

- Go to https://kaylousberg.itch.io/kaykit-forest
- Click "Download Now" and enter $0
- Download the FREE zip (named something like KayKit_Forest_1.0.zip)
- Place it in the same folder as this script
- Run:  python generate_map.py

REQUIREMENTS:
Python 3.8+  (no pip installs needed, uses standard library only)

OUTPUT:
<GODOT_PROJECT>/assets/nature/   <- model files + wrapper .tscn scenes
<GODOT_PROJECT>/generated_map.tscn  <- open this in Godot
"""

import os
import sys
import math
import random
import shutil
import zipfile
import glob
import requests
import io

# -------------------------
# CONFIGURATION
# -------------------------

# Path to your Godot project root (the folder containing project.godot)
# Defaults to a new folder next to this script if not set.
GODOT_PROJECT_DIR = "./godot_project"

# Folder inside the Godot project where nature assets will be placed
ASSETS_SUBDIR = "assets/nature"

# Output scene file name (placed in the Godot project root)
OUTPUT_SCENE = "generated_map.tscn"

# Map generation settings
PATH_LENGTH         = 200.0
PATH_CONTROL_POINTS = 8
PATH_WANDER         = 18.0
SCATTER_INNER       = 2.5
SCATTER_OUTER       = 14.0
OBJECTS_PER_SEGMENT = 6  # Reduced for faster loading
SEED                = 42

# Environment settings
GROUND_SIZE = 500.0
GROUND_COLOR = (0.3, 0.45, 0.2)  # Grass green RGB
ENABLE_FOG = True
FOG_DENSITY = 0.005  # Light fog for sunny day
SUN_ROTATION_X = -55.0  # Degrees, higher sun for brighter day
SUN_ROTATION_Y = -30.0  # Degrees

# -------------------------
# GRAPHICS QUALITY SETTINGS
# -------------------------
# Options: "ultra", "high", "medium", "low"
GRAPHICS_QUALITY = "medium"  # Changed from ultra - SDFGI can cause black screen on some GPUs

# Ultra quality settings (requires good GPU)
GRAPHICS_ULTRA = {
    # Global Illumination - SDFGI (Signed Distance Field GI)
    "sdfgi_enabled": True,
    "sdfgi_cascades": 6,              # More cascades = larger area coverage
    "sdfgi_min_cell_size": 0.2,       # Smaller = more detail
    "sdfgi_cascade0_distance": 12.8,  # First cascade range
    "sdfgi_y_scale": 1.0,             # Vertical scale
    "sdfgi_energy": 1.0,
    "sdfgi_normal_bias": 1.1,
    "sdfgi_probe_bias": 1.1,
    "sdfgi_bounce_feedback": 0.5,     # Light bounces
    "sdfgi_read_sky_light": True,

    # Screen-Space Reflections
    "ssr_enabled": True,
    "ssr_max_steps": 64,
    "ssr_fade_in": 0.15,
    "ssr_fade_out": 2.0,
    "ssr_depth_tolerance": 0.2,

    # Screen-Space Ambient Occlusion
    "ssao_enabled": True,
    "ssao_radius": 1.0,
    "ssao_intensity": 2.0,
    "ssao_power": 1.5,
    "ssao_detail": 0.5,
    "ssao_horizon": 0.06,
    "ssao_sharpness": 0.98,
    "ssao_light_affect": 0.0,
    "ssao_ao_channel_affect": 0.0,

    # Screen-Space Indirect Lighting
    "ssil_enabled": True,
    "ssil_radius": 5.0,
    "ssil_intensity": 1.0,
    "ssil_sharpness": 0.98,
    "ssil_normal_rejection": 1.0,

    # Volumetric Fog (replaces depth fog)
    "volumetric_fog_enabled": True,
    "volumetric_fog_density": 0.01,
    "volumetric_fog_albedo": (0.9, 0.92, 0.95),
    "volumetric_fog_emission": (0.0, 0.0, 0.0),
    "volumetric_fog_emission_energy": 0.0,
    "volumetric_fog_gi_inject": 1.0,
    "volumetric_fog_anisotropy": 0.2,
    "volumetric_fog_length": 200.0,
    "volumetric_fog_detail_spread": 2.0,
    "volumetric_fog_ambient_inject": 0.0,
    "volumetric_fog_sky_affect": 1.0,
    "volumetric_fog_temporal_reprojection_enabled": True,
    "volumetric_fog_temporal_reprojection_amount": 0.9,

    # Glow/Bloom
    "glow_enabled": True,
    "glow_normalized": False,
    "glow_intensity": 0.8,
    "glow_strength": 1.0,
    "glow_bloom": 0.0,
    "glow_blend_mode": 2,             # Softlight blend
    "glow_hdr_threshold": 1.0,
    "glow_hdr_scale": 2.0,
    "glow_hdr_luminance_cap": 12.0,
    "glow_map_strength": 0.8,
    "glow_levels": [1, 0, 1, 0, 1, 0, 0],  # Which mip levels contribute

    # Tonemapping
    "tonemap_mode": 3,                # ACES Filmic (best for realistic look)
    "tonemap_exposure": 1.0,
    "tonemap_white": 1.0,

    # Adjustments
    "adjustment_enabled": True,
    "adjustment_brightness": 1.0,
    "adjustment_contrast": 1.05,
    "adjustment_saturation": 1.1,

    # Shadows (DirectionalLight3D settings)
    "shadow_enabled": True,
    "shadow_blur": 1.0,
    "shadow_bias": 0.02,
    "shadow_normal_bias": 1.0,
    "shadow_transmittance_bias": 0.05,
    "directional_shadow_mode": 2,     # PSSM 4 Splits
    "directional_shadow_split_1": 0.1,
    "directional_shadow_split_2": 0.2,
    "directional_shadow_split_3": 0.5,
    "directional_shadow_max_distance": 200.0,
    "directional_shadow_fade_start": 0.8,
    "directional_shadow_blend_splits": True,

    # Background/Sky
    "sky_custom_fov": 0.0,

    # DOF (optional, disabled by default - can cause performance issues)
    "dof_blur_far_enabled": False,
    "dof_blur_far_distance": 100.0,
    "dof_blur_far_transition": 50.0,
    "dof_blur_near_enabled": False,
}

# High quality settings (balanced)
GRAPHICS_HIGH = {
    "sdfgi_enabled": True,
    "sdfgi_cascades": 4,
    "sdfgi_min_cell_size": 0.4,
    "sdfgi_cascade0_distance": 12.8,
    "sdfgi_y_scale": 1.0,
    "sdfgi_energy": 1.0,
    "sdfgi_normal_bias": 1.1,
    "sdfgi_probe_bias": 1.1,
    "sdfgi_bounce_feedback": 0.3,
    "sdfgi_read_sky_light": True,

    "ssr_enabled": True,
    "ssr_max_steps": 32,
    "ssr_fade_in": 0.15,
    "ssr_fade_out": 2.0,
    "ssr_depth_tolerance": 0.2,

    "ssao_enabled": True,
    "ssao_radius": 1.0,
    "ssao_intensity": 1.5,
    "ssao_power": 1.5,
    "ssao_detail": 0.5,
    "ssao_horizon": 0.06,
    "ssao_sharpness": 0.98,
    "ssao_light_affect": 0.0,
    "ssao_ao_channel_affect": 0.0,

    "ssil_enabled": False,

    "volumetric_fog_enabled": True,
    "volumetric_fog_density": 0.01,
    "volumetric_fog_albedo": (0.9, 0.92, 0.95),
    "volumetric_fog_emission": (0.0, 0.0, 0.0),
    "volumetric_fog_emission_energy": 0.0,
    "volumetric_fog_gi_inject": 0.5,
    "volumetric_fog_anisotropy": 0.2,
    "volumetric_fog_length": 150.0,
    "volumetric_fog_detail_spread": 2.0,
    "volumetric_fog_ambient_inject": 0.0,
    "volumetric_fog_sky_affect": 1.0,
    "volumetric_fog_temporal_reprojection_enabled": True,
    "volumetric_fog_temporal_reprojection_amount": 0.9,

    "glow_enabled": True,
    "glow_normalized": False,
    "glow_intensity": 0.6,
    "glow_strength": 1.0,
    "glow_bloom": 0.0,
    "glow_blend_mode": 2,
    "glow_hdr_threshold": 1.0,
    "glow_hdr_scale": 2.0,
    "glow_hdr_luminance_cap": 12.0,
    "glow_map_strength": 0.8,
    "glow_levels": [1, 0, 1, 0, 1, 0, 0],

    "tonemap_mode": 3,
    "tonemap_exposure": 1.0,
    "tonemap_white": 1.0,

    "adjustment_enabled": False,

    "shadow_enabled": True,
    "shadow_blur": 1.0,
    "shadow_bias": 0.02,
    "shadow_normal_bias": 1.0,
    "directional_shadow_mode": 2,
    "directional_shadow_split_1": 0.1,
    "directional_shadow_split_2": 0.2,
    "directional_shadow_split_3": 0.5,
    "directional_shadow_max_distance": 150.0,
    "directional_shadow_fade_start": 0.8,
    "directional_shadow_blend_splits": True,

    "dof_blur_far_enabled": False,
    "dof_blur_near_enabled": False,
}

# Medium quality settings (good performance)
GRAPHICS_MEDIUM = {
    "sdfgi_enabled": False,

    "ssr_enabled": False,

    "ssao_enabled": True,
    "ssao_radius": 1.0,
    "ssao_intensity": 1.0,
    "ssao_power": 1.5,
    "ssao_detail": 0.5,
    "ssao_horizon": 0.06,
    "ssao_sharpness": 0.98,
    "ssao_light_affect": 0.5,
    "ssao_ao_channel_affect": 0.0,

    "ssil_enabled": False,

    "volumetric_fog_enabled": False,
    "fog_enabled": False,  # Disabled to show sky panorama

    "glow_enabled": True,
    "glow_normalized": False,
    "glow_intensity": 0.5,
    "glow_strength": 1.0,
    "glow_bloom": 0.0,
    "glow_blend_mode": 2,
    "glow_hdr_threshold": 1.0,
    "glow_hdr_scale": 2.0,
    "glow_hdr_luminance_cap": 12.0,
    "glow_levels": [1, 0, 1, 0, 0, 0, 0],

    "tonemap_mode": 2,  # Reinhard
    "tonemap_exposure": 1.0,
    "tonemap_white": 1.0,

    "adjustment_enabled": False,

    "shadow_enabled": True,
    "shadow_blur": 1.0,
    "shadow_bias": 0.03,
    "directional_shadow_mode": 1,  # PSSM 2 Splits
    "directional_shadow_max_distance": 100.0,
    "directional_shadow_blend_splits": False,

    "dof_blur_far_enabled": False,
    "dof_blur_near_enabled": False,
}

# Low quality settings (maximum performance)
GRAPHICS_LOW = {
    "sdfgi_enabled": False,
    "ssr_enabled": False,
    "ssao_enabled": False,
    "ssil_enabled": False,
    "volumetric_fog_enabled": False,
    "fog_enabled": True,
    "glow_enabled": False,
    "tonemap_mode": 0,  # Linear
    "tonemap_exposure": 1.0,
    "adjustment_enabled": False,
    "shadow_enabled": True,
    "shadow_blur": 0.0,
    "shadow_bias": 0.05,
    "directional_shadow_mode": 0,  # Orthogonal
    "directional_shadow_max_distance": 50.0,
    "dof_blur_far_enabled": False,
    "dof_blur_near_enabled": False,
}

def get_graphics_settings():
    """Get the active graphics quality settings."""
    quality_map = {
        "ultra": GRAPHICS_ULTRA,
        "high": GRAPHICS_HIGH,
        "medium": GRAPHICS_MEDIUM,
        "low": GRAPHICS_LOW,
    }
    return quality_map.get(GRAPHICS_QUALITY.lower(), GRAPHICS_ULTRA)

HIGH_QUALITY_ASSET_URLS = {
    "hq_nature": "https://cdn.discordapp.com/attachments/1224863372224565269/1247413941584330752/nature_assets_v1.zip?ex=665fd368&is=665e81e8&hm=b5a93946394337255598d24660b86a3479577558661763c896587c699908d1f7&"
}

def download_and_extract_assets(url, dest_folder):
    """Download and extract a zip file from a URL."""
    print(f"Downloading assets from {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(dest_folder)
        print(f"Assets extracted to {dest_folder}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading assets: {e}")
        return False
    except zipfile.BadZipFile:
        print("Error: Downloaded file is not a valid zip file.")
        return False

# Placement settings - ENHANCED with Poisson Disc Sampling
MIN_OBJECT_SPACING = 1.0    # Global minimum distance between objects
CLEARING_CHANCE = 0.15      # Probability of clearing per path segment
CLEARING_RADIUS = 8.0       # Radius of clearings where no objects spawn
CLUSTER_CHANCE = 0.3        # Chance to add satellite objects near placement

# Poisson Disc Sampling settings (from C# Infinite Runner)
USE_POISSON_SAMPLING = True      # Enable Poisson disc sampling for object placement
POISSON_RADIUS = 2.5             # Minimum spacing between Poisson-sampled points
POISSON_SAMPLES = 30             # Number of attempts before rejecting a point
POISSON_GRID_SCALE = 1.0         # Scale factor for the sampling grid

# Secondary paths
SECONDARY_PATHS = 1         # Number of branching paths
SECONDARY_PATH_LENGTH = 80.0
SECONDARY_PATH_WANDER = 12.0

# Biomes
BIOME_SEGMENT_LENGTH = 30.0  # Distance before biome can change

# Terrain height - ENHANCED with multi-pass noise (from C# Infinite Runner)
TERRAIN_HEIGHT_SCALE = 0.0    # Maximum height variation (0 = flat)
TERRAIN_NOISE_SCALE = 0.02    # Noise frequency (not used when height_scale=0)
TERRAIN_OCTAVES = 4           # Noise detail layers (increased from 3)
TERRAIN_FREQUENCY = 0.6       # Base noise frequency (from C# project)
TERRAIN_CONTRAST = 1.2        # Terrain contrast multiplier
PATH_FLATTEN_RADIUS = 3.0     # Flatten terrain near paths

# Multi-pass terrain blending (from C# MapGenerator)
TERRAIN_PASSES = [
    {"octaves": 4, "frequency": 0.5, "scale": 1.0, "blend": "base", "contrast": 1.0},
    {"octaves": 2, "frequency": 1.5, "scale": 0.3, "blend": "add", "contrast": 1.2},  # Detail pass
]

# -------------------------
# KAYKIT FOREST PACK - known GLB file names in the free tier
# These are the actual filenames inside the KayKit Forest pack zip.
# Mapped to logical roles used by the placer.
# -------------------------

KAYKIT_ASSET_ROLES = {
    # role -> list of possible filenames (first match found will be used)
    # Supports GLB, FBX, and OBJ formats

    # === TREES (many variants for variety) ===
    "tree_pine_1":  ["Tree_1_A_Color1.fbx"],
    "tree_pine_2":  ["Tree_1_B_Color1.fbx"],
    "tree_pine_3":  ["Tree_1_C_Color1.fbx"],
    "tree_tall_1":  ["Tree_2_A_Color1.fbx"],
    "tree_tall_2":  ["Tree_2_B_Color1.fbx"],
    "tree_tall_3":  ["Tree_2_C_Color1.fbx"],
    "tree_tall_4":  ["Tree_2_D_Color1.fbx"],
    "tree_tall_5":  ["Tree_2_E_Color1.fbx"],
    "tree_oak_1":   ["Tree_3_A_Color1.fbx"],
    "tree_oak_2":   ["Tree_3_B_Color1.fbx"],
    "tree_oak_3":   ["Tree_3_C_Color1.fbx"],
    "tree_round_1": ["Tree_4_A_Color1.fbx"],
    "tree_round_2": ["Tree_4_B_Color1.fbx"],
    "tree_round_3": ["Tree_4_C_Color1.fbx"],
    # Bare trees (dead/winter)
    "tree_bare_1":  ["Tree_Bare_1_A_Color1.fbx"],
    "tree_bare_2":  ["Tree_Bare_1_B_Color1.fbx"],
    "tree_bare_3":  ["Tree_Bare_1_C_Color1.fbx"],
    "tree_bare_4":  ["Tree_Bare_2_A_Color1.fbx"],
    "tree_bare_5":  ["Tree_Bare_2_B_Color1.fbx"],
    "tree_bare_6":  ["Tree_Bare_2_C_Color1.fbx"],

    # === ROCKS (various sizes) ===
    # Large boulders
    "rock_boulder_1": ["Rock_1_A_Color1.fbx"],
    "rock_boulder_2": ["Rock_1_B_Color1.fbx"],
    "rock_boulder_3": ["Rock_1_C_Color1.fbx"],
    "rock_boulder_4": ["Rock_1_D_Color1.fbx"],
    "rock_boulder_5": ["Rock_1_E_Color1.fbx"],
    "rock_boulder_6": ["Rock_1_F_Color1.fbx"],
    "rock_boulder_7": ["Rock_1_G_Color1.fbx"],
    # Medium rocks
    "rock_medium_1":  ["Rock_2_A_Color1.fbx"],
    "rock_medium_2":  ["Rock_2_B_Color1.fbx"],
    "rock_medium_3":  ["Rock_2_C_Color1.fbx"],
    "rock_medium_4":  ["Rock_2_D_Color1.fbx"],
    "rock_medium_5":  ["Rock_2_E_Color1.fbx"],
    "rock_medium_6":  ["Rock_2_F_Color1.fbx"],
    # Small rocks
    "rock_small_1":   ["Rock_3_A_Color1.fbx"],
    "rock_small_2":   ["Rock_3_B_Color1.fbx"],
    "rock_small_3":   ["Rock_3_C_Color1.fbx"],
    "rock_small_4":   ["Rock_3_D_Color1.fbx"],
    "rock_small_5":   ["Rock_3_E_Color1.fbx"],
    "rock_small_6":   ["Rock_3_F_Color1.fbx"],

    # === BUSHES (variety of shapes) ===
    "bush_round_1":   ["Bush_1_A_Color1.fbx"],
    "bush_round_2":   ["Bush_1_B_Color1.fbx"],
    "bush_round_3":   ["Bush_1_C_Color1.fbx"],
    "bush_round_4":   ["Bush_1_D_Color1.fbx"],
    "bush_tall_1":    ["Bush_2_A_Color1.fbx"],
    "bush_tall_2":    ["Bush_2_B_Color1.fbx"],
    "bush_tall_3":    ["Bush_2_C_Color1.fbx"],
    "bush_wide_1":    ["Bush_3_A_Color1.fbx"],
    "bush_wide_2":    ["Bush_3_B_Color1.fbx"],

    # === GRASS/FERNS (ground cover) ===
    "grass_1":        ["Grass_1_A_Color1.fbx"],
    "grass_2":        ["Grass_1_B_Color1.fbx"],
    "grass_3":        ["Grass_1_C_Color1.fbx"],
    "grass_4":        ["Grass_1_D_Color1.fbx"],
    "fern_1":         ["Grass_2_A_Color1.fbx"],
    "fern_2":         ["Grass_2_B_Color1.fbx"],
    "fern_3":         ["Grass_2_C_Color1.fbx"],
    "fern_4":         ["Grass_2_D_Color1.fbx"],
}

# -------------------------
# REALISTIC TREE MODELS (Mantissa - CC0 License)
# High-poly realistic trees for photorealistic scenes
# -------------------------
REALISTIC_ASSET_ROLES = {
    # Japanese Maple variants
    "real_maple_1":  ["Mantissa_Japanese_Maple_001.FBX"],
    "real_maple_2":  ["Mantissa_Japanese_Maple_002.FBX"],
    "real_maple_3":  ["Mantissa_Japanese_Maple_003.FBX"],
    "real_maple_4":  ["Mantissa_Japanese_Maple_004.FBX"],
    "real_maple_5":  ["Mantissa_Japanese_Maple_005.FBX"],
    # Cherry Tree variants
    "real_cherry_1": ["Mantissa_Cherry_Tree_001.FBX"],
    "real_cherry_2": ["Mantissa_Cherry_Tree_002.FBX"],
    "real_cherry_3": ["Mantissa_Cherry_Tree_003.FBX"],
    "real_cherry_4": ["Mantissa_Cherry_Tree_004.FBX"],
    "real_cherry_5": ["Mantissa_Cherry_Tree_005.FBX"],
    # Birch Tree variants
    "real_birch_1":  ["Mantissa_Birch_001.FBX"],
    "real_birch_2":  ["Mantissa_Birch_002.FBX"],
    "real_birch_3":  ["Mantissa_Birch_003.FBX"],
    "real_birch_4":  ["Mantissa_Birch_004.FBX"],
    "real_birch_5":  ["Mantissa_Birch_005.FBX"],
    # Generic Tree variants (10 models)
    "real_generic_1":  ["Mantissa_Generic_Tree_001.FBX"],
    "real_generic_2":  ["Mantissa_Generic_Tree_002.FBX"],
    "real_generic_3":  ["Mantissa_Generic_Tree_003.FBX"],
    "real_generic_4":  ["Mantissa_Generic_Tree_004.FBX"],
    "real_generic_5":  ["Mantissa_Generic_Tree_005.FBX"],
    "real_generic_6":  ["Mantissa_Generic_Tree_006.FBX"],
    "real_generic_7":  ["Mantissa_Generic_Tree_007.FBX"],
    "real_generic_8":  ["Mantissa_Generic_Tree_008.FBX"],
    "real_generic_9":  ["Mantissa_Generic_Tree_009.FBX"],
    "real_generic_10": ["Mantissa_Generic_Tree_010.FBX"],
    # Spruce Tree variants
    "real_spruce_1":  ["Mantissa_Free_Spruce_001.FBX"],
    "real_spruce_2":  ["Mantissa_Free_Spruce_002.FBX"],
    "real_spruce_3":  ["Mantissa_Free_Spruce_003.FBX"],
    "real_spruce_4":  ["Mantissa_Free_Spruce_004.FBX"],
    "real_spruce_5":  ["Mantissa_Free_Spruce_005.FBX"],
}

# Folder for realistic assets (separate from KayKit)
REALISTIC_ASSETS_SUBDIR = "assets/realistic_trees"

# Use realistic trees instead of stylized KayKit trees
USE_REALISTIC_TREES = False  # Disabled - using KayKit + new trees instead

# -------------------------
# KENNEY NATURE KIT TREES (CC0 License)
# Higher quality detailed trees from kenney.nl
# -------------------------
KENNEY_TREE_ROLES = {
    # Detailed deciduous trees
    "kenney_detailed_1":    ["tree_detailed.fbx"],
    "kenney_detailed_2":    ["tree_detailed_dark.fbx"],
    "kenney_oak_1":         ["tree_oak.fbx"],
    "kenney_oak_2":         ["tree_oak_dark.fbx"],
    "kenney_tall":          ["tree_tall.fbx"],
    "kenney_fat":           ["tree_fat.fbx"],
    # Detailed pine trees
    "kenney_pine_tall_1":   ["tree_pineTallA_detailed.fbx"],
    "kenney_pine_tall_2":   ["tree_pineTallB_detailed.fbx"],
    "kenney_pine_tall_3":   ["tree_pineTallC_detailed.fbx"],
    "kenney_pine_round_1":  ["tree_pineRoundA.fbx"],
    "kenney_pine_round_2":  ["tree_pineRoundB.fbx"],
}

KENNEY_ASSETS_SUBDIR = "assets/kenney_trees"

# -------------------------
# NEW TREES (user-added OBJ models)
# -------------------------
NEW_TREES_SUBDIR = "assets/new_trees"
NEW_TREE_ROLES = {
    "new_tree_pack": ["trees9.obj"],  # 9 varied trees in one model
}
USE_NEW_TREES = True  # Enable user's new tree models

# Use Kenney trees (higher quality) instead of KayKit
USE_KENNEY_TREES = False  # Disabled - using photorealistic Mantissa trees instead

# Per-asset configuration for spacing, scale, altitude, and rotation
# ENHANCED with settings from C# Infinite Runner project:
#   - min_altitude / max_altitude: Height-based spawn constraints
#   - randomize_y_rotation: Enable random Y-axis rotation
#   - tilt_angle: Maximum random tilt in degrees (X and Z axes)
ASSET_PROPERTIES = {
    # Trees - various sizes and spacing (spawn on lower ground, avoid peaks)
    "tree_pine_1":  {"min_spacing": 3.0, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "tree_pine_2":  {"min_spacing": 3.0, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "tree_pine_3":  {"min_spacing": 3.0, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "tree_tall_1":  {"min_spacing": 3.5, "scale_range": (0.9, 1.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "tree_tall_2":  {"min_spacing": 3.5, "scale_range": (0.9, 1.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "tree_tall_3":  {"min_spacing": 3.5, "scale_range": (0.9, 1.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "tree_tall_4":  {"min_spacing": 3.5, "scale_range": (0.9, 1.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "tree_tall_5":  {"min_spacing": 3.5, "scale_range": (0.9, 1.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "tree_oak_1":   {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 10.0, "randomize_y_rotation": True, "tilt_angle": 2.5},
    "tree_oak_2":   {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 10.0, "randomize_y_rotation": True, "tilt_angle": 2.5},
    "tree_oak_3":   {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 10.0, "randomize_y_rotation": True, "tilt_angle": 2.5},
    "tree_round_1": {"min_spacing": 3.5, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "tree_round_2": {"min_spacing": 3.5, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "tree_round_3": {"min_spacing": 3.5, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "tree_bare_1":  {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 5.0},
    "tree_bare_2":  {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 5.0},
    "tree_bare_3":  {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 5.0},
    "tree_bare_4":  {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 5.0},
    "tree_bare_5":  {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 5.0},
    "tree_bare_6":  {"min_spacing": 4.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 5.0},
    # Boulders - large rocks, widely spaced (can spawn at higher altitudes)
    "rock_boulder_1": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "rock_boulder_2": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "rock_boulder_3": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "rock_boulder_4": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "rock_boulder_5": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "rock_boulder_6": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "rock_boulder_7": {"min_spacing": 4.0, "scale_range": (1.0, 2.0), "y_offset": -0.2, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    # Medium rocks (more tilt variation for natural look)
    "rock_medium_1":  {"min_spacing": 2.0, "scale_range": (0.7, 1.4), "y_offset": -0.1, "min_altitude": -10.0, "max_altitude": 40.0, "randomize_y_rotation": True, "tilt_angle": 12.0},
    "rock_medium_2":  {"min_spacing": 2.0, "scale_range": (0.7, 1.4), "y_offset": -0.1, "min_altitude": -10.0, "max_altitude": 40.0, "randomize_y_rotation": True, "tilt_angle": 12.0},
    "rock_medium_3":  {"min_spacing": 2.0, "scale_range": (0.7, 1.4), "y_offset": -0.1, "min_altitude": -10.0, "max_altitude": 40.0, "randomize_y_rotation": True, "tilt_angle": 12.0},
    "rock_medium_4":  {"min_spacing": 2.0, "scale_range": (0.7, 1.4), "y_offset": -0.1, "min_altitude": -10.0, "max_altitude": 40.0, "randomize_y_rotation": True, "tilt_angle": 12.0},
    "rock_medium_5":  {"min_spacing": 2.0, "scale_range": (0.7, 1.4), "y_offset": -0.1, "min_altitude": -10.0, "max_altitude": 40.0, "randomize_y_rotation": True, "tilt_angle": 12.0},
    "rock_medium_6":  {"min_spacing": 2.0, "scale_range": (0.7, 1.4), "y_offset": -0.1, "min_altitude": -10.0, "max_altitude": 40.0, "randomize_y_rotation": True, "tilt_angle": 12.0},
    # Small rocks - can cluster (high tilt for scattered look)
    "rock_small_1":   {"min_spacing": 0.8, "scale_range": (0.5, 1.2), "y_offset": -0.05, "min_altitude": -10.0, "max_altitude": 30.0, "randomize_y_rotation": True, "tilt_angle": 15.0},
    "rock_small_2":   {"min_spacing": 0.8, "scale_range": (0.5, 1.2), "y_offset": -0.05, "min_altitude": -10.0, "max_altitude": 30.0, "randomize_y_rotation": True, "tilt_angle": 15.0},
    "rock_small_3":   {"min_spacing": 0.8, "scale_range": (0.5, 1.2), "y_offset": -0.05, "min_altitude": -10.0, "max_altitude": 30.0, "randomize_y_rotation": True, "tilt_angle": 15.0},
    "rock_small_4":   {"min_spacing": 0.8, "scale_range": (0.5, 1.2), "y_offset": -0.05, "min_altitude": -10.0, "max_altitude": 30.0, "randomize_y_rotation": True, "tilt_angle": 15.0},
    "rock_small_5":   {"min_spacing": 0.8, "scale_range": (0.5, 1.2), "y_offset": -0.05, "min_altitude": -10.0, "max_altitude": 30.0, "randomize_y_rotation": True, "tilt_angle": 15.0},
    "rock_small_6":   {"min_spacing": 0.8, "scale_range": (0.5, 1.2), "y_offset": -0.05, "min_altitude": -10.0, "max_altitude": 30.0, "randomize_y_rotation": True, "tilt_angle": 15.0},
    # Bushes (slight tilt for organic look)
    "bush_round_1":   {"min_spacing": 1.5, "scale_range": (0.7, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 4.0},
    "bush_round_2":   {"min_spacing": 1.5, "scale_range": (0.7, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 4.0},
    "bush_round_3":   {"min_spacing": 1.5, "scale_range": (0.7, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 4.0},
    "bush_round_4":   {"min_spacing": 1.5, "scale_range": (0.7, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 4.0},
    "bush_tall_1":    {"min_spacing": 1.8, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "bush_tall_2":    {"min_spacing": 1.8, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "bush_tall_3":    {"min_spacing": 1.8, "scale_range": (0.8, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 8.0, "randomize_y_rotation": True, "tilt_angle": 3.0},
    "bush_wide_1":    {"min_spacing": 2.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 6.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "bush_wide_2":    {"min_spacing": 2.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 6.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    # Grass and ferns (high tilt for windswept natural look)
    "grass_1":        {"min_spacing": 0.4, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 5.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "grass_2":        {"min_spacing": 0.4, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 5.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "grass_3":        {"min_spacing": 0.4, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 5.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "grass_4":        {"min_spacing": 0.4, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 5.0, "randomize_y_rotation": True, "tilt_angle": 8.0},
    "fern_1":         {"min_spacing": 0.5, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 6.0, "randomize_y_rotation": True, "tilt_angle": 6.0},
    "fern_2":         {"min_spacing": 0.5, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 6.0, "randomize_y_rotation": True, "tilt_angle": 6.0},
    "fern_3":         {"min_spacing": 0.5, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 6.0, "randomize_y_rotation": True, "tilt_angle": 6.0},
    "fern_4":         {"min_spacing": 0.5, "scale_range": (0.6, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 6.0, "randomize_y_rotation": True, "tilt_angle": 6.0},
    # Realistic trees (Mantissa) - larger spacing due to high detail
    "real_maple_1":   {"min_spacing": 6.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_maple_2":   {"min_spacing": 6.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_maple_3":   {"min_spacing": 6.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_maple_4":   {"min_spacing": 6.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_maple_5":   {"min_spacing": 6.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_cherry_1":  {"min_spacing": 8.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_cherry_2":  {"min_spacing": 8.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_cherry_3":  {"min_spacing": 8.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_cherry_4":  {"min_spacing": 8.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_cherry_5":  {"min_spacing": 8.0, "scale_range": (0.7, 1.1), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    # Birch trees - tall and slender
    "real_birch_1":   {"min_spacing": 5.0, "scale_range": (0.9, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 18.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_birch_2":   {"min_spacing": 5.0, "scale_range": (0.9, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 18.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_birch_3":   {"min_spacing": 5.0, "scale_range": (0.9, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 18.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_birch_4":   {"min_spacing": 5.0, "scale_range": (0.9, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 18.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_birch_5":   {"min_spacing": 5.0, "scale_range": (0.9, 1.3), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 18.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    # Generic trees - variety of deciduous trees
    "real_generic_1":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_2":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_3":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_4":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_5":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_6":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_7":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_8":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_9":  {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "real_generic_10": {"min_spacing": 7.0, "scale_range": (0.8, 1.2), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    # Spruce trees - coniferous, taller
    "real_spruce_1":  {"min_spacing": 6.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 25.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_spruce_2":  {"min_spacing": 6.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 25.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_spruce_3":  {"min_spacing": 6.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 25.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_spruce_4":  {"min_spacing": 6.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 25.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "real_spruce_5":  {"min_spacing": 6.0, "scale_range": (0.9, 1.4), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 25.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    # Kenney Nature Kit trees - higher quality detailed models
    "kenney_detailed_1":   {"min_spacing": 4.0, "scale_range": (1.5, 2.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "kenney_detailed_2":   {"min_spacing": 4.0, "scale_range": (1.5, 2.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "kenney_oak_1":        {"min_spacing": 5.0, "scale_range": (1.8, 3.0), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "kenney_oak_2":        {"min_spacing": 5.0, "scale_range": (1.8, 3.0), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 12.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "kenney_tall":         {"min_spacing": 4.5, "scale_range": (2.0, 3.5), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 18.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "kenney_fat":          {"min_spacing": 5.0, "scale_range": (2.0, 3.0), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 10.0, "randomize_y_rotation": True, "tilt_angle": 2.5},
    "kenney_pine_tall_1":  {"min_spacing": 3.5, "scale_range": (1.5, 2.8), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "kenney_pine_tall_2":  {"min_spacing": 3.5, "scale_range": (1.5, 2.8), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "kenney_pine_tall_3":  {"min_spacing": 3.5, "scale_range": (1.5, 2.8), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 20.0, "randomize_y_rotation": True, "tilt_angle": 1.5},
    "kenney_pine_round_1": {"min_spacing": 4.0, "scale_range": (1.8, 3.0), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    "kenney_pine_round_2": {"min_spacing": 4.0, "scale_range": (1.8, 3.0), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 15.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
    # New user-added trees (OBJ models - 9 varied trees)
    "new_tree_pack": {"min_spacing": 4.0, "scale_range": (0.08, 0.12), "y_offset": 0.0, "min_altitude": -10.0, "max_altitude": 50.0, "randomize_y_rotation": True, "tilt_angle": 2.0},
}

# Default properties for unknown assets
DEFAULT_ASSET_PROPS = {
    "min_spacing": 1.0,
    "scale_range": (0.8, 1.2),
    "y_offset": 0.0,
    "min_altitude": -100.0,  # No lower limit by default
    "max_altitude": 100.0,   # No upper limit by default
    "randomize_y_rotation": True,
    "tilt_angle": 5.0,
}

# Biome definitions - weights for each asset category
BIOMES = {
    "forest": {
        "trees": 0.60,  # Increased for more tree coverage
        "trees_bare": 0.0,
        "boulders": 0.05,
        "rocks": 0.05,
        "bushes": 0.15,
        "ferns": 0.10,
        "grass": 0.05,
    },
    "rocky": {
        "trees": 0.08,
        "trees_bare": 0.0,
        "boulders": 0.20,
        "rocks": 0.30,
        "bushes": 0.12,
        "ferns": 0.15,
        "grass": 0.15,
    },
    "meadow": {
        "trees": 0.10,
        "trees_bare": 0.0,
        "boulders": 0.03,
        "rocks": 0.07,
        "bushes": 0.15,
        "ferns": 0.30,
        "grass": 0.35,
    },
    "winter": {
        "trees": 0.10,
        "trees_bare": 0.25,
        "boulders": 0.15,
        "rocks": 0.25,
        "bushes": 0.05,
        "ferns": 0.10,
        "grass": 0.10,
    },
    "autumn": {
        "trees": 0.20,
        "trees_bare": 0.15,
        "boulders": 0.08,
        "rocks": 0.12,
        "bushes": 0.18,
        "ferns": 0.15,
        "grass": 0.12,
    },
    "realistic": {
        "trees_realistic": 0.60,  # Realistic Mantissa trees
        "trees": 0.0,             # No stylized trees
        "trees_bare": 0.0,
        "boulders": 0.08,
        "rocks": 0.12,
        "bushes": 0.10,
        "ferns": 0.05,
        "grass": 0.05,
    },
}

# Kenney trees category - higher quality detailed trees
KENNEY_TREE_CATEGORY = [
    "kenney_detailed_1", "kenney_detailed_2",
    "kenney_oak_1", "kenney_oak_2",
    "kenney_tall", "kenney_fat",
    "kenney_pine_tall_1", "kenney_pine_tall_2", "kenney_pine_tall_3",
    "kenney_pine_round_1", "kenney_pine_round_2",
]

# Asset category mapping - which asset roles belong to which category
# Realistic tree category - photorealistic Mantissa trees
REALISTIC_TREE_CATEGORY = [
    "real_maple_1", "real_maple_2", "real_maple_3", "real_maple_4", "real_maple_5",
    "real_cherry_1", "real_cherry_2", "real_cherry_3", "real_cherry_4", "real_cherry_5",
]

ASSET_CATEGORIES = {
    "trees": (
        ["new_tree_pack"] if USE_NEW_TREES else [
            # KayKit trees only when new trees disabled
            "tree_pine_1", "tree_pine_2", "tree_pine_3",
            "tree_tall_1", "tree_tall_2", "tree_tall_3", "tree_tall_4", "tree_tall_5",
            "tree_oak_1", "tree_oak_2", "tree_oak_3",
            "tree_round_1", "tree_round_2", "tree_round_3",
        ]
    ),
    "trees_bare": [
        "tree_bare_1", "tree_bare_2", "tree_bare_3",
        "tree_bare_4", "tree_bare_5", "tree_bare_6",
    ],
    "boulders": [
        "rock_boulder_1", "rock_boulder_2", "rock_boulder_3", "rock_boulder_4",
        "rock_boulder_5", "rock_boulder_6", "rock_boulder_7",
    ],
    "rocks": [
        "rock_medium_1", "rock_medium_2", "rock_medium_3",
        "rock_medium_4", "rock_medium_5", "rock_medium_6",
        "rock_small_1", "rock_small_2", "rock_small_3",
        "rock_small_4", "rock_small_5", "rock_small_6",
    ],
    "bushes": [
        "bush_round_1", "bush_round_2", "bush_round_3", "bush_round_4",
        "bush_tall_1", "bush_tall_2", "bush_tall_3",
        "bush_wide_1", "bush_wide_2",
    ],
    "ferns": ["fern_1", "fern_2", "fern_3", "fern_4"],
    "grass": ["grass_1", "grass_2", "grass_3", "grass_4"],
    "trees_realistic": [
        "real_maple_1", "real_maple_2", "real_maple_3", "real_maple_4", "real_maple_5",
        "real_cherry_1", "real_cherry_2", "real_cherry_3", "real_cherry_4", "real_cherry_5",
        "real_birch_1", "real_birch_2", "real_birch_3", "real_birch_4", "real_birch_5",
        "real_generic_1", "real_generic_2", "real_generic_3", "real_generic_4", "real_generic_5",
        "real_generic_6", "real_generic_7", "real_generic_8", "real_generic_9", "real_generic_10",
        "real_spruce_1", "real_spruce_2", "real_spruce_3", "real_spruce_4", "real_spruce_5",
    ],
}

# -------------------------
# ENVIRONMENT PRESETS
# -------------------------

ENVIRONMENT_PRESETS = {
    "forest_park": {
        "name": "Forest Park",
        "description": "Lush forest with boulders",
        # Ground
        "ground_color": (0.3, 0.45, 0.2),       # Grass green
        # Sky
        "sky_top_color": (0.4, 0.65, 0.95),     # Bright blue
        "sky_horizon_color": (0.85, 0.9, 0.95), # Light horizon
        "ground_horizon_color": (0.55, 0.6, 0.5),
        "ground_bottom_color": (0.2, 0.17, 0.13),
        # Lighting - bright high noon sun
        "sun_energy": 2.0,
        "sun_angle_x": -75.0,  # High overhead
        "sun_angle_y": 0.0,
        "ambient_energy": 1.0,
        # Fog
        "fog_enabled": True,
        "fog_density": 0.003,
        "fog_color": (0.85, 0.88, 0.92),
        # Terrain
        "terrain_height_scale": 0.0,
        "terrain_noise_scale": 0.02,
        # Asset weights (category weights)
        "biome_weights": {
            "forest": 0.5,
            "meadow": 0.3,
            "rocky": 0.2,
        },
        # Features
        "features": {
            "water_ponds": True,
            "terrain_height": True,
            "particles": True,
        },
    },

    "autumn_forest": {
        "name": "Autumn Forest",
        "description": "Fall colors with warm lighting and misty atmosphere",
        "ground_color": (0.45, 0.35, 0.2),      # Brown/orange ground
        "sky_top_color": (0.5, 0.6, 0.8),       # Pale blue
        "sky_horizon_color": (0.9, 0.75, 0.6),  # Warm orange horizon
        "ground_horizon_color": (0.5, 0.4, 0.3),
        "ground_bottom_color": (0.25, 0.18, 0.12),
        "sun_energy": 2.0,
        "sun_angle_x": -75.0,  # High noon
        "sun_angle_y": 0.0,
        "ambient_energy": 1.0,
        "fog_enabled": True,
        "fog_density": 0.015,
        "fog_color": (0.8, 0.75, 0.65),         # Warm fog
        "terrain_height_scale": 0.0,
        "terrain_noise_scale": 0.025,
        "biome_weights": {"autumn": 0.6, "forest": 0.3, "meadow": 0.1},
        "features": {
            "water_ponds": True,
            "terrain_height": True,
            "particles": True,
        },
    },

    "desert_canyon": {
        "name": "Desert Canyon",
        "description": "Arid landscape with rock formations and sparse vegetation",
        "ground_color": (0.76, 0.6, 0.42),      # Sand
        "sky_top_color": (0.55, 0.7, 0.9),      # Pale blue
        "sky_horizon_color": (0.95, 0.85, 0.7), # Warm horizon
        "ground_horizon_color": (0.7, 0.55, 0.4),
        "ground_bottom_color": (0.5, 0.35, 0.2),
        "sun_energy": 2.2,
        "sun_angle_x": -75.0,  # High noon
        "sun_angle_y": 0.0,
        "ambient_energy": 1.0,
        "fog_enabled": True,
        "fog_density": 0.001,                   # Very light haze
        "fog_color": (0.9, 0.85, 0.75),
        "terrain_height_scale": 0.0,
        "terrain_noise_scale": 0.015,
        "biome_weights": {"rocky": 0.7, "meadow": 0.2, "forest": 0.1},
        "features": {
            "water_ponds": False,
            "terrain_height": True,
            "particles": False,
        },
    },

    "snowy_peaks": {
        "name": "Snowy Peaks",
        "description": "Winter wonderland with heavy snow",
        "ground_color": (0.9, 0.92, 0.95),      # Snow white
        "sky_top_color": (0.6, 0.75, 0.9),      # Winter blue
        "sky_horizon_color": (0.85, 0.88, 0.92),
        "ground_horizon_color": (0.8, 0.82, 0.85),
        "ground_bottom_color": (0.7, 0.72, 0.75),
        "sun_energy": 2.0,
        "sun_angle_x": -75.0,  # High noon
        "sun_angle_y": 0.0,
        "ambient_energy": 1.0,
        "fog_enabled": True,
        "fog_density": 0.008,
        "fog_color": (0.9, 0.92, 0.95),
        "terrain_height_scale": 0.0,
        "terrain_noise_scale": 0.018,
        "biome_weights": {"winter": 0.6, "rocky": 0.3, "forest": 0.1},
        "features": {
            "water_ponds": False,               # Frozen/no water
            "terrain_height": True,
            "particles": True,                  # Snow particles
        },
    },

    "train_yard": {
        "name": "Train Yard",
        "description": "Industrial rail yard (requires industrial asset pack)",
        "ground_color": (0.25, 0.22, 0.2),      # Gravel
        "sky_top_color": (0.5, 0.55, 0.6),      # Overcast
        "sky_horizon_color": (0.6, 0.6, 0.55),
        "ground_horizon_color": (0.4, 0.38, 0.35),
        "ground_bottom_color": (0.2, 0.18, 0.15),
        "sun_energy": 2.0,
        "sun_angle_x": -75.0,  # High noon
        "sun_angle_y": 0.0,
        "ambient_energy": 1.0,
        "fog_enabled": True,
        "fog_density": 0.02,
        "fog_color": (0.55, 0.55, 0.5),
        "terrain_height_scale": 0.0,            # Mostly flat
        "terrain_noise_scale": 0.005,
        "biome_weights": {"rocky": 0.8, "meadow": 0.2, "forest": 0.0},
        "features": {
            "water_ponds": False,
            "terrain_height": False,
            "particles": False,
        },
        "note": "Requires industrial asset pack - will use available nature assets as placeholders",
    },
}

# Select which preset to use
# Options: "forest_park", "autumn_forest", "desert_canyon", "snowy_peaks", "train_yard"
ACTIVE_PRESET = "forest_park"

def get_preset():
    """Get the active environment preset with defaults."""
    preset = ENVIRONMENT_PRESETS.get(ACTIVE_PRESET, ENVIRONMENT_PRESETS["forest_park"])
    return preset

# -------------------------
# STEP 1 - FIND THE ZIP
# -------------------------

def find_kaykit_zip():
    """Look for the KayKit Forest zip in the script directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    patterns = [
        os.path.join(script_dir, "KayKit_Forest*.zip"),
        os.path.join(script_dir, "kaykit*forest*.zip"),
        os.path.join(script_dir, "kaykit*.zip"),
        os.path.join(script_dir, "*.zip"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=False)
        if matches:
            return matches[0]
    return None

def list_model_files_in_zip(zip_path):
    """Return a dict of basename -> full_zip_path for all model files in the zip."""
    model_map = {}
    supported_ext = (".glb", ".fbx", ".obj")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.lower().endswith(supported_ext):
                basename = os.path.basename(name)
                model_map[basename] = name
    return model_map

# -------------------------
# STEP 2 - EXTRACT AND ORGANISE ASSETS
# -------------------------

def setup_godot_project(project_dir):
    """Create the Godot project folder and a minimal project.godot if needed."""
    os.makedirs(project_dir, exist_ok=True)
    project_godot = os.path.join(project_dir, "project.godot")
    if not os.path.exists(project_godot):
        with open(project_godot, "w") as f:
            f.write('; Engine configuration file.\n')
            f.write('; Generated by generate_map.py\n\n')
            f.write('config_version=5\n\n')
            f.write('[application]\n\n')
            f.write('config/name="GeneratedMap"\n')
            f.write('config/features=PackedStringArray("4.3", "Forward Plus")\n')
        print(f"  Created minimal project.godot in {project_dir}")

def extract_assets(zip_path, model_map, role_map, assets_dir):
    """
    Extract model files for each role into assets_dir.
    Returns a dict of role -> model filename for roles that were found.
    Skips extraction if the file already exists.
    """
    os.makedirs(assets_dir, exist_ok=True)
    resolved = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        for role, candidates in role_map.items():
            for candidate in candidates:
                if candidate in model_map:
                    dest_path = os.path.join(assets_dir, candidate)
                    if os.path.exists(dest_path):
                        resolved[role] = candidate
                        print(f"  Skipped [{role}] <- {candidate} (exists)")
                    else:
                        with zf.open(model_map[candidate]) as src, open(dest_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        resolved[role] = candidate
                        print(f"  Extracted [{role}] <- {candidate}")
                    break

    return resolved

def extract_textures(zip_path, assets_dir):
    """
    Extract texture files from the KayKit zip to assets directory.
    The FBX models reference these textures for their materials.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            # Look for texture files (png, jpg, etc) in fbx folder
            if name.endswith('.png') and '/fbx/' in name.lower() and 'unity' not in name.lower():
                texture_name = os.path.basename(name)
                dest_path = os.path.join(assets_dir, texture_name)
                if not os.path.exists(dest_path):
                    with zf.open(name) as src, open(dest_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"  Extracted texture: {texture_name}")

def load_realistic_assets(project_dir):
    """
    Load realistic tree assets from the realistic_trees folder.
    Returns a dict of role -> model filename, and copies textures to assets folder.
    """
    realistic_dir = os.path.join(project_dir, REALISTIC_ASSETS_SUBDIR)
    if not os.path.exists(realistic_dir):
        print(f"  No realistic assets folder found: {realistic_dir}")
        return {}

    resolved = {}
    for role, candidates in REALISTIC_ASSET_ROLES.items():
        for candidate in candidates:
            src_path = os.path.join(realistic_dir, candidate)
            if os.path.exists(src_path):
                resolved[role] = candidate
                print(f"  Loaded realistic [{role}] <- {candidate}")
                break

    # Copy textures to the realistic assets folder if needed
    textures_dir = os.path.join(realistic_dir, "Textures")
    if os.path.exists(textures_dir):
        for tex_file in os.listdir(textures_dir):
            src = os.path.join(textures_dir, tex_file)
            dst = os.path.join(realistic_dir, tex_file)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"  Copied texture: {tex_file}")

    return resolved

def fuzzy_resolve_assets(zip_path, model_map, missing_roles, role_map, assets_dir):
    """
    Case-insensitive fuzzy match for roles that were not found by exact name.
    Also extracts the matched files.
    """
    resolved = {}
    available = list(model_map.keys())

    with zipfile.ZipFile(zip_path, "r") as zf:
        for role in missing_roles:
            candidates = role_map[role]
            keywords = [c.lower().replace(".glb", "").replace("_", "") for c in candidates]

            for avail in available:
                avail_key = avail.lower().replace(".glb", "").replace("_", "")
                for kw in keywords:
                    if kw in avail_key or avail_key in kw:
                        dest_path = os.path.join(assets_dir, avail)
                        if os.path.exists(dest_path):
                            print(f"  Skipped fuzzy [{role}] <- {avail} (exists)")
                        else:
                            with zf.open(model_map[avail]) as src, open(dest_path, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            print(f"  Fuzzy match  [{role}] <- {avail}")
                        resolved[role] = avail
                        break
                if role in resolved:
                    break

    return resolved

# -------------------------
# STEP 3 - GENERATE .TSCN WRAPPER SCENES FOR EACH MODEL
# -------------------------

def _make_uid(seed_val):
    r = random.Random(int(seed_val) & 0xFFFFFFFF)
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "uid://" + "".join(r.choice(chars) for _ in range(12))

def write_model_wrapper_scene(model_filename, scene_path, res_assets_path):
    """Write a minimal .tscn that instances the model file directly."""
    model_res_path = f"{res_assets_path}/{model_filename}"
    scene_name   = os.path.splitext(model_filename)[0]
    scene_uid    = _make_uid(hash(model_filename))
    model_uid    = _make_uid(hash(model_filename) + 1)

    content = (
        f'[gd_scene load_steps=2 format=3 uid="{scene_uid}"]\n\n'
        f'[ext_resource type="PackedScene" uid="{model_uid}" path="{model_res_path}" id="1_{scene_name}"]\n\n'
        f'[node name="{scene_name}" instance=ExtResource("1_{scene_name}")]\n'
    )
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(content)

def generate_wrapper_scenes(resolved_roles, assets_dir, res_assets_path):
    """
    For each extracted model, create a matching .tscn wrapper scene.
    Returns a dict of role -> res:// .tscn path
    """
    tscn_paths = {}
    for role, model_filename in resolved_roles.items():
        scene_name = os.path.splitext(model_filename)[0] + ".tscn"
        scene_path = os.path.join(assets_dir, scene_name)
        write_model_wrapper_scene(model_filename, scene_path, res_assets_path)
        tscn_paths[role] = f"{res_assets_path}/{scene_name}"
        print(f"  Wrapper scene: {scene_name}")
    return tscn_paths

# -------------------------
# STEP 3.5 - PLAYER SCENE
# -------------------------

def write_player_scene(project_dir):
    """Create the player.tscn scene file with CharacterBody3D and Camera."""
    scripts_dir = os.path.join(project_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    player_scene_path = os.path.join(project_dir, "player.tscn")
    scene_uid = _make_uid(hash("player_scene"))
    script_uid = _make_uid(hash("player_script"))

    content = f'''[gd_scene load_steps=3 format=3 uid="{scene_uid}"]

[ext_resource type="Script" uid="{script_uid}" path="res://scripts/player.gd" id="1_player"]

[sub_resource type="CapsuleShape3D" id="1"]
radius = 0.4
height = 1.8

[node name="Player" type="CharacterBody3D"]
script = ExtResource("1_player")

[node name="CollisionShape3D" type="CollisionShape3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.9, 0)
shape = SubResource("1")

[node name="Head" type="Node3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.6, 0)

[node name="Camera3D" type="Camera3D" parent="Head"]
current = true
fov = 75.0
far = 10000.0
'''
    with open(player_scene_path, "w", encoding="utf-8") as f:
        f.write(content)

    return "res://player.tscn"

# -------------------------
# STEP 3.6 - ENVIRONMENT NODES (Ground, Light, Sky)
# -------------------------

def write_environment_nodes():
    """
    Generate TSCN node definitions for environment: ground plane, sunlight, and sky.
    Returns a list of lines to insert into the scene file.
    """
    lines = []

    # Ground plane - large flat mesh with grass color
    r, g, b = GROUND_COLOR
    lines.append('[node name="Ground" type="MeshInstance3D" parent="."]')
    lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.01, {PATH_LENGTH / 2:.1f})')
    lines.append("")

    # DirectionalLight3D - sun
    rot_x_rad = math.radians(SUN_ROTATION_X)
    rot_y_rad = math.radians(SUN_ROTATION_Y)
    # Build rotation matrix for X then Y rotation
    cx, sx = math.cos(rot_x_rad), math.sin(rot_x_rad)
    cy, sy = math.cos(rot_y_rad), math.sin(rot_y_rad)
    # Combined rotation matrix (Y * X)
    m00, m01, m02 = cy, sx*sy, -cx*sy
    m10, m11, m12 = 0, cx, sx
    m20, m21, m22 = sy, -sx*cy, cx*cy

    lines.append('[node name="Sun" type="DirectionalLight3D" parent="."]')
    lines.append(f'transform = Transform3D({m00:.4f}, {m01:.4f}, {m02:.4f}, {m10:.4f}, {m11:.4f}, {m12:.4f}, {m20:.4f}, {m21:.4f}, {m22:.4f}, 0, 20, 0)')
    lines.append('shadow_enabled = true')
    lines.append('light_energy = 1.8')
    lines.append('light_color = Color(1.0, 0.98, 0.9, 1)')
    lines.append('sky_mode = 0')  # LIGHT_ONLY - using PanoramaSkyMaterial
    lines.append('light_angular_distance = 0.5')  # Sun disc size
    lines.append("")

    # WorldEnvironment with sky
    lines.append('[node name="WorldEnvironment" type="WorldEnvironment" parent="."]')
    lines.append("")

    return lines

def write_environment_resources():
    """
    Generate sub_resource definitions for environment (materials, meshes, sky).
    Uses the active preset for colors, lighting, and features.
    Returns (lines, resource_ids) where resource_ids maps names to IDs.
    """
    preset = get_preset()
    lines = []
    res_ids = {}
    next_id = 100  # Start at 100 to avoid conflicts with ext_resources

    # Get preset values with defaults
    ground_color = preset.get("ground_color", (0.3, 0.45, 0.2))
    sky_top = preset.get("sky_top_color", (0.4, 0.65, 0.95))
    sky_horizon = preset.get("sky_horizon_color", (0.85, 0.9, 0.95))
    ground_horizon = preset.get("ground_horizon_color", (0.55, 0.55, 0.5))
    ground_bottom = preset.get("ground_bottom_color", (0.2, 0.17, 0.13))
    ambient_energy = preset.get("ambient_energy", 0.8)
    # Graphics quality setting overrides preset fog setting
    gfx = get_graphics_settings()
    fog_enabled = gfx.get("fog_enabled", preset.get("fog_enabled", True))
    fog_density = preset.get("fog_density", 0.005)
    fog_color = preset.get("fog_color", (0.9, 0.92, 0.95))
    terrain_height = preset.get("terrain_height_scale", TERRAIN_HEIGHT_SCALE)
    terrain_noise = preset.get("terrain_noise_scale", TERRAIN_NOISE_SCALE)

    # Ground noise generator
    res_ids["ground_noise"] = next_id
    lines.append(f'[sub_resource type="FastNoiseLite" id="{next_id}"]')
    lines.append('noise_type = 3')  # Cellular
    lines.append('frequency = 0.05')
    lines.append('fractal_octaves = 3')
    lines.append("")
    next_id += 1

    # Ground noise texture
    res_ids["ground_noise_texture"] = next_id
    lines.append(f'[sub_resource type="NoiseTexture2D" id="{next_id}"]')
    lines.append('seamless = true')
    lines.append('width = 512')
    lines.append('height = 512')
    lines.append(f'noise = SubResource("{res_ids["ground_noise"]}")')
    lines.append("")
    next_id += 1

    # Ground PBR shader material with multi-layer texturing
    res_ids["ground_material"] = next_id
    lines.append(f'[sub_resource type="ShaderMaterial" id="{next_id}"]')
    lines.append('shader = ExtResource("terrain_pbr_shader")')

    # Heightmap for terrain displacement
    lines.append('shader_parameter/heightmap = ExtResource("heightmap")')
    lines.append(f'shader_parameter/height_scale = {terrain_height}')
    lines.append(f'shader_parameter/terrain_size = {GROUND_SIZE}')

    # Layer 1 - Grass (low areas)
    lines.append('shader_parameter/albedo_tex_1 = ExtResource("grass_albedo")')
    lines.append('shader_parameter/normal_tex_1 = ExtResource("grass_normal")')
    lines.append('shader_parameter/roughness_tex_1 = ExtResource("grass_roughness")')
    lines.append('shader_parameter/uv_scale_1 = 25.0')
    lines.append('shader_parameter/height_min_1 = -10.0')
    lines.append('shader_parameter/height_max_1 = 10.0')

    # Layer 2 - Dirt (mid areas, paths)
    lines.append('shader_parameter/albedo_tex_2 = ExtResource("dirt_albedo")')
    lines.append('shader_parameter/normal_tex_2 = ExtResource("dirt_normal")')
    lines.append('shader_parameter/roughness_tex_2 = ExtResource("dirt_roughness")')
    lines.append('shader_parameter/uv_scale_2 = 30.0')
    lines.append('shader_parameter/height_min_2 = 5.0')
    lines.append('shader_parameter/height_max_2 = 25.0')

    # Layer 3 - Rock (high areas, cliffs)
    lines.append('shader_parameter/albedo_tex_3 = ExtResource("rock_albedo")')
    lines.append('shader_parameter/normal_tex_3 = ExtResource("rock_normal")')
    lines.append('shader_parameter/roughness_tex_3 = ExtResource("rock_roughness")')
    lines.append('shader_parameter/uv_scale_3 = 20.0')
    lines.append('shader_parameter/height_min_3 = 20.0')
    lines.append('shader_parameter/height_max_3 = 50.0')

    # Layer 4 - Snow (peaks)
    lines.append('shader_parameter/albedo_tex_4 = ExtResource("snow_albedo")')
    lines.append('shader_parameter/normal_tex_4 = ExtResource("snow_normal")')
    lines.append('shader_parameter/roughness_tex_4 = ExtResource("snow_roughness")')
    lines.append('shader_parameter/uv_scale_4 = 35.0')
    lines.append('shader_parameter/height_min_4 = 40.0')
    lines.append('shader_parameter/height_max_4 = 100.0')

    # Blending settings
    lines.append('shader_parameter/blend_sharpness = 2.0')
    lines.append('shader_parameter/slope_threshold = 0.6')
    lines.append('shader_parameter/slope_blend = 0.15')
    lines.append('shader_parameter/use_triplanar = true')
    lines.append('shader_parameter/triplanar_sharpness = 4.0')
    lines.append("")
    next_id += 1

    # Ground mesh (PlaneMesh with high subdivision for terrain detail)
    res_ids["ground_mesh"] = next_id
    lines.append(f'[sub_resource type="PlaneMesh" id="{next_id}"]')
    lines.append(f'size = Vector2({GROUND_SIZE}, {GROUND_SIZE})')
    lines.append('subdivide_width = 128')
    lines.append('subdivide_depth = 128')
    lines.append(f'material = SubResource("{res_ids["ground_material"]}")')
    lines.append("")
    next_id += 1

    # Ground collision shape (flat plane - WorldBoundaryShape3D)
    res_ids["ground_collision_shape"] = next_id
    lines.append(f'[sub_resource type="WorldBoundaryShape3D" id="{next_id}"]')
    lines.append("")
    next_id += 1

    # Path/trail material (dirt brown)
    res_ids["path_material"] = next_id
    lines.append(f'[sub_resource type="StandardMaterial3D" id="{next_id}"]')
    lines.append('albedo_color = Color(0.45, 0.35, 0.25, 1)')
    lines.append(f'albedo_texture = SubResource("{res_ids["ground_noise_texture"]}")')
    lines.append('uv1_scale = Vector3(10, 10, 1)')
    lines.append('roughness = 0.85')
    lines.append("")
    next_id += 1

    # Water material (uses shader)
    res_ids["water_material"] = next_id
    lines.append(f'[sub_resource type="ShaderMaterial" id="{next_id}"]')
    lines.append('render_priority = 1')
    lines.append('shader = ExtResource("water_shader")')
    lines.append('shader_parameter/water_color = Vector3(0.1, 0.3, 0.5)')
    lines.append('shader_parameter/foam_color = Vector3(0.8, 0.9, 1.0)')
    lines.append('shader_parameter/wave_speed = 0.5')
    lines.append('shader_parameter/wave_height = 0.08')
    lines.append('shader_parameter/wave_frequency = 2.0')
    lines.append('shader_parameter/transparency = 0.7')
    lines.append("")
    next_id += 1

    # Water mesh (circular pond)
    res_ids["water_mesh"] = next_id
    lines.append(f'[sub_resource type="CylinderMesh" id="{next_id}"]')
    lines.append('top_radius = 1.0')
    lines.append('bottom_radius = 1.0')
    lines.append('height = 0.1')
    lines.append('radial_segments = 24')
    lines.append(f'material = SubResource("{res_ids["water_material"]}")')
    lines.append("")
    next_id += 1

    # PANORAMA SKY - Use custom sky_panorama.png texture
    res_ids["sky_material"] = next_id
    lines.append(f'[sub_resource type="PanoramaSkyMaterial" id="{next_id}"]')
    lines.append('panorama = ExtResource("sky_panorama")')
    lines.append("")
    next_id += 1

    # Sky
    res_ids["sky"] = next_id
    lines.append(f'[sub_resource type="Sky" id="{next_id}"]')
    lines.append(f'sky_material = SubResource("{res_ids["sky_material"]}")')
    lines.append("")
    next_id += 1

    # Environment - configured based on graphics quality
    gfx = get_graphics_settings()

    res_ids["environment"] = next_id
    lines.append(f'[sub_resource type="Environment" id="{next_id}"]')
    lines.append('background_mode = 2')  # Sky mode
    lines.append(f'sky = SubResource("{res_ids["sky"]}")')

    # Ambient lighting
    lines.append('ambient_light_source = 2')  # Sky ambient
    lines.append('ambient_light_color = Color(0.8, 0.85, 1.0, 1)')
    lines.append(f'ambient_light_energy = {ambient_energy + 0.5}')
    lines.append('reflected_light_source = 2')  # Sky reflections

    # Tonemapping
    tonemap_mode = gfx.get("tonemap_mode", 3)
    lines.append(f'tonemap_mode = {tonemap_mode}')  # 0=Linear, 2=Reinhard, 3=ACES
    lines.append(f'tonemap_exposure = {gfx.get("tonemap_exposure", 1.0)}')
    lines.append(f'tonemap_white = {gfx.get("tonemap_white", 1.0)}')

    # SDFGI - Global Illumination
    if gfx.get("sdfgi_enabled", False):
        lines.append('sdfgi_enabled = true')
        lines.append(f'sdfgi_cascades = {gfx.get("sdfgi_cascades", 6)}')
        lines.append(f'sdfgi_min_cell_size = {gfx.get("sdfgi_min_cell_size", 0.2)}')
        lines.append(f'sdfgi_cascade0_distance = {gfx.get("sdfgi_cascade0_distance", 12.8)}')
        lines.append(f'sdfgi_y_scale = {gfx.get("sdfgi_y_scale", 1.0)}')
        lines.append(f'sdfgi_energy = {gfx.get("sdfgi_energy", 1.0)}')
        lines.append(f'sdfgi_normal_bias = {gfx.get("sdfgi_normal_bias", 1.1)}')
        lines.append(f'sdfgi_probe_bias = {gfx.get("sdfgi_probe_bias", 1.1)}')
        lines.append(f'sdfgi_bounce_feedback = {gfx.get("sdfgi_bounce_feedback", 0.5)}')
        lines.append(f'sdfgi_read_sky_light = {str(gfx.get("sdfgi_read_sky_light", True)).lower()}')
        lines.append('sdfgi_use_occlusion = true')

    # SSR - Screen Space Reflections
    if gfx.get("ssr_enabled", False):
        lines.append('ssr_enabled = true')
        lines.append(f'ssr_max_steps = {gfx.get("ssr_max_steps", 64)}')
        lines.append(f'ssr_fade_in = {gfx.get("ssr_fade_in", 0.15)}')
        lines.append(f'ssr_fade_out = {gfx.get("ssr_fade_out", 2.0)}')
        lines.append(f'ssr_depth_tolerance = {gfx.get("ssr_depth_tolerance", 0.2)}')

    # SSAO - Screen Space Ambient Occlusion
    if gfx.get("ssao_enabled", False):
        lines.append('ssao_enabled = true')
        lines.append(f'ssao_radius = {gfx.get("ssao_radius", 1.0)}')
        lines.append(f'ssao_intensity = {gfx.get("ssao_intensity", 2.0)}')
        lines.append(f'ssao_power = {gfx.get("ssao_power", 1.5)}')
        lines.append(f'ssao_detail = {gfx.get("ssao_detail", 0.5)}')
        lines.append(f'ssao_horizon = {gfx.get("ssao_horizon", 0.06)}')
        lines.append(f'ssao_sharpness = {gfx.get("ssao_sharpness", 0.98)}')
        lines.append(f'ssao_light_affect = {gfx.get("ssao_light_affect", 0.0)}')
        lines.append(f'ssao_ao_channel_affect = {gfx.get("ssao_ao_channel_affect", 0.0)}')

    # SSIL - Screen Space Indirect Lighting
    if gfx.get("ssil_enabled", False):
        lines.append('ssil_enabled = true')
        lines.append(f'ssil_radius = {gfx.get("ssil_radius", 5.0)}')
        lines.append(f'ssil_intensity = {gfx.get("ssil_intensity", 1.0)}')
        lines.append(f'ssil_sharpness = {gfx.get("ssil_sharpness", 0.98)}')
        lines.append(f'ssil_normal_rejection = {gfx.get("ssil_normal_rejection", 1.0)}')

    # Volumetric Fog (high-end) or regular depth fog
    if gfx.get("volumetric_fog_enabled", False):
        vf_albedo = gfx.get("volumetric_fog_albedo", (0.9, 0.92, 0.95))
        vf_emission = gfx.get("volumetric_fog_emission", (0.0, 0.0, 0.0))
        lines.append('volumetric_fog_enabled = true')
        lines.append(f'volumetric_fog_density = {gfx.get("volumetric_fog_density", 0.01)}')
        lines.append(f'volumetric_fog_albedo = Color({vf_albedo[0]}, {vf_albedo[1]}, {vf_albedo[2]}, 1)')
        lines.append(f'volumetric_fog_emission = Color({vf_emission[0]}, {vf_emission[1]}, {vf_emission[2]}, 1)')
        lines.append(f'volumetric_fog_emission_energy = {gfx.get("volumetric_fog_emission_energy", 0.0)}')
        lines.append(f'volumetric_fog_gi_inject = {gfx.get("volumetric_fog_gi_inject", 1.0)}')
        lines.append(f'volumetric_fog_anisotropy = {gfx.get("volumetric_fog_anisotropy", 0.2)}')
        lines.append(f'volumetric_fog_length = {gfx.get("volumetric_fog_length", 200.0)}')
        lines.append(f'volumetric_fog_detail_spread = {gfx.get("volumetric_fog_detail_spread", 2.0)}')
        lines.append(f'volumetric_fog_ambient_inject = {gfx.get("volumetric_fog_ambient_inject", 0.0)}')
        lines.append(f'volumetric_fog_sky_affect = {gfx.get("volumetric_fog_sky_affect", 1.0)}')
        if gfx.get("volumetric_fog_temporal_reprojection_enabled", True):
            lines.append('volumetric_fog_temporal_reprojection_enabled = true')
            lines.append(f'volumetric_fog_temporal_reprojection_amount = {gfx.get("volumetric_fog_temporal_reprojection_amount", 0.9)}')
    elif fog_enabled or gfx.get("fog_enabled", False):
        # Regular depth fog fallback
        lines.append('fog_enabled = true')
        lines.append('fog_mode = 1')  # Depth fog
        lines.append(f'fog_light_color = Color({fog_color[0]}, {fog_color[1]}, {fog_color[2]}, 1)')
        lines.append('fog_sun_scatter = 0.5')
        lines.append(f'fog_density = {fog_density * 0.5}')

    # Glow/Bloom
    if gfx.get("glow_enabled", False):
        lines.append('glow_enabled = true')
        lines.append(f'glow_normalized = {str(gfx.get("glow_normalized", False)).lower()}')
        lines.append(f'glow_intensity = {gfx.get("glow_intensity", 0.8)}')
        lines.append(f'glow_strength = {gfx.get("glow_strength", 1.0)}')
        lines.append(f'glow_bloom = {gfx.get("glow_bloom", 0.0)}')
        lines.append(f'glow_blend_mode = {gfx.get("glow_blend_mode", 2)}')  # 0=Additive, 1=Screen, 2=Softlight, 3=Replace, 4=Mix
        lines.append(f'glow_hdr_threshold = {gfx.get("glow_hdr_threshold", 1.0)}')
        lines.append(f'glow_hdr_scale = {gfx.get("glow_hdr_scale", 2.0)}')
        lines.append(f'glow_hdr_luminance_cap = {gfx.get("glow_hdr_luminance_cap", 12.0)}')
        lines.append(f'glow_map_strength = {gfx.get("glow_map_strength", 0.8)}')
        glow_levels = gfx.get("glow_levels", [1, 0, 1, 0, 1, 0, 0])
        for i, enabled in enumerate(glow_levels):
            lines.append(f'glow_levels/{i + 1} = {float(enabled)}')

    # Color Adjustments
    if gfx.get("adjustment_enabled", False):
        lines.append('adjustment_enabled = true')
        lines.append(f'adjustment_brightness = {gfx.get("adjustment_brightness", 1.0)}')
        lines.append(f'adjustment_contrast = {gfx.get("adjustment_contrast", 1.05)}')
        lines.append(f'adjustment_saturation = {gfx.get("adjustment_saturation", 1.1)}')

    # Depth of Field (optional)
    if gfx.get("dof_blur_far_enabled", False):
        lines.append('dof_blur_far_enabled = true')
        lines.append(f'dof_blur_far_distance = {gfx.get("dof_blur_far_distance", 100.0)}')
        lines.append(f'dof_blur_far_transition = {gfx.get("dof_blur_far_transition", 50.0)}')
    if gfx.get("dof_blur_near_enabled", False):
        lines.append('dof_blur_near_enabled = true')
        lines.append(f'dof_blur_near_distance = {gfx.get("dof_blur_near_distance", 2.0)}')
        lines.append(f'dof_blur_near_transition = {gfx.get("dof_blur_near_transition", 1.0)}')

    lines.append("")
    next_id += 1

    # Particle material for falling leaves
    res_ids["leaf_particle_material"] = next_id
    lines.append(f'[sub_resource type="ParticleProcessMaterial" id="{next_id}"]')
    lines.append('emission_shape = 3')  # Box
    lines.append('emission_box_extents = Vector3(80, 0, 80)')
    lines.append('direction = Vector3(0.3, -1, 0.2)')
    lines.append('spread = 25.0')
    lines.append('gravity = Vector3(0, -0.3, 0)')
    lines.append('initial_velocity_min = 0.5')
    lines.append('initial_velocity_max = 1.5')
    lines.append('angular_velocity_min = -60.0')
    lines.append('angular_velocity_max = 60.0')
    lines.append('scale_min = 0.08')
    lines.append('scale_max = 0.2')
    lines.append('color = Color(0.65, 0.5, 0.25, 0.9)')
    lines.append("")
    next_id += 1

    # Dust mote particle material
    res_ids["dust_particle_material"] = next_id
    lines.append(f'[sub_resource type="ParticleProcessMaterial" id="{next_id}"]')
    lines.append('emission_shape = 3')
    lines.append('emission_box_extents = Vector3(40, 10, 40)')
    lines.append('direction = Vector3(0, 0.2, 0)')
    lines.append('spread = 180.0')
    lines.append('gravity = Vector3(0, 0.05, 0)')
    lines.append('initial_velocity_min = 0.1')
    lines.append('initial_velocity_max = 0.3')
    lines.append('scale_min = 0.01')
    lines.append('scale_max = 0.03')
    lines.append('color = Color(1, 1, 0.9, 0.4)')
    lines.append("")
    next_id += 1

    # Simple quad mesh for particles
    res_ids["particle_mesh"] = next_id
    lines.append(f'[sub_resource type="QuadMesh" id="{next_id}"]')
    lines.append('size = Vector2(1, 1)')
    lines.append("")
    next_id += 1

    # Collectible material (glowing gem)
    res_ids["collectible_material"] = next_id
    lines.append(f'[sub_resource type="StandardMaterial3D" id="{next_id}"]')
    lines.append('albedo_color = Color(0.2, 0.8, 0.4, 1)')
    lines.append('emission_enabled = true')
    lines.append('emission = Color(0.3, 1.0, 0.5, 1)')
    lines.append('emission_energy_multiplier = 2.0')
    lines.append("")
    next_id += 1

    # Collectible mesh (small sphere)
    res_ids["collectible_mesh"] = next_id
    lines.append(f'[sub_resource type="SphereMesh" id="{next_id}"]')
    lines.append('radius = 0.3')
    lines.append('height = 0.6')
    lines.append(f'material = SubResource("{res_ids["collectible_material"]}")')
    lines.append("")
    next_id += 1

    # Collectible collision shape
    res_ids["collectible_shape"] = next_id
    lines.append(f'[sub_resource type="SphereShape3D" id="{next_id}"]')
    lines.append('radius = 0.5')
    lines.append("")
    next_id += 1

    # Mountain material
    res_ids["mountain_material"] = next_id
    lines.append(f'[sub_resource type="StandardMaterial3D" id="{next_id}"]')
    lines.append('albedo_texture = ExtResource("mountain_color")')
    lines.append('normal_enabled = true')
    lines.append('normal_texture = ExtResource("mountain_normal")')
    lines.append("")
    next_id += 1

    # Grass MultiMesh material with wind animation
    res_ids["grass_multimesh_material"] = next_id
    lines.append(f'[sub_resource type="ShaderMaterial" id="{next_id}"]')
    lines.append('shader = ExtResource("grass_shader")')
    lines.append('shader_parameter/grass_texture = ExtResource("grass_blade")')
    lines.append('shader_parameter/grass_color_base = Vector3(0.15, 0.35, 0.1)')
    lines.append('shader_parameter/grass_color_tip = Vector3(0.35, 0.55, 0.2)')
    lines.append('shader_parameter/color_variation = 0.08')
    lines.append('shader_parameter/alpha_scissor = 0.4')
    lines.append('shader_parameter/wind_strength = 0.4')
    lines.append('shader_parameter/wind_speed = 1.2')
    lines.append('shader_parameter/wind_direction = Vector2(1.0, 0.3)')
    lines.append('shader_parameter/wind_turbulence = 0.25')
    lines.append('shader_parameter/wind_noise = ExtResource("wind_noise")')
    lines.append('shader_parameter/wind_noise_scale = 0.08')
    lines.append('shader_parameter/fade_start = 60.0')
    lines.append('shader_parameter/fade_end = 100.0')
    lines.append('shader_parameter/subsurface_strength = 0.4')
    lines.append('shader_parameter/subsurface_color = Vector3(0.5, 0.75, 0.3)')
    lines.append("")
    next_id += 1

    # Grass blade mesh for MultiMesh - use PlaneMesh for proper grass rendering
    res_ids["grass_blade_mesh"] = next_id
    lines.append(f'[sub_resource type="PlaneMesh" id="{next_id}"]')
    lines.append('size = Vector2(0.2, 0.6)')  # Width x Height
    lines.append('orientation = 2')  # Face Z - vertical plane
    lines.append('center_offset = Vector3(0, 0.3, 0)')  # Pivot at bottom
    lines.append(f'material = SubResource("{res_ids["grass_multimesh_material"]}")')
    lines.append("")
    next_id += 1

    # MultiMesh for grass instances
    grass_area_size = GROUND_SIZE * 0.6
    grass_density = 8.0  # Reduced for faster loading
    grass_count = int(grass_area_size * grass_area_size * grass_density)
    grass_count = min(grass_count, 50000)  # Reduced cap for faster loading

    res_ids["grass_multimesh"] = next_id
    lines.append(f'[sub_resource type="MultiMesh" id="{next_id}"]')
    lines.append('transform_format = 1')  # 3D transforms
    lines.append(f'instance_count = {grass_count}')
    lines.append(f'mesh = SubResource("{res_ids["grass_blade_mesh"]}")')

    # Generate grass transforms using Poisson-like distribution
    rng = random.Random(SEED + 12345)
    transforms = []
    half_size = grass_area_size / 2

    for i in range(grass_count):
        # Random position in area
        x = rng.uniform(-half_size, half_size)
        z = rng.uniform(-half_size, half_size)
        y = 0.0  # Ground level (shader can displace based on terrain)

        # Random rotation around Y axis
        rot_y = rng.uniform(0, math.pi * 2)

        # Random scale variation
        scale = rng.uniform(0.7, 1.3)

        # Build transform as 3x4 row-major matrix (Godot MultiMesh buffer format)
        # Format: [basis_xx, basis_xy, basis_xz, origin_x,
        #          basis_yx, basis_yy, basis_yz, origin_y,
        #          basis_zx, basis_zy, basis_zz, origin_z]
        cy, sy = math.cos(rot_y), math.sin(rot_y)
        # Y rotation matrix rows: [[cos, 0, sin], [0, 1, 0], [-sin, 0, cos]]
        transforms.append(f"{cy*scale}, 0, {sy*scale}, {x}, 0, {scale}, 0, {y}, {-sy*scale}, 0, {cy*scale}, {z}")

    # Write transforms as buffer (PackedFloat32Array format)
    lines.append(f'buffer = PackedFloat32Array({", ".join(transforms)})')
    lines.append("")
    next_id += 1

    return lines, res_ids

def generate_path_curve_resource(path_pts, res_id):
    """Generate a Curve3D sub_resource for a Path3D from path points."""
    lines = []
    lines.append(f'[sub_resource type="Curve3D" id="{res_id}"]')

    # Sample every Nth point to keep the curve manageable
    step = max(1, len(path_pts) // 50)
    sampled = path_pts[::step]
    if path_pts[-1] not in sampled:
        sampled.append(path_pts[-1])

    # Build the point arrays
    points_str = ", ".join(f"Vector3({p[0]:.2f}, 0.02, {p[1]:.2f})" for p in sampled)
    lines.append(f'point_count = {len(sampled)}')

    for i, p in enumerate(sampled):
        lines.append(f'point_{i}/position = Vector3({p[0]:.2f}, 0.02, {p[1]:.2f})')
        # Add some in/out tangents for smoother curve
        if i > 0 and i < len(sampled) - 1:
            dx = sampled[i+1][0] - sampled[i-1][0]
            dz = sampled[i+1][1] - sampled[i-1][1]
            lines.append(f'point_{i}/in = Vector3({-dx*0.2:.2f}, 0, {-dz*0.2:.2f})')
            lines.append(f'point_{i}/out = Vector3({dx*0.2:.2f}, 0, {dz*0.2:.2f})')

    lines.append("")
    return lines

def write_path_nodes(path_pts, secondary_paths, env_res_ids):
    """Generate nodes for visible path/trail rendering."""
    lines = []

    # Main path
    lines.append('[node name="PathTrail" type="Path3D" parent="."]')
    lines.append(f'curve = SubResource("{env_res_ids["main_path_curve"]}")')
    lines.append("")

    # CSGPolygon3D to give the path shape
    lines.append('[node name="PathMesh" type="CSGPolygon3D" parent="PathTrail"]')
    lines.append('polygon = PackedVector2Array(-1.2, 0, 1.2, 0, 1.2, 0.02, -1.2, 0.02)')
    lines.append('mode = 2')  # PATH mode
    lines.append('path_interval_type = 0')  # DISTANCE
    lines.append('path_interval = 0.5')
    lines.append('path_joined = true')
    lines.append(f'material = SubResource("{env_res_ids["path_material"]}")')
    lines.append("")

    # Secondary paths
    for i, sec_path in enumerate(secondary_paths or []):
        curve_id = env_res_ids.get(f"secondary_path_curve_{i}")
        if curve_id:
            lines.append(f'[node name="SecondaryPath_{i}" type="Path3D" parent="."]')
            lines.append(f'curve = SubResource("{curve_id}")')
            lines.append("")

            lines.append(f'[node name="PathMesh" type="CSGPolygon3D" parent="SecondaryPath_{i}"]')
            lines.append('polygon = PackedVector2Array(-0.8, 0, 0.8, 0, 0.8, 0.02, -0.8, 0.02)')
            lines.append('mode = 2')
            lines.append('path_interval_type = 0')
            lines.append('path_interval = 0.5')
            lines.append('path_joined = true')
            lines.append(f'material = SubResource("{env_res_ids["path_material"]}")')
            lines.append("")

    return lines

# -------------------------
# STEP 4 - PATH AND PLACEMENT LOGIC
# -------------------------

def generate_control_points(length, num_points, wander):
    points = [(0.0, 0.0)]
    step = length / (num_points - 1)
    for _ in range(1, num_points):
        px, pz = points[-1]
        points.append((px + random.uniform(-wander, wander), pz + step))
    return points

def catmull_rom(p0, p1, p2, p3, t):
    def cr1d(a, b, c, d, t):
        return 0.5 * ((2*b) + (-a+c)*t + (2*a-5*b+4*c-d)*t*t + (-a+3*b-3*c+d)*t**3)
    return (cr1d(p0[0],p1[0],p2[0],p3[0],t), cr1d(p0[1],p1[1],p2[1],p3[1],t))

def sample_path(ctrl_pts, samples=20):
    ext = [ctrl_pts[0]] + ctrl_pts + [ctrl_pts[-1]]
    pts = []
    for i in range(1, len(ext)-2):
        for s in range(samples):
            pts.append(catmull_rom(ext[i-1], ext[i], ext[i+1], ext[i+2], s/samples))
    pts.append(ctrl_pts[-1])
    return pts

def tangent_at(pts, i):
    i = max(1, min(i, len(pts)-2))
    dx = pts[i+1][0] - pts[i-1][0]
    dz = pts[i+1][1] - pts[i-1][1]
    l  = math.sqrt(dx*dx + dz*dz) or 1.0
    return (dx/l, dz/l)

def perp(t):
    return (-t[1], t[0])

# -------------------------
# TERRAIN HEIGHT FUNCTIONS (Enhanced from C# Noise.cs and MapGenerator.cs)
# -------------------------

# Cache for terrain noise values (cleared at start of each generation)
_terrain_noise_cache = {}
_heightmap_cache = {}

def clear_terrain_cache():
    """Clear the terrain noise cache."""
    global _terrain_noise_cache, _heightmap_cache
    _terrain_noise_cache = {}
    _heightmap_cache = {}

def _get_noise_value(ix, iz, seed_offset=0):
    """Get a deterministic noise value for integer grid coordinates."""
    key = (ix, iz, seed_offset)
    if key not in _terrain_noise_cache:
        # Use deterministic random based on coordinates (like C# FastNoiseLite)
        r = random.Random(hash((ix, iz, SEED + seed_offset)) & 0x7FFFFFFF)
        _terrain_noise_cache[key] = r.random() * 2.0 - 1.0
    return _terrain_noise_cache[key]

def _smooth_noise(x, z, seed_offset=0):
    """Smoothed noise using bilinear interpolation (from C# Noise.cs)."""
    x0, z0 = int(math.floor(x)), int(math.floor(z))
    fx, fz = x - x0, z - z0

    # Smoothstep interpolation (matches C# Mathf.SmoothStep)
    fx = fx * fx * (3 - 2 * fx)
    fz = fz * fz * (3 - 2 * fz)

    n00 = _get_noise_value(x0, z0, seed_offset)
    n10 = _get_noise_value(x0 + 1, z0, seed_offset)
    n01 = _get_noise_value(x0, z0 + 1, seed_offset)
    n11 = _get_noise_value(x0 + 1, z0 + 1, seed_offset)

    nx0 = n00 * (1 - fx) + n10 * fx
    nx1 = n01 * (1 - fx) + n11 * fx

    return nx0 * (1 - fz) + nx1 * fz

def _simplex_noise_pass(x, z, octaves, frequency, seed_offset=0):
    """
    Generate noise for a single pass, mimicking C# GenerateHeightMapSimplex.
    Uses FBM (Fractal Brownian Motion) with configurable octaves and frequency.
    """
    value = 0.0
    amplitude = 1.0
    freq = frequency
    total_amp = 0.0

    for i in range(octaves):
        value += _smooth_noise(x * freq, z * freq, seed_offset + i) * amplitude
        total_amp += amplitude
        amplitude *= 0.5  # Lacunarity for amplitude
        freq *= 2.0       # Lacunarity for frequency

    return value / total_amp if total_amp > 0 else 0.0

def _apply_contrast(value, contrast, mid=0.0):
    """
    Apply contrast adjustment to a height value.
    From C# MapGenerator.ApplyContrast.
    """
    delta = value - mid
    return mid + delta * contrast

def _blend_passes(base_value, add_value, blend_type, blend_weight=1.0):
    """
    Blend two terrain passes together.
    From C# MapGenerator.ApplyBlend.

    Blend types:
    - "base": Use as base layer
    - "add": Add to base
    - "subtract": Subtract from base
    - "mix": Linear interpolation
    """
    if blend_type == "base":
        return base_value
    elif blend_type == "add":
        return base_value + max(0.0, add_value) * blend_weight
    elif blend_type == "subtract":
        return base_value - max(0.0, add_value) * blend_weight
    elif blend_type == "mix":
        return base_value * (1.0 - blend_weight) + add_value * blend_weight
    else:
        return base_value

def get_terrain_height(x, z, path_pts=None):
    """
    Get terrain height at world position (x, z).
    ENHANCED with multi-pass noise blending from C# MapGenerator.
    """
    # Check cache first
    cache_key = (round(x * 10), round(z * 10))  # Cache with 0.1 unit precision
    if cache_key in _heightmap_cache:
        cached_height = _heightmap_cache[cache_key]
        # Still apply path flattening to cached values
        if path_pts:
            cached_height = _apply_path_flattening(cached_height, x, z, path_pts)
        return cached_height

    height = 0.0

    # Multi-pass terrain generation (from C# MapGenerator)
    for pass_idx, terrain_pass in enumerate(TERRAIN_PASSES):
        octaves = terrain_pass.get("octaves", TERRAIN_OCTAVES)
        frequency = terrain_pass.get("frequency", TERRAIN_FREQUENCY)
        scale = terrain_pass.get("scale", 1.0)
        blend_type = terrain_pass.get("blend", "base")
        contrast = terrain_pass.get("contrast", 1.0)

        # Generate noise for this pass
        pass_value = _simplex_noise_pass(
            x * TERRAIN_NOISE_SCALE,
            z * TERRAIN_NOISE_SCALE,
            octaves,
            frequency,
            seed_offset=pass_idx * 100
        )

        # Apply contrast
        pass_value = _apply_contrast(pass_value, contrast)

        # Scale the pass
        pass_value *= scale

        # Blend with previous passes
        height = _blend_passes(height, pass_value, blend_type)

    # Normalize to [0, 1] and apply height scale
    height = (height + 1) * 0.5  # Normalize from [-1, 1] to [0, 1]
    height *= TERRAIN_HEIGHT_SCALE

    # Cache the result (before path flattening)
    _heightmap_cache[cache_key] = height

    # Flatten terrain near paths
    if path_pts:
        height = _apply_path_flattening(height, x, z, path_pts)

    return height

def _apply_path_flattening(height, x, z, path_pts):
    """Apply path flattening to terrain height."""
    min_dist_sq = float('inf')
    for px, pz in path_pts:
        d_sq = (x - px) ** 2 + (z - pz) ** 2
        if d_sq < min_dist_sq:
            min_dist_sq = d_sq

    min_dist = math.sqrt(min_dist_sq)
    if min_dist < PATH_FLATTEN_RADIUS * 2:
        # Smoothly blend to flat near path (smoothstep)
        blend = min(1.0, min_dist / (PATH_FLATTEN_RADIUS * 2))
        blend = blend * blend * (3 - 2 * blend)
        height *= blend

    return height

# -------------------------
# POISSON DISC SAMPLING (from C# PoissonDisc.cs)
# -------------------------

def poisson_disc_sampling(width, height, radius, samples=30, seed=None):
    """
    Generate evenly distributed points using Poisson Disc Sampling.
    Based on the C# implementation from the Infinite Runner project.

    Args:
        width: Width of the sampling region
        height: Height of the sampling region
        radius: Minimum distance between points
        samples: Number of attempts before rejecting a point (default: 30)
        seed: Random seed for reproducibility

    Returns:
        List of (x, y) points
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    cell_size = radius / math.sqrt(2)
    grid_width = math.ceil(width / cell_size)
    grid_height = math.ceil(height / cell_size)

    # Grid stores index+1 of point in that cell (0 means empty)
    grid = [[0] * grid_height for _ in range(grid_width)]
    points = []
    spawn_points = []

    # Start with a point at the center
    start_point = (width / 2, height / 2)
    spawn_points.append(start_point)

    while spawn_points:
        spawn_index = rng.randint(0, len(spawn_points) - 1)
        spawn_center = spawn_points[spawn_index]
        candidate_accepted = False

        for _ in range(samples):
            angle = rng.random() * math.pi * 2
            direction = (math.sin(angle), math.cos(angle))
            dist = rng.uniform(radius, radius * 2)
            candidate = (
                spawn_center[0] + direction[0] * dist,
                spawn_center[1] + direction[1] * dist
            )

            if _is_valid_point(candidate, width, height, cell_size, radius, points, grid):
                points.append(candidate)
                spawn_points.append(candidate)
                cell_x = int(candidate[0] / cell_size)
                cell_y = int(candidate[1] / cell_size)
                grid[cell_x][cell_y] = len(points)
                candidate_accepted = True
                break

        if not candidate_accepted:
            spawn_points.pop(spawn_index)

    return points


def _is_valid_point(candidate, width, height, cell_size, radius, points, grid):
    """Check if a candidate point is valid (within bounds and not too close to others)."""
    x, y = candidate

    # Check bounds
    if x < 0 or x >= width or y < 0 or y >= height:
        return False

    cell_x = int(x / cell_size)
    cell_y = int(y / cell_size)

    # Search neighboring cells
    search_start_x = max(0, cell_x - 2)
    search_end_x = min(cell_x + 2, len(grid) - 1)
    search_start_y = max(0, cell_y - 2)
    search_end_y = min(cell_y + 2, len(grid[0]) - 1)

    radius_sq = radius * radius

    for sx in range(search_start_x, search_end_x + 1):
        for sy in range(search_start_y, search_end_y + 1):
            point_index = grid[sx][sy] - 1
            if point_index >= 0:
                other = points[point_index]
                dx = candidate[0] - other[0]
                dy = candidate[1] - other[1]
                sqr_dist = dx * dx + dy * dy
                if sqr_dist < radius_sq:
                    return False

    return True


def generate_poisson_points_in_area(x_min, x_max, z_min, z_max, radius, seed=None):
    """
    Generate Poisson disc sampled points within a rectangular area.

    Args:
        x_min, x_max: X bounds of the area
        z_min, z_max: Z bounds of the area
        radius: Minimum distance between points
        seed: Random seed

    Returns:
        List of (x, z) world coordinates
    """
    width = x_max - x_min
    height = z_max - z_min

    # Generate points in local space
    local_points = poisson_disc_sampling(width, height, radius, POISSON_SAMPLES, seed)

    # Transform to world space
    world_points = [(x_min + p[0], z_min + p[1]) for p in local_points]

    return world_points


# -------------------------
# ROTATION MATRICES (enhanced from C# WorldItemSettings)
# -------------------------

def y_rot_matrix():
    """Generate a random Y-axis rotation matrix."""
    a = random.uniform(0, math.tau)
    c, s = math.cos(a), math.sin(a)
    return (c, 0.0, -s,  0.0, 1.0, 0.0,  s, 0.0, c)


def rotation_matrix_with_tilt(y_rotation=None, tilt_x=0.0, tilt_z=0.0):
    """
    Generate a rotation matrix with Y rotation and optional X/Z tilt.
    Based on the C# Infinite Runner rotation system.

    Args:
        y_rotation: Y-axis rotation in radians (None for random)
        tilt_x: X-axis tilt in radians
        tilt_z: Z-axis tilt in radians

    Returns:
        9-tuple representing a 3x3 rotation matrix (row-major)
    """
    if y_rotation is None:
        y_rotation = random.uniform(0, math.tau)

    # Build rotation matrices
    cy, sy = math.cos(y_rotation), math.sin(y_rotation)
    cx, sx = math.cos(tilt_x), math.sin(tilt_x)
    cz, sz = math.cos(tilt_z), math.sin(tilt_z)

    # Combined rotation: Rz * Rx * Ry
    # This matches the typical Godot rotation order
    m00 = cy * cz - sy * sx * sz
    m01 = -cx * sz
    m02 = sy * cz + cy * sx * sz

    m10 = cy * sz + sy * sx * cz
    m11 = cx * cz
    m12 = sy * sz - cy * sx * cz

    m20 = -sy * cx
    m21 = sx
    m22 = cy * cx

    return (m00, m01, m02, m10, m11, m12, m20, m21, m22)


def generate_object_rotation(props):
    """
    Generate a rotation matrix for an object based on its properties.
    Implements the rotation logic from C# MapGenerator.

    Args:
        props: Asset properties dict with 'randomize_y_rotation' and 'tilt_angle'

    Returns:
        9-tuple rotation matrix
    """
    y_rotation = None
    tilt_x = 0.0
    tilt_z = 0.0

    # Random Y rotation (from WorldItemSettings.RandomizeYRotation)
    if props.get("randomize_y_rotation", True):
        y_rotation = random.uniform(0, math.tau)
    else:
        y_rotation = 0.0

    # Random tilt (from WorldItemSettings.RandomizeTiltAngle)
    max_tilt = props.get("tilt_angle", 0.0)
    if max_tilt > 0:
        tilt_x = math.radians(random.uniform(-max_tilt, max_tilt))
        tilt_z = math.radians(random.uniform(-max_tilt, max_tilt))

    return rotation_matrix_with_tilt(y_rotation, tilt_x, tilt_z)

def get_asset_props(role):
    """Get properties for an asset role, falling back to defaults."""
    # Start with defaults
    props = dict(DEFAULT_ASSET_PROPS)

    # Try exact match first
    if role in ASSET_PROPERTIES:
        props.update(ASSET_PROPERTIES[role])
        return props

    # Try base name (e.g., "tree_pine" from "tree_pine_1")
    base = "_".join(role.rsplit("_", 1)[:-1]) if role[-1].isdigit() else role
    if base in ASSET_PROPERTIES:
        props.update(ASSET_PROPERTIES[base])
        return props

    return props


def check_altitude_constraint(height, props):
    """
    Check if a terrain height is within the asset's spawn altitude constraints.
    Based on C# MapGenerator's MinimumSpawnAltitude/MaximumSpawnAltitude check.

    Args:
        height: Terrain height at spawn location
        props: Asset properties dict

    Returns:
        True if height is within constraints, False otherwise
    """
    min_alt = props.get("min_altitude", -100.0)
    max_alt = props.get("max_altitude", 100.0)
    return min_alt <= height <= max_alt

def distance_squared(x1, z1, x2, z2):
    """Calculate squared distance between two 2D points."""
    dx = x2 - x1
    dz = z2 - z1
    return dx * dx + dz * dz

def check_collision(x, z, placed_positions, min_dist):
    """Check if position collides with any existing placement."""
    min_dist_sq = min_dist * min_dist
    for px, pz, p_min_dist in placed_positions:
        # Use the larger of the two minimum distances
        check_dist_sq = max(min_dist, p_min_dist) ** 2
        if distance_squared(x, z, px, pz) < check_dist_sq:
            return True
    return False

def get_biome_at_distance(path_distance):
    """Determine biome based on distance along path."""
    # If using realistic trees, always use the realistic biome
    if USE_REALISTIC_TREES:
        return "realistic"
    # Divide path into segments, each segment can be a different biome
    segment = int(path_distance / BIOME_SEGMENT_LENGTH)
    # Use deterministic random based on segment
    r = random.Random(SEED + segment * 1000)
    return r.choice(list(BIOMES.keys()))

def select_asset_for_biome(biome, available_roles):
    """Select an asset role based on biome weights."""
    biome_weights = BIOMES.get(biome, BIOMES["forest"])

    # Build weighted list of available assets
    weighted = []
    for category, weight in biome_weights.items():
        if category in ASSET_CATEGORIES:
            for role in ASSET_CATEGORIES[category]:
                if role in available_roles:
                    weighted.append((role, weight))

    if not weighted:
        return random.choice(list(available_roles))

    # Weighted random selection
    total = sum(w for _, w in weighted)
    r = random.random() * total
    cumulative = 0
    for role, weight in weighted:
        cumulative += weight
        if r <= cumulative:
            return role
    return weighted[-1][0]

def generate_clearings(path_pts):
    """Generate circular clearing zones along the path.
    Returns (clearings, ponds) where ponds are a subset of clearings with water."""
    clearings = []  # List of (center_x, center_z, radius)
    ponds = []      # List of (center_x, center_z, radius) - subset that have water
    # Generate clearings at intervals along the path
    clearing_interval = max(1, len(path_pts) // 8)  # About 8 potential clearing spots
    for i in range(0, len(path_pts), clearing_interval):
        px, pz = path_pts[i]
        if random.random() < CLEARING_CHANCE * 3:  # Higher chance per spot
            # Offset clearing slightly from path center
            offset = random.uniform(0, CLEARING_RADIUS * 0.3)
            angle = random.uniform(0, math.tau)
            cx = px + math.cos(angle) * offset
            cz = pz + math.sin(angle) * offset
            radius = CLEARING_RADIUS * random.uniform(0.7, 1.0)
            clearings.append((cx, cz, radius))
            # 60% of clearings become ponds
            if random.random() < 0.6:
                pond_radius = radius * random.uniform(0.4, 0.7)
                ponds.append((cx, cz, pond_radius))
    return clearings, ponds

def is_in_clearing(x, z, clearings):
    """Check if a position is inside any clearing."""
    for cx, cz, radius in clearings:
        if distance_squared(x, z, cx, cz) < radius * radius:
            return True
    return False

def generate_secondary_paths(main_path_pts):
    """Generate branching secondary paths from the main path."""
    secondary_paths = []

    for _ in range(SECONDARY_PATHS):
        if len(main_path_pts) < 10:
            continue

        # Pick a branch point somewhere along the main path (not too early or late)
        branch_idx = random.randint(len(main_path_pts) // 4, 3 * len(main_path_pts) // 4)
        branch_x, branch_z = main_path_pts[branch_idx]

        # Get tangent at branch point and pick a perpendicular direction
        tang = tangent_at(main_path_pts, branch_idx)
        p = perp(tang)
        side = random.choice([-1, 1])

        # Generate control points for secondary path
        sec_ctrl_pts = [(branch_x, branch_z)]
        num_points = max(3, int(PATH_CONTROL_POINTS * SECONDARY_PATH_LENGTH / PATH_LENGTH))
        step = SECONDARY_PATH_LENGTH / (num_points - 1)

        for i in range(1, num_points):
            last_x, last_z = sec_ctrl_pts[-1]
            # Curve away from main path
            wander_x = random.uniform(-SECONDARY_PATH_WANDER, SECONDARY_PATH_WANDER)
            wander_z = step
            # Apply perpendicular drift
            drift = (i / num_points) * side * SECONDARY_PATH_WANDER * 0.5
            new_x = last_x + wander_x + p[0] * drift
            new_z = last_z + wander_z + p[1] * drift
            sec_ctrl_pts.append((new_x, new_z))

        secondary_paths.append(sample_path(sec_ctrl_pts, samples=15))

    return secondary_paths

def add_cluster_objects(placements, placed_positions, available_roles, x, z, parent_role, path_pts=None):
    """Add small satellite objects around a placed object."""
    if random.random() > CLUSTER_CHANCE:
        return

    # Determine what can cluster around this object
    cluster_candidates = []
    if "tree" in parent_role:
        # Small plants cluster around trees
        cluster_candidates = [r for r in available_roles if any(
            cat in r for cat in ["fern", "mushroom", "flower", "grass"]
        )]
    elif "rock_large" in parent_role:
        # Small rocks cluster around large rocks
        cluster_candidates = [r for r in available_roles if "rock_small" in r or "moss" in r]
    elif "bush" in parent_role:
        cluster_candidates = [r for r in available_roles if any(
            cat in r for cat in ["fern", "flower", "grass"]
        )]

    if not cluster_candidates:
        return

    # Add 1-3 satellite objects
    num_satellites = random.randint(1, 3)
    for _ in range(num_satellites):
        role = random.choice(cluster_candidates)
        props = get_asset_props(role)
        min_spacing = props["min_spacing"]

        # Position near parent
        angle = random.uniform(0, math.tau)
        dist = random.uniform(min_spacing, min_spacing * 2.5)
        sat_x = x + math.cos(angle) * dist
        sat_z = z + math.sin(angle) * dist

        # Check collision
        if check_collision(sat_x, sat_z, placed_positions, min_spacing):
            continue

        scale_min, scale_max = props["scale_range"]
        y_offset = props["y_offset"]

        # Calculate terrain height
        terrain_y = get_terrain_height(sat_x, sat_z, path_pts)

        # Check altitude constraint (from C# MapGenerator)
        if not check_altitude_constraint(terrain_y, props):
            continue

        placements.append({
            "role": role,
            "x": sat_x,
            "y": terrain_y + y_offset,
            "z": sat_z,
            "scale": random.uniform(scale_min, scale_max),
            "rot": generate_object_rotation(props),  # Use enhanced rotation
        })
        placed_positions.append((sat_x, sat_z, min_spacing))

def generate_placements(path_pts, tscn_paths, secondary_paths=None):
    """
    Generate object placements along paths with improved natural distribution.
    ENHANCED with Poisson Disc Sampling and height-based filtering from C# Infinite Runner.

    Uses:
    - Poisson disc sampling for even distribution (from PoissonDisc.cs)
    - Altitude-based spawn constraints (from WorldItemSettings)
    - Enhanced rotation with tilt (from MapGenerator)
    - Collision avoidance, clearings, biomes, and clustering

    Returns (placements, ponds) where ponds are water features.
    """
    available = list(tscn_paths.keys())
    placements = []
    placed_positions = []  # (x, z, min_dist) for collision checking
    altitude_filtered = 0  # Counter for altitude-filtered objects

    # Separate tree roles for priority placement
    tree_roles = [r for r in available if r in ASSET_CATEGORIES.get("trees", [])]
    non_tree_available = [r for r in available if r not in tree_roles]

    # Generate clearings (some become ponds)
    clearings, ponds = generate_clearings(path_pts)

    # Calculate placement area bounds
    all_x = [p[0] for p in path_pts]
    all_z = [p[1] for p in path_pts]
    x_min = min(all_x) - SCATTER_OUTER
    x_max = max(all_x) + SCATTER_OUTER
    z_min = min(all_z) - SCATTER_OUTER
    z_max = max(all_z) + SCATTER_OUTER

    # Use Poisson Disc Sampling if enabled (from C# PoissonDisc.cs)
    if USE_POISSON_SAMPLING:
        print(f"      Using Poisson Disc Sampling (radius={POISSON_RADIUS})...")

        # Generate Poisson-sampled points in the area
        poisson_points = generate_poisson_points_in_area(
            x_min, x_max, z_min, z_max,
            POISSON_RADIUS * POISSON_GRID_SCALE,
            seed=SEED
        )
        print(f"      Generated {len(poisson_points)} Poisson disc sample points")

        # PASS 1: Place trees first to ensure they get priority
        if tree_roles:
            tree_count = 0
            for x, z in poisson_points:
                if is_in_clearing(x, z, clearings):
                    continue
                # Check path distance
                min_path_dist = float('inf')
                nearest_path_idx = 0
                for i, (px, pz) in enumerate(path_pts):
                    d = math.sqrt(distance_squared(x, z, px, pz))
                    if d < min_path_dist:
                        min_path_dist = d
                        nearest_path_idx = i
                if min_path_dist > SCATTER_OUTER or min_path_dist < SCATTER_INNER:
                    continue
                # Randomly decide to place a tree (30% chance per valid point)
                if random.random() > 0.30:
                    continue
                role = random.choice(tree_roles)
                props = get_asset_props(role)
                min_spacing = props["min_spacing"]
                if check_collision(x, z, placed_positions, min_spacing):
                    continue
                terrain_y = get_terrain_height(x, z, path_pts)
                if not check_altitude_constraint(terrain_y, props):
                    continue
                scale_min, scale_max = props["scale_range"]
                placements.append({
                    "role": role,
                    "x": x,
                    "y": terrain_y + props["y_offset"],
                    "z": z,
                    "scale": random.uniform(scale_min, scale_max),
                    "rot": generate_object_rotation(props),
                })
                placed_positions.append((x, z, min_spacing))
                tree_count += 1
            print(f"      Placed {tree_count} trees in priority pass")

        # PASS 2: Place other objects
        for x, z in poisson_points:
            # Skip if in clearing
            if is_in_clearing(x, z, clearings):
                continue

            # Skip if too far from any path
            min_path_dist = float('inf')
            nearest_path_idx = 0
            for i, (px, pz) in enumerate(path_pts):
                d = math.sqrt(distance_squared(x, z, px, pz))
                if d < min_path_dist:
                    min_path_dist = d
                    nearest_path_idx = i

            if min_path_dist > SCATTER_OUTER:
                continue
            if min_path_dist < SCATTER_INNER:
                continue

            # Calculate distance along path for biome selection
            path_distance = (nearest_path_idx / len(path_pts)) * PATH_LENGTH

            # Select asset based on biome
            biome = get_biome_at_distance(path_distance)
            role = select_asset_for_biome(biome, available)

            # Get asset-specific properties
            props = get_asset_props(role)
            min_spacing = props["min_spacing"]

            # Check collision with already placed objects
            if check_collision(x, z, placed_positions, min_spacing):
                continue

            scale_min, scale_max = props["scale_range"]
            y_offset = props["y_offset"]

            # Calculate terrain height
            terrain_y = get_terrain_height(x, z, path_pts)

            # Check altitude constraint (from C# MapGenerator)
            if not check_altitude_constraint(terrain_y, props):
                altitude_filtered += 1
                continue

            placements.append({
                "role": role,
                "x": x,
                "y": terrain_y + y_offset,
                "z": z,
                "scale": random.uniform(scale_min, scale_max),
                "rot": generate_object_rotation(props),  # Enhanced rotation with tilt
            })
            placed_positions.append((x, z, min_spacing))

            # Add cluster objects around trees and large rocks
            if any(cat in role for cat in ["tree", "rock_large", "bush"]):
                add_cluster_objects(placements, placed_positions, available, x, z, role, path_pts)

    else:
        # Original path-following placement method
        # Combine all paths
        all_paths = [("main", path_pts)]
        if secondary_paths:
            for i, sp in enumerate(secondary_paths):
                all_paths.append((f"secondary_{i}", sp))

        for path_name, pts in all_paths:
            is_secondary = path_name != "main"
            # Secondary paths have fewer objects
            objects_per_seg = OBJECTS_PER_SEGMENT // 2 if is_secondary else OBJECTS_PER_SEGMENT
            scatter_outer = SCATTER_OUTER * 0.7 if is_secondary else SCATTER_OUTER

            for seg in range(len(pts) - 1):
                # Calculate distance along path for biome selection
                path_distance = (seg / len(pts)) * PATH_LENGTH

                for _ in range(objects_per_seg):
                    idx = min(int(seg + random.random()), len(pts) - 1)
                    px, pz = pts[idx]
                    p = perp(tangent_at(pts, idx))
                    side = random.choice([-1, 1])
                    dist = random.uniform(SCATTER_INNER, scatter_outer)

                    # Calculate candidate position
                    x = px + p[0] * side * dist
                    z = pz + p[1] * side * dist

                    # Skip if in clearing
                    if is_in_clearing(x, z, clearings):
                        continue

                    # Select asset based on biome
                    biome = get_biome_at_distance(path_distance)
                    role = select_asset_for_biome(biome, available)

                    # Get asset-specific properties
                    props = get_asset_props(role)
                    min_spacing = props["min_spacing"]

                    # Check collision
                    if check_collision(x, z, placed_positions, min_spacing):
                        continue

                    scale_min, scale_max = props["scale_range"]
                    y_offset = props["y_offset"]

                    # Calculate terrain height
                    terrain_y = get_terrain_height(x, z, path_pts)

                    # Check altitude constraint (from C# MapGenerator)
                    if not check_altitude_constraint(terrain_y, props):
                        altitude_filtered += 1
                        continue

                    placements.append({
                        "role": role,
                        "x": x,
                        "y": terrain_y + y_offset,
                        "z": z,
                        "scale": random.uniform(scale_min, scale_max),
                        "rot": generate_object_rotation(props),  # Enhanced rotation with tilt
                    })
                    placed_positions.append((x, z, min_spacing))

                    # Add cluster objects around trees and large rocks
                    if any(cat in role for cat in ["tree", "rock_large", "bush"]):
                        add_cluster_objects(placements, placed_positions, available, x, z, role, path_pts)

    if altitude_filtered > 0:
        print(f"      Filtered {altitude_filtered} objects by altitude constraints")

    # Add dense grass coverage across the entire playable area
    # Use Poisson disc sampling for grass if enabled
    grass_roles = [r for r in available if r.startswith("grass_")]
    if grass_roles:
        grass_count = 0
        grass_altitude_filtered = 0

        if USE_POISSON_SAMPLING:
            # Use Poisson sampling for grass distribution
            grass_spacing = 3.0  # Increased spacing for faster loading
            grass_points = generate_poisson_points_in_area(
                x_min, x_max, z_min, z_max,
                grass_spacing,
                seed=SEED + 1000  # Different seed for grass
            )

            for jx, jz in grass_points:
                # Skip if in clearing
                if is_in_clearing(jx, jz, clearings):
                    continue

                # Skip if too close to existing objects (trees, rocks)
                too_close = False
                for px, pz, min_d in placed_positions:
                    if (jx - px) ** 2 + (jz - pz) ** 2 < 1.0:
                        too_close = True
                        break

                if not too_close:
                    grass_role = random.choice(grass_roles)
                    props = get_asset_props(grass_role)
                    scale_min, scale_max = props["scale_range"]

                    # Calculate terrain height for grass
                    terrain_y = get_terrain_height(jx, jz, path_pts)

                    # Check altitude constraint
                    if not check_altitude_constraint(terrain_y, props):
                        grass_altitude_filtered += 1
                        continue

                    placements.append({
                        "role": grass_role,
                        "x": jx,
                        "y": terrain_y + props["y_offset"],
                        "z": jz,
                        "scale": random.uniform(scale_min, scale_max),
                        "rot": generate_object_rotation(props),  # Enhanced rotation with tilt
                    })
                    grass_count += 1
        else:
            # Original grid-based grass placement
            grass_spacing = 4.0  # Increased for faster loading
            area_size = GROUND_SIZE * 0.4

            x_start = -area_size / 2
            z_start = 0
            z_end = PATH_LENGTH

            x = x_start
            while x < area_size / 2:
                z = z_start
                while z < z_end:
                    jx = x + random.uniform(-grass_spacing * 0.4, grass_spacing * 0.4)
                    jz = z + random.uniform(-grass_spacing * 0.4, grass_spacing * 0.4)

                    if is_in_clearing(jx, jz, clearings):
                        z += grass_spacing
                        continue

                    too_close = False
                    for px, pz, min_d in placed_positions:
                        if (jx - px) ** 2 + (jz - pz) ** 2 < 1.0:
                            too_close = True
                            break

                    if not too_close:
                        grass_role = random.choice(grass_roles)
                        props = get_asset_props(grass_role)
                        scale_min, scale_max = props["scale_range"]

                        terrain_y = get_terrain_height(jx, jz, path_pts)

                        if not check_altitude_constraint(terrain_y, props):
                            grass_altitude_filtered += 1
                            z += grass_spacing
                            continue

                        placements.append({
                            "role": grass_role,
                            "x": jx,
                            "y": terrain_y + props["y_offset"],
                            "z": jz,
                            "scale": random.uniform(scale_min, scale_max),
                            "rot": generate_object_rotation(props),
                        })
                        grass_count += 1

                    z += grass_spacing
                x += grass_spacing

        print(f"      Added {grass_count} grass patches for ground cover")
        if grass_altitude_filtered > 0:
            print(f"      Filtered {grass_altitude_filtered} grass patches by altitude")

    return placements, ponds

# -------------------------
# STEP 5 - WRITE THE FINAL MAP .TSCN
# -------------------------

def make_transform(rot, scale, x, y, z):
    b = [v*scale for v in rot]
    return (f"Transform3D({b[0]:.4f},{b[1]:.4f},{b[2]:.4f}," 
            f"{b[3]:.4f},{b[4]:.4f},{b[5]:.4f}," 
            f"{b[6]:.4f},{b[7]:.4f},{b[8]:.4f}," 
            f"{x:.4f},{y:.4f},{z:.4f}")

def write_map_scene(placements, tscn_paths, output_path, player_scene_path=None, path_data=None, secondary_paths=None, ponds=None):
    """Write the complete scene file with environment and all placements."""
    used_roles = sorted(set(p["role"] for p in placements))
    resources = {r: tscn_paths[r] for r in used_roles if r in tscn_paths}

    # Generate environment resources
    env_res_lines, env_res_ids = write_environment_resources()

    # Generate path curve resources
    path_curve_lines = []
    next_curve_id = 200  # Start curve IDs at 200

    if path_data:
        env_res_ids["main_path_curve"] = next_curve_id
        path_curve_lines.extend(generate_path_curve_resource(path_data, next_curve_id))
        next_curve_id += 1

        for i, sec_path in enumerate(secondary_paths or []):
            env_res_ids[f"secondary_path_curve_{i}"] = next_curve_id
            path_curve_lines.extend(generate_path_curve_resource(sec_path, next_curve_id))
            next_curve_id += 1

    # Calculate total load steps (ext_resources + sub_resources + 1)
    # +3 shaders (terrain_pbr, grass, water)
    # +12 PBR textures (grass/dirt/rock/snow * 3 each)
    # +5 utility textures (heightmap, wind_noise, detail_noise, grass_blade, sky_panorama)
    # +2 scripts/ui
    # +1 for player if present
    num_ext_resources = len(resources) + 4 + 12 + 5 + 2 + (1 if player_scene_path else 0)
    num_sub_resources = len(env_res_ids)
    load_steps = num_ext_resources + num_sub_resources + 1
    scene_uid = _make_uid(SEED)

    lines = [f'[gd_scene load_steps={load_steps} format=3 uid="{scene_uid}"]', ""]

    # Terrain PBR shader resource
    shader_uid = _make_uid(hash("terrain_pbr_shader"))
    lines.append(f'[ext_resource type="Shader" uid="{shader_uid}" path="res://shaders/terrain_pbr.gdshader" id="terrain_pbr_shader"]')

    # Grass shader resource
    grass_shader_uid = _make_uid(hash("grass_shader"))
    lines.append(f'[ext_resource type="Shader" uid="{grass_shader_uid}" path="res://shaders/grass.gdshader" id="grass_shader"]')

    # Water shader resource
    water_shader_uid = _make_uid(hash("water_shader"))
    lines.append(f'[ext_resource type="Shader" uid="{water_shader_uid}" path="res://shaders/water.gdshader" id="water_shader"]')

    # PBR Textures - Grass
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("grass_albedo"))}" path="res://textures/grass_albedo.png" id="grass_albedo"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("grass_normal"))}" path="res://textures/grass_normal.png" id="grass_normal"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("grass_roughness"))}" path="res://textures/grass_roughness.png" id="grass_roughness"]')

    # PBR Textures - Dirt
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("dirt_albedo"))}" path="res://textures/dirt_albedo.png" id="dirt_albedo"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("dirt_normal"))}" path="res://textures/dirt_normal.png" id="dirt_normal"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("dirt_roughness"))}" path="res://textures/dirt_roughness.png" id="dirt_roughness"]')

    # PBR Textures - Rock
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("rock_albedo"))}" path="res://textures/rock_albedo.png" id="rock_albedo"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("rock_normal"))}" path="res://textures/rock_normal.png" id="rock_normal"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("rock_roughness"))}" path="res://textures/rock_roughness.png" id="rock_roughness"]')

    # PBR Textures - Snow
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("snow_albedo"))}" path="res://textures/snow_albedo.png" id="snow_albedo"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("snow_normal"))}" path="res://textures/snow_normal.png" id="snow_normal"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("snow_roughness"))}" path="res://textures/snow_roughness.png" id="snow_roughness"]')

    # Heightmap and noise textures
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("heightmap"))}" path="res://textures/heightmap.png" id="heightmap"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("wind_noise"))}" path="res://textures/wind_noise.png" id="wind_noise"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("detail_noise"))}" path="res://textures/detail_noise.png" id="detail_noise"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("grass_blade"))}" path="res://textures/grass_blade.png" id="grass_blade"]')

    # Sky panorama texture
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("sky_panorama"))}" path="res://textures/sky_panorama.png" id="sky_panorama"]')

    # Mountain mesh and textures
    mountain_uid = _make_uid(hash("mountain_obj"))
    lines.append(f'[ext_resource type="ArrayMesh" uid="{mountain_uid}" path="res://assets/nature/mountain.obj" id="mountain_mesh"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("mountain_color"))}" path="res://assets/nature/mountain_color.png" id="mountain_color"]')
    lines.append(f'[ext_resource type="Texture2D" uid="{_make_uid(hash("mountain_normal"))}" path="res://assets/nature/mountain_normal.png" id="mountain_normal"]')

    # Collectible script
    collectible_uid = _make_uid(hash("collectible_script"))
    lines.append(f'[ext_resource type="Script" uid="{collectible_uid}" path="res://scripts/collectible.gd" id="collectible_script"]')

    # UI scene
    ui_uid = _make_uid(hash("ui_scene"))
    lines.append(f'[ext_resource type="PackedScene" uid="{ui_uid}" path="res://ui.tscn" id="ui_scene"]')

    # Player scene resource
    if player_scene_path:
        player_uid = _make_uid(hash("player_instance"))
        lines.append(f'[ext_resource type="PackedScene" uid="{player_uid}" path="{player_scene_path}" id="player_scene"]')

    # External resources (packed scenes for nature assets)
    res_ids = {}
    for i, (role, path) in enumerate(resources.items(), 1):
        rid = f"{i}_{role}"
        res_ids[role] = rid
        ruid = _make_uid(hash(path))
        lines.append(
            f'[ext_resource type="PackedScene" uid="{ruid}" path="{path}" id="{rid}"]'
        )

    lines.append("")

    # Sub resources (environment materials, meshes, sky)
    lines.extend(env_res_lines)

    # Path curve resources
    lines.extend(path_curve_lines)

    # Root node
    lines.append('[node name="GeneratedMap" type="Node3D"]')
    lines.append("")

    # Ground plane with collision
    lines.append('[node name="Ground" type="StaticBody3D" parent="."]')
    lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, {PATH_LENGTH / 2:.1f})')
    lines.append("")

    lines.append('[node name="GroundMesh" type="MeshInstance3D" parent="Ground"]')
    lines.append(f'mesh = SubResource("{env_res_ids["ground_mesh"]}")')
    lines.append("")

    lines.append('[node name="GroundCollision" type="CollisionShape3D" parent="Ground"]')
    # Raise collision plane to match average terrain height (half of max displacement)
    preset = get_preset()
    terrain_height = preset.get("terrain_height_scale", TERRAIN_HEIGHT_SCALE)
    avg_terrain_height = terrain_height * 0.5
    lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, {avg_terrain_height}, 0)')
    lines.append(f'shape = SubResource("{env_res_ids["ground_collision_shape"]}")')
    lines.append("")

    # MultiMesh Grass System - shader-based grass with wind animation
    if "grass_blade_mesh" in env_res_ids:
        grass_area_size = GROUND_SIZE * 0.6  # Cover 60% of ground
        grass_density = 8.0  # Reduced for faster loading
        grass_count = int(grass_area_size * grass_area_size * grass_density)
        grass_count = min(grass_count, 50000)  # Reduced cap for faster loading

        lines.append('[node name="GrassField" type="MultiMeshInstance3D" parent="."]')
        lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.01, {PATH_LENGTH / 2:.1f})')
        lines.append('cast_shadow = 0')  # No shadow for grass (performance)

        # Generate grass instance transforms
        lines.append(f'multimesh = SubResource("{env_res_ids["grass_multimesh"]}")')
        lines.append("")

    # Sun (DirectionalLight3D) - REALISTIC daylight with high-quality shadows
    gfx = get_graphics_settings()
    sun_angle_x = -50.0   # Mid-day sun angle
    sun_angle_y = -30.0
    sun_energy = 2.0      # Bright daylight

    rot_x_rad = math.radians(sun_angle_x)
    rot_y_rad = math.radians(sun_angle_y)
    cx, sx = math.cos(rot_x_rad), math.sin(rot_x_rad)
    cy, sy = math.cos(rot_y_rad), math.sin(rot_y_rad)
    m00, m01, m02 = cy, sx * sy, -cx * sy
    m10, m11, m12 = 0, cx, sx
    m20, m21, m22 = sy, -sx * cy, cx * cy

    lines.append('[node name="Sun" type="DirectionalLight3D" parent="."]')
    lines.append(f'transform = Transform3D({m00:.4f}, {m01:.4f}, {m02:.4f}, {m10:.4f}, {m11:.4f}, {m12:.4f}, {m20:.4f}, {m21:.4f}, {m22:.4f}, 0, 50, 0)')
    lines.append('light_color = Color(1.0, 0.95, 0.9, 1)')   # Warm white sunlight
    lines.append(f'light_energy = {sun_energy}')
    lines.append('light_indirect_energy = 1.0')
    lines.append('light_volumetric_fog_energy = 1.0')
    lines.append('light_angular_distance = 0.5')  # Realistic sun size
    lines.append('sky_mode = 0')  # LIGHT_ONLY - using PanoramaSkyMaterial

    # Shadow settings based on graphics quality
    if gfx.get("shadow_enabled", True):
        lines.append('shadow_enabled = true')
        lines.append(f'shadow_bias = {gfx.get("shadow_bias", 0.02)}')
        lines.append(f'shadow_normal_bias = {gfx.get("shadow_normal_bias", 1.0)}')
        if "shadow_blur" in gfx:
            lines.append(f'shadow_blur = {gfx.get("shadow_blur", 1.0)}')
        if "shadow_transmittance_bias" in gfx:
            lines.append(f'shadow_transmittance_bias = {gfx.get("shadow_transmittance_bias", 0.05)}')

        # Directional shadow settings (PSSM)
        shadow_mode = gfx.get("directional_shadow_mode", 2)  # 0=Orthogonal, 1=PSSM 2 Splits, 2=PSSM 4 Splits
        lines.append(f'directional_shadow_mode = {shadow_mode}')

        if shadow_mode >= 1:  # PSSM modes
            if "directional_shadow_split_1" in gfx:
                lines.append(f'directional_shadow_split_1 = {gfx.get("directional_shadow_split_1", 0.1)}')
            if "directional_shadow_split_2" in gfx:
                lines.append(f'directional_shadow_split_2 = {gfx.get("directional_shadow_split_2", 0.2)}')
            if shadow_mode == 2 and "directional_shadow_split_3" in gfx:
                lines.append(f'directional_shadow_split_3 = {gfx.get("directional_shadow_split_3", 0.5)}')
            if gfx.get("directional_shadow_blend_splits", True):
                lines.append('directional_shadow_blend_splits = true')

        lines.append(f'directional_shadow_max_distance = {gfx.get("directional_shadow_max_distance", 200.0)}')
        if "directional_shadow_fade_start" in gfx:
            lines.append(f'directional_shadow_fade_start = {gfx.get("directional_shadow_fade_start", 0.8)}')
    lines.append("")

    # WorldEnvironment
    lines.append('[node name="WorldEnvironment" type="WorldEnvironment" parent="."]')
    lines.append(f'environment = SubResource("{env_res_ids["environment"]}")')
    lines.append("")

    features = preset.get("features", {})

    # Distant Mountain - place mountain model in background
    # Model is large (~500 units) so scale down and position appropriately
    lines.append('[node name="Mountain" type="MeshInstance3D" parent="."]')
    # Scale down to 0.5 and position in distance behind the path
    lines.append(f'transform = Transform3D(0.5, 0, 0, 0, 0.5, 0, 0, 0, 0.5, -250, -200, {PATH_LENGTH / 2 + 700:.1f})')
    lines.append('mesh = ExtResource("mountain_mesh")')
    lines.append(f'surface_material_override/0 = SubResource("{env_res_ids["mountain_material"]}")')
    lines.append("")
    print("      Added mountain backdrop")

    # Particle effects - falling leaves (if enabled in preset)
    if features.get("particles", True) and "leaf_particle_material" in env_res_ids:
        lines.append('[node name="FallingLeaves" type="GPUParticles3D" parent="."]')
        lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 25, {PATH_LENGTH / 2:.1f})')
        lines.append('amount = 80')
        lines.append('lifetime = 12.0')
        lines.append(f'visibility_aabb = AABB(-100, -30, -{PATH_LENGTH/2 + 20}, 200, 60, {PATH_LENGTH + 40})')
        lines.append(f'process_material = SubResource("{env_res_ids["leaf_particle_material"]}")')
        lines.append(f'draw_pass_1 = SubResource("{env_res_ids["particle_mesh"]}")')
        lines.append("")

    # Particle effects - floating dust motes (if enabled in preset)
    if features.get("particles", True) and "dust_particle_material" in env_res_ids:
        lines.append('[node name="DustMotes" type="GPUParticles3D" parent="."]')
        lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 3, {PATH_LENGTH / 2:.1f})')
        lines.append('amount = 100')
        lines.append('lifetime = 15.0')
        lines.append(f'visibility_aabb = AABB(-60, -15, -{PATH_LENGTH/2 + 20}, 120, 30, {PATH_LENGTH + 40})')
        lines.append(f'process_material = SubResource("{env_res_ids["dust_particle_material"]}")')
        lines.append(f'draw_pass_1 = SubResource("{env_res_ids["particle_mesh"]}")')
        lines.append("")

    # Path trails (visible dirt paths)
    if path_data and "main_path_curve" in env_res_ids:
        lines.extend(write_path_nodes(path_data, secondary_paths, env_res_ids))

    # Water ponds (if enabled in preset)
    if features.get("water_ponds", True) and ponds and "water_mesh" in env_res_ids:
        for i, (px, pz, radius) in enumerate(ponds):
            lines.append(f'[node name="Pond_{i}" type="MeshInstance3D" parent="."]')
            # Position pond at terrain height - ponds sit in clearings which are flattened
            # Use the actual terrain height at pond center, add small offset to avoid z-fighting
            pond_terrain_y = get_terrain_height(px, pz, path_data) if path_data else 0.0
            pond_y = pond_terrain_y + 0.05  # Slightly above terrain
            lines.append(f'transform = Transform3D({radius}, 0, 0, 0, 1, 0, 0, 0, {radius}, {px:.2f}, {pond_y:.2f}, {pz:.2f})')
            lines.append(f'mesh = SubResource("{env_res_ids["water_mesh"]}")')
            lines.append("")

    # Player - positioned at start of path with terrain height
    player_x, player_z = 0, -5
    if path_data and len(path_data) > 0:
        player_x, player_z = path_data[0]  # Start of path
    player_terrain_y = get_terrain_height(player_x, player_z, path_data)
    player_y = player_terrain_y + 2.0  # Slightly above terrain

    if player_scene_path:
        lines.append('[node name="Player" parent="." instance=ExtResource("player_scene")]')
        lines.append(f'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {player_x:.2f}, {player_y:.2f}, {player_z:.2f})')
        lines.append("")
    else:
        # Fallback static camera if no player
        camera_y = player_terrain_y + 8.0
        lines.append('[node name="Camera3D" type="Camera3D" parent="."]')
        lines.append(f'transform = Transform3D(1, 0, 0, 0, 0.9659, 0.2588, 0, -0.2588, 0.9659, {player_x:.2f}, {camera_y:.2f}, {player_z - 10:.2f})')
        lines.append('current = true')
        lines.append('fov = 70.0')
        lines.append("")

    # Game UI
    lines.append('[node name="GameUI" parent="." instance=ExtResource("ui_scene")]')
    lines.append("")

    # Nature object placements - grouped by type for organization
    from collections import defaultdict
    placements_by_role = defaultdict(list)
    for p in placements:
        if p["role"] in res_ids:
            placements_by_role[p["role"]].append(p)

    # Create parent nodes for each role type, then instances underneath
    for role, role_placements in placements_by_role.items():
        if not role_placements:
            continue

        # Parent node for this asset type
        lines.append(f'[node name="{role}" type="Node3D" parent="."]')
        lines.append("")

        # Child instances with compact naming
        for i, p in enumerate(role_placements):
            tf = make_transform(p["rot"], p["scale"], p["x"], p["y"], p["z"])
            lines.append(f'[node name="{i}" parent="{role}" instance=ExtResource("{res_ids[role]}")]')
            lines.append(f'transform = {tf})')
            lines.append("")

    print(f"      Created {len(placements)} object instances in {len(placements_by_role)} groups")

    # Write to file
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Wrote scene: {output_path}")


# -------------------------
# MAIN EXECUTION
# -------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("Godot Natural Outdoor Map Generator")
    print("=" * 50)

    random.seed(SEED)
    clear_terrain_cache()

    # Step 1: Find KayKit zip
    print("\n[Step 1] Finding KayKit Forest Pack...")
    zip_path = find_kaykit_zip()
    if not zip_path:
        print("ERROR: Could not find KayKit Forest Pack zip file.")
        print("Download from: https://kaylousberg.itch.io/kaykit-forest")
        sys.exit(1)
    print(f"  Found: {zip_path}")

    # Step 2: Setup project and extract assets
    print("\n[Step 2] Setting up Godot project...")
    project_dir = os.path.abspath(GODOT_PROJECT_DIR)
    assets_dir = os.path.join(project_dir, ASSETS_SUBDIR)
    setup_godot_project(project_dir)

    print("\n[Step 2b] Extracting assets (skipping existing)...")
    model_map = list_model_files_in_zip(zip_path)
    resolved = extract_assets(zip_path, model_map, KAYKIT_ASSET_ROLES, assets_dir)

    # Extract textures
    print("\n[Step 2c] Extracting textures...")
    extract_textures(zip_path, assets_dir)

    # Skip realistic assets (slow to import) - using KayKit only for faster loading
    print("\n[Step 2d] Skipping realistic assets (disabled for faster import)...")
    realistic_resolved = {}

    # Fuzzy match missing roles
    missing = set(KAYKIT_ASSET_ROLES.keys()) - set(resolved.keys())
    if missing:
        print(f"\n[Step 2e] Fuzzy matching {len(missing)} missing roles...")
        fuzzy_resolved = fuzzy_resolve_assets(zip_path, model_map, missing, KAYKIT_ASSET_ROLES, assets_dir)
        resolved.update(fuzzy_resolved)

    print(f"\n  Total resolved roles: {len(resolved)}")

    # Step 3: Generate wrapper scenes
    print("\n[Step 3] Generating wrapper scenes...")
    res_assets_path = f"res://{ASSETS_SUBDIR}"
    tscn_paths = generate_wrapper_scenes(resolved, assets_dir, res_assets_path)

    # Add realistic asset paths
    if realistic_resolved:
        res_realistic_path = f"res://{REALISTIC_ASSETS_SUBDIR}"
        for role, filename in realistic_resolved.items():
            scene_name = filename.replace(".glb", ".tscn").replace(".fbx", ".tscn")
            tscn_paths[role] = f"{res_realistic_path}/{scene_name}"

    # Load new user trees if enabled
    if USE_NEW_TREES:
        print("\n[Step 3a] Loading new tree models...")
        new_trees_dir = os.path.join(project_dir, NEW_TREES_SUBDIR)
        if os.path.exists(new_trees_dir):
            for role, candidates in NEW_TREE_ROLES.items():
                for candidate in candidates:
                    model_path = os.path.join(new_trees_dir, candidate)
                    if os.path.exists(model_path):
                        scene_name = candidate.replace(".obj", ".tscn").replace(".fbx", ".tscn")
                        tscn_paths[role] = f"res://{NEW_TREES_SUBDIR}/{scene_name}"
                        print(f"  Loaded [{role}] <- {candidate}")
                        break
        else:
            print(f"  New trees folder not found: {new_trees_dir}")

    # Step 3.5: Write player scene
    print("\n[Step 3.5] Writing player scene...")
    player_scene = write_player_scene(project_dir)

    # Step 4: Generate path and placements
    print("\n[Step 4] Generating terrain and placements...")
    ctrl_pts = generate_control_points(PATH_LENGTH, PATH_CONTROL_POINTS, PATH_WANDER)
    path_pts = sample_path(ctrl_pts)

    secondary_paths = generate_secondary_paths(path_pts)
    placements, ponds = generate_placements(path_pts, tscn_paths, secondary_paths)
    print(f"  Generated {len(placements)} object placements")
    print(f"  Generated {len(ponds)} water ponds")

    # Step 5: Write final scene
    print("\n[Step 5] Writing final map scene...")
    output_path = os.path.join(project_dir, OUTPUT_SCENE)
    write_map_scene(
        placements,
        tscn_paths,
        output_path,
        player_scene_path="res://player.tscn",
        path_data=path_pts,
        secondary_paths=secondary_paths,
        ponds=ponds
    )

    print("\n" + "=" * 50)
    print("DONE!")
    print(f"Open in Godot: {output_path}")
    print("=" * 50)