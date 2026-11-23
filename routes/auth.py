from functools import wraps
from urllib.parse import urljoin, urlparse
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import mysql.connector
from mysql.connector import Error as MySQLError
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"admin", "teacher", "student"}

DEMO_USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password_hash": generate_password_hash("123456"),
        "role": "admin",
        "full_name": "Quản trị viên",
        "is_active": 1,
    },
    "gv01": {
        "id": 2,
        "username": "gv01",
        "password_hash": generate_password_hash("123456"),
        "role": "teacher",
        "full_name": "Giảng viên",
        "is_active": 1,
    },
    "sv01": {
        "id": 3,
        "username": "sv01",
        "password_hash": generate_password_hash("123456"),
        "role": "student",
        "full_name": "Sinh viên",
        "is_active": 1,
    },
}


def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def get_current_user():
    user_id = session.get("user_id")
    role = session.get("user_role")
    if not user_id or role not in VALID_ROLES:
        return None
    return {
        "id": user_id,
        "username": session.get("username", ""),
        "full_name": session.get("full_name", ""),
        "role": role,
    }


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash("Vui lòng đăng nhập để tiếp tục.", "warning")
            next_url = request.full_path if request.query_string else request.path
            return redirect(url_for("auth.login", next=next_url))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    normalized_roles = {r.strip().lower() for r in allowed_roles if r and r.strip()}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            if not current_user:
                flash("Vui lòng đăng nhập để tiếp tục.", "warning")
                next_url = request.full_path if request.query_string else request.path
                return redirect(url_for("auth.login", next=next_url))

            user_role = current_user["role"]
            if normalized_roles and user_role not in normalized_roles:
                flash("Bạn không có quyền truy cập chức năng này.", "danger")
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg.get("DB_HOST", "localhost"),
        port=int(cfg.get("DB_PORT", 3306)),
        user=cfg.get("DB_USER", "root"),
        password=cfg.get("DB_PASSWORD", ""),
        database=cfg.get("DB_NAME", "edutest_db"),
        connection_timeout=3,
    )


def find_user_by_username(username):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, username, password_hash, role, full_name, is_active
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        role = (row.get("role") or "").strip().lower()
        if role not in VALID_ROLES:
            return None

        return {
            "id": row["id"],
            "username": row["username"],
            "password_hash": row["password_hash"],
            "role": role,
            "full_name": row.get("full_name") or row["username"],
            "is_active": row.get("is_active", 1),
        }
    except MySQLError:
        return DEMO_USERS.get(username)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("home"))

    next_page = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.", "warning")
            return render_template("login.html", next=next_page)

        user = find_user_by_username(username)
        if user and int(user.get("is_active", 1)) == 0:
            flash("Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.", "danger")
            return render_template("login.html", next=next_page)

        if user and user.get("password_hash") and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["user_role"] = user["role"]
            flash(f"Đăng nhập thành công ({user['role']}).", "success")

            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for("home"))

        flash("Sai tên đăng nhập hoặc mật khẩu.", "danger")

    return render_template("login.html", next=next_page)


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    session.clear()
    flash("Đã đăng xuất khỏi hệ thống.", "info")
    return redirect(url_for("auth.login"))