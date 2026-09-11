import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from config import BASE_DIR, UPLOAD_DIR
from database import Database
from rule_engine import normalize_keywords

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def create_app(database: Database | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = secrets.token_hex(16)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    db = database or Database(BASE_DIR / "data" / "newaiseller.db")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def form_values(existing: dict | None = None, image_path: str | None = None) -> dict:
        cooldown_number = request.form.get("cooldown_number", "0", type=int)
        unit = request.form.get("cooldown_unit", "seconds")
        multiplier = {"seconds": 1, "minutes": 60, "hours": 3600}.get(unit, 1)
        return {
            "name": request.form.get("name", "").strip(),
            "keywords_list": normalize_keywords(request.form.get("keywords", "")),
            "match_type": request.form.get("match_type", "ANY_KEYWORD"),
            "reply_text": request.form.get("reply_text", ""),
            "image_path": image_path if image_path is not None else (existing or {}).get("image_path"),
            "send_text": "send_text" in request.form,
            "send_image": "send_image" in request.form,
            "enabled": "enabled" in request.form,
            "priority": request.form.get("priority", "0", type=int),
            "cooldown_seconds": max(0, cooldown_number) * multiplier,
        }

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html", stats=db.stats(), recent=db.recent_matches())

    @app.get("/rules")
    def rules():
        return render_template("rules.html", rules=db.list_rules())

    @app.route("/rules/new", methods=["GET", "POST"])
    def new_rule():
        if request.method == "GET":
            return render_template("edit_rule.html", rule=None)
        values = form_values()
        if not values["name"] or not values["keywords_list"]:
            flash("Name and at least one keyword are required.", "error")
            return render_template("edit_rule.html", rule=values), 400
        values["image_path"] = save_upload(None)
        db.save_rule(values)
        flash("Rule created.", "success")
        return redirect(url_for("rules"))

    @app.route("/rules/<int:rule_id>/edit", methods=["GET", "POST"])
    def edit_rule(rule_id: int):
        rule = db.get_rule(rule_id)
        if rule is None:
            return "Rule not found", 404
        if request.method == "GET":
            return render_template("edit_rule.html", rule=rule)
        image_path = None if "remove_image" in request.form else rule.get("image_path")
        uploaded = save_upload(rule.get("image_path"))
        if uploaded:
            image_path = uploaded
        if "remove_image" in request.form and rule.get("image_path"):
            delete_image(rule["image_path"])
        values = form_values(rule, image_path)
        if not values["name"] or not values["keywords_list"]:
            flash("Name and at least one keyword are required.", "error")
            return render_template("edit_rule.html", rule={**rule, **values}), 400
        db.save_rule(values, rule_id)
        flash("Rule updated.", "success")
        return redirect(url_for("rules"))

    @app.post("/rules/<int:rule_id>/toggle")
    def toggle_rule(rule_id: int):
        rule = db.get_rule(rule_id)
        if rule:
            rule["enabled"] = not bool(rule["enabled"])
            db.save_rule(rule, rule_id)
        return redirect(url_for("rules"))

    @app.post("/rules/<int:rule_id>/delete")
    def delete_rule(rule_id: int):
        rule = db.get_rule(rule_id)
        if rule and rule.get("image_path"):
            delete_image(rule["image_path"])
        db.delete_rule(rule_id)
        return redirect(url_for("rules"))

    def save_upload(old_path: str | None) -> str | None:
        upload = request.files.get("image")
        if not upload or not upload.filename:
            return None
        extension = Path(upload.filename).suffix.lower().lstrip(".")
        if extension not in ALLOWED_EXTENSIONS:
            flash("Only JPG, JPEG, PNG, and WEBP images are allowed.", "error")
            return old_path
        upload.stream.seek(0, os.SEEK_END)
        if upload.stream.tell() > MAX_UPLOAD_BYTES:
            flash("Image must be 10 MB or smaller.", "error")
            return old_path
        upload.stream.seek(0)
        filename = f"{secrets.token_hex(16)}.{secure_filename(extension)}"
        destination = UPLOAD_DIR / filename
        upload.save(destination)
        if old_path:
            delete_image(old_path)
        return str(Path("static") / "uploads" / filename)

    def delete_image(path: str) -> None:
        candidate = BASE_DIR / path
        if candidate.parent.resolve() == UPLOAD_DIR.resolve() and candidate.is_file():
            candidate.unlink()

    return app
