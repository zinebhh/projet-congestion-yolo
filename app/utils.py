import csv
import os
from fpdf import FPDF
import os
import cv2




class Camera:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        # Encodage en JPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes() if ret else None

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

# Instance globale utilisée dans Flask
camera = Camera()

class Analyzer:
    def __init__(self):
        # Si tu utilises un vrai modèle YOLO, charge-le ici
        pass

    def process(self, frame_bytes):
        # Convertir les bytes JPEG en image OpenCV
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Exemple : dessine une boîte fictive pour simuler une détection
        height, width = frame.shape[:2]
        cv2.rectangle(frame, (50, 50), (width-50, height-50), (0, 255, 0), 2)
        cv2.putText(frame, "Objet détecté", (60, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        # Ré-encoder l'image en JPEG pour l'afficher
        ret, jpeg = cv2.imencode('.jpg', frame)
        return (jpeg.tobytes(), {'dummy_data': True}) if ret else (None, {})

# Instance globale utilisée dans Flask
analyzer = Analyzer()



def lire_csv(path):
    """
    Lit un fichier CSV et retourne une liste de dictionnaires.
    """
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [row for row in reader]

def generer_pdf(data, output_path="output/report.pdf"):
    """
    Génère un PDF à partir des données CSV.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Rapport de Trafic Routier", ln=True, align='C')
    pdf.ln(10)

    if not data:
        pdf.cell(200, 10, txt="Aucune donnée disponible.", ln=True)
    else:
        for row in data[:20]:  # Limité à 20 lignes
            text = f"ID: {row['ID']} | Type: {row['Classe']} | Vitesse: {row['Vitesse (px/s)']} px/s"
            pdf.cell(200, 10, txt=text, ln=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path
def get_camera_points():
    return [
        {
            "id": "cam1",
            "name": "Intersection 1",
            "lat": 33.589886,
            "lng": -7.603869,
            "url": "http://192.168.0.101:8080/video"  # Exemple de caméra
        },
        {
            "id": "cam2",
            "name": "Boulevard Zerktouni",
            "lat": 33.586532,
            "lng": -7.611334,
            "url": "http://192.168.0.102:8080/video"
        }
    ]
CAMERA_POINTS = [
    {"id": "cam1", "name": "Avenue Hassan II", "lat": 33.5898, "lng": -7.6038, "url": "http://195.200.199.8/mjpg/video.mjpg"},
    {"id": "cam2", "name": "Route de Casa", "lat": 33.5731, "lng": -7.5898, "url": "http://184.72.239.149/vod/mp4:BigBuckBunny_115k.mov"},
]
