# -*- coding: utf-8 -*-
import torch
import cv2
import numpy as np
from numpy import linalg
import rasterio
from rasterio.windows import Window
from rasterio import Affine
import glob
import os
import matplotlib.pyplot as plt
from lightglue import LightGlue, SuperPoint, viz2d
from lightglue.utils import rbd
from torchvision import transforms
from pyproj import Transformer
import math
import airsim_typesANDutils as airsim_utils
from scipy.ndimage import map_coordinates
from coordinate_system import *
import pickle
import winsound
from plyer import notification
import sys
import airsim_data_managementv2 as airsim_data_management
duration = 5000  # milliseconds
freq = 440  # Hz
VERSION=__file__.split('lightgluev')[-1].replace('.py', '')
print(f'Running Version {VERSION} of Cross View Module')

library=airsim_data_management.library
#rows=airsim_data_management.get_row(None, None, None, None, None, None).to_numpy()
#Aveiro\NED\300\-10\Inland is with another path (same as ESD\300\-10\Inland) to a more fare comparison
rows=airsim_data_management.get_row(place='Zambujeira',
                                    system='ESD',
                                    altitude=[300, 300],
                                    pitch=[-25, -25],
                                    offshore=None,
                                    masked=None
                                    )
rows=airsim_data_management.get_row()
#rows_to_run=[0,1,2,5,6,24,25,26,28,31,55,56,57,70,71,72,73,74,75,76,77,78]
rows_to_run=list(range(79, 83))
#rows_to_run=[26]
print(rows)
rows=rows.to_numpy()
ANGLE=False #if true seacrh for best yaw angle to rotate ortophoto otherwise picks groudth truth yaw
FULL_SEARCH=False #if true seacrs full ortophoto


DEBUG=False
VISUAL=False
FOV=90 #Field of View of Airsim Camera in Degrees
MINIMUM_INLIERS_FOR_PNP=6

# Initialize this at the top of your file with your other models
# ==========================================
# 1. Configuration & Setup
# ==========================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

camera_to_body_translation_in_body_frame=np.array([0.46, .0, 0])
#body frame FLU: Front, left, Up

# Initialize Deep Learning Models
extractor = SuperPoint(max_num_keypoints=2048).eval().to(DEVICE)
matcher = LightGlue(features='superpoint').eval().to(DEVICE)

class CrossView():
    def __init__(self, row, angle_search=ANGLE, full_search=FULL_SEARCH, search_area=2000):
        self.row=row
        self.place, self.ned_flag, self.altitude, self.camera_orientation, self.offshore, self.path, place_geo, self.orto_path=airsim_data_management.get_row_info(row)
        self.pitch=int(self.camera_orientation[1])
        self.path_images=os.path.join(self.path, 'images')
        self.search_area=search_area
        self.full_search=full_search
        self.angle_search=angle_search
        self.mode={'Full Search': self.full_search,
                  'Angle Search': self.angle_search}
        self.save_info=[]
        self.parse_airsim_rec_structured(os.path.join(self.path, "airsim_rec.txt"))
        self.airsim2ecef=None
        if self.ned_flag:
            self.airsim2ecef = AIRSIM2ECEF(place_geo)
        else:
            self.airsim2ecef = AIRSIM2ECEF_ESD(place_geo)
        self.prior_x, self.prior_y, _ = geo2tm06(place_geo)
        print(f'Place: {self.place}\nNED: {self.ned_flag}')
        print(f'Altitude: {self.altitude}\nCamera Orientation (Yaw-Pitch-Roll): {self.camera_orientation}')
        print(f'Offshore distance: {self.offshore}')
        print(f'STARTING COORDINATES IN TM06: {self.prior_x:.2f}, {self.prior_y:.2f}')
        self.savefile=f'Pickle_data\\save_info_{self.place}_{self.ned_flag}_{self.altitude}_{self.pitch}_{self.offshore}_v{VERSION}_final.pkl'
        self.exist=os.path.exists(self.savefile)
        if self.exist: print('The result files already exist')

    def crop_orthophoto(self, raster, center_x, center_y, crop_size_px=2000):    
        """
        Crops a manageable patch from the massive GeoTIFF around an estimated GPS location.
        Returns the image patch and the new geographic transform for that specific patch.
        """
        # Convert GPS to raster pixel coordinates
        py, px = raster.index(center_x, center_y)

        # Define the window to crop
        min_x = int(px - crop_size_px // 2)
        min_y = int(py - crop_size_px // 2)

        window = Window(min_x, min_y, crop_size_px, crop_size_px)

        # Read the data and get the new transform for the cropped window
        # 1. Read the window, but force it to stay the exact requested size
        # by padding out-of-bounds areas with 0 (black).
        patch = raster.read(
            window=window,
            boundless=True,
            fill_value=0
        )

        # 2. Calculate the transform normally.
        # Because the array wasn't truncated, the center of the image
        # is mathematically perfectly aligned with the transform.
        patch_transform = raster.window_transform(window)

        # Convert from rasterio format (Channels, H, W) to OpenCV format (H, W, Channels)
        patch = np.moveaxis(patch, 0, -1)
        heightmap=[]
        # If the GeoTIFF has 4 channels (RGBA), drop the alpha channel
        #print("Patch Shape", patch.shape)
        if patch.shape[2] == 6: #Heightmap+RGBA+Mask
            heightmap=patch[:, :, 0]
            heightmap=heightmap.astype(np.float32) #Im unsure if float32 is not overkill for altitude
            patch = patch[:, :, 1:4]
        else:
            raise BaseException('ORTHOPHOTO MUST BE HEIGHTMAP+RGBA+MASK Format')
        
        patch=patch.astype(np.uint8)

        return patch, heightmap, patch_transform

    def image_to_tensor(self, img):
        """Converts a numpy image to the tensor format expected by LightGlue"""
        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
        tensor = transforms.ToTensor()(img_gray).unsqueeze(0).to(DEVICE)
        return tensor

    def parse_airsim_rec_structured(self, file_path):
        self.img_dicionary={}
        with open(file_path, 'r') as f:
            lines = f.readlines()

        header = lines[0].strip().split()

        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) != len(header):
                continue

            row = dict(zip(header, parts))
            image_name = row.get("ImageFile")

            if image_name:
                # Convert numeric fields
                for k, v in row.items():
                    if k != "ImageFile":
                        try:
                            row[k] = float(v)
                        except ValueError:
                            pass

                self.img_dicionary[image_name] = row

    def get_airsim_ground_truth(self, img_path):
        return [self.img_dicionary[os.path.basename(img_path)]['POS_X'],
                self.img_dicionary[os.path.basename(img_path)]['POS_Y'],
                self.img_dicionary[os.path.basename(img_path)]['POS_Z']]

    def get_airsim_ground_truth_all(self, img_path):
            gt=self.img_dicionary[os.path.basename(img_path)]
            return [[gt['POS_X'], gt['POS_Y'], gt['POS_Z']],airsim_utils.Quaternionr(gt['Q_X'], gt['Q_Y'], gt['Q_Z'], gt['Q_W'])]

    def get_world_points_enu(self,
            matched_satellite_pixels, #Ortophoto pixels that have superpoints matched
            heightmap, #Heightmap with same width and height as the ortophoto; They must be aligned
            patch_transform, #Ortophoto image coordinates to tm06 coordinate transformation
            reference_point # TM06 coordinate for the reference frame. it is assumed to be the ortophoto principal point but can be any other point
        ):
        N = len(matched_satellite_pixels)
        world_points = np.zeros((N, 3))
        ecef2enu=ECEF2ENU(tm062geo(reference_point))
        for i in range(N):
            su, sv = matched_satellite_pixels[i]
            x_tm06_estimated, y_tm06_estimated = patch_transform * (su, sv)
            world_points[i]=ecef2enu.convertfromtm06([x_tm06_estimated, y_tm06_estimated, map_coordinates(heightmap, [[sv], [su]], order=1)[0]])     
        
        # ============================================
        # SANITY CHECK before running PnP
        # ============================================
        if DEBUG:
            print(f"World points range:")
            print(f"  X (North): [{world_points[:,0].min():.1f}, "
                f"{world_points[:,0].max():.1f}]")
            print(f"  Y (East):  [{world_points[:,1].min():.1f}, "
                f"{world_points[:,1].max():.1f}]")
            print(f"  Z (Down):  [{world_points[:,2].min():.1f}, "
                f"{world_points[:,2].max():.1f}]")
        return world_points, ecef2enu

    def compute_reprojection_stats(self,
        world_points,      # Nx3 inlier world points
        image_pixels,      # Nx2 inlier image pixels
        rvec, tvec,        # PnP solution
        K                  # intrinsics
    ):
        """
        Compute reprojection error statistics from OpenCV PnP output.
        """
        
        # Project world points using PnP solution
        projected, _ = cv2.projectPoints(
            world_points.astype(np.float64),
            rvec, tvec, K, 
            distCoeffs=None
        )
        projected = projected.reshape(-1, 2)
        
        # Per-point errors
        errors = np.sqrt(np.sum((projected - image_pixels)**2, axis=1))
        
        stats = {
            'mean_reproj': np.mean(errors),
            'median_reproj': np.median(errors),
            'std_reproj': np.std(errors),
            'max_reproj': np.max(errors),
            'rmse_reproj': np.sqrt(np.mean(errors**2)),
        }

        return stats, errors

    # =============================================================
    #  ROTATION(QUATERNIONS & EULER ANGLES)
    # =============================================================

    def quaternion_to_rotation_matrix(self, q):
        """
        Convert quaternion to rotation matrix.
        
        AirSim API returns orientation as quaternion with fields:
            .w_val, .x_val, .y_val, .z_val
        
        Returns R_world_from_body:
            Transforms a vector FROM body frame TO world frame.
            v_world = R_world_from_body @ v_body
        """
        # Normalize
        q_x, q_y, q_z, q_w=q.to_numpy_array()
        norm = np.sqrt(q_w**2 + q_x**2 + q_y**2 + q_z**2)
        w, x, y, z = q_w/norm, q_x/norm, q_y/norm, q_z/norm
        
        R = np.array([
            [1 - 2*(y*y + z*z),   2*(x*y - w*z),       2*(x*z + w*y)    ],
            [2*(x*y + w*z),       1 - 2*(x*x + z*z),   2*(y*z - w*x)    ],
            [2*(x*z - w*y),       2*(y*z + w*x),       1 - 2*(x*x + y*y)]
        ], dtype=np.float64)
        
        return R

    def euler_to_rotation_matrix(self, roll_rad, pitch_rad, yaw_rad):
        """
        Euler angles (AirSim convention) to rotation matrix.
        
        AirSim uses ZYX intrinsic rotation order:
            R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
        
        roll:  rotation about X (forward), positive = right wing down
        pitch: rotation about Y (right),   positive = nose up
        yaw:   rotation about Z (down),    positive = nose right (CW from above)
        
        Returns R_world_from_body.
        """
        cr, sr = np.cos(roll_rad),  np.sin(roll_rad)
        cp, sp = np.cos(pitch_rad), np.sin(pitch_rad)
        cy, sy = np.cos(yaw_rad),   np.sin(yaw_rad)
        
        Rz = np.array([[ cy, -sy, 0],
                        [ sy,  cy, 0],
                        [  0,   0, 1]])
        
        Ry = np.array([[ cp, 0, sp],
                        [  0, 1,  0],
                        [-sp, 0, cp]])
        
        Rx = np.array([[1,   0,   0],
                        [0,  cr, -sr],
                        [0,  sr,  cr]])
        
        R_world_from_body = Rz @ Ry @ Rx
        return R_world_from_body
    
    def run_pnp_with_full_diagnostics(self,
        world_points_3d,    # Mx3 all matched world points
        image_pixels,       # Mx2 all matched image pixels
        K,                  # intrinsics
        baro_altitude,       # from barometer
        debug=True
    ):
        """
        Run OpenCV PnP and extract everything needed for covariance.
        """
        
        # Run PnP
        success, rvec, tvec, inliers = cv2.solvePnPRansac(
            world_points_3d.astype(np.float64),
            image_pixels.astype(np.float64),
            K,
            distCoeffs=None,
            flags=cv2.SOLVEPNP_SQPNP,
            reprojectionError=8.0,
            confidence=0.99,
            iterationsCount=10000
        )
        
        if not success or inliers is None:
            return None
        
        inliers = inliers.flatten()
        
        # Extract position
        R_est, _ = cv2.Rodrigues(rvec)
        position = (-R_est.T @ tvec).flatten()
        
        # ==========================================
        # Quality signal 1: Inlier statistics
        # ==========================================
        n_total = len(image_pixels)
        n_inliers = len(inliers)
        inlier_ratio = n_inliers / n_total
        
        # ==========================================
        # Quality signal 2: Reprojection error
        # ==========================================
        inlier_world = world_points_3d[inliers]
        inlier_pixels = image_pixels[inliers]
        
        reproj_stats, reproj_errors = self.compute_reprojection_stats(
            inlier_world, inlier_pixels, rvec, tvec, K
        )
        
        # ==========================================
        # Quality signal 3: Altitude consistency
        # ==========================================
        pnp_altitude = -position[2]  # NED to altitude
        altitude_error = abs(pnp_altitude - baro_altitude)
        altitude_ratio = altitude_error / max(baro_altitude, 1.0)
        
        # ==========================================
        # Quality signal 4: Geometric spread of inliers
        # ==========================================
        # Well-spread matches constrain PnP better than clustered ones
        inlier_pixel_spread = np.std(inlier_pixels, axis=0)
        # Normalized by image size
        spread_score = np.mean(inlier_pixel_spread) / max(K[0, 2], 1.0)
        
        # ==========================================
        # Package everything
        # ==========================================
        diagnostics = {
            'position': position,
            'rvec': rvec,
            'tvec': tvec,
            'R': R_est,
            
            # Quality signals
            'n_total_matches': n_total,
            'n_inliers': n_inliers,
            'inlier_ratio': inlier_ratio,
            'mean_reproj_error': reproj_stats['mean_reproj'],
            'median_reproj_error': reproj_stats['median_reproj'],
            'rmse_reproj_error': reproj_stats['rmse_reproj'],
            'altitude_error': altitude_error,
            'altitude_ratio': altitude_ratio,
            'pnp_altitude': pnp_altitude,
            'baro_altitude': baro_altitude,
            'inlier_spread': spread_score,
            'inlier_indices': inliers,
        }
        
        return diagnostics

    def bridge_to_real_pipeline(self,
        matched_drone_pixels,      # Nx2 from SP in ORIGINAL image
        matched_satellite_pixels,  # Nx2 from SP in satellite tile
        patch_transform,           # Orto pixel coordinate to tm06 coordinate
        reference_point,
        heightmap,                 # function: (x,y) → z in NED
        K,                         # camera intrinsics
        img_path                   # Image path to acesss ground truth
    ):
        """
        Bridge from your existing matching to PnP.
        """
        #get object coordinates for pnp as well as ecef2enu coordinate transformation
        world_points, ecef2enu = self.get_world_points_enu(matched_satellite_pixels, heightmap, patch_transform, reference_point) 
        gt, gt_q = self.get_airsim_ground_truth_all(img_path)  # Get ground truth position in airsim coordinates
        Rotation_body_to_world=self.quaternion_to_rotation_matrix(gt_q)
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
        #Accept everything afterwards i choose which path to go
        if not success: #or len(inliers)<30:
            if DEBUG: print("PnP FAILED")
            return None
        
        R_est, _ = cv2.Rodrigues(rvec)
        pos_est = (-R_est.T @ tvec).flatten() #in enu
        pos_est = self.airsim2ecef.invert(ecef2enu.invert(pos_est)) #enu -> ecef -> airsim

        ###ADDED 5/9 AS pos_est being body and not camera pos.

        camera_to_body_translation_in_world_frame=Rotation_body_to_world@camera_to_body_translation_in_body_frame
        pos_est = pos_est - camera_to_body_translation_in_world_frame

        if DEBUG:
            print(f"\n=== PnP RESULT ===")
            print(f"Estimated position: ({pos_est[0]:.1f}, "
                f"{pos_est[1]:.1f}, {pos_est[2]:.1f})")
            print(f"GT position:        ({gt[0]:.1f}, "
                f"{gt[1]:.1f}, {gt[2]:.1f})")
            print(f"Position error: {np.linalg.norm(pos_est - gt):.2f}m \nPosition error [no height]: {np.linalg.norm(pos_est[:2] - gt[:2]):.2f}m")
            print(f"Position error [North]: "
                f"{pos_est[0] - gt[0]:.2f}m [East]{pos_est[1] - gt[1]:.2f}m")
            print(f"Altitude est: {-pos_est[2]:.1f}m, "
                f"GT: {-gt[2]:.1f}m")
            print(f"Inliers: {len(inliers)}/{len(image_points)}")
            distance = np.linalg.norm(gt[:2])
            print(f"Distance: {distance}m")

        
        inliers = inliers.flatten()
        
        # ==========================================
        # Quality signal 1: Inlier statistics
        # ==========================================
        n_total = len(matched_drone_pixels)
        n_inliers = len(inliers)
        inlier_ratio = n_inliers / n_total
        
        # ==========================================
        # Quality signal 2: Reprojection error
        # ==========================================
        inlier_world = world_points[inliers]
        inlier_pixels = matched_drone_pixels[inliers]
        
        reproj_stats, reproj_errors = self.compute_reprojection_stats(
            inlier_world, inlier_pixels, rvec, tvec, K
        )
        
        # ==========================================
        # Quality signal 3: Altitude consistency
        # ==========================================
        baro_altitude=-gt[2]
        pnp_altitude = -pos_est[2]  # NED to altitude
        altitude_error = abs(pnp_altitude - baro_altitude)
        altitude_ratio = altitude_error / max(baro_altitude, 1.0)
        
        # ==========================================
        # Quality signal 4: Geometric spread of inliers
        # ==========================================
        # Well-spread matches constrain PnP better than clustered ones
        inlier_pixel_spread = np.std(inlier_pixels, axis=0)
        # Normalized by image size
        spread_score = np.mean(inlier_pixel_spread) / max(K[0, 2], 1.0)
        
        # ==========================================
        # Package everything
        # ==========================================
        diagnostics = {
            'position': pos_est,

            # Quality signals
            'n_total_matches': n_total,
            'n_inliers': n_inliers,
            'inlier_ratio': inlier_ratio,
            'mean_reproj_error': reproj_stats['mean_reproj'],
            'median_reproj_error': reproj_stats['median_reproj'],
            'rmse_reproj_error': reproj_stats['rmse_reproj'],
            'altitude_error': altitude_error,
            'altitude_ratio': altitude_ratio,
            'pnp_altitude': pnp_altitude,
            'baro_altitude': baro_altitude,
            'inlier_spread': spread_score,
            'inlier_indices': inliers,
        }

        return diagnostics

    # ==========================================
    # 3. Main Pipeline
    # ==========================================
    def run_pipeline(self):
        if self.exist: 
            print('The result files already exist')
            #return 
        prior_x=self.prior_x
        prior_y=self.prior_y
        # Open the massive GeoTIFF once
        ate_north_errors=[]
        ate_east_errors=[]
        with rasterio.open(self.orto_path) as ortho_raster:
            # Get all drone images
            drone_image_paths = sorted(glob.glob(os.path.join(self.path_images, "*.png")))

            for img_path in drone_image_paths:
                print(f"\n--- Processing {os.path.basename(img_path)} ---")

                # Crop a small patch based on our rough prior estimate
                # In a real online system, prior_lat/lon updates from the previous frame
                print(f"Cropping Orthophoto around prior GPS: {prior_x}, {prior_y}...")
                if self.full_search: 
                    print('NO FULL SEACRH INCORPORATED')
                    raise BaseException('NO FULL SEACRH INCORPORATED')
                ortho_patch, ortho_heightmap, patch_transform = self.crop_orthophoto(ortho_raster, prior_x, prior_y, self.search_area)
                raster_h, raster_w, _ = ortho_patch.shape

                if self.angle_search==False:   # degrees WITH POSITIVE IS ANTI-CLOCKWISE 
                    
                    euler=airsim_utils.to_eularian_angles_degrees(self.get_airsim_ground_truth_all(img_path)[1])
                    #print(f'Yaw:{euler[0]:.2f} Pitch:{euler[1]:.2f} Roll:{euler[2]:.2f}')
                    yaw=euler[2]
                    if not self.ned_flag:
                        yaw+=90
                        #yaw*=-1

                    # rotate image around center
                    center = (raster_w / 2, raster_h / 2)

                    M = cv2.getRotationMatrix2D(center, yaw, 1.0)

                    ortho_patch = cv2.warpAffine(
                        ortho_patch,
                        M,
                        (raster_w, raster_h),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT,
                        borderValue=0
                    )
                    
                    ortho_heightmap = cv2.warpAffine(
                        ortho_heightmap,
                        M,
                        (raster_w, raster_h),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT,
                        borderValue=0
                    )

                    # rasterio affine rotation
                    R = (
                        Affine.translation(center[0], center[1]) *
                        Affine.rotation(yaw) *
                        Affine.translation(-center[0], -center[1])
                    )

                    patch_transform = patch_transform * R
                else:
                    print('Yaw/Angle Search is NOT IMPLEMENTED')
                    raise BaseException('Yaw/Angle Search is NOT IMPLEMENTED')
                                
                ortho_tensor = self.image_to_tensor(ortho_patch)

                # 1. Load Drone Image
                drone_img = cv2.imread(img_path)
                drone_img = cv2.cvtColor(drone_img, cv2.COLOR_BGR2RGB)
                h, w, _ = drone_img.shape
                drone_tensor=self.image_to_tensor(drone_img)

                # 3. Deep Learning Extraction & Matching
                with torch.no_grad():
                    feats_drone = extractor.extract(drone_tensor)
                    feats_ortho = extractor.extract(ortho_tensor)
                    matches_dict = matcher({"image0": feats_drone, "image1": feats_ortho})

                # Clean up dimensions
                feats_drone, feats_ortho, matches_dict = rbd(feats_drone), rbd(feats_ortho), rbd(matches_dict)
                matches = matches_dict['matches']

                # Extract matched (x, y) pixel coordinates
                pts_drone = feats_drone['keypoints'][matches[..., 0]].cpu().numpy()
                pts_ortho = feats_ortho['keypoints'][matches[..., 1]].cpu().numpy()

                if DEBUG: print(f"Found {len(pts_drone)} SuperPoint matches.")

                if len(pts_drone) < MINIMUM_INLIERS_FOR_PNP:
                    if DEBUG: print("Not enough matches to localize. Skipping...")
                    prior_x, prior_y=self.airsim2ecef.convert2tm06(self.get_airsim_ground_truth(img_path))[:2]
                    continue

                #TM06 actual drone coordinate
                focal=w/(2*math.tan(FOV*math.pi/180/2))
                K=np.array([[focal, 0, w/2],[0, focal, h/2], [0,0,1]])# camera intrinsics
                diagnostics=self.bridge_to_real_pipeline(
                    pts_drone,
                    pts_ortho,
                    patch_transform, 
                    [prior_x, prior_y, ortho_heightmap[int(raster_h/2), int(raster_w/2)] ], 
                    ortho_heightmap, 
                    K, 
                    img_path
                )

                gt=self.get_airsim_ground_truth(img_path)
                if type(diagnostics)!=type(None):
                    if VISUAL:
                            axes = viz2d.plot_images([drone_img, ortho_patch, ortho_heightmap])
                                    
                            viz2d.plot_matches(
                                        pts_drone,
                                        pts_ortho,
                                        color="lime",
                                        lw=0.2 # Line width
                            )
                            plt.show()
                    pos=diagnostics['position']
                    ate_north_errors.append(pos[0]-gt[0])
                    ate_east_errors.append(pos[1]-gt[1])
                    #prior_x, prior_y = self.airsim2ecef.convert2tm06(pos)[:2]    
                    prior_x, prior_y = self.airsim2ecef.convert2tm06(gt)[:2]
                else:
                    prior_x, prior_y=self.airsim2ecef.convert2tm06(gt)[:2]
                self.save_info.append([diagnostics, gt, self.place, self.ned_flag, self.altitude, self.pitch, self.offshore, self.mode])

        ate_east_errors=np.array(ate_east_errors)
        ate_north_errors=np.array(ate_north_errors)
        print(f'{ate_east_errors.mean():.2f}±{ate_east_errors.std():.2f},{ate_north_errors.mean():.2f}±{ate_north_errors.std():.2f}')
        print(f'East RMSE: {np.sqrt(np.mean(ate_east_errors**2)):2f}, North RMSE: {np.sqrt(np.mean(ate_north_errors**2)):2f}')
        with open(self.savefile, "wb") as f:
            pickle.dump(self.save_info, f) 

def beep(): winsound.Beep(freq, duration)

if __name__ == "__main__":
    for step, row_index in enumerate(rows_to_run):
            row=rows[row_index]
            print(f'{step+1}:',row)
    for step, row_index in enumerate(rows_to_run):
        row=rows[row_index]
        print(f'Row index: {row_index} Step:{step}/{len(rows_to_run)}')
        crossview=CrossView(row)
        crossview.run_pipeline()
    exit()
    if len(rows.shape)>1:
        for row in rows:
            crossview=CrossView(row)
            crossview.run_pipeline()
    else:
        crossview=CrossView(rows)
        crossview.run_pipeline() 
    exit()
    try:
        if len(rows.shape)>1:
            for row in rows:
                crossview=CrossView(row)
                crossview.run_pipeline()
        else:
            crossview=CrossView(rows)
            crossview.run_pipeline()    
        while True:
            notification.notify(
                title = "Finished",
                message = f"Finished executing {os.path.basename(sys.argv[0])} successful",
            )
            break
    except BaseException as msg:
        while True:
            notification.notify(
                title = "Failed",
                message = f"Failed executing {os.path.basename(sys.argv[0])}: {msg}",
            )
            break
        print(msg)
    finally:
        beep()

        
