from flask import Flask, render_template
from config import Config
from routes.auth import auth_bp, get_current_user, role_required

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(auth_bp)


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


@app.errorhandler(403)
def forbidden(_error):
    return (
        render_template(
            "base.html",
            page_heading="403 - Không có quyền truy cập",
            page_message="Tài khoản của bạn không đủ quyền để vào trang này.",
        ),
        403,
    )


@app.route("/")
def home():
    return render_template(
        "base.html",
        page_heading="EduTest - Trang chủ",
        page_message="Hệ thống tạo đề và quản lý kiểm tra.",
    )


@app.route("/teacher/dashboard")
@role_required("teacher", "admin")
def teacher_dashboard():
    return render_template(
        "base.html",
        page_heading="Khu vực Giảng viên / Quản trị",
        page_message="Dành cho vai trò teacher và admin.",
    )


@app.route("/student/exam")
@role_required("student", "teacher", "admin")
def student_exam():
    return render_template(
        "base.html",
        page_heading="Khu vực Làm bài kiểm tra",
        page_message="Sinh viên, giảng viên và quản trị viên đều có thể truy cập.",
    )


if __name__ == "__main__":
    app.run(debug=True)