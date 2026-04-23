# Warehouse IQ

Hệ thống quản lý kho hàng thông minh cho doanh nghiệp vừa và nhỏ.

Trạng thái hiện tại của repo: **Module 6 - Nhập / xuất / tồn kho đang ở mức demo tối thiểu chạy được**.

## Mục tiêu demo hiện tại

Dự án đang ưu tiên một luồng demo kho hàng rõ ràng, có thể chạy và kiểm thử ngay:

- Người dùng đăng nhập theo vai trò.
- Sidebar và route được phân quyền theo permission.
- Admin/Manager quản lý tài khoản, nhân sự, danh mục, sản phẩm, kho bãi.
- Có dữ liệu demo đủ dày cho hàng hóa, kho, vị trí và tồn kho.
- Có thể xem tồn kho và lịch sử biến động tồn kho.
- Có thể tạo phiếu nhập nháp, sửa/hủy nháp, xác nhận để tăng tồn kho.
- Có thể tạo phiếu xuất nháp, sửa/hủy nháp, xác nhận để trừ tồn kho.
- Có thể tạo phiếu điều chuyển nháp, xác nhận để giảm kho nguồn và tăng kho đích.

## Công nghệ sử dụng

- Frontend: React, Vite, Ant Design.
- Backend: Flask, SQLAlchemy, Marshmallow, JWT, Flask-Migrate.
- Database dev: SQLite.
- Database mục tiêu đồ án: MySQL.
- Test: Pytest, Vitest, ESLint, Vite build.

## Tiến độ theo module

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Module 1 - Xác thực và phân quyền | Hoàn thành nền tảng | JWT, route guard, roles, permissions, profile, đổi mật khẩu, ủy quyền user-level |
| Module 2 - Người dùng và nhân sự | Hoàn thành nền tảng | CRUD users, CRUD employees, liên kết user-employee, audit log, dashboard cá nhân |
| Module 3 - Danh mục nền | Hoàn thành | Category, Supplier, Customer, BankAccount, trang `/catalogs` dạng tab |
| Module 4 - Hàng hóa | Hoàn thành mức demo | CRUD sản phẩm, liên kết nhóm hàng, tồn tổng, min stock, trạng thái |
| Module 5 - Kho bãi và vị trí kho | Hoàn thành mức demo | CRUD kho, CRUD vị trí kho, trang `/warehouses` dạng tab |
| Module 6 - Nhập / xuất / tồn kho | Đang hoàn thiện | Inventory read-only, movement log, nhập kho, xuất kho, điều chuyển kho tối thiểu |
| Module 7 - Vận chuyển | Chưa bắt đầu | Sẽ làm sau khi Module 6 ổn định |
| Module 8 - Hóa đơn / thanh toán | Chưa bắt đầu | Sẽ phụ thuộc phiếu xuất đã xác nhận |
| Module 9 - Thông báo / công việc | Chưa bắt đầu | Ưu tiên sau nghiệp vụ kho chính |
| Module 10 - Chat nội bộ | Chưa bắt đầu | Chưa cần cho demo kho tối thiểu |
| Module 11 - Báo cáo | Chưa bắt đầu | Sẽ tổng hợp từ dữ liệu nhập/xuất/điều chuyển |

## Chức năng đã có

### Module 1 - Auth/RBAC

- Đăng nhập JWT với 5 vai trò mặc định: `admin`, `manager`, `staff`, `accountant`, `shipper`.
- API `login`, `me`, `logout`.
- Ma trận quyền theo module.
- Route guard frontend theo permission.
- Trang hồ sơ cá nhân.
- Đổi mật khẩu, password policy, first-login reset.
- Ủy quyền quyền hạn theo từng user, có hạn dùng và lịch sử.
- Audit log cho thao tác quan trọng.

### Module 2 - Users/Employees

- Quản lý tài khoản người dùng.
- Quản lý hồ sơ nhân sự.
- Tự sinh mã nhân viên theo dữ liệu đầu vào.
- Liên kết `users` 1-1 với `employees` qua `user_id`.
- Phân trang, lọc, sort server-side.
- Dashboard riêng cho user/nhân sự.

### Module 3 - Catalogs

- Nhóm hàng.
- Nhà cung cấp.
- Khách hàng.
- Tài khoản ngân hàng.
- Trang `/catalogs` dùng tab và chỉ hiển thị tab theo quyền.

### Module 4 - Products

- Quản lý sản phẩm.
- Liên kết sản phẩm với nhóm hàng.
- Theo dõi tồn tổng `quantity_total`.
- Theo dõi ngưỡng `min_stock`.
- Hiển thị trạng thái hàng dưới tồn tối thiểu.

### Module 5 - Warehouses

- Quản lý kho.
- Quản lý vị trí kho.
- Trang `/warehouses` dùng tab cho Kho và Vị trí kho.
- Staff được xem, Admin/Manager được quản lý.

### Module 6 - Inventory Flow

- API đọc tồn kho: `GET /inventory`.
- API đọc movement: `GET /inventory/movements`.
- Seed tồn kho demo nhiều kho, nhiều vị trí, nhiều sản phẩm.
- Phiếu nhập:
  - `GET /import-receipts`
  - `POST /import-receipts`
  - `PUT /import-receipts/<id>`
  - `POST /import-receipts/<id>/confirm`
  - `POST /import-receipts/<id>/cancel`
  - UI `/import-receipts`
- Phiếu xuất:
  - `GET /export-receipts`
  - `POST /export-receipts`
  - `PUT /export-receipts/<id>`
  - `POST /export-receipts/<id>/confirm`
  - `POST /export-receipts/<id>/cancel`
  - UI `/export-receipts`
- Phiếu điều chuyển:
  - `GET /stock-transfers`
  - `POST /stock-transfers`
  - `GET /stock-transfers/<id>`
  - `POST /stock-transfers/<id>/confirm`
  - UI `/stock-transfers`

## Dữ liệu demo đã seed

Seed hiện tại tạo sẵn:

- 5 tài khoản mặc định theo role.
- Hồ sơ nhân sự tương ứng.
- Nhiều category, supplier, customer, bank account.
- Nhiều sản phẩm demo.
- 2 kho chính: `WH001`, `WH002`.
- Nhiều vị trí kho.
- Nhiều dòng tồn kho ban đầu.
- Movement log mở kho.
- Phiếu nhập nháp `IMP-DEMO-001`.
- Phiếu xuất nháp `EXP-DEMO-001`.
- Phiếu điều chuyển nháp `TRF-DEMO-001`.

## Tài khoản test

| Vai trò | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Manager | `manager` | `Manager@123` |
| Staff | `staff` | `Staff@123` |
| Accountant | `accountant` | `Accountant@123` |
| Shipper | `shipper` | `Shipper@123` |

## Cách chạy backend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\backend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
(Get-Content .env) -replace '^DATABASE_URL=.*$','DATABASE_URL=sqlite:///warehouse.db' | Set-Content .env
Remove-Item -LiteralPath '.\instance\warehouse.db' -Force -ErrorAction SilentlyContinue
python -m flask --app run.py init-db
python run.py
```

API health:

- [http://localhost:5000/health](http://localhost:5000/health)

## Cách chạy frontend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
npm install
npm run dev
```

Frontend:

- [http://localhost:5173](http://localhost:5173)

## Kiểm thử tự động

Backend:

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành'
pytest backend/tests -q
```

Frontend:

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
npm run test -- --run
npm run lint
npm run build
```

Kết quả kiểm thử gần nhất:

- Backend: `125 passed`.
- Frontend smoke: `25 passed`.
- Frontend lint: pass.
- Frontend build: pass.

## Luồng demo đề xuất

1. Đăng nhập bằng `admin` hoặc `manager`.
2. Mở Dashboard cá nhân để xác nhận thông tin người dùng và quyền.
3. Mở Danh mục nền để xem dữ liệu category, supplier, customer, bank account.
4. Mở Sản phẩm để xem tồn tổng và cảnh báo dưới tồn tối thiểu.
5. Mở Kho bãi để xem kho và vị trí kho.
6. Mở Tồn kho để xem số lượng hiện tại và movement log.
7. Mở Nhập kho, tạo phiếu nháp, xác nhận để tăng tồn.
8. Mở Xuất kho, tạo phiếu nháp, xác nhận để trừ tồn.
9. Mở Điều chuyển kho, tạo phiếu nháp, xác nhận để giảm kho nguồn và tăng kho đích.
10. Quay lại Tồn kho để đối chiếu movement mới.

## Chưa làm

- Sửa/hủy phiếu điều chuyển nháp.
- Full quy trình vận chuyển.
- Hóa đơn và thanh toán.
- Thông báo và công việc nội bộ.
- Chat nội bộ.
- Báo cáo thống kê nghiệp vụ.
- Object-level permission sâu theo từng kho.
- Tối ưu UI/UX cuối kỳ và script demo hoàn chỉnh.

## Bước tiếp theo đề xuất

Tiếp tục trong Module 6 với thao tác **sửa phiếu điều chuyển nháp trước khi xác nhận**, sau đó bổ sung **hủy phiếu điều chuyển nháp** để đồng bộ với nhập kho và xuất kho.
