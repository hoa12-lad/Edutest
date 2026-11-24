
import os
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "edutest-secret-key")


# KẾT NỐI MYSQL
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "edutest")
    )


# KIỂM TRA THỜI GIAN CÒN LẠI
def get_exam_time(cursor, exam_id):
    cursor.execute(
        """
        SELECT
            duration,
            GREATEST(
                0,
                TIMESTAMPDIFF(
                    SECOND,
                    NOW(),
                    DATE_ADD(created_at, INTERVAL duration MINUTE)
                )
            ) AS remaining_seconds
        FROM exams
        WHERE exam_id = %s
        """,
        (exam_id,)
    )
    return cursor.fetchone()


# TRANG CHỦ
@app.route("/")
def home():
    return render_template("index.html")


# TẠO ĐỀ THI NGẪU NHIÊN
@app.route("/start", methods=["POST"])
def start_exam():
    student_id = request.form.get("student_id", "").strip()
    exam_name = request.form.get(
        "exam_name", "Đề kiểm tra EduTest"
    ).strip()
    duration = request.form.get("duration", "30")

    if not student_id.isdigit():
        flash("Mã sinh viên phải là số.")
        return redirect(url_for("home"))

    try:
        duration = int(duration)
        if duration < 1 or duration > 180:
            raise ValueError
    except ValueError:
        flash("Thời gian làm bài phải từ 1 đến 180 phút.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM questions ORDER BY RAND() LIMIT 10"
        )
        questions = cursor.fetchall()

        if len(questions) < 10:
            flash("Cần ít nhất 10 câu hỏi trong ngân hàng câu hỏi.")
            return redirect(url_for("home"))

        cursor.execute(
            """
            INSERT INTO exams (exam_name, duration)
            VALUES (%s, %s)
            """,
            (exam_name, duration)
        )

        exam_id = cursor.lastrowid

        for index, question in enumerate(questions, start=1):
            cursor.execute(
                """
                INSERT INTO exam_questions
                (exam_id, question_id, question_order)
                VALUES (%s, %s, %s)
                """,
                (exam_id, question["question_id"], index)
            )

        conn.commit()

        return redirect(
            url_for(
                "take_exam",
                exam_id=exam_id,
                student_id=student_id
            )
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# GIAO DIỆN LÀM BÀI
@app.route("/exam/<int:exam_id>")
def take_exam(exam_id):
    student_id = request.args.get("student_id", "").strip()

    if not student_id.isdigit():
        flash("Mã sinh viên không hợp lệ.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM exams WHERE exam_id = %s",
            (exam_id,)
        )
        exam = cursor.fetchone()

        if not exam:
            flash("Không tìm thấy đề thi.")
            return redirect(url_for("home"))

        time_info = get_exam_time(cursor, exam_id)

        if time_info["remaining_seconds"] <= 0:
            flash("Đề thi đã hết thời gian làm bài.")
            return redirect(url_for("home"))

        cursor.execute(
            """
            SELECT
                q.question_id,
                q.content,
                q.option_a,
                q.option_b,
                q.option_c,
                q.option_d,
                eq.question_order
            FROM exam_questions eq
            JOIN questions q
                ON eq.question_id = q.question_id
            WHERE eq.exam_id = %s
            ORDER BY eq.question_order
            """,
            (exam_id,)
        )

        questions = cursor.fetchall()

        return render_template(
            "exam.html",
            exam=exam,
            questions=questions,
            student_id=student_id,
            remaining_seconds=time_info["remaining_seconds"]
        )

    finally:
        cursor.close()
        conn.close()


# NỘP BÀI VÀ CHẤM ĐIỂM
@app.route("/submit/<int:exam_id>", methods=["POST"])
def submit_exam(exam_id):
    student_id = request.form.get("student_id", "").strip()

    if not student_id.isdigit():
        flash("Mã sinh viên không hợp lệ.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # KIỂM TRA ĐỀ THI VÀ THỜI GIAN
        time_info = get_exam_time(cursor, exam_id)

        if not time_info:
            flash("Không tìm thấy đề thi.")
            return redirect(url_for("home"))

        if time_info["remaining_seconds"] <= 0:
            flash("Đã hết thời gian. Hệ thống không nhận bài nộp muộn.")
            return redirect(url_for("home"))

        # LẤY ĐÁP ÁN ĐÚNG
        cursor.execute(
            """
            SELECT q.question_id, q.correct_answer
            FROM exam_questions eq
            JOIN questions q
                ON eq.question_id = q.question_id
            WHERE eq.exam_id = %s
            """,
            (exam_id,)
        )

        questions = cursor.fetchall()

        if not questions:
            flash("Đề thi không có câu hỏi.")
            return redirect(url_for("home"))

        # CHẤM ĐIỂM
        correct_count = 0

        for question in questions:
            selected = request.form.get(
                f"question_{question['question_id']}", ""
            ).upper()

            if selected == question["correct_answer"].upper():
                correct_count += 1

        total_questions = len(questions)

        score = round(
            correct_count * 10 / total_questions, 2
        )

        # LƯU KẾT QUẢ
        cursor.execute(
            """
            INSERT INTO submissions
            (exam_id, student_id, score)
            VALUES (%s, %s, %s)
            """,
            (exam_id, int(student_id), score)
        )

        submission_id = cursor.lastrowid
        conn.commit()

        return render_template(
            "result.html",
            score=score,
            correct_count=correct_count,
            total_questions=total_questions,
            submission_id=submission_id
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# CHẠY ỨNG DỤNG
if __name__ == "__main__":
    app.run(debug=True)
