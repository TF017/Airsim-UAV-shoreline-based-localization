import re

def dms_to_decimal(coord_str):
    """
    Convert a coordinate in DMS format (e.g., 41°24'12.2"N) to decimal.
    """
    pattern = r"(\d+)[°:\s]+(\d+)[']+(\d+(?:\.\d+)?)[\"]?\s*([NSEW])"
    match = re.match(pattern, coord_str.strip(), re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Invalid coordinate format: {coord_str}")
    
    degrees, minutes, seconds, direction = match.groups()
    
    decimal = float(degrees) + float(minutes)/60 + float(seconds)/3600
    
    if direction.upper() in ['S', 'W']:
        decimal *= -1
        
    return decimal


def parse_coordinates(coord_pair):
    """
    Convert a full coordinate string like:
    '41°24\'12.2"N 2°10\'26.5"E'
    into (lat, lon)
    """
    parts = coord_pair.split()
    if len(parts) != 2:
        raise ValueError("Input must contain latitude and longitude")
    
    lat = dms_to_decimal(parts[0])
    lon = dms_to_decimal(parts[1])
    
    return lat, lon


# Example usage
if __name__ == "__main__":
    coord = input("Coordinates: ")
    lat, lon = parse_coordinates(coord)
    
    print(f"Latitude: {round(lat, 6)}")
    print(f"Longitude: {round(lon, 6)}")