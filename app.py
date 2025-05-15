import os
import uuid
import cv2
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, redirect, url_for, request, flash, jsonify,
    send_from_directory, Response,send_file)
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user, login_required,
    current_user, UserMixin)
from camera import VideoCamera
from ultralytics import YOLO
from collections import Counter
from fpdf import FPDF

from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw
from datetime import datetime, timedelta
from app.processor import detect_stream, TrafficAnalyzer, Analyzer, analyser_video
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import shutil
from urllib.request import urlretrieve
from pytube import YouTube
import yt_dlp
from difflib import SequenceMatcher
from app.utils import camera,analyzer   # ou ton objet de capture




# ------------------- CONFIGURATION -------------------

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Définition des chemins
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "outputs")
ANNOTATED_FOLDER = os.path.join(BASE_DIR, "static", "annotated")


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ANNOTATED_FOLDER, exist_ok=True)

# Configuration Flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['STATIC_FOLDER'] = 'static'
app.config['ANNOTATED_FOLDER'] = ANNOTATED_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/python/project-root/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
os.makedirs(os.path.join(BASE_DIR, 'app'), exist_ok=True)
db_path = os.path.join(BASE_DIR, 'app', 'database.db')
if not os.path.exists(db_path):
    open(db_path, 'a').close()  # crée un fichier vide si absent

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)



# ------------------- MODELS -------------------

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # correspond au nom de la table SQLite

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    fullname = db.Column(db.String(150))
    gender = db.Column(db.String(20))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class video_analysees(db.Model):
    __tablename__ = 'video_analysees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    filename = db.Column(db.String(255))
    result_path = db.Column(db.String(255))
    type = db.Column(db.String(10))
    analysis_date = db.Column(db.DateTime)
    nb_vehicules = db.Column(db.Integer)
    vitesse_moyenne = db.Column(db.Float)
    etat = db.Column(db.String(50))






# ------------------- LOGIN -------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------- ROUTES -------------------
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/search')
def search():
    query = request.args.get('q', '').lower()

    # Données simulées (à remplacer par tes vraies vidéos/rapports)
    fake_data = [
        {'type': 'vidéo', 'title': 'Trafic Casablanca', 'url': '/videos/1'},
        {'type': 'vidéo', 'title': 'Caméra Marrakech', 'url': '/videos/2'},
        {'type': 'rapport', 'title': 'Rapport Avril 2025', 'url': '/reports/avril2025'},
        {'type': 'rapport', 'title': 'Résumé Congestion 2024', 'url': '/reports/2024-summary'},
    ]

    # Fonction pour mesurer la similarité entre la requête et chaque titre
    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()

    # Calcul et tri des résultats
    sorted_results = sorted(
        fake_data,
        key=lambda item: similarity(query, item['title'].lower()),
        reverse=True
    )

    return render_template('search_results.html', query=query, results=sorted_results)

@app.route('/notifications')
def notifications():
    # Exemple statique – tu peux connecter à une DB
    notifications = [
        {"title": "Nouvelle Vidéo Analysée", "text": "Votre rapport est prêt au téléchargement.", "img": "/static/vendors/images/img.jpg"},
        {"title": "Caméra en direct", "text": "Une activité inhabituelle détectée.", "img": "/static/vendors/images/photo1.jpg"},
    ]
    return jsonify(notifications)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Identifiants incorrects", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Compte créé avec succès !")
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/changer_mot_de_passe', methods=['GET', 'POST'])
@login_required
def changer_mot_de_passe():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('changer_mot_de_passe'))

        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash("Mot de passe mis à jour avec succès.", "success")
        return redirect(url_for('dashboard'))

    return render_template("changer_mot_de_passe.html")


@app.route('/dashboard')
@login_required
def dashboard():    
    # Récupération de toutes les analyses de l'utilisateur, triées par date
    all_analyses = video_analysees.query.filter_by(user_id=current_user.id).order_by(video_analysees.analysis_date.desc()).all()


    # Récupération uniquement des analyses des 3 derniers jours
    three_days_ago = datetime.now() - timedelta(days=3)
    recent_analyses = [
        {
            "date": a.analysis_date.strftime("%Y-%m-%d %H:%M"),
            "type": a.type,
            "nb_vehicules": a.nb_vehicules,
            "vitesse_moyenne": a.vitesse_moyenne,
            "etat": a.etat
        }
        for a in all_analyses if a.analysis_date >= three_days_ago
    ]

    # Statistiques globales
    stats = {
        "videos_analysees": sum(1 for a in all_analyses if a.type == "video"),
        "images_analysees": sum(1 for a in all_analyses if a.type == "image"),
        "alertes_congestion": sum(1 for a in all_analyses if a.etat.lower() == "congestion"),
        "utilisateurs_actifs": 1  # ou plus si tu veux gérer une vraie statistique globale
    }

    # Liste des caméras à afficher sur la carte
    carte_points = [
        {
            "id": "cam1",
            "name": "Caméra Live - Berlin",
            "lat": 52.52,
            "lng": 13.405,
            "url": "http://91.191.213.70/mjpg/video.mjpg"
        },
        {
            "id": "cam2",
            "name": "Caméra Live - Casablanca",
            "lat": 33.5898,
            "lng": -7.6038,
            "url": "http://213.230.113.4:81/mjpg/video.mjpg"
        }
    ]

    return render_template(
        "dashboard.html",
        name=current_user.username or current_user.email, 
        stats=stats,
        recent_analyses=recent_analyses,
        carte_points=carte_points
    )
@app.route('/analyse-video', methods=['GET', 'POST'])
@login_required
def analyse_video():
    if request.method == 'POST':
        file = request.files['video']
        filename = secure_filename(file.filename)
        input_path = os.path.join('static/videos', filename)
        output_path = os.path.join('static/videos', f"processed_{filename}")
        file.save(input_path)

        stats = analyser_video(input_path, output_path)


        # Conversion pour compatibilité HTML5
        output_filename = os.path.basename(output_path)
        fixed_output_filename = f"fixed_{output_filename}"

        fixed_output_path = os.path.join(app.config['OUTPUT_FOLDER'], fixed_output_filename)
        ffmpeg_cmd = f'ffmpeg -y -i "{output_path}" -vcodec libx264 -acodec aac "{fixed_output_path}"'
        os.system(ffmpeg_cmd)

      

        # Enregistrement en base de données
        db.session.add(video_analysees(
        user_id=current_user.id,
        filename=filename,
        analysis_date=datetime.now(),  # N'oubliez pas cette ligne sinon la colonne ne sera pas remplie
        type="video",
        nb_vehicules=stats.get('vehicles', 0),
        vitesse_moyenne=stats.get('average_speed', 0.0),
        etat=stats.get('congestion', "Non défini"),
        result_path=fixed_output_path

    ))

        db.session.commit()

        # Génération PDF
        rapport_pdf = f"{fixed_output_filename.replace('.mp4', '')}_rapport.pdf"
        rapport_path = os.path.join(app.config['OUTPUT_FOLDER'], rapport_pdf)
        generer_rapport_pdf(stats, rapport_path)

        return render_template("analyse_video.html",
                               video_path=fixed_output_filename,
                               stats=stats,
                               rapport_pdf=rapport_pdf)

    return render_template("analyse_video.html")



def generer_rapport_pdf(stats, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Rapport d'Analyse de la Vidéo", ln=True, align='C')
    pdf.ln(10)
    for key, val in stats.items():
        pdf.cell(200, 10, txt=f"{key.replace('_', ' ').capitalize()} : {val}", ln=True)
    pdf.output(output_path)

model = YOLO("yolov5s.pt")

@app.route("/analyse-image", methods=["GET", "POST"])
@login_required
def analyse_image():
    if request.method == "POST":
        file = request.files.get("image")
        if not file:
            flash("Aucune image téléchargée.", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(input_path)

        # Détection avec YOLO
        results = model(input_path)[0]
        image = Image.open(input_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        vehicle_classes = ['car', 'bus', 'truck', 'motorbike']
        vehicles_detected = 0

        for r in results.boxes.data.tolist():
            x1, y1, x2, y2, conf, cls = r
            class_name = model.names[int(cls)]
            if class_name in vehicle_classes:
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
                draw.text((x1, y1 - 10), class_name, fill="red")
                vehicles_detected += 1

        # Sauvegarde image annotée
        output_filename = f"annotated_{filename}"
        output_path = os.path.join(app.config["ANNOTATED_FOLDER"], output_filename)
        image.save(output_path)

        # Déterminer l'état de congestion
        etat = "Congestion" if vehicles_detected > 10 else "Fluide"

        # Sauvegarde en base de données
        db.session.add(video_analysees(
            user_id=current_user.id,
            filename=filename,
            analysis_date=datetime.now(),
            type="image",
            nb_vehicules=vehicles_detected,
            vitesse_moyenne=0.0,
            etat=etat,
            result_path=output_path
        ))
        db.session.commit()

        # Statistiques à afficher
        stats = {
            "vehicles": vehicles_detected,
            "average_speed": "N/A",
            "congestion": etat
        }

        return render_template("analyse_image.html", image_path=output_filename, stats=stats)

    return render_template("analyse_image.html")


@app.route('/outputs/<path:filename>')
def serve_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

def generate_image_report(path, objects, stats):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "Rapport d'analyse d'image")
    y -= 1.5 * cm

    # Résumé
    c.setFont("Helvetica", 12)
    for key, value in stats.items():
        c.drawString(2 * cm, y, f"{key} : {value}")
        y -= 0.7 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Détails des objets détectés")
    y -= 1 * cm

    c.setFont("Helvetica", 10)
    max_items = 50
    for i, obj in enumerate(objects):
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 10)
        if i >= max_items:
            c.drawString(2 * cm, y, f"... et {len(objects) - max_items} objets supplémentaires non affichés.")
            break
        print(objects)  # pour voir la structure exacte

        c.drawString(
        2 * cm,
        y,
        f"{i+1}. Type: {obj.get('class', 'Inconnu')} | Confiance: {obj.get('confidence', 0):.2f} | Position: {obj.get('bbox', [])}"
    )
        y -= 0.6 * cm

    c.save()




@app.route("/telechargement-lien", methods=["GET", "POST"])
@login_required
def telechargement_lien():
    if request.method == "POST":
        url = request.form.get("url")

        if not url:
            return render_template("telechargement_lien.html", error="Lien invalide.")

        try:
            if "youtube.com" not in url and "youtu.be" not in url:
                raise ValueError("Le lien fourni n'est pas une URL YouTube valide.")

            yt = YouTube(url)
            stream = yt.streams.get_highest_resolution()

            if not stream:
                raise ValueError("Aucun flux vidéo disponible pour ce lien.")

            # 👇 Ces lignes doivent être ici, dans la fonction
            unique_id = uuid.uuid4().hex
            video_filename = f"{unique_id}.mp4"
            video_path = os.path.join(app.config["UPLOAD_FOLDER"], video_filename)

            stream.download(output_path=app.config["UPLOAD_FOLDER"], filename=video_filename)

            # Traitement YOLO
            processed_path, objects, stats = process_video_with_yolo(video_path, unique_id)

            # Génération rapport
            report_filename = f"rapport_video_{unique_id}.pdf"
            report_path = os.path.join(app.config["STATIC_FOLDER"], "reports", report_filename)
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            generate_video_report(report_path, objects, stats)

            return render_template(
                "telechargement_lien.html",
                video_path=url_for("static", filename=f"processed/{os.path.basename(processed_path)}"),
                report_path=url_for("static", filename=f"reports/{report_filename}"),
                video_name=video_title
            )

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return render_template("telechargement_lien.html", error=f"Erreur : {str(e)}")

    return render_template("telechargement_lien.html")



def process_video_with_yolo(input_path, unique_id):
    output_path = os.path.join("static/processed", f"processed_{unique_id}.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    model = YOLO("yolov5s.pt")
    results = model(input_path, save=True, save_txt=False)

    # Analyse des objets
    objects = []
    stats = {}

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls)
            class_name = model.names[class_id]
            conf = float(box.conf)
            objects.append({"class": class_name, "conf": conf})
            stats[class_name] = stats.get(class_name, 0) + 1

    # Récupérer la vidéo annotée
    annotated_video_path = os.path.join("runs", "detect", "predict", os.path.basename(input_path))
    shutil.move(annotated_video_path, output_path)

    return output_path, objects, stats





def generate_video_report(report_path, objects, stats):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Rapport d'analyse vidéo", ln=True, align="C")
    pdf.ln(10)

    pdf.cell(200, 10, txt="Résumé des objets détectés :", ln=True)
    for cls, count in stats.items():
        pdf.cell(200, 10, txt=f"{cls}: {count}", ln=True)

    pdf.output(report_path)


@app.route("/camera-direct")
@login_required
def camera_direct():
    return render_template("camera_direct.html")
@app.route('/analyse_carte')
@login_required
def analyse_carte():
    points = [
        {"id": "cam1", "name": "Avenue Hassan II", "lat": 33.5898, "lng": -7.6038, "url": "http://195.200.199.8/mjpg/video.mjpg"},
        {"id": "cam2", "name": "Route de Casa", "lat": 33.5731, "lng": -7.5898, "url": "http://184.72.239.149/vod/mp4:BigBuckBunny_115k.mov"},
        {"id": "cam3", "name": "Boulevard Zerktouni", "lat": 33.5800, "lng": -7.6100, "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"},
        {"id": "cam4", "name": "Place des Nations Unies", "lat": 33.5940, "lng": -7.6020, "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4"},
    ]
    return render_template("analyse_carte.html", points=points)


@app.route('/detect-stream')
@login_required
def detect_stream():
    url = request.args.get("url")
    return redirect(url)
@app.route('/generate-report')
@login_required
def generate_report():
    # Exemple : générer un fichier PDF ou HTML statique
    return send_file('static/rapport_demo.pdf', as_attachment=True)
def create_dummy_pdf(path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Rapport de démonstration", ln=True, align='C')
    pdf.output(path)

create_dummy_pdf("static/rapport_demo.pdf")


@app.route("/profile")
@login_required
def profile():
    videos = video_analysees.query.filter_by(user_id=current_user.id).order_by(video_analysees.analysis_date.desc()).all()
    for video in videos:
        if video.analysis_date is None:
            video.analysis_date = "Non disponible"  # ou datetime.now(), selon le besoin

    return render_template("profile.html", user=current_user, videos=videos)



@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Simule un lien de reset, ex : /reset-password/<user_id>
            flash("Un lien de réinitialisation a été envoyé à votre adresse email.", "success")
            return redirect(url_for('changer_mot_de_passe', user_id=user.id))
        else:
            flash("Aucun compte trouvé avec cet email.", "danger")
    return render_template('forgot-password.html')

@app.route('/changer_mot_de_passe/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    # Logique pour afficher le formulaire de réinitialisation et traiter la nouvelle saisie du mot de passe
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(request.url)

        user = User.query.get(user_id)
        if user:
            user.set_password(new_password)  # Assure-toi que tu as une méthode set_password
            db.session.commit()
            flash("Password updated successfully", "success")
            return redirect(url_for('login'))
        else:
            flash("User not found", "danger")
            return redirect(url_for('forgot_password'))

    return render_template('changer_mot_de_passe.html', user_id=user_id)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
            processed_frame, data = analyzer.process(frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + processed_frame + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stats')
def stats():
    return jsonify(analyzer.get_statistics())
@app.route('/formation')
@login_required
def formation():
   return render_template('formation.html')

# ------------------- DB INIT + RUN -------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="admin@example.com").first():
        hashed_pw = generate_password_hash("admin123")
        user = User(username="Admin", email="admin@example.com", password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        print("Utilisateur admin créé : admin@example.com / admin123")

if __name__ == '__main__':
    app.run(debug=True)
