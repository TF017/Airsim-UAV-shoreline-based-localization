import numpy as np
lat0=37.612989
lon0=-8.810189
alt0=49.0
R=6378137.0
def ned2WGS84(n, e, d):
    lat = lat0 + (n / R) * (180 / np.pi)
    lon = lon0 + (e / (R * np.cos(np.radians(lat0)))) * (180 / np.pi)
    alt = alt0 - d
    return lon, lat, alt

print(ned2WGS84(7133.500, 1568.400, 62.70))