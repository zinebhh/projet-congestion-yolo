from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import Counter
import cv2
import csv

# Charger modèle YOLO
model = YOLO('yolov8n.pt')

# Initialiser DeepSORT
tracker = DeepSort(max_age=30)

# Ouvrir vidéo
cap = cv2.VideoCapture("video.mp4")
frame_rate = cap.get(cv2.CAP_PROP_FPS)

# CSV pour stocker les résultats
csv_file = open("resultats.csv", mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["ID", "Classe", "Vitesse (px/s)", "Temps (s)", "X", "Y"])

# Structures de suivi
positions = {}  # {track_id: (x, y, frame)}
frame_num = 0

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

        # Calcul vitesse
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

        # Affichage sur la vidéo
        cv2.rectangle(frame, (int(l), int(t)), (int(r), int(b)), (0, 255, 0), 2)
        cv2.putText(frame, f"ID:{track_id} {cls_name} {int(speed)}px/s", (int(l), int(t) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # Calcul des indicateurs
    nb_vehicules = sum(compteur_types.values())
    vitesse_moyenne = sum(vitesses) / len(vitesses) if vitesses else 0
    surface_visible = frame.shape[0] * frame.shape[1]
    densite = nb_vehicules / surface_visible

    def evaluer_congestion(nb_vehicules, vitesse_moyenne):
        if nb_vehicules > 15 and vitesse_moyenne < 10:
            return "🚨 Congestion ÉLEVÉE"
        elif nb_vehicules > 10 and vitesse_moyenne < 20:
            return "⚠️ Congestion MOYENNE"
        else:
            return "🟢 Trafic FLUIDE"

    etat = evaluer_congestion(nb_vehicules, vitesse_moyenne)

    cv2.putText(frame, f"Etat: {etat}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow("YOLO + DeepSORT", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

    frame_num += 1

cap.release()
csv_file.close()
cv2.destroyAllWindows()
