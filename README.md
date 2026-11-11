# BuildingHub

سامانهٔ چندمستأجری SaaS مدیریت ساختمان (Django + DRF + React + PostgreSQL)

## قابلیت‌ها

### مدیریت ساختمان (موجود)
- ساختمان، واحد، عضویت، سکونت (مالک/مستأجر)
- هزینه با ۴ روش تقسیم + snapshot + پرداخت جزئی و تأیید رسید
- تعمیرات، اطلاعیه، اعلان، گزارش، Audit Log
- JWT و isolation سمت سرور

### لایه SaaS (جدید)
- ثبت‌نام مدیر + آنبوردینگ ساختمان
- پلن‌های اشتراک ماهانه/سالانه با قیمت‌گذاری قابل تنظیم
- پرداخت کارت‌به‌کارت + آپلود رسید + تأیید/رد سوپرادمین
- Grace period قابل تنظیم + دستور `process_subscriptions`
- دعوت ساکن با توکن یک‌بارمصرف
- تیکت پشتیبانی مستقل از تعمیرات
- پنل سوپرادمین با آمار واقعی
- PWA (manifest + service worker بدون کش دادهٔ خصوصی)
- UI فارسی RTL

## پیش‌نیاز

- Python 3.11+
- Node.js 20+
- Docker (برای PostgreSQL) یا `USE_SQLITE=True`

## راه‌اندازی

```bash
cd E:\BuildingHub
docker compose up -d

python -m pip install -r requirements.txt
copy .env.example .env   # در صورت نیاز
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install --registry https://registry.npmjs.org/
npm run dev
```

- Frontend: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/api/docs/
- Backend: http://127.0.0.1:8000/api/v1/

## ساخت سوپرادمین

حساب سوپرادمین به‌صورت hardcode ساخته نمی‌شود:

```bash
python manage.py createsuperadmin --username admin --email admin@buildinghub.local --password "ChangeMe123!" --phone 09120000000
```

سپس وارد `/admin` در فرانت یا Django admin شوید.

## انقضای اشتراک (cron)

```bash
python manage.py process_subscriptions
```

## حساب‌های دمو (`seed_demo`)

| نقش | نام کاربری | رمز | توضیح |
|---|---|---|---|
| مدیر | `manager` | `Manager123!` | برج آسمان + سپیدار (ACTIVE) |
| مدیر کمکی | `assistant` | `Assistant123!` | برج آسمان |
| ساکن | `resident1` … `resident8` | `Resident123!` | واحدهای نمونه |

`seed_demo` پلن‌ها، تنظیمات کارت، یک ساختمان PENDING و اشتراک‌های ACTIVE را هم می‌سازد.

```bash
python manage.py seed_demo --reset
```

## تست

```bash
# Windows PowerShell
$env:USE_SQLITE='True'; python manage.py test finance.tests subscriptions.tests -v 2
```

## APIهای کلیدی SaaS

| مسیر | توضیح |
|---|---|
| `POST /api/v1/auth/register-manager/` | ثبت‌نام مدیر |
| `POST /api/v1/onboarding/building/` | ساخت ساختمان PENDING |
| `POST /api/v1/onboarding/select-plan/` | انتخاب پلن |
| `POST /api/v1/onboarding/submit-payment/` | پرداخت + رسید |
| `POST /api/v1/admin/subscription-payments/{id}/approve/` | تأیید پرداخت |
| `POST /api/v1/invitations/` / `accept/` | دعوت ساکن |
| `GET/POST /api/v1/support/tickets/` | پشتیبانی |
| `GET /api/v1/admin/dashboard/stats/` | آمار پلتفرم |

## صفحات فرانت

- عمومی: `/` `/pricing` `/register` `/login` `/onboarding` `/forgot-password` `/invite/:token`
- مدیر: `/app/*` شامل اشتراک، دعوت، پشتیبانی
- سوپرادمین: `/admin/*`

## ساختار

```
BuildingHub/
  accounts/ buildings/ finance/ maintenance/ communications/
  subscriptions/ support/ core/ config/
  frontend/
```

PostgreSQL روی پورت `5433` مپ شده است.
