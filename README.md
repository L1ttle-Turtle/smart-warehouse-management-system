# Warehouse IQ

Hệ thống quản lý kho hàng thông minh cho doanh nghiệp vừa và nhỏ, phát triển theo hướng đồ án tốt nghiệp nhưng ưu tiên khả năng chạy thật, test được và demo được theo từng module.

Trạng thái hiện tại của repo: **đã hoàn thành nền tảng Module 1-5 và đang ở Module 6 với luồng kho tối thiểu chạy được end-to-end**.

## 1. Mục tiêu dự án

Project này tập trung vào 4 mục tiêu chính:

- Có thể chạy local nhanh bằng SQLite để demo và kiểm thử.
- Có cấu trúc đủ rõ ràng để nâng lên MySQL cho đồ án chính thức.
- Mỗi module có phạm vi riêng, không làm lan toàn hệ thống cùng lúc.
- Ưu tiên một câu chuyện demo mạch lạc hơn là làm thật nhiều chức năng dang dở.

Demo narrative hiện tại đã đi được đến mức:

1. Đăng nhập theo vai trò.
2. Kiểm soát điều hướng và quyền truy cập theo permission.
3. Quản lý người dùng, nhân sự, danh mục nền, sản phẩm, kho bãi.
4. Xem tồn kho thật theo kho và vị trí.
5. Tạo và xử lý các phiếu kho tối thiểu:
   - nhập kho
   - xuất kho
   - điều chuyển kho
   - điều chỉnh tồn kho sau kiểm kê
6. Truy vết lại movement history để giải thích biến động tồn kho.

## 2. Công nghệ sử dụng

### Frontend

- React 19
- Vite 8
- Ant Design 6
- React Router DOM 7
- Axios
- Recharts
- Socket.IO Client

### Backend

- Flask 3
- Flask SQLAlchemy
- Flask JWT Extended
- Flask Migrate
- Flask SocketIO
- Marshmallow
- PyMySQL

### Database

- Development: SQLite
- Target triển khai đồ án: MySQL 8

### Kiểm thử và chất lượng

- Pytest cho backend
- Vitest + Testing Library cho frontend smoke test
- ESLint
- Vite build

## 3. Kiến trúc tổng quan

Project tách thành 2 phần:

- `frontend/`: giao diện web SPA
- `backend/`: REST API, xử lý nghiệp vụ, seed dữ liệu, migration

Luồng dữ liệu chính:

1. Frontend gọi API Flask qua `VITE_API_URL`
2. Backend xác thực JWT
3. Backend kiểm tra permission theo role và delegation
4. Backend thao tác database qua SQLAlchemy
5. Serializer trả dữ liệu JSON về cho frontend

## 4. Cấu trúc thư mục chính

```text
.
├── backend
│   ├── app
│   │   ├── routes
│   │   ├── services
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── constants.py
│   │   └── seed.py
│   ├── migrations
│   ├── tests
│   ├── requirements.txt
│   └── run.py
├── frontend
│   ├── src
│   │   ├── pages
│   │   ├── components
│   │   ├── auth
│   │   ├── config
│   │   └── api
│   ├── package.json
│   └── .env.example
└── README.md
```

## 5. Roadmap module và trạng thái hiện tại

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Module 1 - Xác thực và phân quyền | Hoàn thành nền tảng | Login JWT, me/logout, route guard, role/permission, profile, đổi mật khẩu, ủy quyền user-level |
| Module 2 - Người dùng và nhân sự | Hoàn thành nền tảng | CRUD user, CRUD employee, liên kết user-employee, audit log, dashboard cá nhân |
| Module 3 - Danh mục nền | Hoàn thành | Category, Supplier, Customer, BankAccount, giao diện `/catalogs` |
| Module 4 - Sản phẩm | Hoàn thành mức demo | CRUD sản phẩm, category, min stock, status, quantity total |
| Module 5 - Kho bãi và vị trí kho | Hoàn thành mức demo | CRUD kho, CRUD vị trí, route `/warehouses` dạng tab |
| Module 6 - Nghiệp vụ kho | Đang triển khai, đã usable | Inventory, movement history, nhập, xuất, điều chuyển, điều chỉnh tồn kho tối thiểu |
| Module 7 - Vận chuyển | Chưa bắt đầu | Để sau khi luồng kho ổn định |
| Module 8 - Hóa đơn và thanh toán | Chưa bắt đầu | Phụ thuộc phiếu xuất và khách hàng |
| Module 9 - Thông báo và công việc | Chưa bắt đầu | Chưa ưu tiên cho demo kho lõi |
| Module 10 - Chat nội bộ | Chưa bắt đầu | Chưa cần cho demo tối thiểu |
| Module 11 - Dashboard và báo cáo nghiệp vụ | Chưa bắt đầu sâu | Mới có dashboard cá nhân, chưa có dashboard nghiệp vụ kho |

## 6. Những gì đã hoàn thành theo module

### Module 1 - Auth / RBAC

- Đăng nhập bằng username/password, trả JWT access token
- `GET /auth/me`
- `POST /auth/logout`
- Cập nhật profile cá nhân
- Đổi mật khẩu theo password policy
- Bắt buộc đổi mật khẩu lần đầu nếu cần
- Role và permission được seed tự động
- Frontend route guard theo `requiredPermission` và `requiredPermissionsAny`

### Module 2 - Users / Employees

- CRUD user
- CRUD employee
- Liên kết `employees.user_id` 1-1 với `users.id`
- Audit log cho create/update/delete/login
- Phân trang, lọc, sort server-side
- Dashboard cá nhân tại `/`
- Tự sinh mã nhân viên theo tiền tố phòng ban
- Ủy quyền quyền hạn theo từng user, không theo role hàng loạt

### Module 3 - Base Catalogs

- Category
- Supplier
- Customer
- BankAccount
- Trang `/catalogs` dạng tab
- Tab hiển thị theo permission người dùng
- CRUD + search + filter + sort server-side

### Module 4 - Products

- CRUD sản phẩm
- Liên kết category
- Theo dõi:
  - `quantity_total`
  - `min_stock`
  - `status`
- Frontend quản lý sản phẩm tại `/products`

### Module 5 - Warehouses / Locations

- CRUD kho
- CRUD vị trí kho
- Không cho xóa kho/vị trí khi đã có inventory hoặc movement phụ thuộc
- Frontend quản lý tại `/warehouses`
- Giao diện dùng tab:
  - Kho
  - Vị trí kho

### Module 6 - Inventory Core

#### Phần inventory read-only

- `GET /inventory`
- `GET /inventory/movements`
- Có thể lọc movement theo:
  - `reference_type`
  - `reference_id`

#### Luồng nhập kho tối thiểu

- `GET /import-receipts`
- `POST /import-receipts`
- `GET /import-receipts/<id>`
- `PUT /import-receipts/<id>`
- `POST /import-receipts/<id>/confirm`
- `POST /import-receipts/<id>/cancel`

Đã có trên frontend:

- Route `/import-receipts`
- Xem danh sách phiếu nhập
- Tạo phiếu nháp
- Sửa phiếu nháp
- Hủy phiếu nháp
- Xác nhận phiếu để tăng tồn kho thật
- Xem lịch sử movement của chính phiếu nhập đang chọn

#### Luồng xuất kho tối thiểu

- `GET /export-receipts`
- `POST /export-receipts`
- `GET /export-receipts/<id>`
- `PUT /export-receipts/<id>`
- `POST /export-receipts/<id>/confirm`
- `POST /export-receipts/<id>/cancel`

Đã có trên frontend:

- Route `/export-receipts`
- Xem danh sách phiếu xuất
- Tạo phiếu nháp
- Sửa phiếu nháp
- Hủy phiếu nháp
- Xác nhận phiếu để trừ tồn kho thật
- Xem lịch sử movement của chính phiếu xuất đang chọn

#### Luồng điều chuyển kho tối thiểu

- `GET /stock-transfers`
- `POST /stock-transfers`
- `GET /stock-transfers/<id>`
- `PUT /stock-transfers/<id>`
- `POST /stock-transfers/<id>/confirm`
- `POST /stock-transfers/<id>/cancel`

Đã có trên frontend:

- Route `/stock-transfers`
- Xem danh sách phiếu điều chuyển
- Tạo phiếu nháp
- Sửa phiếu nháp
- Hủy phiếu nháp
- Xác nhận phiếu để giảm kho nguồn, tăng kho đích
- Xem lịch sử movement của chính phiếu điều chuyển đang chọn

#### Điều chỉnh tồn kho tối thiểu

Đây là bước mới nhất của Module 6.

- `POST /inventory/adjustments`
- Permission mới: `inventory.manage`
- Dùng để nhập `actual_quantity` sau kiểm kê
- Hệ thống tự tính chênh lệch so với tồn hiện tại
- Sinh movement loại `adjustment`
- Ghi audit log `inventory.adjusted`

Đã có trên frontend:

- Tab `Điều chỉnh tồn kho` trong route `/inventory`
- Chọn kho, vị trí, sản phẩm
- Nhập số lượng thực tế
- Xem trước chênh lệch
- Ghi nhận điều chỉnh và refresh tồn kho + movement history

## 7. Các route frontend đang có

| Route | Mục đích |
|---|---|
| `/` | Dashboard cá nhân |
| `/login` | Đăng nhập |
| `/profile` | Hồ sơ cá nhân, đổi mật khẩu |
| `/users` | Quản lý tài khoản |
| `/employees` | Quản lý nhân sự |
| `/catalogs` | Danh mục nền |
| `/products` | Quản lý sản phẩm |
| `/warehouses` | Quản lý kho và vị trí kho |
| `/inventory` | Tồn kho, movement, điều chỉnh tồn |
| `/import-receipts` | Nhập kho |
| `/export-receipts` | Xuất kho |
| `/stock-transfers` | Điều chuyển kho |
| `/delegations` | Ủy quyền quyền hạn |
| `/audit-logs` | Audit log |
| `/roles` | Ma trận vai trò và quyền |
| `/forbidden` | Trang chặn quyền |

## 8. Các nhóm API backend đang có

### Auth

- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/profile`
- `POST /auth/logout`

### Dashboard / audit

- `GET /dashboard/identity`
- `GET /audit-logs`

### Users / employees

- `GET /directory/users`
- `GET /users`
- `POST /users`
- `GET /users/<id>`
- `PUT /users/<id>`
- `DELETE /users/<id>`
- `GET /employees`
- `POST /employees`
- `GET /employees/<id>`
- `PUT /employees/<id>`
- `DELETE /employees/<id>`

### RBAC / delegation

- `GET /roles`
- Các API delegation hiện có trong module phân quyền

### Catalogs

- `/categories`
- `/suppliers`
- `/customers`
- `/bank-accounts`

Mỗi resource hỗ trợ:

- `GET list`
- `POST create`
- `GET detail`
- `PUT update`
- `DELETE delete`

### Products

- `GET /products`
- `POST /products`
- `GET /products/<id>`
- `PUT /products/<id>`
- `DELETE /products/<id>`

### Warehouses / locations

- `GET /warehouses`
- `POST /warehouses`
- `GET /warehouses/<id>`
- `PUT /warehouses/<id>`
- `DELETE /warehouses/<id>`
- `GET /locations`
- `POST /locations`
- `GET /locations/<id>`
- `PUT /locations/<id>`
- `DELETE /locations/<id>`

### Inventory / warehouse flow

- `GET /inventory`
- `GET /inventory/movements`
- `POST /inventory/adjustments`
- `GET /import-receipts`
- `POST /import-receipts`
- `GET /import-receipts/<id>`
- `PUT /import-receipts/<id>`
- `POST /import-receipts/<id>/confirm`
- `POST /import-receipts/<id>/cancel`
- `GET /export-receipts`
- `POST /export-receipts`
- `GET /export-receipts/<id>`
- `PUT /export-receipts/<id>`
- `POST /export-receipts/<id>/confirm`
- `POST /export-receipts/<id>/cancel`
- `GET /stock-transfers`
- `POST /stock-transfers`
- `GET /stock-transfers/<id>`
- `PUT /stock-transfers/<id>`
- `POST /stock-transfers/<id>/confirm`
- `POST /stock-transfers/<id>/cancel`

## 9. Database và domain hiện có

Các bảng nổi bật đang dùng thật trong project:

- `roles`
- `permissions`
- `role_permissions`
- `users`
- `employees`
- `audit_logs`
- `user_permission_delegations`
- `categories`
- `suppliers`
- `customers`
- `bank_accounts`
- `products`
- `warehouses`
- `warehouse_locations`
- `inventory`
- `inventory_movements`
- `import_receipts`
- `import_receipt_details`
- `export_receipts`
- `export_receipt_details`
- `stock_transfers`
- `stock_transfer_details`

Relationship chính của domain kho:

- `Warehouse 1-n WarehouseLocation`
- `Product 1-n Inventory`
- `WarehouseLocation 1-n Inventory`
- `InventoryMovement` gắn với:
  - kho
  - vị trí
  - sản phẩm
  - người thực hiện
- `ImportReceipt`, `ExportReceipt`, `StockTransfer` có detail riêng

## 10. Dữ liệu seed demo hiện có

Seed hiện tại đủ dày để demo các luồng chính mà không cần nhập tay từ đầu.

### Tài khoản và nhân sự

- 5 user mặc định:
  - `admin`
  - `manager`
  - `staff`
  - `accountant`
  - `shipper`
- 5 employee tương ứng

### Danh mục nền

- 4 nhóm hàng
- 4 nhà cung cấp
- 4 khách hàng
- 3 tài khoản ngân hàng

### Kho và sản phẩm

- 2 kho:
  - `WH001` - Kho Trung Tâm
  - `WH002` - Kho Miền Nam
- 6 vị trí kho
- 7 sản phẩm demo
- Nhiều dòng tồn kho phân bố theo kho và vị trí
- Movement seed opening stock và stock check ban đầu

### Chứng từ kho demo

- `IMP-DEMO-001`
- `EXP-DEMO-001`
- `TRF-DEMO-001`

## 11. Tài khoản test mặc định

| Vai trò | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Manager | `manager` | `Manager@123` |
| Staff | `staff` | `Staff@123` |
| Accountant | `accountant` | `Accountant@123` |
| Shipper | `shipper` | `Shipper@123` |

## 12. Biến môi trường

### Backend `.env`

File mẫu: [backend/.env.example](D:/Đồ%20án%20nghành/backend/.env.example)

```env
SECRET_KEY=warehouse-secret-key-with-32-plus-characters
JWT_SECRET_KEY=warehouse-jwt-secret-key-with-32-plus-characters
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/warehouse_db
FRONTEND_URL=http://localhost:5173
SOCKETIO_CORS_ALLOWED_ORIGINS=http://localhost:5173
DEFAULT_PASSWORD=Password123!
```

### Frontend `.env`

File mẫu: [frontend/.env.example](D:/Đồ%20án%20nghành/frontend/.env.example)

```env
VITE_API_URL=http://localhost:5000
```

## 13. Cách chạy project local

### Chạy backend với SQLite

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\backend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
(Get-Content .env) -replace '^DATABASE_URL=.*$','DATABASE_URL=sqlite:///warehouse.db' | Set-Content .env
Remove-Item -LiteralPath '.\instance\warehouse.db' -Force -ErrorAction SilentlyContinue
python -m flask --app run.py init-db
python run.py
```

Backend sẽ chạy tại:

- [http://localhost:5000](http://localhost:5000)
- Health check: [http://localhost:5000/health](http://localhost:5000/health)

### Chạy frontend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
npm install
npm run dev
```

Frontend sẽ chạy tại:

- [http://localhost:5173](http://localhost:5173)

## 14. Cách kiểm thử

### Backend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành'
pytest backend/tests -q
```

### Frontend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
npm run test -- --run
npm run lint
npm run build
```

### Kết quả kiểm thử gần nhất

- Backend: `139 passed`
- Frontend smoke: `27 passed`
- Frontend lint: `pass`
- Frontend build: `pass`

## 15. Kịch bản demo gợi ý

### Kịch bản 1 - Demo nền tảng

1. Đăng nhập bằng `admin`
2. Mở dashboard cá nhân
3. Vào `Tài khoản`, `Nhân sự`, `Vai trò và quyền`
4. Mở `Ủy quyền quyền hạn`
5. Mở `Audit log`

### Kịch bản 2 - Demo danh mục và master data

1. Vào `Danh mục nền`
2. Xem các tab:
   - Nhóm hàng
   - Nhà cung cấp
   - Khách hàng
   - Tài khoản ngân hàng
3. Vào `Sản phẩm`
4. Vào `Kho bãi`

### Kịch bản 3 - Demo nghiệp vụ kho

1. Vào `Tồn kho` để xem số lượng hiện tại
2. Vào `Nhập kho`, tạo phiếu nháp rồi xác nhận
3. Quay lại `Tồn kho` để xem số lượng tăng và movement mới
4. Vào `Xuất kho`, tạo phiếu nháp rồi xác nhận
5. Quay lại `Tồn kho` để xem số lượng giảm và movement mới
6. Vào `Điều chuyển kho`, tạo phiếu nháp rồi xác nhận
7. Xem history điều chuyển theo phiếu
8. Vào lại `Tồn kho`, dùng tab `Điều chỉnh tồn kho` để nhập số lượng kiểm kê thực tế
9. Mở `Lịch sử biến động` để xem movement `adjustment`

## 16. Quyền theo vai trò ở mức hiện tại

### Admin

- Toàn quyền trên các module đã làm

### Manager

- Quản lý nhân sự
- Quản lý danh mục nền trừ bank account
- Quản lý sản phẩm
- Quản lý kho, vị trí kho
- Quản lý nhập, xuất, điều chuyển, điều chỉnh tồn

### Staff

- Xem sản phẩm, kho, vị trí, tồn kho
- Thao tác nhập kho, xuất kho, điều chuyển kho
- Điều chỉnh tồn kho tối thiểu
- Không quản lý user, employee, catalog master

### Accountant

- Dashboard cá nhân
- Khách hàng
- Tài khoản ngân hàng
- Chưa có module hóa đơn / thanh toán ở thời điểm này

### Shipper

- Mới có dashboard cá nhân
- Chưa có module vận chuyển nên scope còn rất nhỏ

## 17. Known issues và những gì chưa làm

### Nợ tính năng còn mở

Các phần sau vẫn nằm ngoài phạm vi hoàn thành hiện tại:

- Shipment / vận chuyển
- Invoice / payment
- Notification / task
- Chat nội bộ
- Dashboard nghiệp vụ kho
- Báo cáo tồn kho, nhập xuất, doanh thu
- Phiếu kiểm kê đầy đủ nhiều dòng
- Phê duyệt nhiều bước
- Phân quyền object-level theo từng kho hoặc từng chứng từ
- Tích hợp ngân hàng thật
- Socket realtime cho nghiệp vụ kho

### Known issues kỹ thuật còn lại

Các điểm dưới đây đã được automation review nhắc tới và **vẫn chưa xử lý xong hoàn toàn**:

- JWT logout hiện mới dừng ở mức audit log, chưa có blocklist / token revocation thật.
- Frontend vẫn lưu bearer token trong `localStorage`, chưa chuyển sang chiến lược an toàn hơn.
- Chưa có rate limit / lockout cho đăng nhập.
- Phân quyền hiện vẫn là global permission, chưa có warehouse-level scope hay object-level scope.
- CORS đang để khá rộng cho môi trường dev, chưa siết theo hướng production.
- Các module `Shipment`, `Invoice`, `Payment`, `Reports`, `Notifications`, `Chat` vẫn chưa mounted đầy đủ nên chưa nên claim trong demo.

## 18. Tiến độ hardening gần đây

Các fix dưới đây được làm sau khi đối chiếu kết quả automation review với code thật của repo:

- Đã sửa bootstrap backend để `create_app()` tự nạp `backend/.env`, giúp `init-db` và `python run.py` dùng cùng cấu hình runtime thay vì dễ trỏ sang 2 database khác nhau.
- Đã thêm regression test cho runtime env loading qua `WAREHOUSE_ENV_FILE` để khóa lỗi bootstrap trong các lần refactor sau.
- Đã khóa lỗ hổng delegation của `users.manage`: user được ủy quyền quyền quản lý tài khoản không thể tạo hoặc gán tài khoản với role cao hơn quyền gốc của mình.
- Đã chặn user được ủy quyền `users.manage` sửa hoặc xóa tài khoản thuộc role cấp cao hơn phạm vi được phép quản lý.
- Đã harden luồng `stock_transfers` để `update / cancel / confirm` phải claim phiếu nháp trong transaction trước khi mutate, giảm rủi ro race condition làm lệch metadata và movement tồn kho.
- Đã siết validate `GET /inventory/movements`: `reference_id` không hợp lệ giờ trả `400` rõ ràng thay vì âm thầm mở rộng kết quả truy vấn.

## 19. Hướng đi tiếp theo được khuyến nghị

Thứ tự tiếp theo an toàn nhất cho project:

1. Hoàn thiện tiếp Module 6 theo chiều sâu demo:
   - cảnh báo tồn thấp hơn `min_stock`
   - bộ lọc tồn kho hữu dụng hơn
   - có thể cân nhắc phiếu kiểm kê tối thiểu nếu cần
2. Sau đó mới sang Module 7:
   - shipment tối thiểu từ phiếu xuất đã xác nhận
3. Khi shipment ổn thì sang Module 8:
   - invoice và payment thủ công
4. Sau khi flow nghiệp vụ đủ dày mới quay lại harden tiếp:
   - token revocation
   - rate limiting
   - object-level authorization
5. Cuối cùng mới mở rộng dashboard nghiệp vụ và báo cáo

## 20. Ghi chú quan trọng

- Project đang tối ưu cho **demo và nghiệm thu đồ án**, không phải cho production load lớn.
- Luồng đang được giữ theo nguyên tắc **mỗi bước nhỏ nhưng chạy thật**.
- Nếu dùng database cũ, sau khi cập nhật permission mới như `inventory.manage` hoặc hardening RBAC liên quan `users.manage`, nên chạy lại seed để đồng bộ quyền.
- README này được cập nhật theo trạng thái code hiện tại đến thời điểm đã có **stock adjustment tối thiểu trong Module 6** và batch hardening sau automation review.
