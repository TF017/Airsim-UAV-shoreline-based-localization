# Shoreline-Based Absolute Localization for UAVs in GNSS-Denied Coastal Areas

**Master's Thesis — Electrical and Computer Engineering, Instituto Superior Técnico (IST)**

**Author:** Tiago Ferreira
**Degree:** Electrical and Computer Engineering
**Institution:** Instituto Superior Técnico (IST)

---

## 📌 Overview

This repository contains the simulation environment, perception methods, geometric localization algorithms, and experimental results developed as part of a Master's thesis on **absolute localization of Unmanned Aerial Vehicles (UAVs) in coastal environments where GNSS is unavailable or unreliable**.

The main objective is to investigate whether **shoreline information can be used as a geometric reference for absolute UAV localization**.

The proposed framework is developed in a simulated coastal environment using **AirSim, Unreal Engine, and Cesium**. The UAV is equipped with a camera and operates without relying on GNSS measurements for localization.

The work explores a localization pipeline based on:

1. **Cross-view localization** for an initial position estimate.
2. **Shoreline extraction and geometric matching** using camera ray casting, Procrustes analysis, and ICP.
3. **Particle-filter localization** using inverse ray casting and Digital Elevation Model (DEM) information.
4. **Water/land segmentation** as a perception component for extracting the shoreline from UAV imagery.

A particular characteristic of the experimental setup is the **temporal separation between the reference and simulated imagery**. The georeferenced reference data is derived from a **2018 DGT orthophoto**, while the simulated imagery is generated using **2014 Bing Maps imagery provided through Cesium**. Consequently, the reference and observation data are not generated from the same image source or acquisition period.

> **Status:** The particle-filter evaluation and final experimental analysis are currently ongoing. Results presented in this repository will be updated as the evaluation progresses.

---

## 🎥 Demonstration

The following video demonstrates the particle-filter localization framework operating in a simulated coastal environment.

**Coming soon / YouTube link to be added**

<!-- Replace the section below with the YouTube thumbnail once the video is uploaded.

[![UAV Shoreline-Based Localization Demo](https://img.youtube.com/vi/YOUTUBE_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUTUBE_VIDEO_ID)

-->

---

## 🧭 Research Pipeline

The overall research framework can be summarized as:

```text
                    ┌─────────────────────────┐
                    │  Georeferenced Coastal  │
                    │     Reference Data       │
                    │      DGT Orthophoto      │
                    │          2018            │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Reference Shoreline  │
                    └────────────┬────────────┘
                                 │
                                 │
       ┌─────────────────────────┴──────────────────────────┐
       │                                                    │
       ▼                                                    ▼
┌──────────────────┐                              ┌──────────────────┐
│   AirSim UAV     │                              │ Cross-View       │
│                  │                              │ Localization     │
│ Unreal + Cesium  │                              │                  │
│                  │                              │ Lightweight      │
│ Camera           │                              │ implementation   │
└────────┬─────────┘                              └────────┬─────────┘
         │                                                │
         ▼                                                │
┌──────────────────┐                                      │
│ UAV Camera Frame │                                      │
└────────┬─────────┘                                      │
         │                                                │
         ▼                                                │
┌──────────────────────────┐                              │
│ Water/Land Segmentation  │                              │
│                          │                              │
│ SAM 3 / SegFormer-B2 /   │                              │
│ other experiments        │                              │
└────────────┬─────────────┘                              │
             │                                            │
             ▼                                            │
┌──────────────────────────┐                              │
│      Shoreline           │                              │
│      Extraction          │                              │
└────────────┬─────────────┘                              │
             │                                            │
             ▼                                            │
┌──────────────────────────┐                              │
│       Ray Casting        │                              │
│                          │                              │
│ Camera intrinsics +      │                              │
│ camera extrinsics        │                              │
└────────────┬─────────────┘                              │
             │                                            │
             ▼                                            │
┌──────────────────────────┐                              │
│ Metric Shoreline         │                              │
│ Representation           │                              │
└────────────┬─────────────┘                              │
             │                                            │
             ▼                                            │
┌──────────────────────────┐                              │
│ Procrustes + ICP         │◄─────────────────────────────┘
│ Shoreline Matching       │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│    Particle Filter       │
│                          │
│    Inverse Ray Casting   │
│    + DEM Information     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Absolute UAV Position    │
│ Relative to Reference    │
│ Map                      │
└──────────────────────────┘
```

---

# 🌊 Simulation Environment

The experimental environment is based on a combination of:

* **AirSim** — UAV simulation and sensor acquisition.
* **Unreal Engine** — simulation environment and scene control.
* **Cesium** — geospatial environment and terrain/imagery integration.

The UAV is equipped with a simulated camera. The camera is currently modeled without measurement noise.

The simulation uses **2014 Bing Maps imagery provided through Cesium**, while the external reference used for localization is based on a **2018 DGT orthophoto**.

This temporal separation is maintained throughout the localization experiments and introduces differences between the simulated observation and the georeferenced reference data.

### Coordinate Frame

The localization framework currently operates using a **local simulation coordinate frame**.

Utilities for coordinate conversion are also included in the repository where required by the simulation and geospatial data-processing pipeline.

---

# 📍 Localization Framework

## 1. Lightweight Cross-View Localization

A lightweight cross-view localization module was developed as an initial approach for obtaining an approximate UAV location from visual information.

The module provides an initial investigation into matching the simulated UAV view with georeferenced coastal reference imagery.

This implementation is intentionally lightweight and serves primarily as one component of the broader localization framework.

Experimental results for this module are included in the repository.

---

## 2. Shoreline-Based Geometric Matching

The main geometric localization approach uses the shoreline as a spatial feature.

### Shoreline Observation

The UAV camera frame is processed to obtain the shoreline separating **water and land**.

The observed shoreline is then transformed from image coordinates into metric coordinates using the camera model.

The transformation uses:

* Camera intrinsic parameters
* Camera extrinsic parameters
* Camera pose
* Ray casting

The resulting shoreline is represented in a metric coordinate system and can subsequently be compared with the georeferenced reference shoreline.

### Procrustes Alignment

The reconstructed shoreline is aligned with the reference shoreline using **Procrustes analysis**.

This provides a geometric alignment between the observed and reference shoreline representations.

### ICP Refinement

The alignment can subsequently be refined using **Iterative Closest Point (ICP)**.

The combination of Procrustes alignment and ICP is used to investigate geometric correspondence between the shoreline observed by the UAV and the reference shoreline extracted from the georeferenced map.

---

# 🎯 Particle-Filter Localization

The particle-filter approach extends the geometric shoreline concept into a probabilistic localization framework.

Each particle represents a candidate UAV position in the local simulation frame.

For each candidate position, the expected shoreline observation is generated using **inverse ray casting**.

The predicted observation is then compared against the shoreline observed by the UAV.

Conceptually:

```text
                 Candidate UAV Position
                          │
                          ▼
                  ┌───────────────┐
                  │ Inverse Ray   │
                  │    Casting    │
                  └───────┬───────┘
                          │
                          ▼
                 Predicted Shoreline
                          │
                          │ comparison
                          ▼
Observed Shoreline ──► Likelihood
                          │
                          ▼
                    Particle Weight
                          │
                          ▼
                  Resampling / Update
                          │
                          ▼
                 Estimated UAV Position
```

The output of the particle filter is the **absolute UAV position relative to the georeferenced reference map**.

---

## ⛰️ DEM-Aware Shoreline Modeling

A Digital Elevation Model (DEM) is incorporated into the particle-filter formulation to account for the elevation of the shoreline.

A simplified assumption that the shoreline always lies at:

```text
z = 0
```

is not generally valid in coastal environments.

For example, a shoreline may occur at an elevation of approximately:

```text
z = 5 m
```

depending on the local terrain.

This elevation affects the intersection between camera rays and the terrain and therefore influences the predicted shoreline observed from a candidate UAV pose.

The DEM is consequently used to make the inverse-ray-casting prediction more representative of the simulated environment.

---

# 🛰️ Reference and Observation Data

An important characteristic of this work is the use of temporally separated imagery.

| Dataset              | Source             | Year | Role                       |
| -------------------- | ------------------ | ---: | -------------------------- |
| Reference orthophoto | DGT                | 2018 | Georeferenced reference    |
| Simulated imagery    | Bing Maps / Cesium | 2014 | UAV simulation environment |

The reference and simulated imagery therefore differ in acquisition time and source.

This creates a more challenging matching problem than directly comparing imagery generated from the same map source.

The temporal difference is maintained across the different localization experiments.

---

# 🖼️ Water/Land Segmentation

A separate component of the project investigates automatic extraction of the shoreline from UAV imagery.

The segmentation problem is formulated as a **water-versus-land segmentation task**, with the shoreline represented by the boundary between the two classes.

A small custom dataset was created for this purpose.

The repository contains experiments involving the fine-tuning and evaluation of segmentation models, including:

* **SAM 3**
* **SegFormer-B2**
* Other segmentation experiments

The resulting segmentation masks can be used as input to the shoreline extraction and localization pipeline.

### Segmentation Pipeline

```text
UAV Image
    │
    ▼
Water / Land Segmentation
    │
    ▼
Water Mask + Land Mask
    │
    ▼
Water/Land Boundary
    │
    ▼
Shoreline
    │
    ▼
Geometric Localization
```

Segmentation results are included separately from the localization results because segmentation represents a perception component of the overall system.

---

# 📊 Results

Experimental results are currently available for several components of the project.

## Cross-View Localization

Results for the lightweight cross-view localization module are available and are being used to characterize its behavior within the simulated environment.

**Results:** `results/` — to be documented/linked here.

---

## Shoreline Matching

Experiments have been conducted using:

* Ray-cast shoreline reconstruction
* Procrustes alignment
* ICP refinement

These experiments provide an evaluation of the geometric shoreline-matching approach.

**Results:** `results/` — to be documented/linked here.

---

## Segmentation

Segmentation experiments have been conducted using the custom dataset and different model configurations, including SAM 3 and SegFormer-B2.

Results can include metrics and qualitative examples such as:

* Segmentation accuracy
* Intersection over Union (IoU)
* Boundary quality
* Qualitative segmentation examples

**Results:** `results/segmentation/`

---

## Particle Filter

The particle-filter localization framework is currently under evaluation.

The final evaluation will investigate the behavior of the proposed method under the simulated coastal GNSS-denied scenario and will be added to this repository as the experiments are completed.

**Status:** 🚧 Evaluation in progress

---

# 📁 Repository Structure

The current repository is organized around the different components developed during the thesis:

```text
.
├── Controller/
│   └── Python files for controlling the AirSim simulation
│       and acquiring/saving UAV images
│
├── Coordinates/
│   └── Coordinate-system conversion utilities
│
├── LightGlue/
│   └── Lightweight cross-view localization module
│
├── MDTmerger/
│   └── Tools for merging/preparing DTM data
│       for integration with Cesium
│
├── Unreal/
│   └── Utilities for controlling/configuring
│       the Unreal Engine simulation
│
├── Water Segmentation/
│   └── Water/land segmentation experiments,
│       model fine-tuning and related code
│
├── results/
│   └── Experimental results
│
└── README.md
```

> The repository structure is evolving as the thesis work progresses.

---

# ⚙️ Installation

The project is primarily implemented in **Python**.

Because several components depend on external simulation and geospatial software, installation requirements vary between modules.

At a minimum, the Python environment should be configured according to the requirements of the specific module being used.

A consolidated `requirements.txt` will be provided once the software dependencies are finalized.

### Python

```bash
git clone <REPOSITORY_URL>
cd <REPOSITORY_NAME>
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

> Installation instructions are currently being finalized as the different experimental components are consolidated.

---

# 🚀 Running the Simulation

The AirSim simulation is controlled through Python scripts located in the `Controller/` directory.

The general workflow is:

```text
Unreal Engine
      │
      ▼
Cesium Coastal Environment
      │
      ▼
AirSim
      │
      ▼
Simulated UAV
      │
      ▼
Camera Images
      │
      ▼
Localization / Segmentation Pipeline
```

The controller scripts can be used to initialize the UAV simulation and acquire camera images for subsequent processing.

Detailed execution instructions will be added as the simulation setup is finalized.

---

# 🧪 Experimental Setup

The experimental framework uses:

| Component                | Configuration                                   |
| ------------------------ | ----------------------------------------------- |
| Simulator                | AirSim                                          |
| Game Engine              | Unreal Engine                                   |
| Geospatial framework     | Cesium                                          |
| UAV sensor               | Camera                                          |
| Camera noise             | None                                            |
| Reference data           | DGT orthophoto                                  |
| Reference year           | 2018                                            |
| Simulated imagery        | Bing Maps via Cesium                            |
| Simulated imagery year   | 2014                                            |
| Coordinate frame         | Local simulation frame                          |
| Localization output      | Absolute UAV position relative to reference map |
| Shoreline representation | Metric coordinates                              |
| Particle filter          | DEM-aware                                       |
| Shoreline prediction     | Inverse ray casting                             |

---

# 🎓 Thesis Information

**Title:**
*Shoreline-Based Absolute Localization for UAVs in GNSS-Denied Coastal Areas*

**Author:**
Tiago Ferreira

**Degree:**
Master's Degree in Electrical and Computer Engineering

**Institution:**
Instituto Superior Técnico (IST)

**Department:**
Electrical and Computer Engineering

**Supervisors:**
*To be added*

**Academic Year:**
*To be added*

---

# 📄 Thesis

The final thesis document will be made available here once it is ready.

```text
[Thesis PDF — coming soon]
```

---

# 📚 Publications

Publications and related academic work will be listed here if applicable.

```text
[Publications — to be added]
```

---

# 🔗 Related Resources

* AirSim simulation framework
* Unreal Engine
* Cesium
* DGT geospatial data
* Segmentation model resources

Specific links and dataset references will be added as the repository is finalized.

---

# ⚠️ Data and Model Availability

Some components of this project rely on third-party imagery, geospatial data, simulation assets, and pretrained models.

The availability and redistribution of these resources may be subject to their respective licenses and terms of use.

The repository therefore does not necessarily redistribute all external datasets or assets used during the experiments.

Instructions for obtaining required external resources will be provided where appropriate.

---

# 📜 License

**License: To be determined**

The repository is currently maintained as part of an ongoing Master's thesis project.

A license will be added once the distribution status of the source code, datasets, simulation assets, and third-party dependencies has been established.

---

# 👤 Author

**Tiago Ferreira**
Master's Student in Electrical and Computer Engineering
Instituto Superior Técnico

---

## 🚧 Project Status

This repository represents ongoing Master's thesis research.

Current development includes:

* [x] AirSim/Unreal/Cesium simulation environment
* [x] Camera-based UAV observation
* [x] Lightweight cross-view localization
* [x] Shoreline reconstruction through ray casting
* [x] Procrustes shoreline alignment
* [x] ICP shoreline refinement
* [x] DEM-aware inverse ray-casting framework
* [x] Particle-filter localization framework
* [x] Custom water/land segmentation dataset
* [x] Segmentation model experiments
* [ ] Complete particle-filter evaluation
* [ ] Final quantitative comparison
* [ ] Final thesis documentation
* [ ] Repository cleanup and reproducibility instructions

---

## 🙏 Acknowledgements

This work was developed as part of a Master's thesis in Electrical and Computer Engineering at Instituto Superior Técnico.

Additional acknowledgements and supervisor information will be added to the final version of this repository.
