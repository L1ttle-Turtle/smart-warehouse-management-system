# Warehouse IQ

Trang thai hien tai cua repo: **Module 1 - Nen tang xac thuc va phan quyen**.

## Pham vi da hoan thanh

- Dang nhap JWT voi 5 vai tro: `admin`, `manager`, `staff`, `accountant`, `shipper`
- API `login`, `me`, `logout`
- API `roles` de xem role-permission matrix theo role
- API va UI uy quyen quyen han theo **tung user**
- Rule chan role cap thap nhu `staff`, `shipper` khong duoc nhan/dung quyen uy quyen tiep
- Trang `Profile` cho moi user tu cap nhat:
  - email
  - so dien thoai
  - mat khau
- Frontend co:
  - man hinh dang nhap
  - route guard
  - trang tong quan quyen cua tai khoan dang dang nhap
  - trang role matrix chi cho user co quyen `roles.view`
  - trang uy quyen theo user chi cho user co quyen `delegations.manage`
  - trang ho so ca nhan
  - trang `403 Forbidden`

## Chay backend

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

## Chay frontend

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
npm install
npm run dev
```

Frontend:

- [http://localhost:5173](http://localhost:5173)

## Tai khoan test

- `admin / Admin@123`
- `manager / Manager@123`
- `staff / Staff@123`
- `accountant / Accountant@123`
- `shipper / Shipper@123`

## Kiem thu tu dong

```powershell
Set-Location -LiteralPath 'D:\Đồ án nghành\backend'
pytest

Set-Location -LiteralPath 'D:\Đồ án nghành\frontend'
npm run lint
npm run test
npm run build
```
