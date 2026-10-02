import numpy as np
from pyproj import Transformer

# TM06 → lat/lon (ETRS89)
tm06_to_geo  = Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True)
geo_to_tm06 = Transformer.from_crs("EPSG:4326", "EPSG:3763", always_xy=True)

# TM06 → ECEF (WGS84)
tm06_to_ecef = Transformer.from_crs("EPSG:3763", "EPSG:4978", always_xy=True)
ecef_to_tm06 = Transformer.from_crs("EPSG:4978", "EPSG:3763", always_xy=True)

# lat/lon → ECEF (WGS84)
geo_to_ecef = Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)
ecef_to_geo = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)

def tm062geo(coordinates): return list(tm06_to_geo.transform(coordinates[0], coordinates[1], coordinates[2]))
def tm062ecef(coordinates): return list(tm06_to_ecef.transform(coordinates[0], coordinates[1], coordinates[2]))
def geo2tm06(coordinates): return list(geo_to_tm06.transform(coordinates[0], coordinates[1], coordinates[2]))
def ecef2tm06(coordinates): return list(ecef_to_tm06.transform(coordinates[0], coordinates[1], coordinates[2]))
def geo2ecef(coordinates): return list(geo_to_ecef.transform(coordinates[0], coordinates[1], coordinates[2]))
def ecef2geo(coordinates): return list(ecef_to_geo.transform(coordinates[0], coordinates[1], coordinates[2]))



class AIRSIM2ECEF:
    def __init__(self, origin_point):
        lon, lat, h = origin_point
        self.origin = np.array(geo2ecef(origin_point))

        lat = np.radians(lat)
        lon = np.radians(lon)

        # NED → ECEF rotation
        self.R = np.array([
            [-np.sin(lat)*np.cos(lon), -np.sin(lon), -np.cos(lat)*np.cos(lon)],
            [-np.sin(lat)*np.sin(lon),  np.cos(lon), -np.cos(lat)*np.sin(lon)],
            [ np.cos(lat),               0,            -np.sin(lat)]
        ])

    def convert(self, ned): #airsim ned to ecef
        return self.origin + self.R @ ned
    
    def invert(self, ecef):#ecef to airsim ned
        return self.R.T @ (ecef - self.origin)
    
    def convert2geo(self, ned): #airsim ned to geo(lon, lat, alt)
        return ecef2geo(self.convert(ned))
    
    def convert2tm06(self, ned): #airsim ned to tm06(east, north, alt)
        return ecef2tm06(self.convert(ned))
    
    def invertfromgeo(self, geo): #geo(lon, lat, alt) to airsim ned
        return self.invert(geo2ecef(geo))
    
    def invertfromtm06(self, tm06): #tm06(east, north, alt) to airsim ned
        return self.invert(tm062ecef(tm06))


class ECEF2ENU:
    def __init__(self, origin_point):
        lon, lat, h = origin_point
        self.origin = np.array(geo2ecef(origin_point))

        lat = np.radians(lat)
        lon = np.radians(lon)
        
        self.R = np.array([
        [-np.sin(lon),  np.cos(lon), 0],
        [-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)],
        [ np.cos(lat)*np.cos(lon),  np.cos(lat)*np.sin(lon), np.sin(lat)]
        ])

    def convert(self, ecef): #ecef to enu
        return self.R @ (ecef - self.origin)
    
    def invert(self, enu): # enu to ecef
        return self.origin + self.R.T @ enu
    
    def invert2geo(self, enu): #enu to geo(lon, lat, alt)
        return ecef2geo(self.invert(enu))
    
    def invert2tm06(self, enu):#enu to tm06(east, north, alt)
        return ecef2tm06(self.invert(enu))
    
    def convertfromgeo(self, geo): #geo(lon, lat, alt) to enu
        return self.convert(geo2ecef(geo))
    
    def convertfromtm06(self, tm06): #tm06(east, north, alt) to enu
        return self.convert(tm062ecef(tm06))
    

class AIRSIM2ECEF_ESD:
    def __init__(self, origin_point):
        lon, lat, h = origin_point

        self.origin = np.array(geo2ecef(origin_point))

        lat = np.radians(lat)
        lon = np.radians(lon)

        # ESD -> ECEF rotation
        # Axes:
        # E = East
        # S = South
        # D = Down

        east = np.array([
            -np.sin(lon),
             np.cos(lon),
             0
        ])

        south = np.array([
             np.sin(lat) * np.cos(lon),
             np.sin(lat) * np.sin(lon),
            -np.cos(lat)
        ])

        down = np.array([
            -np.cos(lat) * np.cos(lon),
            -np.cos(lat) * np.sin(lon),
            -np.sin(lat)
        ])

        self.R = np.column_stack((east, south, down))

    def convert(self, esd):
        """ESD -> ECEF"""
        return self.origin + self.R @ esd

    def invert(self, ecef):
        """ECEF -> ESD"""
        return self.R.T @ (ecef - self.origin)
    
    def convert2geo(self, esd): #airsim esd to geo(lon, lat, alt)
        return ecef2geo(self.convert(esd))
    
    def convert2tm06(self, esd): #airsim esd to tm06(east, north, alt)
        return ecef2tm06(self.convert(esd))
    
    def invertfromgeo(self, geo): #geo(lon, lat, alt) to airsim esd
        return self.invert(geo2ecef(geo))
    
    def invertfromtm06(self, tm06): #tm06(east, north, alt) to airsim esd
        return self.invert(tm062ecef(tm06))



def compare(ned, geo_coordinates_correct):
    ecef_airsim_coordinates=airsim2ecef.convert(ned)
    ecef_right_coordinates=geo2ecef(geo_coordinates_correct)
    geo_airsim_coordinates=ecef2geo(ecef_airsim_coordinates)
    array=[]
    for i in range(len(ecef_right_coordinates)):
        array.append(ecef_right_coordinates[i]-ecef_airsim_coordinates[i])
    array.append(np.linalg.norm(array))
    array=array+geo_airsim_coordinates
    #Array: [error in x; error in y; error in z; norm of error; estimated lon; estimated lat; estimated h]
    return array
    

if __name__ == "__main__":
    #Origin Point
    LAT0 = 37.612989
    LON0 = -8.810189
    H0 = 49.0
    airsim2ecef = AIRSIM2ECEF([LON0, LAT0, H0])
    #ecef2enu = ECEF2ENU([LON0, LAT0, H0])
    print(geo2ecef([LON0, LAT0, H0])) #ECEF of the Origin Point
    print(compare([0, 0, 0], [LON0, LAT0, H0])) #Should be error 0.0
    print(compare([7133.500, 1568.400, 17.0], [-8.792408, 37.677269, 27.04])) # Error is 9.22 m but ortos are not precise
    print(compare([900.400, 236.8, -112.24+89.34], [-8.807511, 37.62112, 70.78])) # Closer to origin and 2.41 m is ok. Same as above
    print(compare([7131.200, 1858.900, -65.600+89.34], [-8.789111, 37.677245, 30.18])) #Easy to locate preciselly in both google earth and unreal and small error

    # Example TM06 coordinates
    E, N, h = -59781.18654933569, -227937.10765380578, 49.0 # Origin Point in TM06 (obtain in a website)

    lon, lat, _h = tm062geo([E, N, h]) #Convert TM06 to Geo
    x, y, z = geo2ecef([lon, lat, _h]) #Geo to ECEF; Theorically tm06->geo->ecef = tm06->ecef (geo must always be done in the background)
    print(lat, lon)
    print(x, y, z)
    print(airsim2ecef.convert2geo([10, 0, 0])) #stays 9.99m meter North in Google Earth so Excelent

