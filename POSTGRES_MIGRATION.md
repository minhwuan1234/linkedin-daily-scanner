# Chuyển ứng dụng sang Railway PostgreSQL

Mã ứng dụng sử dụng `OUTREACH_DATABASE_URL`; nếu biến này không có thì sử dụng `DATABASE_URL`. Không đưa các biến này vào mã giao diện hoặc kho Git.

- Trên Railway, đặt `DATABASE_URL` của ứng dụng tham chiếu đến PostgreSQL trong cùng project (địa chỉ private).
- Trên máy chạy worker, đặt `OUTREACH_DATABASE_URL` thành PostgreSQL public URL của Railway, rồi cài lại thư viện bằng `python3 -m pip install -r requirements.txt`. Địa chỉ `*.railway.internal` chỉ hoạt động bên trong mạng Railway.
- Worker Messages, Session và Reply Send kiểm tra hàng đợi PostgreSQL mỗi 5 giây. Cửa sổ Session cập nhật mỗi 5 giây khi đang mở.

Trước khi chuyển môi trường thật, dừng worker và mọi thao tác ghi trên web; kiểm tra và đồng bộ các thay đổi phát sinh ở Supabase sau lần sao chép ban đầu. Xác minh dữ liệu, cấu trúc, hàm và quyền trên đích trước khi đổi biến kết nối. Sau khi triển khai, kiểm tra dashboard và từng worker, chỉ sau đó mới cho phép gửi thực tế trở lại. Bản sao `public` không bao gồm Supabase Auth, Storage hoặc các schema khác.
