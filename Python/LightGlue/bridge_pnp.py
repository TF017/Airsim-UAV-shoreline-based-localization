def bridge_to_real_pipeline(
    matched_drone_pixels,      # Nx2 from SP in ORIGINAL image
    matched_satellite_pixels,  # Nx2 from SP in satellite tile
    ortho_origin_ned,          # (x_north, y_east) of tile corner
    meters_per_pixel,          # ortho resolution
    heightmap,                 # function: (x,y) → z in NED
    K,                         # camera intrinsics
    img_path                   # Image path to acesss ground truth
):
    """
    Bridge from your existing matching to PnP.
    """
    
    N = len(matched_drone_pixels)
    
    # Convert satellite pixels to world 3D points
    world_points = np.zeros((N, 3))
    
    for i in range(N):
        su, sv = matched_satellite_pixels[i]
        
        # ★★★ THIS MAPPING IS CRITICAL ★★★
        # Which satellite pixel axis is North? Which is East?
        # 
        # Most common for north-up imagery:
        #   pixel u (horizontal, rightward) → East
        #   pixel v (vertical, downward)    → South (!) 
        #
        # So:
        wx = ortho_origin_ned[0] - sv * meters_per_pixel  # North
        wy = ortho_origin_ned[1] + su * meters_per_pixel  # East
        
        # Or if your ortho origin is top-left and 
        # increases South and East:
        # wx = ortho_origin_ned[0] - sv * meters_per_pixel
        # wy = ortho_origin_ned[1] + su * meters_per_pixel
        
        #wz = heightmap[wx, wy]  # terrain height in NED Z
        wz = map_coordinates(heightmap, [[sv], [su]], order=1)[0]
        #wz = heightmap[int(round(sv)), int(round(su))]  # terrain height in NED Z
        world_points[i] = [wx, wy, wz]
    
    # ============================================
    # SANITY CHECK before running PnP
    # ============================================
    print(f"World points range:")
    print(f"  X (North): [{world_points[:,0].min():.1f}, "
          f"{world_points[:,0].max():.1f}]")
    print(f"  Y (East):  [{world_points[:,1].min():.1f}, "
          f"{world_points[:,1].max():.1f}]")
    print(f"  Z (Down):  [{world_points[:,2].min():.1f}, "
          f"{world_points[:,2].max():.1f}]")
    
    gt = get_airsim_ground_truth(img_path)  # your function
    expected_distance = (-gt[2]) * np.tan(np.radians(80))
    centroid = np.mean(world_points[:, :2], axis=0)
    actual_distance = np.linalg.norm(centroid - gt[:2])
    
    print(f"\nDrone GT position: ({gt[0]:.1f}, {gt[1]:.1f})")
    print(f"World points centroid: ({centroid[0]:.1f}, {centroid[1]:.1f})")
    print(f"Distance drone → centroid: {actual_distance:.1f}m")
    print(f"Expected at 80° oblique: {expected_distance:.1f}m")
    
    if actual_distance < 50:
        print("⚠️ Points too close — satellite→world conversion "
              "may be wrong")
    elif actual_distance > 3 * expected_distance:
        print("⚠️ Points too far — scaling or axis swap error")
    else:
        print("✅ Distance looks plausible")
    
    # ============================================
    # Run PnP
    # ============================================
    image_points = matched_drone_pixels.astype(np.float64)
    object_points = world_points.astype(np.float64)
    
    success, rvec, tvec, inliers = cv2.solvePnPRansac(
        object_points,
        image_points,
        K,
        distCoeffs=None,
        flags=cv2.SOLVEPNP_SQPNP,
        reprojectionError=8.0,
        confidence=0.99,
        iterationsCount=10000
    )
    
    if not success or len(inliers)<30:
        print("PnP FAILED")
        return None
    
    
    R_est, _ = cv2.Rodrigues(rvec)
    pos_est = (-R_est.T @ tvec).flatten()
    
    print(f"\n=== PnP RESULT ===")
    print(f"Estimated position: ({pos_est[0]:.1f}, "
          f"{pos_est[1]:.1f}, {pos_est[2]:.1f})")
    print(f"GT position:        ({gt[0]:.1f}, "
          f"{gt[1]:.1f}, {gt[2]:.1f})")
    print(f"Position error: "
          f"{np.linalg.norm(pos_est - gt):.2f}m")
    print(f"Altitude est: {-pos_est[2]:.1f}m, "
          f"GT: {-gt[2]:.1f}m")
    print(f"Inliers: {len(inliers)}/{len(image_points)}")
    
    # Verify recovered orientation
    optical_axis = R_est.T @ np.array([0, 0, 1])
    pitch_recovered = np.degrees(np.arccos(
        np.clip(-optical_axis[2], -1, 1)
    ))
    print(f"Recovered pitch from vertical: {pitch_recovered:.1f}° "
          f"(expected ~80°)")
    
    error_u=[]
    error_v=[]
    img_pts_proj, _ = cv2.projectPoints(object_points, rvec, tvec, K, distCoeffs=None)
    for i in range(len(img_pts_proj)):
        u_proj,v_proj=img_pts_proj[i][0]
        u,v=image_points[i]
        error_u.append(u-u_proj)
        error_v.append(v-v_proj)
    error_u=np.array(error_u)
    error_v=np.array(error_v)
    print(f'U RMSE: {np.sqrt(np.mean(error_u**2)):2f}, V RMSE: {np.sqrt(np.mean(error_v**2)):2f}')
    
    success, rvec, tvec=cv2.solvePnP(
    object_points[inliers],
    image_points[inliers],
    K,
    None,
    rvec,
    tvec,
    useExtrinsicGuess=True
    )
    if not success:
        print("PnP Extrinsic Guess FAILED")
    
    R_est, _ = cv2.Rodrigues(rvec)
    pos_est = (-R_est.T @ tvec).flatten()
    
    print(f"\n=== PnP Extrinsic RESULT ===")
    print(f"Estimated position: ({pos_est[0]:.1f}, "
          f"{pos_est[1]:.1f}, {pos_est[2]:.1f})")
    print(f"GT position:        ({gt[0]:.1f}, "
          f"{gt[1]:.1f}, {gt[2]:.1f})")
    print(f"Position error: "
          f"{np.linalg.norm(pos_est - gt):.2f}m")
    print(f"Altitude est: {-pos_est[2]:.1f}m, "
          f"GT: {-gt[2]:.1f}m")

    return pos_est