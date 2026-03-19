import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import rowcol
from PIL import Image

# =========================
# USER SETTINGS
# =========================

tif_path = "terrain.tif" # File name
center_x = -101349      # <-- replace with real coordinate (CRS units)
center_y = -107864     # <-- replace with real coordinate
output_size = 505     # Unreal target size
export_png = True      # False if you want RAW only

# =========================

with rasterio.open(tif_path) as src:
    print("Resolution:", src.res)   # should print (0.5, 0.5) for your DEM
    print("Width x Height:", src.width, src.height)
    print("Bounds:", src.bounds)
    # Convert world coordinates to pixel row/col
    row, col = rowcol(src.transform, center_x, center_y)

    half = output_size // 2

    window = Window(
        col - half,
        row - half,
        output_size,
        output_size
    )
    print(window)
    elevation = src.read(1, window=window)
print(elevation.shape)
# Replace nodata
elevation = np.nan_to_num(elevation)

# Compute real elevation range
min_elev = np.min(elevation)
max_elev = np.max(elevation)
elev_range = max_elev - min_elev

print("Elevation min:", min_elev)
print("Elevation max:", max_elev)
print("Elevation range:", elev_range)

# Normalize to 0–65535
scaled = (elevation - min_elev) / elev_range
heightmap_16bit = (scaled * 65535).astype(np.uint16)

# Export RAW
heightmap_16bit.tofile("heightmap.raw")

# Optional PNG export
if export_png:
    img = Image.fromarray(heightmap_16bit)
    img.save("heightmap.png")

# =========================
# Unreal Scale Calculation
# =========================

pixel_resolution = 0.5  # meters per pixel (your DEM resolution)

# X and Y scale
# Unreal: 100 = 1 meter
xy_scale = pixel_resolution * 100

# Z scale
# Unreal default height range = 512m at Z=100
z_scale = (elev_range / 512) * 100

print("\n=== UNREAL IMPORT SETTINGS ===")
print("Section size: 63")
print("Components: depends on layout")
print("Overall resolution:", output_size, "x", output_size)
print("X scale:", xy_scale)
print("Y scale:", xy_scale)
print("Z scale:", z_scale)
print("Z start:", min_elev)
