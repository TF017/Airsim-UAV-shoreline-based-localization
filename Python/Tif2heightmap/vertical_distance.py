import unreal

# Get selected actors
selected = unreal.EditorLevelLibrary.get_selected_level_actors()

if len(selected) != 2:
    print("Select exactly 2 actors!")
else:
    loc1 = selected[0].get_actor_location()
    loc2 = selected[1].get_actor_location()

    # Compute distance vector
    delta = loc2 - loc1
    delta.y=0;
    delta.x=0;
    # Use .length() instead of .size()
    distance_cm = delta.length()
    distance_m = distance_cm / 100

    #print("Distance in cm:", distance_cm)
    print("Vertical distance [m]:", distance_m)
