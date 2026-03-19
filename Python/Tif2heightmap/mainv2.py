import os
import math
import numpy as np
import rasterio
from rasterio.enums import Resampling

# ---- SETTINGS ----
input_geotiff = "merged.tif"
output_folder = "tiles"

tile_resolution = 1009   # UE4 valid sizes: 505, 1009, 2017
target_meters_per_pixel = 1.0  # UE4 landscape vertex spacing

os.makedirs(output_folder, exist_ok=True)

with rasterio.open(input_geotiff) as src:

    # detect source resolution
    src_res_x = src.transform[0]
    src_res_y = abs(src.transform[4])

    print("Source resolution:", src_res_x, "m")

    scale_factor = src_res_x / target_meters_per_pixel

    new_width = int(src.width * scale_factor)
    new_height = int(src.height * scale_factor)

    print("Resampling to:", new_width, "x", new_height)

    heightmap = src.read(
        1,
        out_shape=(new_height, new_width),
        resampling=Resampling.bilinear
    )

height, width = heightmap.shape

print("Resampled size:", width, "x", height)

# ---- TILE GRID CALCULATION ----

step = tile_resolution - 1

tiles_x = math.floor((width - 1) / step)
tiles_y = math.floor((height - 1) / step)

print("Tile grid:", tiles_x, "x", tiles_y)

# ---- EXPORT TILES ----

for ty in range(tiles_y):
    for tx in range(tiles_x):

        x_start = tx * step
        y_start = ty * step

        x_end = x_start + tile_resolution
        y_end = y_start + tile_resolution

        tile = heightmap[y_start:y_end, x_start:x_end]

        if tile.shape != (tile_resolution, tile_resolution):
            continue

        tile = np.clip(tile, 0, 65535).astype(np.uint16)

        filename = f"heightmap_x{tx}_y{ty}.raw"
        filepath = os.path.join(output_folder, filename)

        tile.tofile(filepath)

print("Done.")