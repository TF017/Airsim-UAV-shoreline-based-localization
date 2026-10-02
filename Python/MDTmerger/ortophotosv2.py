"""
WMTS Orthophoto Downloader — Portugal TM06 (EPSG:3763)
Source : https://cartografia.dgterritorio.gov.pt/ortos2018/service
Layer  : Ortos2018-RGB
TMS    : PTTM_06  (native EPSG:3763 — no CRS conversion needed)

Outputs:
  - orthophoto.png   plain image
  - orthophoto.tif   GeoTIFF in EPSG:3763

Install:
    pip install owslib Pillow rasterio numpy
"""

import io
import math
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from owslib.wmts import WebMapTileService

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

WMTS_URL        = "https://cartografia.dgterritorio.gov.pt/ortos2018/service"
LAYER           = "Ortos2018-RGB"
TILE_MATRIX_SET = "PTTM_06"

# Bounding box — upper-left and lower-right corners in EPSG:3763 (meters)
UL_X = -94_000   # Easting  upper-left
UL_Y = -90_000   # Northing upper-left
LR_X = -93_950   # Easting  lower-right
LR_Y = -90_050   # Northing lower-right

# Desired output resolution (meters per pixel)
# 0.5 → very high detail   1.0 → high   2.0 → medium   5.0 → overview
RESOLUTION = 0.1

# Output files
OUTPUT_PNG     = "orthophoto.png"
OUTPUT_GEOTIFF = "orthophoto.tif"

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_tile_matrix(wmts, tms_id, target_res_m):
    """
    Pick the TileMatrix whose native resolution is closest to (but at least
    as detailed as) target_res_m.

    Each TileMatrix in PTTM_06 has:
      - identifier  : zoom label (e.g. "0", "1", …)
      - scaledenominator : map scale denominator
      - topleftcorner    : (easting, northing) of tile grid origin
      - tilewidth / tileheight : pixels per tile (typically 256)
    
    Resolution (m/px) = ScaleDenominator × 0.00028
    (0.00028 m is the OGC standard pixel size)
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
    Convert a bounding box (EPSG:3763 meters) to tile col/row ranges
    for the given TileMatrix.

    TileMatrix origin is top-left. Columns go right (east), rows go down (south).
    tile_col = floor((x - origin_x) / tile_span_x)
    tile_row = floor((origin_y - y) / tile_span_y)   ← y axis is inverted
    """
    OGC_PIXEL_M  = 0.00028
    res          = tm.scaledenominator * OGC_PIXEL_M      # m/px
    tile_span    = res * tm.tilewidth                      # meters per tile (square tiles)

    origin_x, origin_y = tm.topleftcorner                 # (easting, northing)

    col_min = int(math.floor((ul_x - origin_x) / tile_span))
    col_max = int(math.floor((lr_x - origin_x) / tile_span))
    row_min = int(math.floor((origin_y - ul_y) / tile_span))
    row_max = int(math.floor((origin_y - lr_y) / tile_span))

    return col_min, col_max, row_min, row_max, tile_span, res


def fetch_tile(wmts, layer, tms_id, tm_id, row, col):
    tile = wmts.gettile(
        layer=layer,
        tilematrixset=tms_id,
        tilematrix=tm_id,
        row=row,
        column=col,
        format="image/png",
    )
    print(f"    HTTP status: {tile.info().get('Content-Type')}, size: {len(tile.read())} bytes")
    return Image.open(io.BytesIO(tile.read())).convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    assert UL_X < LR_X, "UL_X must be less than LR_X"
    assert LR_Y < UL_Y, "LR_Y (south) must be less than UL_Y (north)"

    width_m  = LR_X - UL_X
    height_m = UL_Y - LR_Y

    print("=" * 55)
    print("  WMTS Downloader — EPSG:3763 (PTTM_06)")
    print("=" * 55)
    print(f"  BBox     : ({UL_X}, {UL_Y}) → ({LR_X}, {LR_Y}) m")
    print(f"  Area     : {width_m:.0f} m × {height_m:.0f} m")
    print(f"  Target   : {RESOLUTION} m/px")

    # Connect
    print("\nConnecting to WMTS…")
    wmts = WebMapTileService(WMTS_URL)

    # Pick the best TileMatrix for the requested resolution
    tm, native_res = get_tile_matrix(wmts, TILE_MATRIX_SET, RESOLUTION)
    print(f"  TileMatrix : {tm.identifier}  ({native_res:.4f} m/px native)")

    # Tile range covering the bounding box
    col_min, col_max, row_min, row_max, tile_span, res = \
        bbox_to_tile_range(tm, UL_X, UL_Y, LR_X, LR_Y)

    n_cols = col_max - col_min + 1
    n_rows = row_max - row_min + 1
    total  = n_cols * n_rows
    print(f"  Tiles      : {n_cols} × {n_rows} = {total}")

    # ── Download & stitch at native tile resolution ───────────────────────────
    TILE_PX  = tm.tilewidth
    mosaic_w = n_cols * TILE_PX
    mosaic_h = n_rows * TILE_PX
    mosaic   = Image.new("RGB", (mosaic_w, mosaic_h))

    print(f"\nDownloading {total} tiles…")
    for ri, row in enumerate(range(row_min, row_max + 1)):
        for ci, col in enumerate(range(col_min, col_max + 1)):
            idx = ri * n_cols + ci + 1
            print(f"  [{idx:>4}/{total}] col={col} row={row}", end="\r")
            try:
                img = fetch_tile(wmts, LAYER, TILE_MATRIX_SET, tm.identifier, row, col)
                mosaic.paste(img, (ci * TILE_PX, ri * TILE_PX))
            except Exception as e:
                print(f"\n  Warning: tile col={col} row={row} failed — {e}")

    print(f"\n  Mosaic : {mosaic_w} × {mosaic_h} px @ {native_res:.4f} m/px")

    # Geographic extent of the stitched mosaic (exact tile edges, EPSG:3763)
    origin_x, origin_y = tm.topleftcorner
    mosaic_x_min = origin_x + col_min * tile_span
    mosaic_x_max = origin_x + (col_max + 1) * tile_span
    mosaic_y_max = origin_y - row_min * tile_span
    mosaic_y_min = origin_y - (row_max + 1) * tile_span

    # ── Crop exactly to the requested bounding box ────────────────────────────
    # Convert bbox corners to pixel offsets within the mosaic
    px_ul_x = int(round((UL_X - mosaic_x_min) / native_res))
    px_ul_y = int(round((mosaic_y_max - UL_Y)  / native_res))
    px_lr_x = int(round((LR_X - mosaic_x_min) / native_res))
    px_lr_y = int(round((mosaic_y_max - LR_Y)  / native_res))

    cropped = mosaic.crop((px_ul_x, px_ul_y, px_lr_x, px_lr_y))

    # Resample to the requested output resolution
    out_px_w = int(math.ceil(width_m  / RESOLUTION))
    out_px_h = int(math.ceil(height_m / RESOLUTION))

    if (out_px_w, out_px_h) != cropped.size:
        cropped = cropped.resize((out_px_w, out_px_h), Image.BILINEAR)

    print(f"  Output : {out_px_w} × {out_px_h} px @ {RESOLUTION} m/px")

    # ── Save PNG ──────────────────────────────────────────────────────────────
    cropped.save(OUTPUT_PNG)
    print(f"\n  ✓ PNG     → {OUTPUT_PNG}")

    # ── Save GeoTIFF (EPSG:3763, exact bbox, requested resolution) ───────────
    arr       = np.moveaxis(np.array(cropped), -1, 0)   # (3, H, W)
    transform = from_bounds(UL_X, LR_Y, LR_X, UL_Y, out_px_w, out_px_h)

    with rasterio.open(
        OUTPUT_GEOTIFF, "w",
        driver    = "GTiff",
        height    = out_px_h,
        width     = out_px_w,
        count     = 3,
        dtype     = arr.dtype,
        crs       = CRS.from_epsg(3763),
        transform = transform,
        compress  = "lzw",
    ) as dst:
        dst.write(arr[0], 1)
        dst.write(arr[1], 2)
        dst.write(arr[2], 3)

    print(f"  ✓ GeoTIFF → {OUTPUT_GEOTIFF}  (EPSG:3763)")
    print("\nDone!")


if __name__ == "__main__":
    main()