# 🌿 AgriNova — AI-Powered Smart Agriculture Ecosystem

> **Smart Farming, Better Harvest**  
> A complete AgriTech system combining drone-based crop health monitoring, real-time AI detection, and farmer alerts — built for Indian farmers.

---

## 📱 App Screenshots

| Language Selection | Login | Home Dashboard |
|---|---|---|
| ![Language](images/Screenshot%202026-05-25%20113307.png) | ![Login](images/Screenshot%202026-05-25%20113315.png) | ![Home](images/Screenshot%202026-05-25%20113417.png) |

| Drone Control | Live Farm Monitor | Live Drone Feed |
|---|---|---|
| ![Drone Control](images/Screenshot%202026-05-25%20113325.png) | ![Live Monitor](images/Screenshot%202026-05-25%20113334.png) | ![Drone Feed](images/Screenshot%202026-05-25%20113338.png) |

| AI Expert | Pest Detection | Drone Capture |
|---|---|---|
| ![AI Expert](images/Screenshot%202026-05-25%20113344.png) | ![Pest Detection](images/Screenshot%202026-05-25%20113356.png) | ![Drone Capture](images/Screenshot%202026-05-25%20113401.png) |

| Agri Market | Farm Health Grid | My Profile |
|---|---|---|
| ![Market](images/Screenshot%202026-05-25%20113321.png) | ![Farm Grid](images/Screenshot%202026-05-25%20112434.png) | ![Profile](images/Screenshot%202026-05-25%20113412.png) |

---

## 🚀 What is AgriNova?

AgriNova is a **full-stack smart agriculture ecosystem** where a drone flies over a farm, detects crop diseases in real time using AI, maps every tree's health status, and instantly alerts the farmer via WhatsApp — all from a mobile app.

---

## 🏗️ System Architecture

```
Drone Camera (PiCamera2)
        ↓
Raspberry Pi 4  ←→  YOLOv8 Model (Edge AI)
        ↓                    ↓
  Pixhawk GPS         Disease Detection
        ↓                    ↓
   Flask Server (Port 8000) on Pi
        ↓
  Android Mobile App
  ├── Live Drone Feed (MJPEG Stream)
  ├── Real-Time Farm Grid (7×7 Tree Map)
  ├── Gallery Scan (Plantix-style)
  ├── AI Expert Diagnosis
  ├── Agri Market
  └── Farm Area Calculator (GPS)
        ↓
  WhatsApp Alerts via Twilio
  ├── Per-detection alert (pest + confidence + GPS)
  └── Full farm scan summary report
```

---

## ✨ Features

### 🚁 Drone Module
- **Live Drone Feed** — Real-time MJPEG video stream from PiCamera2 to mobile app
- **Edge AI Detection** — YOLOv8 runs directly on Raspberry Pi (no cloud needed)
- **Drone Capture** — Capture image on demand with instant AI analysis
- **GPS Geotagging** — Every detection tagged with GPS coordinates via Pixhawk flight controller
- **Detection Logging** — All detections saved as images + JSON with GPS + Google Maps link

### 🗺️ Farm Grid
- **Live 7×7 Tree Health Map** — Each tree shown as Affected / Healthy / Pending
- **Configurable Grid** — Set rows, columns, frames per tree, and detection threshold at runtime
- **Auto-refreshes every 5 seconds** — Live updates as drone scans the farm
- **Visual Web Dashboard** — Flask serves a live HTML grid page

### 📱 Mobile App (Android)
- **Multi-language** — English, Marathi, Hindi
- **Home Dashboard** — Live weather, your crops, daily farming tips
- **Drone Control Panel** — Drone Capture, Live Stream, Gallery Scan, Live Farm Grid
- **Gallery Scan** — Farmer uploads any crop photo → instant pest/disease detection
- **AI Expert** — Describe problem + upload photo → AI gives diagnosis and advice
- **Agri Market** — Buy seeds, pesticides, fertilizers directly in app (₹)
- **Farm Area Calculator** — Calculate field area via GPS in Acres, Hectares, Guntha
- **User Authentication** — Login/Register system

### 💬 WhatsApp Alerts (Twilio)
- **Real-time pest alert** — Sent when disease detected with name, confidence %, GPS, timestamp
- **Full scan summary** — Sent after complete farm scan with total affected/healthy trees, disease breakdown, and Google Maps location link

---

## 🦠 Diseases Detected

| # | Disease | Crop |
|---|---|---|
| 1 | Powdery Mildew | Grapes, Tomato |
| 2 | Downy Mildew | Grapes |
| 3 | Early Blight | Tomato |

> 🔄 **Coming Soon:** Nutritional deficiency detection (dataset ready, model training in progress)

---

## 🛠️ Tech Stack

### AI & Computer Vision
- **YOLOv8** — Object detection model (trained on custom dataset)
- **OpenCV** — Image processing and video streaming
- **Python** — Core backend language

### Hardware
- **Raspberry Pi 4** — Edge computing, runs detection + Flask server
- **PiCamera2** — Drone-mounted camera
- **Pixhawk Flight Controller** — GPS via MAVLink protocol

### Backend & API
- **Flask** — REST API + MJPEG video streaming server on Pi
- **PyMAVLink** — Drone GPS communication
- **Twilio** — WhatsApp alert integration

### Mobile App
- **Android** — Native mobile application
- **HTTP** — Connects to Flask server on Raspberry Pi

### Model Training
- **Google Colab** — YOLOv8 model training
- **Custom Dataset** — Annotated crop disease images

---

## 📡 Flask API Endpoints (Runs on Raspberry Pi)

| Endpoint | Description |
|---|---|
| `/video_feed` | Live MJPEG drone stream |
| `/latest_detection` | Latest detected frame as JPEG |
| `/detection_info` | Latest pest detection as JSON |
| `/status` | System status + GPS info |
| `/log` | Full geotagged detection log |
| `/tree_health` | Farm scan summary JSON |
| `/farm_grid` | Full grid status JSON |
| `/grid_view` | 🌿 Visual farm health webpage |

---

## ⚙️ Setup & Configuration

### Requirements
```bash
pip install ultralytics picamera2 pymavlink twilio flask opencv-python
```

### Configuration
Before running, set your credentials in `agrinova_modified.py`:
```python
TWILIO_SID    = "your_twilio_sid_here"
TWILIO_TOKEN  = "your_twilio_token_here"
TWILIO_FROM   = "whatsapp:+XXXXXXXXXXXXX"
FARMER_NUMBER = "whatsapp:+91XXXXXXXXXX"
```

### Run on Raspberry Pi
```bash
python agrinova_modified.py
```
You will be prompted to enter:
- Number of rows and columns (farm grid size)
- Frames per tree (how many frames to analyze per tree)
- Detection threshold % (e.g. 20 means 20% pest frames = affected)

---

## 🏆 Achievements

- 🥇 **1st Place** — Open Innovation Track, Sambhaji Rao Jondhale College of Engineering, Dombivli
- 🏆 **Winner** — ExpoTech Competition, Vision 2026, Walchand College of Engineering, Sangli
- 🥈 **Runner-Up** — Ideathon, Vision 2026, Walchand College of Engineering, Sangli

---

## 👨‍💻 Team

Built by a team of 4 — Robotics & Automation Engineering students at **Walchand College of Engineering, Sangli**

---

## 📄 Files in This Repository

| File | Description |
|---|---|
| `agrinova_modified.py` | Main Raspberry Pi script — detection + Flask server + WhatsApp alerts |
| `galleryscanfeature.py` | Gallery scan feature — farmer uploads photo for detection |
| `collabmodeltraining.ipynb` | Google Colab notebook for YOLOv8 model training |
| `changingdefaultlabels.ipynb` | Notebook for customizing dataset labels |
| `data12.yaml` | YOLOv8 dataset configuration file |

> ⚠️ `best.pt` (trained model) is not included in this repo due to file size. Contact us to get the model.

---

*AgriNova v1.0 • Made for Indian Farmers 🌾*
