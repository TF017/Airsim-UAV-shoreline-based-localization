import numpy as np
import pickle
import os

SAFETY_FACTOR=1.5

def build_covariance_model(all_diagnostics, all_gt_positions):
    """
    Run this ONCE on your full dataset.
    Fits a model: quality signals → expected position error.
    
    This gives you the empirical basis for your EKF covariance.
    """
    
    # Collect features and targets
    features = []
    errors_north = []
    errors_east = []
    
    for diag, gt in zip(all_diagnostics, all_gt_positions):
        if diag is None:
            continue
        if diag['baro_altitude']<100 and diag['baro_altitude']>160:
            continue
        
        est = diag['position']
        
        features.append([
            diag['n_inliers'],
            diag['inlier_ratio'],
            diag['mean_reproj_error'],
            diag['altitude_error'],
            diag['inlier_spread'],
            diag['baro_altitude'],  # altitude affects accuracy at 80°
            diag['altitude_ratio'],
            diag['inlier_spread'],
        ])
        
        errors_north.append(est[0] - gt[0])
        errors_east.append(est[1] - gt[1])
    
    features = np.array(features)
    errors_north = np.array(errors_north)
    errors_east = np.array(errors_east)
    abs_errors = np.sqrt(errors_north**2 + errors_east**2)
    
    # ==========================================
    # Analysis 1: Error vs each quality signal
    # ==========================================
    signal_names = [
        'n_inliers', 'inlier_ratio', 'mean_reproj', 
        'altitude_error', 'spread', 'altitude', 'altitude_ratio', 'inlier_spread'
    ]
    
    print("=== CORRELATION WITH HORIZONTAL ERROR ===")
    for i, name in enumerate(signal_names):
        corr = np.corrcoef(features[:, i], abs_errors)[0, 1]
        print(f"  {name:20s}: r = {corr:+.3f}")
    
    # ==========================================
    # Analysis 2: Binned statistics
    # ==========================================
    print("\n=== ERROR BY INLIER COUNT ===")
    for low, high in [(6, 20), (20, 35), (35, 50), (50, 75), (75, 200),(201, 1000)]:
        mask = (features[:, 0] >= low) & (features[:, 0] < high)
        if np.sum(mask) < 3:
            continue
        n_rmse = np.sqrt(np.mean(errors_north[mask]**2))
        e_rmse = np.sqrt(np.mean(errors_east[mask]**2))
        count = np.sum(mask)
        pct = 100 * count / len(mask)
        print(f"  [{low:3d}, {high:3d}) inliers: "
              f"N_RMSE={n_rmse:6.1f}m, E_RMSE={e_rmse:6.1f}m "
              f"({count} frames, {pct:.0f}%)")
    
    print("\n=== ERROR BY REPROJECTION ERROR ===")
    for low, high in [(0, 2), (2, 4), (4, 6), (6, 10), (10, 50),(51, 1000)]:
        mask = (features[:, 2] >= low) & (features[:, 2] < high)
        if np.sum(mask) < 3:
            continue
        n_rmse = np.sqrt(np.mean(errors_north[mask]**2))
        e_rmse = np.sqrt(np.mean(errors_east[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:4.0f}, {high:4.0f}) px reproj: "
              f"N_RMSE={n_rmse:6.1f}m, E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    print("\n=== ERROR BY ALTITUDE ERROR ===")
    for low, high in [(0, 5), (5, 15), (15, 30), (30, 60), (60, 500),(500, 1000)]:
        mask = (features[:, 3] >= low) & (features[:, 3] < high)
        if np.sum(mask) < 3:
            continue
        n_rmse = np.sqrt(np.mean(errors_north[mask]**2))
        e_rmse = np.sqrt(np.mean(errors_east[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:4.0f}, {high:4.0f})m alt err: "
              f"N_RMSE={n_rmse:6.1f}m, E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    print("\n=== ERROR BY DRONE ALTITUDE ===")
    for low, high in [(20, 50), (50, 100), (100, 175), (175, 250), (250, 350)]:
        mask = (features[:, 5] >= low) & (features[:, 5] < high)
        if np.sum(mask) < 3:
            continue
        n_rmse = np.sqrt(np.mean(errors_north[mask]**2))
        e_rmse = np.sqrt(np.mean(errors_east[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:3.0f}, {high:3.0f})m altitude: "
              f"N_RMSE={n_rmse:6.1f}m, E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    print("\n=== ERROR BY ALTITUDE RATIO===")
    for low, high in [(0.0, 0.02), (.02, 0.05), (0.05, 0.2), (.2, .4), (.4, 1)]:
        mask = (features[:, 6] >= low) & (features[:, 6] < high)
        if np.sum(mask) < 3:
            continue
        n_rmse = np.sqrt(np.mean(errors_north[mask]**2))
        e_rmse = np.sqrt(np.mean(errors_east[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:0.2f}, {high:0.2f})% altitude: "
              f"N_RMSE={n_rmse:6.1f}m, E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
        
    
    print("\n=== ERROR BY INLIER SPREAD===")
    for low, high in [(0.0, 0.02), (.02, 0.05), (0.05, 0.2), (.2, .4), (.4, 1)]:
        mask = (features[:, 7] >= low) & (features[:, 7] < high)
        if np.sum(mask) < 3:
            continue
        n_rmse = np.sqrt(np.mean(errors_north[mask]**2))
        e_rmse = np.sqrt(np.mean(errors_east[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:0.2f}, {high:0.2f})% altitude: "
              f"N_RMSE={n_rmse:6.1f}m, E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    return features, errors_north, errors_east

def cross_tabulate(all_diagnostics, all_gt_positions):
    """
    The key question: among GOOD fixes (50+ inliers), 
    does drone altitude still affect accuracy?
    
    If YES → add altitude as a covariance factor
    If NO  → inlier count alone is sufficient
    """
    
    # Filter to 50+ inliers only
    signal_names=['error_n', 'error_e', 'abs_error', 'altitude',  'n_inliers', 'alt_error', 'reproj', 'alt_error_per', 'inlier_spread']
    good_data = []
    for diag, gt in zip(all_diagnostics, all_gt_positions):
        if diag is None:
            continue
        if diag['n_inliers'] < 50:
            continue

        est = diag['position']
        error_n = est[0] - gt[0]
        error_e = est[1] - gt[1]
        
        good_data.append([ 
            error_n,
            error_e,
            np.sqrt(error_n**2 + error_e**2),
            diag['baro_altitude'],
            diag['n_inliers'],
            diag['altitude_error'],
            diag['mean_reproj_error'],
            diag['altitude_ratio'],
            diag['inlier_spread']
        ])
    
    df = np.array(good_data)
    
    print("=== AMONG 50+ INLIER FRAMES ONLY ===\n")
    
    en=df[:, 0]
    ee=df[:, 1]
    abs_error=df[:, 2]

    print("=== CORRELATION WITH HORIZONTAL ERROR ===")
    for i, name in enumerate(signal_names):
        if i<3: continue
        corr = np.corrcoef(df[:, i], abs_error)[0, 1]
        print(f"  {name:20s}: r = {corr:+.3f}")

    # By altitude
    print("Altitude effect (50+ inliers):")
    for low, high in [(20, 75), (75, 150), (150, 250), (250, 350)]:
        mask = (df[:, 3] >= low) & (df[:, 3] < high)
        if np.sum(mask) < 5:
            continue
        n_rmse = np.sqrt(np.mean(en[mask]**2))
        e_rmse = np.sqrt(np.mean(ee[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:3d}, {high:3d})m: "
              f"N_RMSE={n_rmse:6.1f}m, "
              f"E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    # By inlier count (finer bins within 50+)
    print("\nInlier effect (finer bins):")
    for low, high in [(50, 65), (65, 85), (85, 120), 
                       (120, 175), (175, 300), (300, 1000)]:
        mask = (df[:, 4] >= low) & (df[:, 4] < high)
        if np.sum(mask) < 5:
            continue
        n_rmse = np.sqrt(np.mean(en[mask]**2))
        e_rmse = np.sqrt(np.mean(ee[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:3d}, {high:3d}): "
              f"N_RMSE={n_rmse:6.1f}m, "
              f"E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    # By altitude error (among good fixes)
    print("\nAltitude error effect (50+ inliers):")
    for low, high in [(0, 3), (3, 8), (8, 15), (15, 40), (40, 200)]:
        mask = (df[:, 5] >= low) & (df[:, 5] < high)
        if np.sum(mask) < 5:
            continue
        n_rmse = np.sqrt(np.mean(en[mask]**2))
        e_rmse = np.sqrt(np.mean(ee[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:3d}, {high:3d})m: "
              f"N_RMSE={n_rmse:6.1f}m, "
              f"E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
        
    
    print("\nAltitude error percentage effect (50+ inliers):")
    for low, high in [(0.0, 0.03), (0.03, 0.08), (0.08, 0.15), (0.15, 0.40), (0.40, 1.0)]:
        mask = (df[:, 7] >= low) & (df[:, 7] < high)
        if np.sum(mask) < 5:
            continue
        n_rmse = np.sqrt(np.mean(en[mask]**2))
        e_rmse = np.sqrt(np.mean(ee[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:.2f}, {high:.2f}): "
              f"N_RMSE={n_rmse:6.1f}m, "
              f"E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    print("\nAltitude error percentage & inliners effect (50+ inliers):")
    for low, high in [(0.0, 0.03), (0.03, 0.08), (0.08, 0.15), (0.15, 0.40), (0.40, 1.0)]:
        for _low, _high in [(50, 65), (65, 85), (85, 120), (120, 175), (175, 300), (300, 1000)]:
            mask = (df[:, 7] >= low) & (df[:, 7] < high) & (df[:, 4] >= _low) & (df[:, 4] < _high)
            if np.sum(mask) < 5:
                continue
            n_rmse = np.sqrt(np.mean(en[mask]**2))
            e_rmse = np.sqrt(np.mean(ee[mask]**2))
            count = np.sum(mask)
            print(f"  [{low:.2f}, {high:.2f}): "
                f"N_RMSE={n_rmse:6.1f}m, "
                f"E_RMSE={e_rmse:6.1f}m "
                f"({count} frames)")
    
    print("\nMEAN REPROJ error effect (50+ inliers):")
    for low, high in [(0.0, 0.5), (0.5, 1), (1, 3), (3, 4), (4, 5), (5, 6), (7, 8)]:
        mask = (df[:, 6] >= low) & (df[:, 6] < high)
        if np.sum(mask) < 5:
            continue
        n_rmse = np.sqrt(np.mean(en[mask]**2))
        e_rmse = np.sqrt(np.mean(ee[mask]**2))
        count = np.sum(mask)
        print(f"  [{low:.2f}, {high:.2f}): "
              f"N_RMSE={n_rmse:6.1f}m, "
              f"E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    
    print("\nInliers Spread (50+ inliers):")
    for low, high in [(0.0, 0.05), (0.05, 0.1),(0.1, 0.12), (0.12, 0.15), (0.15, 0.18), (0.18, 0.2), (0.2, 0.25), (0.25, 0.3), (0.3, 0.35), (0.35, 0.45), (0.45, 1.0)]:
        mask = (df[:, 8] >= low) & (df[:, 8] < high)
        if np.sum(mask) < 5:
            continue
        _en=en[mask]
        _ee=ee[mask]
        n_rmse = np.sqrt(np.mean(_en**2))
        e_rmse = np.sqrt(np.mean(_ee**2))
        count = np.sum(mask)
        print(f"  [{low:.2f}, {high:.2f}): "
              f"N_RMSE={n_rmse:6.1f}m, "
              f"E_RMSE={e_rmse:6.1f}m "
              f"({count} frames)")
    
    print("\nInliers spread & # inliners effect (50+ inliers):")
    for low, high in [(0.0, 0.1), (0.1, 0.15), (0.15, 0.2), (0.2, 0.25), (0.25, 1.0)]:
        for _low, _high in [(50, 65), (65, 85), (85, 120), (120, 175), (175, 300), (300, 1000)]:
            mask = (df[:, 8] >= low) & (df[:, 8] < high) & (df[:, 4] >= _low) & (df[:, 4] < _high)
            if np.sum(mask) < 3:
                continue
            n_rmse = np.sqrt(np.mean(en[mask]**2))
            e_rmse = np.sqrt(np.mean(ee[mask]**2))
            abs_rmse=np.sqrt(np.mean(abs_error[mask]**2))
            count = np.sum(mask)
            print(f"  [{low:.2f}, {high:.2f}) & "
                  f"[{_low:.2f}, {_high:.2f}): "
                f"N_RMSE={n_rmse:6.1f}m, "
                f"E_RMSE={e_rmse:6.1f}m "
                f" RMSE={abs_rmse:6.1f}m "
                f"({count} frames)")
    

PATH=r'Pickle_data'
files=[file for file in os.listdir(PATH) if file.endswith('.pkl')]
all_info=[]
for file in files:
    x=open(os.path.join(PATH, file), 'rb')
    info=pickle.load(x)
    all_info= all_info + info  #arrays.append([np.load(), file])
    x.close()

all_diag=[]
all_gt=[]
for diag, gt, altitude, place in all_info: 
    all_diag.append(diag)
    all_gt.append(gt)

build_covariance_model(all_diag, all_gt)
#cross_tabulate(all_diag, all_gt)
exit()


class CrossViewCovarianceModel:
    """
    Empirically calibrated from 1092 frames across
    2 locations and 5 altitude levels.
    
    Primary predictor: number of PnP inliers
    Secondary predictor: altitude error (when available)
    """
    
    def __init__(self):
        # ==========================================
        # From your empirical data:
        # ==========================================
        #
        # Inlier bin    N_RMSE   E_RMSE   Frames
        # [50, 75)      9.9m     11.7m    43
        # [75, 200)     6.0m     6.7m     237
        # [200+)        2.6m     2.8m     81
        # [35, 50)      100.8m   98.6m    26  (marginal)
        #
        # Minimum reject threshold: 35 inliers
        
        self.min_inliers = 35  # hard reject below this
        
        # Lookup table: (min_inliers, max_inliers) → (sigma_n, sigma_e)
        # Sigma values set to empirical RMSE × safety factor
        # Safety factor of 1.2-1.5 prevents overconfidence
        self.safety_factor = SAFETY_FACTOR#1.10

        self.loockup_table=[
            [0.0, 1.0, 35, 50, 100.8,  98.6, 141.0, 55.0],
            [0.0, 0.1, 50.0, 65.0, 7.6, 26.7, 27.7, 4.0],
            [0.1, 0.15, 50.0, 65.0, 13.0, 10.8, 16.9, 14.0],
            [0.1, 0.15, 65.0, 85.0, 9.3, 9.1, 13.0, 25.0],
            [0.1, 0.15, 85.0, 120.0, 8.5, 9.9, 13.1, 30.0], 
            [0.15, 1.0, 50.0, 65.0, 4.6, 6.1, 7.6, 3.0], #cover all above 0.2
            [0.15, 0.2, 65.0, 85.0, 6.3, 6.6, 9.1, 17.0], 
            [0.15, 0.2, 85.0, 120.0, 6.8, 7.3, 10.0, 50.0], 
            [0.15, 0.2, 120.0, 175.0, 5.0, 5.8, 7.7, 52.0], 
            [0.15, 0.2, 175.0, 300.0, 3.3, 3.1, 4.5, 23.0], 
            [0.2, 1.0, 65.0, 85.0, 7.1, 3.1, 7.8, 4.0], #cover all above 0.25
            [0.2, 0.25, 85.0, 120.0, 4.1, 6.4, 7.6, 9.0], 
            [0.2, 0.25, 120.0, 175.0, 4.1, 5.0, 6.5, 10.0], 
            [0.2, 0.25, 175.0, 300.0, 2.5, 3.0, 3.9, 60.0], 
            [0.25, 1.0, 85.0, 120.0, 1.4, 7.2, 7.3, 3.0], 
            [0.25, 1.0, 120.0, 175.0, 3.7, 4.5, 5.8, 10.0], 
            [0.25, 1.0, 175.0, 300.0, 2.6, 2.6, 3.7, 42.0],
        ]
    
    def compute_R(self, diagnostics):
        """
        Compute 2x2 measurement covariance for EKF.
        
        Returns None if measurement should be rejected.
        """
        
        n_inliers = diagnostics['n_inliers']
        inliers_spread= diagnostics['inlier_spread']
        # ==========================================
        # Hard rejection
        # ==========================================
        if n_inliers < self.min_inliers:
            return None  # reject
        
        # ==========================================
        # Base covariance from inlier count
        # ==========================================
        sigma_n = None
        sigma_e = None
        
        for min_spread, max_spread, min_inl, max_inl, sn, se, sa, _ in self.loockup_table:
            if min_inl <= n_inliers < max_inl and min_spread <= inliers_spread< max_spread:
                sigma_n = sn * self.safety_factor
                sigma_e = se * self.safety_factor
                break
            
        
        if sigma_n is None:
            print (f'WARNING: {n_inliers} and {inliers_spread:.2f} are not categororized')
            return None
        
        # ==========================================
        # Secondary adjustment: altitude error
        # (your second strongest predictor, r=0.652)
        # ==========================================
        # alt_err = diagnostics.get('altitude_error', None)
        # if alt_err is not None:
        #     # From your data, altitude ratio > 0.20 → error doubles
        #     alt_ratio = diagnostics.get('altitude_ratio', 0)
            
        #     if alt_ratio > 0.40:
        #         alt_factor = 3.0
        #     elif alt_ratio > 0.20:
        #         alt_factor = 2.0
        #     elif alt_ratio > 0.05:
        #         alt_factor = 1.3
        #     else:
        #         alt_factor = 1.0
            
        #     sigma_n *= alt_factor
        #     sigma_e *= alt_factor
        
        # ==========================================
        # Build covariance matrix
        # ==========================================
        R = np.diag([sigma_n**2, sigma_e**2])
        
        return R
    
    def process_measurement(self, diagnostics):
        """
        Full processing: reject or accept with covariance.
        Returns measurement dict for EKF or None.
        """
        
        R = self.compute_R(diagnostics)
        
        if R is None:
            return None
        
        position_ne = diagnostics['position'][0:2]
        
        return {
            'position_ne': position_ne,
            'covariance_ne': R,
            'n_inliers': diagnostics['n_inliers'],
            'sigma_n': np.sqrt(R[0, 0]),
            'sigma_e': np.sqrt(R[1, 1]),
            'quality': str(diagnostics['n_inliers']/10)
        }
    

def validate_final_model(all_diagnostics, all_gt_positions):
    """Quick validation of the calibrated model."""
    
    model = CrossViewCovarianceModel()
    
    normalized_n = []
    normalized_e = []
    quality_counts = {'rejected': 0}
    
    for diag, gt in zip(all_diagnostics, all_gt_positions):
        if diag is None:
            quality_counts['rejected'] = quality_counts.get('rejected', 0) + 1
            continue
        
        meas = model.process_measurement(diag)
        
        if meas is None:
            quality_counts['rejected'] = quality_counts.get('rejected', 0) + 1
            continue
        
        label = meas['quality']
        quality_counts[label] = quality_counts.get(label, 0) + 1
        
        error_n = diag['position'][0] - gt[0]
        error_e = diag['position'][1] - gt[1]
        
        normalized_n.append(error_n / meas['sigma_n'])
        normalized_e.append(error_e / meas['sigma_e'])
    
    normalized_n = np.array(normalized_n)
    normalized_e = np.array(normalized_e)
    
    # ==========================================
    # Print results
    # ==========================================
    
    #print("=== MEASUREMENT BREAKDOWN ===")
    #total = sum(quality_counts.values())
    #for label, count in sorted(quality_counts.items()):
        #print(f"  {label:20s}: {count:4d} ({100*count/total:.1f}%)")
    
    
    print(f"\n=== NORMALIZED ERROR STATISTICS ===")
    print(f"(Should look like standard normal: mean≈0, std≈1)\n")
    
    for name, ne in [("North", normalized_n), ("East", normalized_e)]:
        w1 = 100 * np.mean(np.abs(ne) < 1.0)
        w2 = 100 * np.mean(np.abs(ne) < 2.0)
        w3 = 100 * np.mean(np.abs(ne) < 3.0)
        
        print(f"  {name}:")
        print(f"    Mean:       {np.mean(ne):+.3f}  (expect ≈ 0)")
        print(f"    Std:         {np.std(ne):.3f}  (expect ≈ 1)")
        print(f"    Within 1σ:  {w1:.1f}%  (expect 68%)")
        print(f"    Within 2σ:  {w2:.1f}%  (expect 95%)")
        print(f"    Within 3σ:  {w3:.1f}%  (expect 99%)")
    
    # ==========================================
    # Adjustment guidance
    # ==========================================
    overall_std = np.std(np.concatenate([normalized_n, normalized_e]))
    
    print(f"\n=== CALIBRATION GUIDANCE ===")
    print(f"  Overall normalized std: {overall_std:.3f}")
    
    if overall_std > 1.2:
        new_safety = model.safety_factor * overall_std
        print(f"  ⚠️  OVERCONFIDENT — increase safety_factor "
              f"from {model.safety_factor:.1f} to {new_safety:.2f}")
    elif overall_std < 0.6:
        new_safety = model.safety_factor * overall_std
        print(f"  ⚠️  UNDERCONFIDENT — decrease safety_factor "
              f"from {model.safety_factor:.1f} to {new_safety:.2f}")
    else:
        print(f"  ✅  Model is well calibrated (std in [0.6, 1.2])")
    
    return quality_counts, normalized_n, normalized_e

validate_final_model(all_diag, all_gt)
