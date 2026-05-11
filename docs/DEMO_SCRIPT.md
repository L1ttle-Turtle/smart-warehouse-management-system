# Warehouse IQ Demo Script

Tài liệu này dùng để chạy demo đồ án theo một câu chuyện liền mạch. Mục tiêu là thể hiện hệ thống chạy thật, dữ liệu đủ dày, phân quyền rõ và các nghiệp vụ kho có thể truy vết.

## 1. Chuẩn bị dữ liệu

Chạy lại database SQLite sạch trước buổi demo:

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\backend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
(Get-Content .env) -replace '^DATABASE_URL=.*$','DATABASE_URL=sqlite:///warehouse.db' | Set-Content .env
Remove-Item -LiteralPath '.\instance\warehouse.db' -Force -ErrorAction SilentlyContinue
python -m flask --app run.py init-db
python run.py
```

Chạy frontend:

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
npm install
npm run dev
```

## 2. Tài khoản demo

| Vai trò | Username | Password | Mục đích demo |
|---|---|---|---|
| Admin | `admin` | `Admin@123` | Toàn hệ thống, phân quyền, audit |
| Manager | `manager` | `Manager@123` | Kho, phiếu nghiệp vụ, vận chuyển, task |
| Staff | `staff` | `Staff@123` | Nhập/xuất/điều chuyển/tồn kho |
| Accountant | `accountant` | `Accountant@123` | Hóa đơn, payment, đối soát |
| Shipper | `shipper` | `Shipper@123` | Shipment được giao |

## 3. Câu chuyện demo chính

### Bước 1 - Nền tảng và phân quyền

1. Đăng nhập `admin`.
2. Mở Dashboard để giới thiệu danh tính, quyền và tóm tắt hệ thống.
3. Mở `Vai trò và quyền` để thấy permission matrix.
4. Mở `Trao quyền tạm thời` để giới thiệu trao quyền theo từng user, có tìm kiếm/lọc và lịch sử.
5. Mở `Audit log` để cho thấy hệ thống có truy vết thao tác.

### Bước 2 - Master data

1. Mở `Danh mục nền`.
2. Lướt các tab `Nhóm hàng`, `Nhà cung cấp`, `Khách hàng`, `Tài khoản ngân hàng`.
3. Mở `Sản phẩm` để thấy 20 sản phẩm seed.
4. Mở `Kho bãi` để thấy 4 kho và 13 vị trí.

### Bước 3 - Tồn kho và movement

1. Mở `Tồn kho`.
2. Bật `Chỉ tồn thấp` để thấy dòng `Tồn thấp` và `Hết hàng`.
3. Lọc theo kho hoặc nhóm hàng.
4. Mở `Lịch sử biến động` để giải thích vì sao tồn thay đổi.

### Bước 4 - Phiếu kho

1. Mở `Nhập kho`, chọn phiếu nháp hoặc tạo phiếu mới, sau đó xác nhận để tăng tồn.
2. Mở `Xuất kho`, xác nhận phiếu để trừ tồn.
3. Mở `Điều chuyển kho`, xác nhận phiếu để giảm kho nguồn và tăng kho đích.
4. Với mỗi phiếu, mở khu vực lịch sử movement theo chính mã phiếu.

### Bước 5 - Kiểm kê

1. Mở `Kiểm kê kho`.
2. Tạo phiếu kiểm kê nhiều dòng hoặc mở `STK-DEMO-001`.
3. Giải thích: phiếu nháp chưa làm đổi tồn.
4. Xác nhận phiếu để cập nhật tồn theo số lượng thực tế.
5. Xem movement có `reference_type = stocktake`.

### Bước 6 - Vận chuyển

1. Đăng nhập `manager`.
2. Mở `Vận chuyển`, chọn `SHP-DEMO-001` hoặc tạo shipment từ phiếu xuất đã xác nhận.
3. Xem timeline giao hàng.
4. Đăng nhập `shipper`.
5. Cập nhật trạng thái `assigned -> in_transit -> delivered`.

### Bước 7 - Hóa đơn và thanh toán

1. Đăng nhập `accountant`.
2. Mở `Hóa đơn`.
3. Chọn `INV-DEMO-001` để xem tổng tiền, đã thu, còn phải thu và lịch sử payment.
4. Ghi nhận thanh toán thủ công hoặc dùng nút `Thu đủ`.
5. Mở `Thanh toán` để xem payment vừa phát sinh.

### Bước 8 - Đối soát ngân hàng giả lập

1. Mở `Đối soát ngân hàng`.
2. Chọn giao dịch `BNK-DEMO-003` đang `Đã khớp hóa đơn`.
3. Bấm `Đối soát`.
4. Quay lại `Hóa đơn` hoặc `Thanh toán` để thấy payment thật và trạng thái hóa đơn đã cập nhật.
5. Bấm `Mô phỏng giao dịch` để tạo giao dịch mới, có thể nhập mã hóa đơn hoặc để trống để demo trạng thái `Chờ kiểm tra`.

### Bước 9 - Cộng tác nội bộ

1. Đăng nhập `manager`, mở `Công việc & thông báo`.
2. Tạo task giao cho `staff`.
3. Đăng nhập `staff`, kiểm tra task và notification.
4. Mở `Chat nội bộ`, gửi tin nhắn 1-1 giữa manager và staff.
5. Nếu mở 2 trình duyệt song song, notification/chat có realtime nhẹ qua Socket.IO.

### Bước 10 - Báo cáo

1. Mở `Báo cáo`.
2. Giới thiệu KPI tổng quan: tồn kho, dòng tồn cần chú ý, chứng từ nháp, shipment, doanh thu, công nợ.
3. Lướt các biểu đồ: tồn theo kho, nhập/xuất theo tháng, trạng thái vận chuyển, doanh thu, top hàng hóa.

## 4. Điểm nhấn khi thuyết trình

- Hệ thống có phân quyền thật theo role và permission.
- Dữ liệu không phải rỗng: seed đủ dày để lọc, sort, báo cáo và demo nhiều trạng thái.
- Mọi biến động tồn kho đều sinh movement history.
- Hóa đơn và payment không làm thay đổi tồn kho, đúng ranh giới nghiệp vụ.
- Bank integration đang là stub có kiểm soát, không giả vờ là kết nối ngân hàng thật.
- Các phần realtime là mức demo nhẹ, chưa claim production realtime đầy đủ.

## 5. Nếu gặp lỗi khi demo

- Nếu frontend báo 401, đăng xuất và đăng nhập lại.
- Nếu dữ liệu lệch sau khi demo nhiều lần, reset SQLite bằng lệnh ở phần chuẩn bị dữ liệu.
- Nếu không thấy menu, kiểm tra đang đăng nhập đúng vai trò.
- Nếu `shipper` không thấy đơn, dùng shipment seed `SHP-DEMO-001` hoặc đăng nhập `manager` để tạo shipment mới.
