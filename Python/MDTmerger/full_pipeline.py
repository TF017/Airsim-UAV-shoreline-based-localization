"""
Integrated Geospatial Processing Pipeline
==========================================

This script combines three processing steps:
1. Merge DEM tiles using rasterio (main.py)
2. Convert merged DEM to Unreal Engine tiled heightmaps (merged2tiles.py)
3. Download and process orthophoto data from WMTS service (ortophotosv2.py)

Requirements:
    pip install subprocess glob rasterio owslib Pillow numpy

Usage:
    python integrated_pipeline.py

Pipeline Flow:
    DEM Tiles → Merged DEM → Unreal Tiles + Orthophoto Download
"""

import io
import os
import math
import subprocess
import glob
import numpy as np
from PIL import Image
import rasterio
from rasterio.merge import merge
from rasterio.windows import Window
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from owslib.wmts import WebMapTileService

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: DEM MERGING CONFIG (main.py)
# ─────────────────────────────────────────────────────────────────────────────

DEM_PATH = r"Sagres"
MERGED_DEM_OUTPUT = DEM_PATH+r'/merged.tif'

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: UNREAL ENGINE TILED HEIGHTMAP CONFIG (merged2tiles.py)
# ─────────────────────────────────────────────────────────────────────────────

INPUT_TIF = MERGED_DEM_OUTPUT  # Use merged DEM as input
TILES_OUTPUT_DIR = DEM_PATH+r"/tiles_resized"

# Tile size — must be a valid Unreal landscape tile size:
#   505, 1009, 2017, 4033
TILE_SIZE = 1009

# Height normalization (None = auto-detect)
HEIGHT_MIN = None  # e.g. 0.0
HEIGHT_MAX = None  # e.g. 500.0

# Padding mode: "edge" or "minimum"
PADDING_MODE = "edge"

# Output format: "png" or "raw" # raw is Not working properly
OUTPUT_FORMAT = "png"

# Valid Unreal tile sizes
VALID_SIZES = [127, 253, 505, 1009, 2017, 4033, 8129]

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: WMTS ORTHOPHOTO CONFIG (ortophotosv2.py)
# ─────────────────────────────────────────────────────────────────────────────

WMTS_URL = "https://cartografia.dgterritorio.gov.pt/ortos2018/service"
LAYER = "Ortos2018-RGB"
TILE_MATRIX_SET = "PTTM_06"

# Desired output resolution (meters per pixel) #max is 0.25
ORTHOPHOTO_RESOLUTION = 0.5

# Output files
ORTHOPHOTO_OUTPUT_DIR =DEM_PATH+r'/Ortophotos'
#OUTPUT_PNG = "orthophoto.png"
#OUTPUT_GEOTIFF = "orthophoto.tif"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 FUNCTIONS: DEM MERGING
# ─────────────────────────────────────────────────────────────────────────────

def merge_dem_tiles():
    """Merge all DEM tiles from directory into single GeoTIFF."""
    print("=" * 55)
    print("  STEP 1: DEM TILE MERGING")
    print("=" * 55)
    
    tiles = glob.glob(DEM_PATH + "\\*.tif")
    
    if not tiles:
        print(f"  ERROR: No .tif files found in {DEM_PATH}")
        return False
    
    print(f"  Found {len(tiles)} tiles to merge")
    
    try:
        src_files = [rasterio.open(f) for f in tiles]
        mosaic, transform = merge(src_files)
        
        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": transform,
            "compress": "deflate",
            "tiled": True,
            "bigtiff": "YES"
        })
        
        with rasterio.open(MERGED_DEM_OUTPUT, "w", **out_meta) as dest:
            dest.write(mosaic)
        
        for src in src_files:
            src.close()
        
        print(f"  ✓ Merged DEM saved → {MERGED_DEM_OUTPUT}")
        print(f"  Dimensions: {mosaic.shape[2]} x {mosaic.shape[1]} px\n")
        return True
        
    except Exception as e:
        print(f"  ERROR during merge: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 FUNCTIONS: UNREAL ENGINE TILED HEIGHTMAPS
# ─────────────────────────────────────────────────────────────────────────────

def validate_tile_size(size):
    """Validate tile size against Unreal Engine standards."""
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


def read_tile_data(src, col_off, row_off, read_w, read_h, tile_size, nodata):
    """Read a tile window, handling edges with padding."""
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
    elif output_format == "raw": #Not working properly
        # 16-bit big-endian raw (some older UE versions need this)
        tile_data.byteswap().tofile(filepath)


def create_unreal_tiles():
    """Convert merged DEM to Unreal Engine tiled heightmaps."""
    print("=" * 55)
    print("  STEP 2: UNREAL ENGINE TILED HEIGHTMAP EXPORT")
    print("=" * 55)

    # Validate
    validate_tile_size(TILE_SIZE)
    os.makedirs(TILES_OUTPUT_DIR, exist_ok=True)
    os.makedirs(ORTHOPHOTO_OUTPUT_DIR, exist_ok=True)

    try:
        with rasterio.open(INPUT_TIF) as src:
            raster_w = src.width
            raster_h = src.height
            nodata = src.nodata
            crs = src.crs
            res = src.res  # (x_res, y_res) in map units
            raster_north=src.bounds.top
            raster_weast=src.bounds.left


            print(f"\n  Input DEM:    {os.path.basename(INPUT_TIF)}")
            print(f"  Dimensions:   {raster_w} x {raster_h} px")
            print(f"  Resolution:   {res[0]}m x {res[1]}m")
            print(f"  CRS:          {crs}")
            print(f"  NoData value: {nodata}")
            print(f"\n  Tile size:    {TILE_SIZE} x {TILE_SIZE} px")

            # Calculate grid
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

            print(f"\n  Output dir:   {TILES_OUTPUT_DIR}")
            print(f"  Format:       16-bit {OUTPUT_FORMAT.upper()}")
            print(f"\n  Starting export...\n")

            # Export tiles
            ext = "png" if OUTPUT_FORMAT == "png" else "r16"
            completed = 0

            for row_idx in range(rows):
                for col_idx in range(cols):
                    col_off = col_idx * step
                    row_off = row_idx * step

                    # How much of the tile is within the raster bounds
                    read_w = min(TILE_SIZE, raster_w - col_off)
                    read_h = min(TILE_SIZE, raster_h - row_off)
                    
                    filename = f"ortophoto_x{col_idx}_y{row_idx}.png"
                    filepath = os.path.join(ORTHOPHOTO_OUTPUT_DIR, filename)
                    filename = f"ortophoto_x{col_idx}_y{row_idx}.tif"
                    geotiff_filepath=os.path.join(ORTHOPHOTO_OUTPUT_DIR, filename)
                    north=raster_north-row_off*res[1]
                    weast=raster_weast+col_off*res[0]
                    south=north-read_h*res[1]
                    east=weast+read_w*res[0]
                    #download_orthophoto(north, weast, east, south, filepath, geotiff_filepath)

                    # Read and normalize
                    tile_data = read_tile_data(src, col_off, row_off, read_w, read_h, TILE_SIZE, nodata)
                    tile_16bit = normalize_to_16bit(tile_data, h_min, h_max)

                    # Save
                    filename = f"heightmap_x{col_idx}_y{row_idx}.{ext}"
                    filepath = os.path.join(TILES_OUTPUT_DIR, filename)
                    save_tile(tile_16bit, filepath, OUTPUT_FORMAT)

                    completed += 1
                    print(f"  [{completed:>4}/{total}] {filename}")

            print(f"\n  ✓ Done! {total} tiles saved to:\n  {TILES_OUTPUT_DIR}")

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
            return True

    except Exception as e:
        print(f"  ERROR during tile export: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 FUNCTIONS: WMTS ORTHOPHOTO DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

def get_tile_matrix(wmts, tms_id, target_res_m):
    """
    Pick the TileMatrix whose native resolution is closest to target_res_m.
    """
    OGC_PIXEL_M = 0.00028
    tms = wmts.tilematrixsets[tms_id]

    best = None
    best_res = None
    for tm_id, tm in tms.tilematrix.items():
        res = tm.scaledenominator * OGC_PIXEL_M
        if best is None or (res <= target_res_m and res > best_res) or \
           (best_res > target_res_m and res < best_res):
            best = tm
            best_res = res

    return best, best_res


def bbox_to_tile_range(tm, ul_x, ul_y, lr_x, lr_y):
    """
    Convert a bounding box (EPSG:3763 meters) to tile col/row ranges.
    """
    OGC_PIXEL_M = 0.00028
    res = tm.scaledenominator * OGC_PIXEL_M
    tile_span = res * tm.tilewidth

    origin_x, origin_y = tm.topleftcorner

    col_min = int(math.floor((ul_x - origin_x) / tile_span))
    col_max = int(math.floor((lr_x - origin_x) / tile_span))
    row_min = int(math.floor((origin_y - ul_y) / tile_span))
    row_max = int(math.floor((origin_y - lr_y) / tile_span))

    return col_min, col_max, row_min, row_max, tile_span, res


def fetch_tile(wmts, layer, tms_id, tm_id, row, col):
    """Fetch a single tile from WMTS service."""
    tile = wmts.gettile(
        layer=layer,
        tilematrixset=tms_id,
        tilematrix=tm_id,
        row=row,
        column=col,
        format="image/png",
    )
    return Image.open(io.BytesIO(tile.read())).convert("RGB")


def download_orthophoto(north, weast, east, south, output, output_geotiff):
    """Download and process orthophoto from WMTS service."""

    UL_X=weast; LR_X=east;
    UL_Y=north; LR_Y=south;

    assert UL_X < LR_X, "UL_X must be less than LR_X"
    assert LR_Y < UL_Y, "LR_Y (south) must be less than UL_Y (north)"

    width_m = LR_X - UL_X
    height_m = UL_Y - LR_Y

    print(f"\n  BBox     : ({UL_X}, {UL_Y}) → ({LR_X}, {LR_Y}) m")
    print(f"  Area     : {width_m:.0f} m × {height_m:.0f} m")
    print(f"  Target   : {ORTHOPHOTO_RESOLUTION} m/px")

    try:
        # Connect
        print("\n  Connecting to WMTS…")
        wmts = WebMapTileService(WMTS_URL)

        # Pick the best TileMatrix for the requested resolution
        tm, native_res = get_tile_matrix(wmts, TILE_MATRIX_SET, ORTHOPHOTO_RESOLUTION)
        print(f"  TileMatrix : {tm.identifier}  ({native_res:.4f} m/px native)")

        # Tile range covering the bounding box
        col_min, col_max, row_min, row_max, tile_span, res = \
            bbox_to_tile_range(tm, UL_X, UL_Y, LR_X, LR_Y)

        n_cols = col_max - col_min + 1
        n_rows = row_max - row_min + 1
        total = n_cols * n_rows
        print(f"  Tiles      : {n_cols} × {n_rows} = {total}")

        # Download & stitch at native tile resolution
        TILE_PX = tm.tilewidth
        mosaic_w = n_cols * TILE_PX
        mosaic_h = n_rows * TILE_PX
        mosaic = Image.new("RGB", (mosaic_w, mosaic_h))

        print(f"\n  Downloading {total} tiles…")
        for ri, row in enumerate(range(row_min, row_max + 1)):
            for ci, col in enumerate(range(col_min, col_max + 1)):
                idx = ri * n_cols + ci + 1
                print(f"    [{idx:>4}/{total}] col={col} row={row}", end="\r")
                try:
                    img = fetch_tile(wmts, LAYER, TILE_MATRIX_SET, tm.identifier, row, col)
                    mosaic.paste(img, (ci * TILE_PX, ri * TILE_PX))
                except Exception as e:
                    print(f"\n    Warning: tile col={col} row={row} failed — {e}")

        print(f"\n  Mosaic : {mosaic_w} × {mosaic_h} px @ {native_res:.4f} m/px")

        # Geographic extent of the stitched mosaic
        origin_x, origin_y = tm.topleftcorner
        mosaic_x_min = origin_x + col_min * tile_span
        mosaic_x_max = origin_x + (col_max + 1) * tile_span
        mosaic_y_max = origin_y - row_min * tile_span
        mosaic_y_min = origin_y - (row_max + 1) * tile_span

        # Crop exactly to the requested bounding box
        px_ul_x = int(round((UL_X - mosaic_x_min) / native_res))
        px_ul_y = int(round((mosaic_y_max - UL_Y) / native_res))
        px_lr_x = int(round((LR_X - mosaic_x_min) / native_res))
        px_lr_y = int(round((mosaic_y_max - LR_Y) / native_res))
        print((px_ul_x, px_ul_y, px_lr_x, px_lr_y), (mosaic_x_min, mosaic_y_min, mosaic_x_max, mosaic_y_max))
        cropped = mosaic.crop((px_ul_x, px_ul_y, px_lr_x, px_lr_y))

        # Resample to the requested output resolution
        out_px_w = int(math.ceil(width_m / ORTHOPHOTO_RESOLUTION))
        out_px_h = int(math.ceil(height_m / ORTHOPHOTO_RESOLUTION))

        if (out_px_w, out_px_h) != cropped.size:
            cropped = cropped.resize((out_px_w, out_px_h), Image.BILINEAR)

        print(f"  Output : {out_px_w} × {out_px_h} px @ {ORTHOPHOTO_RESOLUTION} m/px")

        # Save PNG
        cropped.save(output)
        print(f"\n  ✓ PNG     → {output}")
        
        # Save GeoTIFF (EPSG:3763)
        arr = np.moveaxis(np.array(cropped), -1, 0)   # (3, H, W)
        transform = from_bounds(UL_X, LR_Y, LR_X, UL_Y, out_px_w, out_px_h)

        with rasterio.open(
            output_geotiff, "w",
            driver="GTiff",
            height=out_px_h,
            width=out_px_w,
            count=3,
            dtype=arr.dtype,
            crs=CRS.from_epsg(3763),
            transform=transform,
            compress="lzw",
        ) as dst:
            dst.write(arr[0], 1)
            dst.write(arr[1], 2)
            dst.write(arr[2], 3)

        print(f"  ✓ GeoTIFF → {output_geotiff}  (EPSG:3763)")
        print("\n" + "=" * 55)
        
        return True

    except Exception as e:
        print(f"\n  ERROR during orthophoto download: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run the complete geospatial processing pipeline."""
    print("\n")
    print("╔" + "=" * 53 + "╗")
    print("║" + " INTEGRATED GEOSPATIAL PROCESSING PIPELINE ".center(53) + "║")
    print("╚" + "=" * 53 + "╝")
    print()
    
    '''
    # Step 1: Merge DEM tiles
    print("\n[1/2] Merging DEM tiles...")
    if not merge_dem_tiles():
        print("\n  ✗ Pipeline aborted at Step 1")
        return
    '''

    # Step 2: Create Unreal Engine tiles
    print("\n[2/2] Creating Unreal Engine tiled heightmaps...")
    if not create_unreal_tiles():
        print("\n  ✗ Pipeline aborted at Step 2")
        return


    # All done
    print("\n")
    print("╔" + "=" * 53 + "╗")
    print("║" + " ✓ PIPELINE COMPLETED SUCCESSFULLY ".center(53) + "║")
    print("╚" + "=" * 53 + "╝")
    print()
    print("  Outputs:")
    print(f"    • DEM Merge:      {MERGED_DEM_OUTPUT}")
    print(f"    • Unreal Tiles:   {TILES_OUTPUT_DIR}/")
    print(f"    • Orthophoto:     {ORTHOPHOTO_OUTPUT_DIR}/")
    print()


if __name__ == "__main__":
    main()
