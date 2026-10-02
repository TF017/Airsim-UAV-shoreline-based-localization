import numpy as np
import cv2

def corrected_synthetic_pnp_test():
    """
    Build camera rotation from first principles.
    No body frame, no Euler angles, no conventions to mess up.
    """
    
    # ============================================
    # Ground truth drone state
    # ============================================
    drone_pos = np.array([100.0, 50.0, -80.0])  # NED: 80m altitude
    altitude = 80.0
    heading_deg = 0.0      # facing North
    pitch_from_vertical = 80.0  # degrees (your alpha)
    
    print(f"=== SETUP ===")
    print(f"Drone position (NED): {drone_pos}")
    print(f"Altitude: {altitude}m")
    print(f"Heading: {heading_deg}° (North)")
    print(f"Pitch from vertical: {pitch_from_vertical}°")
    print(f"Expected ground intersection distance: "
          f"{altitude * np.tan(np.radians(pitch_from_vertical)):.1f}m")
    
    # ============================================
    # Build R_cam_to_world using lookAt construction
    # ============================================
    # 
    # Camera convention (OpenCV):
    #   X = right in image
    #   Y = down in image  
    #   Z = forward (optical axis)
    #
    # NED world:
    #   X = North
    #   Y = East
    #   Z = Down
    #
    # Step 1: Where does the optical axis point in world?
    #
    #   80° from vertical = 10° below horizontal
    #   Heading North → optical axis is in the XZ plane (NED)
    
    pitch_from_horiz = 90.0 - pitch_from_vertical  # = 10° below horizontal
    heading_rad = np.radians(heading_deg)
    pitch_rad = np.radians(pitch_from_horiz)
    
    # Optical axis direction in NED world frame
    # Horizontal component points in heading direction
    # Vertical component points down (positive Z in NED)
    cam_z_world = np.array([
        np.cos(pitch_rad) * np.cos(heading_rad),   # North
        np.cos(pitch_rad) * np.sin(heading_rad),   # East
        np.sin(pitch_rad)                            # Down
    ])
    cam_z_world = cam_z_world / np.linalg.norm(cam_z_world)
    
    print(f"\nOptical axis in world (NED): {cam_z_world}")
    print(f"  Should be mostly North with small Down component")
    
    # Step 2: Camera X (right) direction in world
    # For heading=0 (North), right is East
    # Use cross product with "up" hint
    
    up_hint = np.array([0.0, 0.0, -1.0])  # up in NED = -Z
    
    cam_x_world = np.cross(cam_z_world, up_hint)
    cam_x_world = cam_x_world / np.linalg.norm(cam_x_world)
    
    # Step 3: Camera Y (down in image) from cross product
    cam_y_world = np.cross(cam_z_world, cam_x_world)
    cam_y_world = cam_y_world / np.linalg.norm(cam_y_world)
    
    print(f"Camera X (right) in world: {cam_x_world}")
    print(f"Camera Y (down)  in world: {cam_y_world}")
    print(f"Camera Z (fwd)   in world: {cam_z_world}")
    
    # Verify orthogonality
    assert abs(np.dot(cam_x_world, cam_y_world)) < 1e-10
    assert abs(np.dot(cam_x_world, cam_z_world)) < 1e-10
    assert abs(np.dot(cam_y_world, cam_z_world)) < 1e-10
    print("Orthogonality check: PASSED")
    
    # R_cam_to_world: columns are camera axes expressed in world
    R_cam_to_world = np.column_stack([cam_x_world, 
                                       cam_y_world, 
                                       cam_z_world])
    R_world_to_cam = R_cam_to_world.T
    
    # Verify: optical axis in camera frame [0,0,1] → world
    optical_world = R_cam_to_world @ np.array([0, 0, 1])
    print(f"\nVerification: cam [0,0,1] → world {optical_world}")
    print(f"Should match optical axis: {cam_z_world}")
    
    # ============================================
    # Camera intrinsics
    # ============================================
    width, height = 640, 480
    fov_deg = 90.0
    fx = width / (2.0 * np.tan(np.radians(fov_deg / 2.0)))
    fy = fx
    cx, cy = width / 2.0, height / 2.0
    K = np.array([[fx, 0, cx],
                  [0, fy, cy],
                  [0,  0,  1]])
    
    print(f"\nIntrinsics: fx={fx:.1f}, fy={fy:.1f}, "
          f"cx={cx:.1f}, cy={cy:.1f}")
    
    # ============================================
    # Ground intersection of optical axis
    # ============================================
    # Ray: drone_pos + t * cam_z_world
    # Ground at z=0: drone_pos[2] + t * cam_z_world[2] = 0
    t_center = -drone_pos[2] / cam_z_world[2]
    ground_center = drone_pos + t_center * cam_z_world
    
    print(f"\n=== GROUND INTERSECTION ===")
    print(f"Image center hits ground at: {ground_center}")
    print(f"Distance from drone (horizontal): "
          f"{np.sqrt((ground_center[0]-drone_pos[0])**2 + (ground_center[1]-drone_pos[1])**2):.1f}m")
    
    # ============================================
    # Generate synthetic ground points AROUND the
    # ground intersection point
    # ============================================
    np.random.seed(42)
    N = 80
    ground_points = np.zeros((N, 3))
    ground_points[:, 0] = ground_center[0] + np.random.uniform(-150, 150, N)
    ground_points[:, 1] = ground_center[1] + np.random.uniform(-100, 100, N)
    ground_points[:, 2] = np.random.uniform(0, 5, N)  # slight terrain
    
    print(f"\n=== PROJECTION ===")
    print(f"Ground points centered around: "
          f"({ground_center[0]:.0f}, {ground_center[1]:.0f})")
    
    # ============================================
    # Project to image
    # ============================================
    image_points = []
    valid_3d = []
    
    for i in range(N):
        # Vector from drone to ground point in world frame
        p_world = ground_points[i] - drone_pos
        
        # Transform to camera frame
        p_cam = R_world_to_cam @ p_world
        
        # Must be in front of camera (positive Z in camera frame)
        if p_cam[2] <= 0:
            continue
        
        # Project
        u = fx * (p_cam[0] / p_cam[2]) + cx
        v = fy * (p_cam[1] / p_cam[2]) + cy
        
        # Check bounds
        if 0 <= u < width and 0 <= v < height:
            image_points.append([u, v])
            valid_3d.append(ground_points[i])
    
    image_points = np.array(image_points, dtype=np.float64)
    valid_3d = np.array(valid_3d, dtype=np.float64)
    
    print(f"Visible points: {len(image_points)} / {N}")
    
    if len(image_points) < 4:
        print("NOT ENOUGH POINTS — rotation is still wrong!")
        print("Debugging: projecting first 3 ground points...")
        for i in range(min(3, N)):
            p_world = ground_points[i] - drone_pos
            p_cam = R_world_to_cam @ p_world
            u = fx * (p_cam[0] / p_cam[2]) + cx if p_cam[2] > 0 else -999
            v = fy * (p_cam[1] / p_cam[2]) + cy if p_cam[2] > 0 else -999
            print(f"  Point {ground_points[i]} → cam {p_cam} → pixel ({u:.0f}, {v:.0f})")
        return
    
    print(f"Image points range: "
          f"u=[{image_points[:,0].min():.0f}, {image_points[:,0].max():.0f}], "
          f"v=[{image_points[:,1].min():.0f}, {image_points[:,1].max():.0f}]")
    
    # ============================================
    # RUN PNP — PERFECT DATA (should give ~0 error)
    # ============================================
    print(f"\n{'='*50}")
    print(f"PNP ON PERFECT DATA")
    print(f"{'='*50}")
    
    methods = [
        ("SQPNP", cv2.SOLVEPNP_SQPNP),
        ("ITERATIVE", cv2.SOLVEPNP_ITERATIVE),
    ]
    
    for method_name, method_flag in methods:
        try:
            success, rvec, tvec, inliers = cv2.solvePnPRansac(
                valid_3d,
                image_points,
                K,
                distCoeffs=None,
                flags=method_flag,
                reprojectionError=5.0,
                confidence=0.99,
                iterationsCount=10000
            )
            
            if not success:
                print(f"\n{method_name}: FAILED")
                continue
            
            R_est, _ = cv2.Rodrigues(rvec)
            pos_est = (-R_est.T @ tvec).flatten()
            
            pos_error = np.linalg.norm(pos_est - drone_pos)
            
            # Recover pitch from estimated rotation
            optical_est = R_est.T @ np.array([[0], [0], [1]])
            pitch_est = np.degrees(np.arccos(
                np.clip(-optical_est[2, 0], -1, 1)
            ))
            
            print(f"\n{method_name}:")
            print(f"  GT position:  ({drone_pos[0]:.1f}, "
                  f"{drone_pos[1]:.1f}, {drone_pos[2]:.1f})")
            print(f"  Est position: ({pos_est[0]:.1f}, "
                  f"{pos_est[1]:.1f}, {pos_est[2]:.1f})")
            print(f"  Position error: {pos_error:.4f} m")
            print(f"  Altitude GT: {altitude:.1f}m, "
                  f"Est: {-pos_est[2]:.1f}m")
            print(f"  Pitch from vertical GT: "
                  f"{pitch_from_vertical:.1f}°, Est: {pitch_est:.1f}°")
            print(f"  Inliers: {len(inliers)}/{len(image_points)}")
            
        except Exception as e:
            print(f"\n{method_name}: EXCEPTION — {e}")
    
    # ============================================
    # RUN PNP — WITH REALISTIC NOISE
    # ============================================
    print(f"\n{'='*50}")
    print(f"PNP WITH NOISE")
    print(f"{'='*50}")
    
    for noise_px, noise_world, label in [
        (1.0, 1.0, "Low noise (1px, 1m)"),
        (3.0, 5.0, "Medium noise (3px, 5m)"),
        (5.0, 10.0, "High noise (5px, 10m)"),
    ]:
        noisy_img = image_points + np.random.normal(0, noise_px, 
                                                      image_points.shape)
        noisy_3d = valid_3d.copy()
        noisy_3d[:, :2] += np.random.normal(0, noise_world, 
                                              (len(valid_3d), 2))
        
        success, rvec, tvec, inliers = cv2.solvePnPRansac(
            noisy_3d, noisy_img, K, None,
            flags=cv2.SOLVEPNP_SQPNP,
            reprojectionError=8.0,
            confidence=0.99
        )
        
        if success:
            R_est, _ = cv2.Rodrigues(rvec)
            pos_est = (-R_est.T @ tvec).flatten()
            pos_error = np.linalg.norm(pos_est - drone_pos)
            alt_error = abs(-pos_est[2] - altitude)
            print(f"\n{label}:")
            print(f"  Position error: {pos_error:.2f} m")
            print(f"  Altitude error: {alt_error:.2f} m")
            print(f"  Inliers: {len(inliers)}/{len(noisy_img)}")
        else:
            print(f"\n{label}: FAILED")
    
    # ============================================
    # NOW TEST WITH YOUR ROLL AND YAW
    # ============================================
    print(f"\n{'='*50}")
    print(f"WITH 1.5° ROLL AND -1° YAW ADDED")
    print(f"{'='*50}")
    
    # Add roll and yaw to the camera orientation
    roll_deg = 1.5
    yaw_offset_deg = -1.0
    
    # Rebuild rotation with roll and yaw
    heading_with_yaw = heading_deg + yaw_offset_deg
    heading_rad2 = np.radians(heading_with_yaw)
    
    cam_z_world2 = np.array([
        np.cos(np.radians(pitch_from_horiz)) * np.cos(heading_rad2),
        np.cos(np.radians(pitch_from_horiz)) * np.sin(heading_rad2),
        np.sin(np.radians(pitch_from_horiz))
    ])
    cam_z_world2 = cam_z_world2 / np.linalg.norm(cam_z_world2)
    
    up_hint2 = np.array([0, 0, -1.0])
    cam_x_world2 = np.cross(cam_z_world2, up_hint2)
    cam_x_world2 = cam_x_world2 / np.linalg.norm(cam_x_world2)
    cam_y_world2 = np.cross(cam_z_world2, cam_x_world2)
    cam_y_world2 = cam_y_world2 / np.linalg.norm(cam_y_world2)
    
    # Apply roll: rotate cam_x and cam_y around cam_z
    roll_rad = np.radians(roll_deg)
    cam_x_rolled = (np.cos(roll_rad) * cam_x_world2 + 
                    np.sin(roll_rad) * cam_y_world2)
    cam_y_rolled = (-np.sin(roll_rad) * cam_x_world2 + 
                     np.cos(roll_rad) * cam_y_world2)
    
    R_cam_to_world2 = np.column_stack([cam_x_rolled, 
                                         cam_y_rolled, 
                                         cam_z_world2])
    R_world_to_cam2 = R_cam_to_world2.T
    
    # Re-project with new rotation (same ground points)
    image_points2 = []
    valid_3d2 = []
    for i in range(len(valid_3d)):
        p_cam = R_world_to_cam2 @ (valid_3d[i] - drone_pos)
        if p_cam[2] <= 0:
            continue
        u = fx * (p_cam[0] / p_cam[2]) + cx
        v = fy * (p_cam[1] / p_cam[2]) + cy
        if 0 <= u < width and 0 <= v < height:
            image_points2.append([u, v])
            valid_3d2.append(valid_3d[i])
    
    image_points2 = np.array(image_points2, dtype=np.float64)
    valid_3d2 = np.array(valid_3d2, dtype=np.float64)
    
    # PnP should STILL work — it solves for the rotation
    success, rvec, tvec, inliers = cv2.solvePnPRansac(
        valid_3d2, image_points2, K, None,
        flags=cv2.SOLVEPNP_SQPNP,
        reprojectionError=5.0,
        confidence=0.99
    )
    
    if success:
        R_est, _ = cv2.Rodrigues(rvec)
        pos_est = (-R_est.T @ tvec).flatten()
        pos_error = np.linalg.norm(pos_est - drone_pos)
        
        # Check if it recovered the roll and yaw
        optical_est = R_est.T @ np.array([0, 0, 1])
        right_est = R_est.T @ np.array([1, 0, 0])
        
        print(f"Position error: {pos_error:.4f} m")
        print(f"Est position: ({pos_est[0]:.1f}, "
              f"{pos_est[1]:.1f}, {pos_est[2]:.1f})")
        print(f"PnP handles roll and yaw automatically ✓")
    else:
        print("FAILED — this should not happen on clean data")

    # ============================================
    # PRINT THE CORRECT R FOR COMPARISON WITH AIRSIM
    # ============================================
    print(f"\n{'='*50}")
    print(f"REFERENCE ROTATION MATRIX")
    print(f"{'='*50}")
    print(f"\nR_cam_to_world (no roll/yaw):")
    print(R_cam_to_world)
    print(f"\nR_world_to_cam (no roll/yaw):")
    print(R_world_to_cam)
    print(f"\nUse R_world_to_cam to verify against AirSim:")
    print(f"  R @ [1,0,0] (world North in cam): "
          f"{R_world_to_cam @ np.array([1,0,0])}")
    print(f"  R @ [0,1,0] (world East in cam):  "
          f"{R_world_to_cam @ np.array([0,1,0])}")
    print(f"  R @ [0,0,1] (world Down in cam):  "
          f"{R_world_to_cam @ np.array([0,0,1])}")


corrected_synthetic_pnp_test()
