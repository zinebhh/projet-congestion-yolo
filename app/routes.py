
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.user_model import User

main = Blueprint('main', __name__)

@main.route('/')
def dashboard():
    return render_template('dashboard/index.html')

@main.route('/login')
def login():
    return render_template('authentication/login.html')

@app.route('/analyse_camera', methods=['POST'])
def analyse_camera():
    cam_url = request.json.get('url')
    result = analyser_flux(cam_url)
    return jsonify(result)


routes = Blueprint('routes', __name__)
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        gender = request.form.get('gender')
        city = request.form.get('city')
        state = request.form.get('state')

        # Vérifie si email ou username déjà utilisé
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("Email ou nom d'utilisateur déjà utilisé.")
            return redirect(url_for('routes.register'))

        # Création utilisateur
        new_user = User(
            fullname=fullname,
            email=email,
            username=username,
            gender=gender,
            city=city,
            state=state
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Inscription réussie. Vous pouvez maintenant vous connecter.")
        return redirect(url_for('routes.register'))  # ou redirige vers page login

    return render_template('register.html')
