import os
import uuid
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from . import db
from .models import User, Memory, Highlight

main_bp = Blueprint("main", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MEMORY_CATEGORIES = ("School", "Class", "Event", "Trip", "Graduation", "Reunion", "Random", "Other")


def _matches_image_signature(ext, header):
    if ext == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if ext == "webp":
        return header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


def save_upload(file):
    """Store a UUID-named image only when its bytes match an allowed image type."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    stream = file.stream
    try:
        original_position = stream.tell()
        header = stream.read(12)
        stream.seek(original_position)
    except (AttributeError, OSError):
        return None
    if not _matches_image_signature(ext, header):
        return None

    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename

@main_bp.route("/")
def home():
    memories = Memory.query.filter_by(status="approved").order_by(Memory.created_at.desc()).limit(12).all()
    alumni = User.query.order_by(User.full_name).limit(24).all()
    return render_template("index.html", memories=memories, alumni=alumni)

@main_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)

@main_bp.route("/alumni")
def alumni():
    q = request.args.get("q", "").strip()
    generation = request.args.get("generation", "").strip()
    class_name = request.args.get("class_name", "").strip()
    graduation_year = request.args.get("graduation_year", "").strip()

    query = User.query
    if q:
        query = query.filter(User.full_name.ilike(f"%{q}%"))
    if generation:
        query = query.filter(User.generation == generation)
    if class_name:
        query = query.filter(User.class_name == class_name)

    if graduation_year:
        try:
            graduation_year = int(graduation_year)
        except ValueError:
            graduation_year = ""
        else:
            query = query.filter(User.graduation_year == graduation_year)

    generations = [value for (value,) in db.session.query(User.generation)
                   .filter(User.generation.isnot(None), User.generation != "")
                   .distinct().order_by(User.generation).all()]
    classes = [value for (value,) in db.session.query(User.class_name)
               .filter(User.class_name.isnot(None), User.class_name != "")
               .distinct().order_by(User.class_name).all()]
    graduation_years = [value for (value,) in db.session.query(User.graduation_year)
                        .filter(User.graduation_year.isnot(None))
                        .distinct().order_by(User.graduation_year.desc()).all()]

    return render_template(
        "alumni.html",
        alumni=query.order_by(User.full_name).all(),
        q=q,
        generation=generation,
        class_name=class_name,
        graduation_year=graduation_year,
        generations=generations,
        classes=classes,
        graduation_years=graduation_years,
        total_count=User.query.count(),
        hub_crew=User.query.order_by(User.full_name).limit(6).all(),
    )

@main_bp.route("/alumni/<int:user_id>")
def profile_public(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return "Not found", 404
    memories = Memory.query.filter_by(user_id=user.id, status="approved").order_by(Memory.created_at.desc()).all()
    return render_template("profile.html", user=user, memories=memories, public=True)

@main_bp.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)
    pending_memories = Memory.query.filter_by(status="pending").order_by(Memory.created_at.asc()).all()
    return render_template(
        "admin.html",
        pending_memories=pending_memories,
        pending_count=len(pending_memories),
        alumni_count=User.query.filter_by(role="alumni").count(),
        approved_memory_count=Memory.query.filter_by(status="approved").count(),
    )


@main_bp.route("/admin/memories/<int:memory_id>/review", methods=["POST"])
@login_required
def review_memory(memory_id):
    if not current_user.is_admin:
        abort(403)

    memory = db.session.get(Memory, memory_id)
    if memory is None:
        abort(404)

    action = request.form.get("action", "")
    if memory.status != "pending" or action not in {"approve", "reject"}:
        flash("This memory is no longer awaiting review.", "error")
        return redirect(url_for("main.admin"))

    memory.status = "approved" if action == "approve" else "rejected"
    db.session.commit()
    flash("Memory approved." if action == "approve" else "Memory rejected.", "success")
    return redirect(url_for("main.admin"))


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        f = request.form
        full_name = f.get("full_name", "").strip()
        if not full_name or len(full_name) > 120:
            flash("Enter a name between 1 and 120 characters.", "error")
            return redirect(url_for("main.profile"))

        try:
            entry_year = int(f["entry_year"]) if f.get("entry_year") else None
            graduation_year = int(f["graduation_year"]) if f.get("graduation_year") else None
            university_year = int(f["university_year"]) if f.get("university_year") else None
            for value in (entry_year, graduation_year, university_year):
                if value is not None and not 1900 <= value <= 2100:
                    raise ValueError
        except ValueError:
            flash("Enter valid years between 1900 and 2100.", "error")
            return redirect(url_for("main.profile"))

        current_user.full_name = full_name
        current_user.class_name = f.get("class_name", "").strip()
        current_user.generation = f.get("generation", "").strip()
        current_user.bio = f.get("bio", "").strip()
        current_user.city = f.get("city", "").strip()
        current_user.occupation = f.get("occupation", "").strip()
        current_user.university = f.get("university", "").strip()
        current_user.major = f.get("major", "").strip()
        current_user.instagram = f.get("instagram", "").strip()
        current_user.github = f.get("github", "").strip()
        current_user.linkedin = f.get("linkedin", "").strip()
        current_user.entry_year = entry_year
        current_user.graduation_year = graduation_year
        current_user.university_year = university_year

        photo = save_upload(request.files.get("profile_photo"))
        if photo:
            current_user.profile_photo = photo

        db.session.commit()
        flash("Profil berhasil diperbarui.", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html", user=current_user, memories=current_user.memories, public=False)

@main_bp.route("/profile/highlight", methods=["POST"])
@login_required
def add_highlight():
    image = save_upload(request.files.get("image"))
    h = Highlight(
        owner=current_user,
        title=request.form.get("title", "").strip(),
        description=request.form.get("description", "").strip(),
        image=image,
    )
    db.session.add(h)
    db.session.commit()
    return redirect(url_for("main.profile"))

@main_bp.route("/memory/new", methods=["GET", "POST"])
@login_required
def add_memory():
    if request.method == "GET":
        return render_template("memory_upload.html", categories=MEMORY_CATEGORIES)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    category = request.form.get("category", "Other")
    year_raw = request.form.get("year", "").strip()

    if not title or len(title) > 160:
        flash("Enter a memory title between 1 and 160 characters.", "error")
        return redirect(url_for("main.add_memory"))
    if len(description) > 5000 or len(location) > 160:
        flash("Description or location is too long.", "error")
        return redirect(url_for("main.add_memory"))
    if category not in MEMORY_CATEGORIES:
        flash("Choose a valid memory category.", "error")
        return redirect(url_for("main.add_memory"))

    year = None
    if year_raw:
        try:
            year = int(year_raw)
        except ValueError:
            flash("Enter a valid year between 1900 and 2100.", "error")
            return redirect(url_for("main.add_memory"))
        if not 1900 <= year <= 2100:
            flash("Enter a valid year between 1900 and 2100.", "error")
            return redirect(url_for("main.add_memory"))

    image_file = request.files.get("image")
    image = save_upload(image_file)
    if image_file and image_file.filename and not image:
        flash("Choose a PNG, JPG, or WebP image with matching image content.", "error")
        return redirect(url_for("main.add_memory"))

    memory = Memory(
        uploader=current_user,
        title=title,
        description=description,
        year=year,
        location=location,
        category=category,
        image=image,
        status="pending",
    )
    db.session.add(memory)
    db.session.commit()
    flash("Memory submitted and is waiting for admin review.", "success")
    return redirect(url_for("main.profile"))

@main_bp.route("/memories")
def memories():
    q = request.args.get("q", "").strip()
    query = Memory.query.filter_by(status="approved")
    if q:
        query = query.filter(
            db.or_(
                Memory.title.ilike(f"%{q}%"),
                Memory.description.ilike(f"%{q}%"),
                Memory.location.ilike(f"%{q}%")
            )
        )
    return render_template("memories.html", memories=query.order_by(Memory.created_at.desc()).all(), q=q)

@main_bp.route("/galaxy")
def galaxy():
    alumni = User.query.order_by(User.full_name).all()
    return render_template("galaxy.html", alumni=alumni)

@main_bp.route("/timeline")
def timeline():
    return render_template("timeline.html")
