from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import base64
import os

app = Flask(__name__)

# ============================================================
# STEP 1: Change this to your actual model path
# Example: "C:/Users/YourName/yolo/best.pt"
# ============================================================
MODEL_PATH = "C:/Users/anilk/Downloads/best (1).pt"

print(f"Loading model from: {MODEL_PATH}")
model = YOLO(MODEL_PATH)
print("Model loaded successfully!")


@app.route("/detect", methods=["POST"])
def detect():
    try:
        # ---- Get image from request ----
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        file = request.files["image"]
        image_bytes = file.read()

        # ---- Convert to OpenCV format ----
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "Could not read image"}), 400

        orig_h, orig_w = img.shape[:2]

        # ---- Run YOLOv8 inference ----
        results = model(img, conf=0.25)

        detections = []
        annotated = img.copy()

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                # Bounding box coords (pixel values)
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                pest_name = model.names[cls_id]

                detections.append({
                    "pest_name": pest_name,
                    "confidence": round(conf * 100, 1),   # e.g. 87.3
                    "bbox": {
                        "x1": x1, "y1": y1,
                        "x2": x2, "y2": y2,
                        "width": x2 - x1,
                        "height": y2 - y1
                    }
                })

                # Draw on annotated image
                color = (0, 200, 50)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                label = f"{pest_name} {conf*100:.1f}%"
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(annotated, (x1, y1 - lh - 10), (x1 + lw + 6, y1), color, -1)
                cv2.putText(annotated, label, (x1 + 3, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # ---- Encode annotated image to base64 ----
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({
            "success": True,
            "total_detections": len(detections),
            "detections": detections,
            "annotated_image": img_base64,   # Base64 JPEG with boxes drawn
            "image_width": orig_w,
            "image_height": orig_h
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_PATH})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
