import rasterio
from rasterio.windows import from_bounds
import numpy as np

# =========================
# INPUT PARAMETERS
# =========================

input_tif = "x.tif"
output_file = "cropped_output.tif"   # or .png

#This assumes (0.5, 0.5)m per pixel. If (0.25;0.25)m then heightmap_size or square_size_m must change.
center_x = -101349      # <-- replace with real coordinate (CRS units)
center_y = -107864     # <-- replace with real coordinate
heightmap_size = 505     # Unreal target size
square_size_m = heightmap_size*0.5  # resolution of heightmap is 0.5 m

# =========================
# PROCESS
# =========================

half_size = square_size_m / 2

xmin = center_x - half_size
xmax = center_x + half_size
ymin = center_y - half_size
ymax = center_y + half_size

with rasterio.open(input_tif) as src:
    window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
    window = window.round_offsets().round_lengths()
    
    data = src.read(window=window)
    transform = src.window_transform(window)

    profile = src.profile
    profile.update({
        "height": data.shape[1],
        "width": data.shape[2],
        "transform": transform
    })

    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(data)

    profile.update(driver="PNG")


print("Crop complete!")
