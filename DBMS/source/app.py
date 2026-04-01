import os
import sys
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps

import config
import database


app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)


def login_required(f):
    """Decorator to protect routes that need authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    """Check if a file extension is allowed."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def format_file_size(size_bytes):
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"



app.jinja_env.globals.update(
    format_file_size=format_file_size,
    categories=config.CATEGORIES,
    now=datetime.now
)




@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please fill in all fields.", "error")
            return render_template('login.html', mode='login')

        user = database.get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            database.log_activity(user['user_id'], "Login", "Logged in successfully")
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "error")

    return render_template('login.html', mode='login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        aadhaar = request.form.get('aadhaar', '').strip() or None
        phone = request.form.get('phone', '').strip() or None

        if not name or not email or not password:
            flash("Name, email, and password are required.", "error")
            return render_template('login.html', mode='register')

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template('login.html', mode='register')

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template('login.html', mode='register')

        pw_hash = generate_password_hash(password)
        user_id = database.add_user(name, email, pw_hash, aadhaar, phone)

        if user_id is None:
            flash("An account with this email already exists.", "error")
            return render_template('login.html', mode='register')

        database.log_activity(user_id, "Register", "Account created")
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        flash("Account created successfully! Welcome to DigiLocker.", "success")
        return redirect(url_for('dashboard'))

    return render_template('login.html', mode='register')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        database.log_activity(session['user_id'], "Logout", "Logged out")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))




@app.route('/dashboard')
@login_required
def dashboard():
    stats = database.get_user_stats(session['user_id'])
    activity = database.get_recent_activity(session['user_id'], limit=8)
    recent_docs = database.get_user_documents(session['user_id'])[:5]
    return render_template(
        'dashboard.html',
        stats=stats,
        activity=activity,
        recent_docs=recent_docs
    )




@app.route('/documents')
@login_required
def documents():
    category = request.args.get('category', 'All')
    search = request.args.get('search', '').strip()
    docs = database.get_user_documents(
        session['user_id'],
        category=category,
        search=search if search else None
    )
    return render_template(
        'documents.html',
        documents=docs,
        current_category=category,
        search_query=search
    )


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for('documents'))

    file = request.files['file']
    category = request.form.get('category', 'Other')

    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('documents'))

    if not allowed_file(file.filename):
        flash("File type not allowed.", "error")
        return redirect(url_for('documents'))

    user_dir = os.path.join(config.UPLOAD_FOLDER, str(session['user_id']))
    os.makedirs(user_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)
    final_name = filename
    counter = 1
    while os.path.exists(os.path.join(user_dir, final_name)):
        final_name = f"{base}_{counter}{ext}"
        counter += 1

    file_path = os.path.join(user_dir, final_name)
    file.save(file_path)

    file_size = os.path.getsize(file_path)
    file_type = ext[1:].lower() if ext else "unknown"

    doc_id = database.add_document(
        user_id=session['user_id'],
        file_name=final_name,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type,
        category=category
    )

    database.log_activity(
        session['user_id'], "Upload",
        f"Uploaded '{final_name}' ({format_file_size(file_size)}) in {category}"
    )

    flash(f"'{final_name}' uploaded successfully!", "success")
    return redirect(url_for('documents'))


@app.route('/download/<int:doc_id>')
@login_required
def download(doc_id):
    doc = database.get_document_by_id(doc_id)
    if not doc or doc['user_id'] != session['user_id']:
        flash("Document not found.", "error")
        return redirect(url_for('documents'))

    if not os.path.exists(doc['file_path']):
        flash("File not found on server.", "error")
        return redirect(url_for('documents'))

    database.log_activity(
        session['user_id'], "Download", f"Downloaded '{doc['file_name']}'"
    )
    return send_file(doc['file_path'], as_attachment=True, download_name=doc['file_name'])


@app.route('/preview/<int:doc_id>')
@login_required
def preview(doc_id):
    doc = database.get_document_by_id(doc_id)
    if not doc or doc['user_id'] != session['user_id']:
        flash("Document not found.", "error")
        return redirect(url_for('documents'))

    if not os.path.exists(doc['file_path']):
        flash("File not found on server.", "error")
        return redirect(url_for('documents'))

    mime_map = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'txt': 'text/plain',
    }
    mime = mime_map.get(doc['file_type'], None)
    if mime:
        return send_file(doc['file_path'], mimetype=mime)
    else:
        return send_file(doc['file_path'], as_attachment=True, download_name=doc['file_name'])


@app.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete(doc_id):
    doc = database.get_document_by_id(doc_id)
    if not doc or doc['user_id'] != session['user_id']:
        flash("Document not found.", "error")
        return redirect(url_for('documents'))

    if os.path.exists(doc['file_path']):
        os.remove(doc['file_path'])

    database.delete_document(doc_id, session['user_id'])
    database.log_activity(
        session['user_id'], "Delete", f"Deleted '{doc['file_name']}'"
    )

    flash(f"'{doc['file_name']}' deleted.", "info")
    return redirect(url_for('documents'))


@app.route('/share/<int:doc_id>', methods=['POST'])
@login_required
def share(doc_id):
    doc = database.get_document_by_id(doc_id)
    if not doc or doc['user_id'] != session['user_id']:
        return jsonify({"error": "Document not found"}), 404

    token = database.create_share_link(doc_id, hours=24)
    share_url = request.host_url.rstrip('/') + url_for('shared_view', token=token)

    database.log_activity(
        session['user_id'], "Share", f"Shared '{doc['file_name']}'"
    )

    return jsonify({"url": share_url, "token": token})


@app.route('/shared/<token>')
def shared_view(token):
    doc = database.get_shared_document(token)
    if not doc:
        return render_template('shared.html', doc=None, error="This link is invalid or has expired.")
    return render_template('shared.html', doc=doc, token=token)


@app.route('/shared/<token>/download')
def shared_download(token):
    doc = database.get_shared_document(token)
    if not doc:
        abort(404)

    if not os.path.exists(doc['file_path']):
        abort(404)

    return send_file(doc['file_path'], as_attachment=True, download_name=doc['file_name'])




@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        aadhaar = request.form.get('aadhaar', '').strip() or None
        phone = request.form.get('phone', '').strip() or None

        database.update_user_profile(session['user_id'], name=name, aadhaar=aadhaar, phone=phone)
        if name:
            session['user_name'] = name
        database.log_activity(session['user_id'], "Profile", "Updated profile")
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    user = database.get_user_by_id(session['user_id'])
    stats = database.get_user_stats(session['user_id'])
    return render_template('profile.html', user=user, stats=stats)



@app.errorhandler(413)
def too_large(e):
    flash("File is too large. Maximum size is 10 MB.", "error")
    return redirect(url_for('documents'))


@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error="Page not found"), 404



if __name__ == '__main__':
    database.init_db()
    print("[DigiLocker] Server starting at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)