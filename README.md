# Warehouse IQ

Trạng thái hiện tại của repo: **Module 2 - Người dùng và nhân sự**.

## Phạm vi đã hoàn thành

- Nền tảng xác thực và phân quyền của Module 1:
  - Đăng nhập JWT với 5 vai trò `admin`, `manager`, `staff`, `accountant`, `shipper`
  - API `login`, `me`, `logout`
  - Ma trận quyền theo role
  - Ủy quyền quyền hạn theo từng user
  - Trang hồ sơ cá nhân để đổi email, số điện thoại, mật khẩu
- Module 2:
  - CRUD tài khoản người dùng
  - CRUD hồ sơ nhân sự
  - Liên kết `users` 1-1 với `employees` qua `user_id`
  - Phân quyền:
    - `admin` quản lý tài khoản và nhân sự
    - `manager` quản lý nhân sự, không quản lý tài khoản
  - Seed dữ liệu mẫu nhân sự tương ứng với 5 tài khoản mặc định
  - Frontend có thêm:
    - trang `Tài khoản`
    - trang `Nhân sự`
    - điều hướng sidebar theo quyền

## Chạy backend

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

## Chạy frontend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
npm install
npm run dev
```

Frontend:

- [http://localhost:5173](http://localhost:5173)

## Tài khoản test

- `admin / Admin@123`
- `manager / Manager@123`
- `staff / Staff@123`
- `accountant / Accountant@123`
- `shipper / Shipper@123`

## Kiểm thử tự động

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\backend'
python -m pytest

Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
npm run lint
npm run test -- --run
npm run build
```
