import torch
import cv2
import numpy as np
from PIL import Image
from werkzeug.datastructures import FileStorage
import os
import uuid
import subprocess
from app.utils import Analyzer  # Ton module de détection (YOLO)
from datetime import datetime
from ultralytics import YOLO 

from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import Counter
import cv2
import csv

# Charger le modèle YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', force_reload=False)
model.eval()




def analyser_video(input_path, output_path):
    model = YOLO('yolov8n.pt')
    tracker = DeepSort(max_age=30)

    cap = cv2.VideoCapture(input_path)
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), frame_rate, (width, height))

    csv_path = os.path.splitext(output_path)[0] + "_resultats.csv"
    csv_file = open(csv_path, mode='w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["ID", "Classe", "Vitesse (px/s)", "Temps (s)", "X", "Y"])

    positions = {}
    frame_num = 0
    total_vehicles = 0
    all_speeds = []
    last_counts = Counter()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        detections = model(frame)[0]
        dets = []

        for d in detections.boxes:
            x1, y1, x2, y2 = map(int, d.xyxy[0])
            conf = float(d.conf[0])
            cls = int(d.cls[0])
            dets.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))

        tracks = tracker.update_tracks(dets, frame=frame)
        compteur_types = Counter()
        vitesses = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            l, t, r, b = track.to_ltrb()
            x_center = int((l + r) / 2)
            y_center = int((t + b) / 2)

            if track_id in positions:
                prev_x, prev_y, prev_frame = positions[track_id]
                dist = ((x_center - prev_x) ** 2 + (y_center - prev_y) ** 2) ** 0.5
                time_diff = (frame_num - prev_frame) / frame_rate
                speed = dist / time_diff if time_diff > 0 else 0
            else:
                speed = 0

            positions[track_id] = (x_center, y_center, frame_num)
            cls_name = model.names[track.det_class]
            compteur_types[cls_name] += 1
            vitesses.append(speed)

            timestamp = frame_num / frame_rate
            csv_writer.writerow([track_id, cls_name, round(speed, 2), round(timestamp, 2), x_center, y_center])

            cv2.rectangle(frame, (int(l), int(t)), (int(r), int(b)), (0, 255, 0), 2)
            cv2.putText(frame, f"ID:{track_id} {cls_name} {int(speed)}px/s", (int(l), int(t) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        nb_vehicules = sum(compteur_types.values())
        vitesse_moyenne = sum(vitesses) / len(vitesses) if vitesses else 0
        surface_visible = frame.shape[0] * frame.shape[1]
        densite = nb_vehicules / surface_visible

        def evaluer_congestion(n, v):
            if n > 15 and v < 10:
                return "🚨 Congestion ÉLEVÉE"
            elif n > 10 and v < 20:
                return "⚠️ Congestion MOYENNE"
            else:
                return "🟢 Trafic FLUIDE"

        etat = evaluer_congestion(nb_vehicules, vitesse_moyenne)
        cv2.putText(frame, f"Etat: {etat}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        out.write(frame)
        frame_num += 1
        all_speeds.extend(vitesses)
        last_counts.update(compteur_types)

    cap.release()
    csv_file.close()
    out.release()
    cv2.destroyAllWindows()

    nb_total = sum(last_counts.values())
    vitesse_moy = sum(all_speeds) / len(all_speeds) if all_speeds else 0
    etat_final = evaluer_congestion(nb_total, vitesse_moy)

    return {
        "vehicles": nb_total,
        "average_speed": round(vitesse_moy, 2),
        "congestion": etat_final,
        "csv_path": csv_path,
        "video_path": output_path
    }


def detect_image_objects(file_storage: FileStorage):
    """
    Prend une image envoyée via formulaire Flask et retourne les objets détectés.
    """
    image = Image.open(file_storage.stream).convert('RGB')
    results = model(image)

    objects_detected = []
    for *box, conf, cls in results.xyxy[0]:
        label = model.names[int(cls)]
        objects_detected.append({
            "label": label,
            "confidence": float(conf)
        })

    # Sauvegarder l'image annotée dans /static/
    annotated_img = results.render()[0]  # BGR numpy array
    filename = f"{uuid.uuid4().hex}.jpg"
    output_path = os.path.join("static", "outputs", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, annotated_img)

    return objects_detected, output_path



def analyser_flux_video(url, camera_id):
    cap = cv2.VideoCapture(url)
    vehicle_counts = []
    speeds = []
    distances = []

    t_start = time.time()
    frame_skip = 5  # pour sauter des frames et éviter surcharge

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret or frame_count > 200:  # 200 frames max
            break
        if frame_count % frame_skip != 0:
            frame_count += 1
            continue

        results = model(frame)
        detections = results.xyxy[0]

        count = 0
        frame_speeds = []
        frame_distances = []

        for *box, conf, cls in detections:
            label = model.names[int(cls)]
            if label in ['car', 'truck', 'motorbike', 'bus']:
                count += 1
                # Dummy estimation — à remplacer par distance réelle + tracking
                frame_speeds.append(np.random.uniform(20, 70))  
                frame_distances.append(np.random.uniform(5, 30))

        vehicle_counts.append(count)
        speeds += frame_speeds
        distances += frame_distances

        frame_count += 1

    cap.release()
    t_end = time.time()

    return {
        'camera_id': camera_id,
        'vehicle_count': sum(vehicle_counts) // len(vehicle_counts) if vehicle_counts else 0,
        'avg_speed': round(np.mean(speeds), 2) if speeds else 0,
        'avg_distance': round(np.mean(distances), 2) if distances else 0,
        'duration': round(t_end - t_start, 2)
    }

def analyser_flux(url):
    cap = cv2.VideoCapture(url)
    count = 0
    vehicle_count = 0
    total_speed = 0
    tracked_objects = {}  # Pour calculer la vitesse plus tard

    while count < 300:  # Limiter l’analyse à ~10 sec
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        detections = results.xyxy[0]

        for *box, conf, cls in detections:
            label = model.names[int(cls)]
            if label in ['car', 'truck', 'bus', 'motorbike']:
                vehicle_count += 1
                # TODO: ajouter calcul vitesse avec tracking + temps

        count += 1

    cap.release()
    return {
        "vehicles": vehicle_count,
        "average_speed": total_speed / max(1, vehicle_count),  # à implémenter
        "congestion": "Élevée" if vehicle_count > 20 else "Modérée"
    }

models = YOLO("yolov8n.pt") 

def detect_stream(video_url):
    cap = cv2.VideoCapture(video_url)

    if not cap.isOpened():
        print("Erreur : Impossible d’ouvrir le flux vidéo.")
        return

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Erreur : Lecture frame échouée.")
            break

        try:
            results = models.predict(frame, imgsz=640, conf=0.4, verbose=False)
            annotated_frame = results[0].plot()

            _, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print("Erreur de traitement :", e)
            break

    cap.release()
class TrafficAnalyzer:
    def __init__(self):
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.model.conf = 0.4
        self.stats = {"vehicles": 0, "cars": 0, "trucks": 0, "motos": 0}

    def process(self, frame_bytes):
        # Décodage
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # YOLO inference
        results = self.model(frame)
        labels, cords = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]

        # Comptage
        vehicles = 0
        for i in range(len(labels)):
            cls = int(labels[i])
            name = self.model.names[cls]
            if name in ["car", "truck", "bus", "motorbike"]:
                vehicles += 1
                # Dessin
                x1, y1, x2, y2 = cords[i][:4]
                h, w = frame.shape[:2]
                x1, y1, x2, y2 = int(x1*w), int(y1*h), int(x2*w), int(y2*h)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                cv2.putText(frame, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)

        self.stats["vehicles"] = vehicles

        # Encode frame for MJPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes(), self.stats

    def get_statistics(self):
        return self.stats