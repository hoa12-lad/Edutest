# EduTest – Hệ thống tạo đề và quản lý kiểm tra trực tuyến

## 1. Cấu trúc thư mục
- `app.py`: Điểm khởi chạy ứng dụng Flask và đăng ký Blueprint.
- `config.py`: Cấu hình hệ thống và kết nối CSDL.
- `requirements.txt`: Danh sách thư viện cài đặt.
- `routes/`: Các module chức năng (`auth.py`, ...).
- `templates/`: Giao diện HTML (`base.html`, `login.html`, ...).
- `static/`: Tài nguyên tĩnh (`css/`, `js/`).

## 2. Hướng dẫn chạy trên máy Local
1. Clone repository:
   git clone https://github.com/hoa12-lad/Edutest.git
   cd Edutest
2. Tạo và kích hoạt môi trường ảo:
   python -m venv venv
   source venv/Scripts/activate
3. Cài đặt thư viện và chạy ứng dụng:
   pip install -r requirements.txt
   python app.py

## 3. Quy ước nhánh Git
- `main`: Nhánh chính ổn định, gộp code qua Pull Request (PR).
- `feat/<ten-thanh-vien>-<ten-tinh-nang>`: Nhánh phát triển riêng (ví dụ: `feat/hoa-auth`).
