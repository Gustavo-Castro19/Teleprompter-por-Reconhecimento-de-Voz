from flask import render_template, current_app, send_from_directory
from app.routes import teleprompter_bp


@teleprompter_bp.route("/")
def index():
    return render_template("comando.html")


@teleprompter_bp.route("/comando")
def comando():
    return render_template("comando.html")


@teleprompter_bp.route("/tp")
def teleprompter():
    return render_template("tp.html")


@teleprompter_bp.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(current_app.static_folder, filename)