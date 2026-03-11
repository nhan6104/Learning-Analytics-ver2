# Tài liệu Dashboard Phân tích Dữ liệu (Datamart Analytics)

## 1. Tổng quan
**Microlearning Analytics Dashboard** là giao diện trực quan hóa dữ liệu được thiết kế để hiển thị trực tiếp các thông số từ kho dữ liệu (Datamart) của hệ thống Moodle. Dashboard này không sử dụng các thuật toán dự báo phức tạp, thay vào đó tập trung vào tính trung thực và minh bạch của dữ liệu học tập gốc.

---

## 2. Nguồn dữ liệu & Các chỉ số chính

### 📊 2.1. Dữ liệu Hoạt động Hàng ngày (`fact_daily_student_engagement`)
Hiển thị chi tiết nỗ lực học tập của từng học viên theo từng ngày.
*   **Tổng số phút (Active Minutes)**: Thời gian thực tế học viên thao tác trên hệ thống.
*   **Điểm tương tác (Engagement Score)**: Chỉ số tổng hợp về mức độ hoạt động trong ngày, được tính theo công thức trọng số:
    *   **Thời gian học**: 1 điểm cho mỗi phút (tối đa 60 điểm).
    *   **Tài liệu**: 1 điểm cho mỗi lần truy cập tài liệu/resource (tối đa 20 điểm).
    *   **Bài tập/Quiz**: 2 điểm cho mỗi lần làm bài (tối đa 20 điểm).
    *   **=> Tổng cộng tối đa**: 100 điểm/ngày.
*   **Mục đích**: Giúp học viên theo dõi nhịp điệu học tập cá nhân và mức độ hoàn thành mục tiêu hàng ngày.

### ⚠️ 2.2. Dữ liệu Rủi ro & Hiệu suất (`fact_risk_student_weekly`)
Tổng hợp dữ liệu theo tuần để đánh giá tình trạng học tập.
*   **Tỷ lệ Rủi ro (Risk Level)**: Đánh giá dựa trên mức độ tham gia và hoàn thành bài tập.
*   **Xác suất bỏ học (Dropout %)**: Con số thô phản ánh nguy cơ học viên ngừng khóa học.
*   **Mục đích**: Giúp giảng viên lọc nhanh danh sách những học viên cần chú ý.

### 📈 2.3. Dữ liệu Phân phối & Xu hướng lớp (`fact_class_engagement_distribution`)
Cái nhìn tổng thể về toàn bộ lớp học.
*   **Điểm trung bình lớp**: Mức tương tác bình quân của tất cả học viên.
*   **Phân loại (Engagement Mix)**: Thống kê số lượng học viên thuộc các nhóm Tích cực, Trung bình, Thấp, và Thụ động.
*   **Mục đích**: Đánh giá sức sống và sự đồng đều của lớp học qua từng tuần.

### 🔄 2.4. Dữ liệu Vòng đời học tập (`fact_student_course_lifecycle`)
Theo dõi lộ trình từ lúc bắt đầu đến khi kết thúc.
*   **Tiến độ (%)**: Phần trăm module đã hoàn thành.
*   **Trạng thái**: Hoạt động, Đã hoàn thành, hoặc Ngừng học.
*   **Ngày hoạt động cuối**: Thời điểm gần nhất học viên tương tác với hệ thống.

---

## 3. Các thành phần giao diện

### Dành cho Giảng viên (Teacher View)
*   **Thẻ chỉ số tổng quát**: Tổng số học viên, Điểm tương tác trung bình, và Cảnh báo học dồn.
*   **Biểu đồ xu hướng lớp**: Theo dòi sự biến động mức độ tương tác của cả lớp qua các tuần.
*   **Bảng chi tiết học viên**: Hiển thị danh sách học viên kèm Tiến độ, Rủi ro, và Ngày hoạt động cuối cùng.
*   **Biểu đồ phân loại**: Tỷ lệ các nhóm học tập trong lớp.

### Dành cho Người học (Student View)
*   **Thẻ cá nhân**: Xem nhanh tiến độ, trạng thái hiện tại và tổng thời gian đã học.
*   **Biểu đồ lịch sử**: Theo dõi điểm tương tác cá nhân so với thời gian.
*   **Nhật ký hoạt động**: Danh sách các ngày học gần nhất kèm số phút tương tác cụ thể.

---

## 4. Công nghệ sử dụng
*   **Frontend**: Tailwind CSS (UI tối giản, hiện đại).
*   **Visualization**: ApexCharts (Biểu đồ tương tác).
*   **Data API**: Truy vấn trực tiếp từ PostgreSQL thông qua PHP AJAX.

---
*Ghi chú: Mọi số liệu trên giao diện này đều được lấy trực tiếp từ các bảng Fact và Dimension trong schema `datamart`. Nếu dữ liệu không hiển thị, vui lòng kiểm tra lại tiến trình ETL (Trích xuất và nạp dữ liệu).*
