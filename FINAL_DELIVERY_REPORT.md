# BuildingHub — Final Delivery Report

## Implemented features

- JWT auth (login / refresh / me / register)
- Buildings, units, memberships, occupancies + create-resident
- Expenses with equal / resident / area / custom allocation + preview + finalize + cancel
- Payments with receipt upload, partial payments, approve/reject + audit
- Maintenance requests, messages, status workflow
- Announcements + in-app notifications
- Manager/resident dashboards, reports, audit logs
- Protected media endpoint
- Persian RTL React SaaS UI (Vazirmatn, teal architectural theme)
- Demo seed data + finance automated tests

## Technologies

- Backend: Django 5, DRF, SimpleJWT, drf-spectacular, PostgreSQL 16 (Docker :5433)
- Frontend: React 19, TypeScript, Vite 6, Tailwind 4, Axios, React Router 7

## Demo credentials

- Manager: `manager` / `Manager123!`
- Resident: `resident1` / `Resident123!`

## Start commands

```bash
cd E:\BuildingHub
docker compose up -d
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

cd frontend
npm install --registry https://registry.npmjs.org/
npm run dev
```

- UI: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/api/docs/

## Tests executed

```
python manage.py test finance.tests -v 2
Ran 10 tests — OK
```

Coverage: equal/resident/area/custom allocation, rounding, pending vs approved payments, reject reason, access isolation, snapshot stability.

## UI/UX skills installed

- frontend-design (Anthropic)
- web-design-guidelines / react-best-practices (Vercel) — attempted
- ui-ux-pro-max (+ related design skills)

## Known limitations

- Online payment / SMS / email out of v1 scope
- Excel/PDF export not included
- npm may need official registry if corporate mirror fails
- Postgres mapped to host port **5433**
