# Shoreline-Based Absolute Localization for UAVs in GNSS-Denied Coastal Areas

**Master's Thesis — Electrical and Computer Engineering, Instituto Superior Técnico**

**Author:** Tiago Ferreira

---

## 📌 Overview

This repository contains the perception, visual localization, shoreline matching, and particle-filter localization methods developed as part of a Master's thesis investigating **absolute UAV localization in GNSS-denied coastal environments**.

The central idea is to exploit **georeferenced aerial imagery and shoreline geometry as a global reference**.

Rather than relying exclusively on the appearance of the complete scene, the proposed localization framework extracts the boundary between water and land from the UAV image and uses this shoreline as a persistent geometric feature. Since the reference shoreline is georeferenced, matching it with an onboard observation allows the UAV position to be estimated relative to the global reference map.

The system is developed and evaluated in a simulated coastal environment using **AirSim, Unreal Engine, and Cesium**.

The complete framework consists of three main stages:

```text
UAV Camera Image
       │
       ▼
┌─────────────────────────┐
│ Water/Land Segmentation │
│                         │
│ SAM 3 / SegFormer-B2    │
└────────────┬────────────┘
             │
             ▼
        Shoreline
             │
       ┌─────┴──────┐
       │            │
       ▼            ▼
 Global Shoreline   Sequential
 Localization       Localization
       │            │
       ▼            ▼
 Procrustes + ICP   Particle Filter
       │            │
       │       Inverse Ray Casting
       │            |
       │            |
       │            │
       └─────┬──────┘
             ▼
    Absolute UAV Position
       Relative to Map
```

---

🗺️ Reference-Based Visual Localization

A complementary localization approach uses the georeferenced aerial map directly as a global visual reference.

Given an RGB image acquired onboard the UAV, visual correspondences are established with a local region of the reference orthophoto. Because the orthophoto is georeferenced, the recovered camera pose can be expressed in the map reference frame, providing an absolute localization estimate.

This is a cross-view localization problem: the UAV image and the reference orthophoto are captured from substantially different viewpoints and can exhibit significant differences in:

* viewpoint;

* scale;

* illumination;

* image appearance;

* scene representation.

Moreover, as the UAV moves farther away from the land and a larger portion of the ocean becomes visible in the onboard camera image, extracting and matching meaningful visual features becomes increasingly difficult. This can negatively affect the ability of SuperPoint and LightGlue to establish reliable correspondences, since ocean regions generally contain fewer stable and distinctive visual structures than land areas.

The repository therefore includes a lightweight implementation based on learned local features and neural feature matching.

Feature Matching

The implemented pipeline uses:

* SuperPoint for local feature extraction;

* LightGlue for feature matching;

* geometric pose estimation;

* a Digital Elevation Model (DEM) to associate image correspondences with three-dimensional world points;

* Perspective-n-Point (PnP) optimization for camera pose recovery.

The resulting pose provides an independent absolute localization estimate and can serve as an initialization for the shoreline-based approaches.

---

# 🌊 Shoreline-Based Localization

The main focus of the work is to use the **shoreline as a geometric environmental feature** rather than attempting to match complete image appearance.

The boundary between land and water provides a large-scale feature that can be represented both:

* in the UAV observation; and
* in a georeferenced coastal map.

This representation is particularly relevant to coastal navigation because the shoreline geometry can provide positional information even when GNSS is unavailable.

The shoreline localization framework consists of **two complementary strategies**.

---

## 1. Global Shoreline Localization

The first strategy estimates the UAV position from a **single shoreline observation**.

The complete reference shoreline is searched for candidate segments that could correspond to the shoreline observed by the UAV.

The localization process follows a coarse-to-fine registration strategy:

```text
Observed UAV Shoreline
          │
          ▼
    Ray Casting
          │
          ▼
Metric Shoreline
          │
          ▼
 Candidate Reference Segments
          │
          ▼
 Procrustes Alignment
          │
          ▼
 Promising Candidates
          │
          ▼
      ICP Refinement
          │
          ▼
 Estimated UAV Position
```

### Ray Casting

The shoreline extracted from the UAV image is transformed from image coordinates into metric coordinates using the camera model.

The transformation uses the camera:

* intrinsic parameters;
* extrinsic parameters(Orientation and altitude).

together with ray casting to obtain a metric representation of the observed shoreline.

### Procrustes Alignment

Rigid Procrustes alignment provides a coarse geometric registration between the observed shoreline and candidate reference shoreline segments.

This stage is used to identify promising candidate locations efficiently.

### ICP Refinement

The best candidate alignments are refined using **Iterative Closest Point (ICP)**.

The combination of Procrustes alignment and ICP provides a coarse-to-fine geometric registration approach for single-observation shoreline localization.

The global method does not require a previous localization estimate and can therefore provide an **absolute initialization**.

---

# 🧭 2. Sequential Shoreline Localization with a Particle Filter

The second strategy incorporates shoreline observations into a **particle filter**.

Instead of searching the complete shoreline map for every camera frame, each particle represents a candidate UAV pose.

The predicted shoreline is then compared with the observed shoreline to calculate a measurement likelihood.

```text
                 Particle Set
                     │
                     ▼
             Candidate UAV Poses
                     │
                     ▼
              Inverse Ray Casting
                     │
                     ▼
           Predicted Image Shoreline
                     │
                     │
                     ▼
Observed Shoreline ────────► Measurement
                              Likelihood
                                  │
                                  ▼
                         Particle Weights
                                  │
                                  ▼
                             Resampling
                                  │
                                  ▼
                       Estimated UAV Position
```

The particle filter combines:

* temporal motion information;
* shoreline observations;
* map geometry;
* inverse ray casting.

The output is the **absolute UAV position relative to the georeferenced reference map**.

---

# 🖼️ Water/Land Segmentation

Shoreline localization depends on obtaining a reliable shoreline observation from the UAV camera.

The perception front-end formulates this as a **water-versus-land segmentation problem**, where the shoreline is represented by the boundary between the two classes.

A custom dataset was created for this purpose and used to investigate several segmentation approaches, including:

* **SAM 3**
* **SegFormer-B2**
* **SegFormer-B5**
* **U-Net**
* **DeepLabv3+**
* zero-shot baselines.

The segmentation experiments use a leakage-free **leave-location-out evaluation protocol**.

The results indicate that segmentation quality should not be assessed solely using region-overlap metrics. Since the segmentation output is ultimately used to estimate a shoreline for geometric localization, **boundary-level and metric shoreline errors** are particularly relevant.

The evaluation therefore considers metrics that better capture shoreline alignment, including:

* region overlap;
* Boundary F-score;
* strict Boundary IoU;
* metre-scale shoreline error.

The segmentation experiments provide the perception component required by the subsequent shoreline localization methods.

---

# 🔬 Research Components

The repository therefore contains several interconnected research components:

| Component               | Purpose                                                                  |
| ----------------------- | ------------------------------------------------------------------------ |
| Cross-view localization | Absolute visual localization from UAV image and georeferenced orthophoto |
| SuperPoint + LightGlue  | Local feature extraction and cross-view matching                         |
| DTM/DEM integration     | Associate visual/map information with terrain elevation                  |
| Water/land segmentation | Extract shoreline from UAV imagery                                       |
| Ray casting             | Convert image shoreline into metric coordinates                          |
| Procrustes alignment    | Coarse shoreline registration                                            |
| ICP                     | Fine shoreline registration                                              |
| Particle filter         | Sequential shoreline-based localization                                  |
| Inverse ray casting     | Predict shoreline observations for candidate poses                       |
| DEM-aware modeling      | Account for non-zero shoreline elevation                                 |
| AirSim/Unreal/Cesium    | Simulated coastal UAV environment                                        |

---

# 🛰️ Experimental Environment

The simulation environment combines:

* **AirSim** for UAV simulation and sensor acquisition;
* **Unreal Engine** for the simulated environment;
* **Cesium** for geospatial terrain and imagery.

The UAV is equipped with a camera, with the current simulation using an idealized camera model without measurement noise.

### Temporal Separation of Reference and Simulation Data

An important characteristic of the experimental setup is that the reference and simulated imagery are **temporally separated**.

| Data                 | Source             | Year | Role                    |
| -------------------- | ------------------ | ---: | ----------------------- |
| Reference orthophoto | DGT                | 2018 | Georeferenced reference |
| Simulated imagery    | Bing Maps / Cesium | 2014 | Simulation environment  |

The localization framework therefore does not rely on matching imagery generated from exactly the same source and acquisition period.

This temporal separation is maintained across the localization experiments and represents an additional source of appearance and geometric discrepancy between the UAV observations and the reference data.

# 🚀 Demonstration

A demonstration of the particle-filter localization framework is available below.

<!-- Replace YOUTUBE_VIDEO_ID after uploading the demonstration -->

[![Shoreline-Based UAV Localization Demo](https://img.youtube.com/vi/qzDkh_uzslQ/0.jpg)](https://www.youtube.com/watch?v=qzDkh_uzslQ)

The demonstration shows the particle filter operating in a simulated coastal environment and estimating the UAV's absolute position using shoreline observations.
