import secrets

from flask import current_app, render_template, send_from_directory, session

from app.routes import teleprompter_bp


def _page_context(is_operator: bool) -> dict:
    # The signed Flask session pairs the operator and display tabs in one browser.
    if "teleprompter_id" not in session or "teleprompter_token" not in session:
        session["teleprompter_id"] = secrets.token_urlsafe(24)
        session["teleprompter_token"] = secrets.token_urlsafe(32)
    return {
        "auth_token": session["teleprompter_token"],
        "teleprompter_id": session["teleprompter_id"],
        "is_operator": is_operator,
    }


@teleprompter_bp.route("/")
def index():
    return render_template("comando.html", **_page_context(True))


@teleprompter_bp.route("/comando")
def comando():
    return render_template("comando.html", **_page_context(True))


@teleprompter_bp.route("/tp")
def teleprompter():
    return render_template("tp.html", **_page_context(False))


@teleprompter_bp.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(current_app.static_folder, filename)
