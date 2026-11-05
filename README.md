# BuildingHub

سامانه مدیریت ساختمان (Django + DRF + React + PostgreSQL)

## قابلیت‌ها

- مدیریت ساختمان، واحد، عضویت و سکونت
- ثبت هزینه و ۴ روش تقسیم (مساوی / نفرات / متراژ / سفارشی) با snapshot
- پرداخت دستی + آپلود رسید + تأیید/رد مدیر + پرداخت جزئی
- درخواست تعمیر، پیام‌رسانی، اطلاعیه و اعلان درون‌سامانه‌ای
- داشبورد مدیر/ساکن، گزارش مالی، Audit Log
- JWT، کنترل دسترسی سمت سرور، فایل‌های محافظت‌شده

## پیش‌نیاز

- Python 3.11+
- Node.js 20+
- Docker (برای PostgreSQL)

## راه‌اندازی سریع

```bash
# 1) دیتابیس
cd E:\BuildingHub
docker compose up -d

# 2) بک‌اند
python -m pip install -r requirements.txt
copy .env.example .env   # در صورت نیاز
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# 3) فرانت‌اند
cd frontend
npm install --registry https://registry.npmjs.org/
npm run dev
```

- Frontend: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/api/docs/
- Backend: http://127.0.0.1:8000/api/v1/

## حساب‌های دمو

| نقش | نام کاربری | رمز | توضیح |
|---|---|---|---|
| مدیر | `manager` | `Manager123!` | علی مدیری — برج آسمان + سپیدار |
| مدیر کمکی | `assistant` | `Assistant123!` | مریم کاظمی — برج آسمان |
| ساکن | `resident1` | `Resident123!` | رضا احمدی — واحد ۱۰۱ (+ سپیدار ۱۱) |
| ساکن | `resident2` | `Resident123!` | سارا محمدی — واحد ۱۰۲ |
| ساکن | `resident3` … `resident8` | `Resident123!` | ساکنین واحدهای ۲۰۱ تا ۴۰۲ |

برای بازنشانی و تکمیل مجدد دیتا:

```bash
python manage.py seed_demo --reset
```

## تست

```bash
python manage.py test finance.tests -v 2
```

## ساختار

```
BuildingHub/
  accounts/ buildings/ finance/ maintenance/ communications/ core/
  config/
  frontend/
  docker-compose.yml
  requirements.txt
```

PostgreSQL روی پورت `5433` مپ شده است تا با سرویس‌های محلی تداخل نداشته باشد.
