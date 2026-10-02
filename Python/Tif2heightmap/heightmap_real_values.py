import unreal

# Get the selected landscape actor
selected = unreal.EditorLevelLibrary.get_selected_level_actors()

if len(selected) != 1:
    print("Select exactly 1 landscape actor!")
else:
    landscape = selected[0]

    # Get the bounds of the landscape
    bounds = landscape.get_actor_bounds(False)  # False = do not include children
    origin = bounds[0]  # Center point (Vector)
    extent = bounds[1]  # Half-size in each axis (Vector)

    # Full size in Unreal units (cm)
    size_x_cm = extent.x * 2
    size_y_cm = extent.y * 2
    size_z_cm = extent.z * 2

    # Convert to meters
    size_x_m = size_x_cm / 100
    size_y_m = size_y_cm / 100
    size_z_m = size_z_cm / 100

    print("Landscape real-world dimensions:")
    print(f"X (width)  = {size_x_m:.2f} m")
    print(f"Y (length) = {size_y_m:.2f} m")
    print(f"Z (height) = {size_z_m:.2f} m")

    landscape = selected[0]

    # Get bounding box corners
    origin, extent = landscape.get_actor_bounds(False)

    # Compute world-space min and max corners
    min_corner = origin - extent
    max_corner = origin + extent

    # Compute true world dimensions (cm)
    size_x_cm = max_corner.x - min_corner.x
    size_y_cm = max_corner.y - min_corner.y

    # Convert to meters
    size_x_m = size_x_cm / 100
    size_y_m = size_y_cm / 100

    print("=== TRUE WORLD SIZE ===")
    print(f"Width  (X): {size_x_m:.3f} meters")
    print(f"Length (Y): {size_y_m:.3f} meters")

