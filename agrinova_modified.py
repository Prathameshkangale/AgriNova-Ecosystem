from ultralytics import YOLO
from picamera2 import Picamera2
from pymavlink import mavutil
from twilio.rest import Client
import cv2
import time
import threading
import datetime
import json
import os
from flask import Flask, Response, jsonify
import signal
import sys

# ============================================================
# TWILIO WHATSAPP ALERT CONFIG
# ============================================================
TWILIO_SID    = "your_twilio_sid_here"   # ← Your Account SID
TWILIO_TOKEN  = "your_twilio_token_here"     # ← Your Auth Token
TWILIO_FROM   = "whatsapp:+XXXXXXXXXXXXX"                # Twilio sandbox number
FARMER_NUMBER = "whatsapp:+91XXXXXXXXXX"               # ← Farmer's WhatsApp number

def send_whatsapp_alert(pest_name, confidence, lat, lon):
    # This function is kept but no longer called per-frame.
    # Final summary is sent via send_whatsapp_summary() instead.
    pass

def send_whatsapp_summary(disease_frame_counts, total_frames, affected_trees, healthy_trees, lat, lon):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        maps_link = (
            f"https://maps.google.com/?q={lat},{lon}"
            if lat and lon else "No GPS Fix"
        )

        # Build per-disease breakdown lines
        disease_lines = ""
        for disease, count in disease_frame_counts.items():
            pct = round((count / total_frames) * 100, 1) if total_frames > 0 else 0
            disease_lines += f"   🔸 {disease}: *{count}* frames ({pct}%)\n"

        if not disease_lines:
            disease_lines = "   ✅ No diseases detected\n"

        message = f"""
🌿 *AgriNova Farm Scan Complete!*

📊 *Overall Scan Summary*
━━━━━━━━━━━━━━━━━━━━
🌳 Total Trees  : *{affected_trees + healthy_trees}*
🔴 Affected     : *{affected_trees}* trees
🟢 Healthy      : *{healthy_trees}* trees
🎞️ Total Frames : *{total_frames}*

🦠 *Disease Frame Breakdown:*
{disease_lines}
📍 Location : {maps_link}
⏰ Time     : {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

Please inspect affected trees immediately!
        """.strip()

        client.messages.create(
            body=message,
            from_=TWILIO_FROM,
            to=FARMER_NUMBER
        )
        print("✅ WhatsApp SUMMARY alert sent to farmer!")
    except Exception as e:
        print(f"❌ WhatsApp summary alert failed: {e}")

# ============================================================
# FARM SETUP — Input via terminal
# ============================================================
print("╔══════════════════════════════════╗")
print("║     AgriNova Farm Setup          ║")
print("╚══════════════════════════════════╝")
GRID_ROWS       = int(input("Enter number of rows: "))
GRID_COLS       = int(input("Enter number of columns: "))
TOTAL_TREES     = GRID_ROWS * GRID_COLS
FRAMES_PER_TREE = int(input("Enter frames per tree: "))
THRESHOLD       = float(input("Enter threshold % (e.g. 20): ")) / 100

print(f"\n✅ Farm Setup Confirmed:")
print(f"   Grid         : {GRID_ROWS} rows x {GRID_COLS} cols")
print(f"   Total trees  : {TOTAL_TREES}")
print(f"   Frames/tree  : {FRAMES_PER_TREE}")
print(f"   Threshold    : {THRESHOLD*100}%")
print(f"   Total frames : {TOTAL_TREES * FRAMES_PER_TREE}")
print("\nStarting system...\n")

# ============================================================
# CONFIG
# ============================================================
MODEL_PATH   = "/home/raspberry-pi-4-ra/ag_detect/best.pt"
MAVLINK_PORT = '/dev/ttyACM0'
MAVLINK_BAUD = 57600
SAVE_DIR     = "/home/raspberry-pi-4-ra/detections"
LOG_FILE     = "/home/raspberry-pi-4-ra/detections/geo_log.json"

CLASS_NAMES  = ["Powdery_mildew", "Downy_mildew", "Early_blight"]
CLASS_COLORS = {
    "Powdery_mildew": (0, 255, 255),
    "Downy_mildew":   (255, 180, 0),
    "Early_blight":   (0, 0, 255),
}
os.makedirs(SAVE_DIR, exist_ok=True)

# ============================================================
# GPS THREAD
# ============================================================
current_gps = {"lat": None, "lon": None, "alt": None, "fix": False}

def gps_thread():
    try:
        print("🔌 Connecting to Pixhawk for GPS...")
        master = mavutil.mavlink_connection(MAVLINK_PORT, baud=MAVLINK_BAUD)
        master.wait_heartbeat()
        master.mav.request_data_stream_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            10, 1
        )
        print("✅ Pixhawk connected! Waiting for GPS fix...")
        while True:
            msg = master.recv_match(
                type='GLOBAL_POSITION_INT', blocking=True, timeout=5)
            if msg:
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt = msg.alt / 1000
                if lat != 0.0 and lon != 0.0:
                    current_gps["lat"] = lat
                    current_gps["lon"] = lon
                    current_gps["alt"] = alt
                    current_gps["fix"] = True
                    print(f"📍 GPS: {lat:.6f}, {lon:.6f}, Alt: {alt:.1f}m")
            time.sleep(0.1)
    except Exception as e:
        print(f"❌ GPS error: {e}")
        print("⚠️  Running without GPS — detections will have no coordinates")

# ============================================================
# SAVE GEOTAGGED DETECTION
# ============================================================
last_saved = {}

def save_detection(frame_bgr, label, conf):
    timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    img_filename = f"{timestamp}_{label}.jpg"
    img_path     = os.path.join(SAVE_DIR, img_filename)

    cv2.imwrite(img_path, frame_bgr)

    entry = {
        "timestamp":  datetime.datetime.now().isoformat(),
        "class":      label,
        "confidence": round(conf, 2),
        "image":      img_path,
        "gps": {
            "lat": current_gps["lat"],
            "lon": current_gps["lon"],
            "alt": current_gps["alt"],
            "fix": current_gps["fix"]
        },
        "maps_link": (
            f"https://maps.google.com/?q={current_gps['lat']},{current_gps['lon']}"
            if current_gps["fix"] else "No GPS fix"
        )
    }

    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            try:
                log = json.load(f)
            except:
                log = []
    log.append(entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

    print(f"💾 Saved: {img_path}")
    print(f"🗺️  Maps: {entry['maps_link']}")

    return entry

# ============================================================
# MODEL + CAMERA SETUP
# ============================================================
model = YOLO(MODEL_PATH)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (640, 480)}))
picam2.start()
time.sleep(2)
print("✅ Camera started!")

flask_app = Flask(__name__)

# ============================================================
# SHARED VARIABLES
# ============================================================
detected_frame = None
detection_info = []
lock           = threading.Lock()

frame_counter        = 0
current_tree         = 1
pest_frame_count     = 0
tree_results         = {}
detection_done       = False
disease_frame_counts = {name: 0 for name in CLASS_NAMES}  # tracks frames per disease
total_pest_frames    = 0  # total frames where any disease was detected

# ============================================================
# HELPER
# ============================================================
def get_grid_position(tree_id):
    row = (tree_id - 1) // GRID_COLS
    col = (tree_id - 1) % GRID_COLS
    return row, col

# ============================================================
# CAPTURE + DETECT THREAD
# ============================================================
def capture_and_detect():
    global detected_frame, detection_info
    global frame_counter, current_tree
    global pest_frame_count, tree_results, detection_done
    global disease_frame_counts, total_pest_frames

    while True:
        frame     = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        results    = model(frame_bgr, conf=0.4)
        detections = results[0].boxes

        gps_text = (
            f"GPS: {current_gps['lat']:.5f}, {current_gps['lon']:.5f}"
            if current_gps["fix"] else "GPS: No Fix ⏳"
        )

        if len(detections) > 0:
            annotated = frame_bgr.copy()
            cv2.putText(annotated, gps_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            info = []
            for box in detections:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf  = float(box.conf[0])
                cls   = int(box.cls[0])
                label = CLASS_NAMES[cls] if cls < len(CLASS_NAMES) else f"class_{cls}"
                color = CLASS_COLORS.get(label, (0, 255, 0))

                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated, f"{label} {conf:.2f}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                info.append({
                    "pest":       label,
                    "confidence": round(conf * 100, 1)
                })

                now = time.time()
                if label not in last_saved or now - last_saved[label] > 10:
                    save_detection(annotated, label, conf)
                    last_saved[label] = now

                # Count frames per disease (outside save throttle)
                disease_frame_counts[label] = disease_frame_counts.get(label, 0) + 1

            total_pest_frames += 1

            annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            with lock:
                detected_frame = annotated_rgb.copy()
                detection_info = info
                print(f"🐛 Pest detected: {[i['pest'] for i in info]}")

        else:
            display_frame = frame_bgr.copy()
            cv2.rectangle(display_frame, (10, 10), (250, 60), (0, 0, 0), -1)
            cv2.putText(display_frame, "No Detection", (20, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, gps_text, (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            display_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            with lock:
                detected_frame = display_rgb.copy()
                detection_info = []

        with lock:
            if detection_done:
                continue

            frame_counter += 1

            if len(detections) > 0:
                pest_frame_count += 1

            if frame_counter % FRAMES_PER_TREE == 0:
                ratio = pest_frame_count / FRAMES_PER_TREE

                if ratio >= THRESHOLD:
                    status = "affected"
                    emoji  = "🔴"
                else:
                    status = "healthy"
                    emoji  = "🟢"

                tree_results[current_tree] = status
                row, col = get_grid_position(current_tree)

                print(f"{emoji} Tree {current_tree:3d} "
                      f"(Row {row+1:2d}, Col {col+1:2d}) → "
                      f"{status.upper():8s} "
                      f"({pest_frame_count}/{FRAMES_PER_TREE} frames) "
                      f"GPS: {current_gps['lat']}, {current_gps['lon']}")

                pest_frame_count = 0
                current_tree    += 1

                if current_tree > TOTAL_TREES:
                    detection_done = True
                    # ❌ REMOVED: Don't send WhatsApp here anymore!
                    # Message now sent only on Ctrl+C interrupt

        time.sleep(0.1)

# ============================================================
# SIGNAL HANDLER FOR GRACEFUL SHUTDOWN + ALERT SENDING
# ============================================================
def signal_handler(sig, frame):
    """Called when user presses Ctrl+C — sends summary before exit"""
    print("\n\n⚠️  Scan interrupted by user!")
    print("📤 Sending WhatsApp summary before exit...\n")
    
    # Calculate final stats
    with lock:
        affected = sum(1 for v in tree_results.values() if v == "affected")
        healthy  = TOTAL_TREES - affected
    
    print(f"📊 Final Summary:")
    print(f"   🔴 Affected: {affected} trees")
    print(f"   🟢 Healthy: {healthy} trees")
    print(f"   🎞️ Total pest frames: {total_pest_frames}")
    
    # Send WhatsApp summary
    send_whatsapp_summary(
        disease_frame_counts,
        total_pest_frames,
        affected,
        healthy,
        current_gps["lat"],
        current_gps["lon"]
    )
    
    print("\n✅ Summary sent! Exiting...\n")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ============================================================
# FLASK ROUTES — Existing
# ============================================================
def generate_frames():
    while True:
        with lock:
            if detected_frame is None:
                continue
            ret, buffer = cv2.imencode('.jpg', detected_frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               frame_bytes + b'\r\n')
        time.sleep(0.5)

@flask_app.route('/latest_detection')
def latest_detection():
    with lock:
        if detected_frame is None:
            return "No pest detected yet", 404
        ret, buffer = cv2.imencode('.jpg', detected_frame)
        return buffer.tobytes(), 200, {'Content-Type': 'image/jpeg'}

@flask_app.route('/detection_info')
def get_detection_info():
    with lock:
        if not detection_info:
            return jsonify({"detected": False, "pests": []})
        return jsonify({"detected": True, "pests": detection_info})

@flask_app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@flask_app.route('/status')
def status():
    return jsonify({
        "status":  "running",
        "model":   "ag_pest_v1",
        "classes": CLASS_NAMES,
        "gps":     current_gps
    })

@flask_app.route('/log')
def log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify([])

# ============================================================
# FLASK ROUTES — Tree health JSON
# ============================================================
@flask_app.route('/tree_health')
def tree_health():
    with lock:
        total    = len(tree_results)
        affected = sum(1 for v in tree_results.values()
                       if v == "affected")
        healthy  = total - affected
        return jsonify({
            "total_trees_processed" : total,
            "total_trees"           : TOTAL_TREES,
            "affected"              : affected,
            "healthy"               : healthy,
            "detection_done"        : detection_done,
            "grid_rows"             : GRID_ROWS,
            "grid_cols"             : GRID_COLS,
            "frames_per_tree"       : FRAMES_PER_TREE,
            "threshold_percent"     : THRESHOLD * 100,
            "gps"                   : current_gps
        })

@flask_app.route('/farm_grid')
def farm_grid():
    with lock:
        grid = []
        for row in range(GRID_ROWS):
            grid_row = []
            for col in range(GRID_COLS):
                tree_id = row * GRID_COLS + col + 1
                if tree_id in tree_results:
                    status = tree_results[tree_id]
                else:
                    status = "pending"
                grid_row.append({
                    "tree_id" : tree_id,
                    "row"     : row + 1,
                    "col"     : col + 1,
                    "status"  : status
                })
            grid.append(grid_row)

        return jsonify({
            "grid_rows"      : GRID_ROWS,
            "grid_cols"      : GRID_COLS,
            "detection_done" : detection_done,
            "grid"           : grid
        })

# ============================================================
# FLASK ROUTE — Visual grid webpage
# ============================================================
@flask_app.route('/grid_view')
def grid_view():
    with lock:
        total    = TOTAL_TREES
        affected = sum(1 for v in tree_results.values() if v == "affected")
        healthy  = sum(1 for v in tree_results.values() if v == "healthy")
        pending  = total - len(tree_results)
        done     = detection_done

        # Build grid HTML
        grid_html = ""
        for row in range(GRID_ROWS):
            grid_html += "<tr>"
            for col in range(GRID_COLS):
                tree_id = row * GRID_COLS + col + 1
                if tree_id in tree_results:
                    status = tree_results[tree_id]
                else:
                    status = "pending"

                if status == "affected":
                    color   = "#e74c3c"
                    symbol  = "✕"
                    tooltip = f"Tree {tree_id} — AFFECTED"
                elif status == "healthy":
                    color   = "#2ecc71"
                    symbol  = "✓"
                    tooltip = f"Tree {tree_id} — HEALTHY"
                else:
                    color   = "#bdc3c7"
                    symbol  = "?"
                    tooltip = f"Tree {tree_id} — PENDING"

                grid_html += f"""
                <td title="{tooltip}" style="
                    width:36px; height:36px;
                    background:{color};
                    border-radius:50%;
                    text-align:center;
                    vertical-align:middle;
                    font-size:16px;
                    font-weight:bold;
                    color:white;
                    cursor:pointer;
                    border: 2px solid rgba(0,0,0,0.1);
                ">{symbol}</td>
                """
            grid_html += "</tr>"

    gps_str = (
        f"{current_gps['lat']:.5f}, {current_gps['lon']:.5f}"
        if current_gps["fix"] else "No GPS Fix"
    )

    status_color = "#2ecc71" if done else "#e67e22"
    status_text  = "✅ Complete" if done else "⏳ In Progress"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgriNova — Farm Health Grid</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="5">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: Arial, sans-serif;
                background: #1a1a2e;
                color: white;
                padding: 20px;
            }}
            h1 {{
                text-align: center;
                color: #2ecc71;
                font-size: 26px;
                margin-bottom: 6px;
            }}
            .subtitle {{
                text-align: center;
                color: #aaa;
                font-size: 13px;
                margin-bottom: 20px;
            }}
            .stats {{
                display: flex;
                justify-content: center;
                gap: 16px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}
            .stat-box {{
                padding: 12px 20px;
                border-radius: 10px;
                text-align: center;
                min-width: 110px;
            }}
            .stat-box .num {{
                font-size: 28px;
                font-weight: bold;
            }}
            .stat-box .label {{
                font-size: 12px;
                margin-top: 2px;
            }}
            .grid-wrap {{
                overflow-x: auto;
                display: flex;
                justify-content: center;
            }}
            table {{
                border-collapse: separate;
                border-spacing: 6px;
            }}
            .legend {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 18px;
                font-size: 13px;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .legend-dot {{
                width: 16px;
                height: 16px;
                border-radius: 50%;
            }}
            .gps-bar {{
                text-align: center;
                margin-top: 14px;
                font-size: 12px;
                color: #aaa;
            }}
            .refresh-note {{
                text-align: center;
                margin-top: 8px;
                font-size: 11px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>🌿 AgriNova Farm Health</h1>
        <div class="subtitle">
            Grid: {GRID_ROWS} × {GRID_COLS} &nbsp;|&nbsp;
            Total Trees: {total} &nbsp;|&nbsp;
            Status: <span style="color:{status_color}">{status_text}</span>
        </div>

        <div class="stats">
            <div class="stat-box" style="background:#c0392b22; border:1px solid #e74c3c">
                <div class="num" style="color:#e74c3c">{affected}</div>
                <div class="label">🔴 Affected</div>
            </div>
            <div class="stat-box" style="background:#27ae6022; border:1px solid #2ecc71">
                <div class="num" style="color:#2ecc71">{healthy}</div>
                <div class="label">🟢 Healthy</div>
            </div>
            <div class="stat-box" style="background:#7f8c8d22; border:1px solid #bdc3c7">
                <div class="num" style="color:#bdc3c7">{pending}</div>
                <div class="label">⬜ Pending</div>
            </div>
            <div class="stat-box" style="background:#2980b922; border:1px solid #3498db">
                <div class="num" style="color:#3498db">{total}</div>
                <div class="label">🌳 Total</div>
            </div>
        </div>

        <div class="grid-wrap">
            <table>
                {grid_html}
            </table>
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-dot" style="background:#e74c3c"></div>
                Affected
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#2ecc71"></div>
                Healthy
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#bdc3c7"></div>
                Pending
            </div>
        </div>

        <div class="gps-bar">📍 GPS: {gps_str}</div>
        <div class="refresh-note">⟳ Auto-refreshes every 5 seconds</div>
    </body>
    </html>
    """
    return html

# ============================================================
# START
# ============================================================
gps = threading.Thread(target=gps_thread, daemon=True)
gps.start()

detect_thread = threading.Thread(target=capture_and_detect, daemon=True)
detect_thread.start()

print(f"\n🚀 Flask running on Raspberry Pi...")
print(f"   /video_feed        → live stream")
print(f"   /latest_detection  → latest detected frame")
print(f"   /detection_info    → latest pest JSON")
print(f"   /status            → system + GPS status")
print(f"   /log               → full geo log")
print(f"   /tree_health       → summary JSON")
print(f"   /farm_grid         → full grid JSON")
print(f"   /grid_view         → 🌿 VISUAL GRID WEBPAGE")
print(f"\n💡 TIP: Press Ctrl+C to stop scanning and send WhatsApp summary\n")

flask_app.run(host='0.0.0.0', port=8000, debug=False)
