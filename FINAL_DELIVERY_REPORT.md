# BuildingHub — Final Delivery Report (SaaS Layer)

## Summary

لایهٔ کامل SaaS روی MVP موجود پیاده‌سازی شد: اشتراک، آنبوردینگ، پرداخت دستی، grace period، دعوت ساکن، پشتیبانی، پنل سوپرادمین، PWA و UI فارسی RTL — بدون شکستن ماژول‌های مالی/تعمیرات.

## Implemented modules

### Backend apps
- `subscriptions/` — Plan, Pricing, Subscription, Payment, Receipt, History, PlatformSettings
- `support/` — Ticket, Message, Attachment, StatusHistory
- Extended `buildings` — `Building.status`, floors/apartments, `ResidentInvitation`
- Extended `accounts` — `User.platform_role` (`SUPER_ADMIN` / `SUPPORT_OPERATOR`)

### Permissions / gates
- `IsSuperAdmin`, `IsSupportOperator`
- `building_management_allowed` → write only when building ACTIVE + subscription ACTIVE
- Grace/Expired → read + renew + support only

### Management commands
- `createsuperadmin`
- `process_subscriptions` (ACTIVE→GRACE→EXPIRED + deduped notifications)

## Key endpoints

**Public / onboarding**
- `POST /api/v1/auth/register-manager/`
- `POST /api/v1/onboarding/building|select-plan|submit-payment/`
- `GET /api/v1/subscriptions/plans/public/`
- `POST /api/v1/invitations/accept/`
- `POST /api/v1/auth/password-reset/` (+ confirm)

**Manager**
- `GET /api/v1/subscriptions/mine/`
- `GET /api/v1/subscriptions/gate/`
- `POST /api/v1/invitations/`
- Support tickets CRUD + reply

**Super admin**
- `GET /api/v1/admin/dashboard/stats/`
- Plans CRUD, buildings activate/suspend
- Subscription payments approve/reject
- Platform settings, managers/residents lists

## Frontend pages

- Landing, pricing, register, login, onboarding, password recovery, invite accept
- Manager: subscription, invitations, support (+ existing ops pages)
- Super admin: `/admin/*` dashboard, buildings, managers, plans, payments, subscriptions, support, settings
- PWA: `manifest.webmanifest`, `sw.js`, `offline.html`, icons

## Migrations

Applied successfully (`accounts.0002`, `buildings.0002`, `communications.0002`, `subscriptions.0001`, `support.0001` + prior baseline).

```text
python manage.py migrate
# OK — subscriptions + support + Building.status + User.platform_role
```

## Automated tests (REAL)

Command:

```powershell
$env:USE_SQLITE='True'; python manage.py test finance.tests subscriptions.tests -v 2
```

Result:

```text
Found 22 test(s).
Ran 22 tests in 47.442s
OK
```

Coverage includes: allocation/rounding/partial payments, isolation, manager registration, monthly onboarding+approve, yearly snapshot, payment reject, grace/expiry dedupe, write gate, invitations single-use/expiry, support tickets, password recovery, capacity, admin stats, PWA asset presence.

## Super admin creation

```bash
python manage.py createsuperadmin --username admin --email admin@buildinghub.local --password "ChangeMe123!"
```

## Start the app

```bash
# DB
docker compose up -d

# Backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# Frontend
cd frontend && npm install && npm run dev
```

Optional cron:

```bash
python manage.py process_subscriptions
```

## Demo accounts

- `manager` / `Manager123!`
- `resident1` / `Resident123!`
- Super admin: create via `createsuperadmin` (not seeded hardcoded)

## Remaining limitations

- No online payment gateway (manual card-to-card only, by design)
- SMS/email delivery for invites/reset not wired (copyable link / DEBUG token)
- Support operator is a platform role; full operator UI is admin-oriented
- PWA icons are simple generated placeholders
- Password-reset token returned in API body only when `DEBUG=True`
- Celery not used; rely on cron/`process_subscriptions`
- Frontend TypeScript may need a local `npm run build` pass for production bundle polish

## Security notes

- Tenant isolation enforced in querysets/permissions
- Private receipts via authenticated media endpoints
- Invitation tokens random, expiring, single-use, revocable
- Duplicate subscription payment approval prevented with `select_for_update`
- Money stored as `BigIntegerField` (toman)
