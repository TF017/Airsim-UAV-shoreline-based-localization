import subprocess, glob
import rasterio
from rasterio.merge import merge

PATH="MDT"
OUTPUT_PATH='merged.tif'
tiles = glob.glob(PATH+"\\*.tif")
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

with rasterio.open(OUTPUT_PATH, "w", **out_meta) as dest:
    dest.write(mosaic)

for src in src_files:
    src.close()


'''
#Alternative
tiles = " ".join(glob.glob(path+ "//*.tif"))
subprocess.run(f"gdal_merge.py -o merged_dem.tif {tiles}", shell=True)
'''


'''
#Alternative
files = "tile1.tif tile2.tif tile3.tif"
subprocess.run(f"gdal_merge.py -o merged.tif -of GTiff {files}", shell=True)
'''

'''
#Alternative
import rasterio
from rasterio.merge import merge

# Open all TIF files
src_files = [rasterio.open(f) for f in ["tile1.tif", "tile2.tif", "tile3.tif"]]

# Merge them
mosaic, transform = merge(src_files)

# Write the result
out_meta = src_files[0].meta.copy()
out_meta.update({
    "driver": "GTiff",
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": transform
})

with rasterio.open("merged_heightmap.tif", "w", **out_meta) as dest:
    dest.write(mosaic)

# Close sources
for src in src_files:
    src.close()
'''