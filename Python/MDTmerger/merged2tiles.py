"""
DEM to Unreal Engine Tiled Heightmap Exporter
----------------------------------------------
Converts a merged GeoTIFF DEM into 16-bit grayscale PNG tiles
ready for import into Unreal Engine's Landscape system.

Requirements:
    pip install rasterio numpy Pillow

Usage:
    python dem_to_unreal_tiles.py

Configuration:
    Edit the CONFIG section below.
"""

import os
import numpy as np
import rasterio
from rasterio.windows import Window
from PIL import Image

# ─────────────────────────────────────────────
# CONFIG — edit these values
# ─────────────────────────────────────────────

INPUT_TIF      = r"merged.tif"   # Input merged DEM
OUTPUT_DIR     = r"tilesv2"           # Where tiles will be saved

# Tile size — must be a valid Unreal landscape tile size:
#   505, 1009, 2017, 4033
# 1009 is recommended for 0.5m resolution / 160km² datasets
TILE_SIZE      = 1009

# Height normalization
# If None, the script will auto-detect min/max from the entire DEM.
# Set manually if you want consistent values across multiple exports:
#   e.g. HEIGHT_MIN = 0.0, HEIGHT_MAX = 500.0
HEIGHT_MIN     = None   # e.g. 0.0
HEIGHT_MAX     = None   # e.g. 500.0

# Padding: how to fill tiles that hang over the edge of the DEM.
# "edge"    — repeats the last row/column (recommended for landscapes)
# "minimum" — fills with the minimum height value (creates a flat border)
PADDING_MODE   = "edge"

# Output format: "png" (recommended) or "raw" (16-bit big-endian, some UE versions need this)
OUTPUT_FORMAT  = "png"

# ─────────────────────────────────────────────
# VALID UNREAL TILE SIZES (for reference)
# ─────────────────────────────────────────────
VALID_SIZES = [127, 253, 505, 1009, 2017, 4033, 8129]


def validate_tile_size(size):
    if size not in VALID_SIZES:
        print(f"  WARNING: {size} is not a standard Unreal tile size.")
        print(f"  Valid sizes: {VALID_SIZES}")
        print(f"  Continuing anyway — double-check your Unreal import settings.\n")


def get_height_range(src, nodata):
    """Scan the full raster to get min/max (ignoring nodata)."""
    print("  Scanning DEM for height range (this may take a moment)...")
    data = src.read(1).astype(np.float32)
    if nodata is not None:
        data = np.where(data == nodata, np.nan, data)
    h_min = float(np.nanmin(data))
    h_max = float(np.nanmax(data))
    print(f"  Detected height range: {h_min:.2f}m → {h_max:.2f}m")
    return h_min, h_max


def read_tile_data(src, col_off, row_off, tile_size, nodata):
    """Read a tile window, handling edges with padding."""
    raster_h, raster_w = src.height, src.width

    # How much of the tile is within the raster bounds
    read_w = min(tile_size, raster_w - col_off)
    read_h = min(tile_size, raster_h - row_off)
    print('\t', (col_off, row_off), (col_off+read_w, row_off+read_h))
    window = Window(col_off, row_off, read_w, read_h)
    data = src.read(1, window=window).astype(np.float32)

    # Replace nodata with NaN
    if nodata is not None:
        data = np.where(data == nodata, np.nan, data)

    
    # Pad if tile hangs over raster edge
    if read_w < tile_size or read_h < tile_size:
        pad_h = tile_size - read_h
        pad_w = tile_size - read_w

        if PADDING_MODE == "edge":
            data = np.pad(data, ((0, pad_h), (0, pad_w)), mode="edge")
        else:
            fill = float(np.nanmin(data)) if not np.all(np.isnan(data)) else 0.0
            data = np.pad(data, ((0, pad_h), (0, pad_w)),
                          mode="constant", constant_values=fill)
    
    return data


def normalize_to_16bit(data, h_min, h_max):
    """Normalize float height data to 16-bit unsigned integer range."""
    if h_max == h_min:
        return np.zeros_like(data, dtype=np.uint16)

    # Replace any remaining NaNs with minimum
    data = np.where(np.isnan(data), h_min, data)

    # Clamp to range
    data = np.clip(data, h_min, h_max)

    # Normalize to 0–65535
    normalized = (data - h_min) / (h_max - h_min) * 65535.0
    return normalized.astype(np.uint16)


def save_tile(tile_data, filepath, output_format):
    """Save a 16-bit tile as PNG or RAW."""
    if output_format == "png":
        img = Image.fromarray(tile_data, mode="I;16")
        img.save(filepath)
    elif output_format == "raw":
        # 16-bit big-endian raw (some older UE versions need this)
        tile_data.byteswap().tofile(filepath)


def main():
    print("=" * 55)
    print("  DEM → Unreal Tiled Heightmap Exporter")
    print("=" * 55)

    # Validate
    validate_tile_size(TILE_SIZE)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with rasterio.open(INPUT_TIF) as src:
        raster_w = src.width
        raster_h = src.height
        nodata   = src.nodata
        crs      = src.crs
        res      = src.res  # (x_res, y_res) in map units

        print(f"\n  Input DEM:    {os.path.basename(INPUT_TIF)}")
        print(f"  Dimensions:   {raster_w} x {raster_h} px")
        print(f"  Resolution:   {res[0]}m x {res[1]}m")
        print(f"  CRS:          {crs}")
        print(f"  NoData value: {nodata}")
        print(f"\n  Tile size:    {TILE_SIZE} x {TILE_SIZE} px")

        # Calculate grid — step by (TILE_SIZE - 1) so adjacent tiles share edge pixels
        # e.g. 1009px tiles step by 1008, meaning last col of x0 == first col of x1
        step = TILE_SIZE - 1
        cols = int(np.ceil((raster_w - 1) / step))
        rows = int(np.ceil((raster_h - 1) / step))
        total = cols * rows
        print(f"  Tile step:    {step} px (tiles share edge pixels)")
        print(f"  Tile grid:    {cols} cols x {rows} rows = {total} tiles")

        # Coverage info
        tile_coverage_m = TILE_SIZE * res[0]
        tile_coverage_km2 = (tile_coverage_m ** 2) / 1_000_000
        print(f"  Tile coverage: ~{tile_coverage_m:.0f}m x {tile_coverage_m:.0f}m "
              f"({tile_coverage_km2:.2f} km²)")

        # Height range
        h_min = HEIGHT_MIN
        h_max = HEIGHT_MAX
        if h_min is None or h_max is None:
            h_min, h_max = get_height_range(src, nodata)
        else:
            print(f"  Using manual height range: {h_min}m → {h_max}m")

        print(f"\n  Output dir:   {OUTPUT_DIR}")
        print(f"  Format:       16-bit {OUTPUT_FORMAT.upper()}")
        print(f"\n  Starting export...\n")

        # Export tiles
        ext = "png" if OUTPUT_FORMAT == "png" else "r16"
        completed = 0

        for row_idx in range(rows):
            for col_idx in range(cols):
                col_off = col_idx * step
                row_off = row_idx * step

                # Read and normalize
                print(row_idx, col_idx)
                tile_data  = read_tile_data(src, col_off, row_off, TILE_SIZE, nodata)
                tile_16bit = normalize_to_16bit(tile_data, h_min, h_max)

                # Save
                filename = f"heightmap_x{col_idx}_y{row_idx}.{ext}"
                filepath = os.path.join(OUTPUT_DIR, filename)
                save_tile(tile_16bit, filepath, OUTPUT_FORMAT)

                completed += 1
                print(f"  [{completed:>4}/{total}] {filename}")

        print(f"\n  ✓ Done! {total} tiles saved to:\n  {OUTPUT_DIR}")

        # Print Unreal import hints
        print("\n" + "=" * 55)
        print("  UNREAL ENGINE IMPORT NOTES")
        print("=" * 55)
        print(f"  Landscape scale (X, Y): {res[0] * 100:.0f} "
              f"(= {res[0]}m in UE cm units)")
        height_range_m = h_max - h_min
        z_scale = (height_range_m / 512) * 100
        print(f"  Landscape scale (Z):    {z_scale:.4f} "
              f"(for {height_range_m:.1f}m elevation range)")
        print(f"  Import as:              Tiled landscape")
        print(f"  Tile size in UE:        {TILE_SIZE - 1} quads "
              f"(= {TILE_SIZE} verts)")
        print("=" * 55)


if __name__ == "__main__":
    main()