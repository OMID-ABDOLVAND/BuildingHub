import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, Outlet, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, unwrapList } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button, Card, Input, Label } from '@/components/ui'
import { formatToman } from '@/lib/format'

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8">…</div>
  if (!user) return <Navigate to="/login" replace />
  if (!user.roles.includes('super_admin') && user.platform_role !== 'SUPER_ADMIN') {
    return <Navigate to="/app/dashboard" replace />
  }
  return <>{children}</>
}

export function AdminShell() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const links = [
    { to: '/admin', label: 'داشبورد' },
    { to: '/admin/buildings', label: 'ساختمان‌ها' },
    { to: '/admin/managers', label: 'مدیران' },
    { to: '/admin/plans', label: 'پلن‌ها' },
    { to: '/admin/payments', label: 'پرداخت‌ها' },
    { to: '/admin/subscriptions', label: 'اشتراک‌ها' },
    { to: '/admin/support', label: 'پشتیبانی' },
    { to: '/admin/settings', label: 'تنظیمات' },
  ]
  return (
    <AdminGuard>
      <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
        <aside className="border-l bg-[#111827] text-slate-100">
          <div className="p-5 text-lg font-bold">BuildingHub Admin</div>
          <nav className="space-y-1 px-3 pb-6">
            {links.map((l) => (
              <Link key={l.to} to={l.to} className="block rounded-lg px-3 py-2 text-sm hover:bg-white/10">
                {l.label}
              </Link>
            ))}
            <button
              className="mt-4 block w-full rounded-lg px-3 py-2 text-right text-sm text-rose-200 hover:bg-white/10"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              خروج
            </button>
          </nav>
        </aside>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </AdminGuard>
  )
}

export function AdminDashboardPage() {
  const [stats, setStats] = useState<any>(null)
  useEffect(() => {
    void api.get('/admin/dashboard/stats/').then((r) => setStats(r.data))
  }, [])
  if (!stats) return <div>در حال بارگذاری…</div>
  const items = [
    ['ساختمان‌ها', stats.total_buildings],
    ['فعال', stats.active_buildings],
    ['در انتظار', stats.pending_buildings],
    ['مدیران', stats.total_managers],
    ['ساکنین', stats.total_residents],
    ['واحدها', stats.total_apartments],
    ['اشتراک فعال', stats.active_subscriptions],
    ['ارفاق', stats.grace_period_subscriptions],
    ['منقضی', stats.expired_subscriptions],
    ['پرداخت معلق', stats.pending_payments],
    ['درآمد ثبت‌شده', formatToman(stats.recorded_subscription_revenue)],
    ['تیکت باز', stats.open_support_tickets],
  ]
  return (
    <div>
      <h1 className="text-2xl font-bold">داشبورد پلتفرم</h1>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {items.map(([label, value]) => (
          <Card key={String(label)}>
            <div className="text-xs text-muted">{label}</div>
            <div className="mt-2 text-xl font-bold">{value}</div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function AdminBuildingsPage() {
  const [buildings, setBuildings] = useState<any[]>([])
  const load = async () => {
    const { data } = await api.get('/admin/buildings/')
    setBuildings(unwrapList(data))
  }
  useEffect(() => {
    void load()
  }, [])
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">ساختمان‌ها</h1>
      <div className="space-y-2">
        {buildings.map((b) => (
          <Card key={b.id} className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-bold">{b.name}</div>
              <div className="text-xs text-muted">
                {b.status} · مدیر: {b.manager_name}
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                className="!py-1 !text-xs"
                onClick={async () => {
                  await api.post(`/admin/buildings/${b.id}/activate/`)
                  toast.success('فعال شد')
                  await load()
                }}
              >
                فعال
              </Button>
              <Button
                className="!py-1 !text-xs !bg-amber-700"
                onClick={async () => {
                  await api.post(`/admin/buildings/${b.id}/suspend/`)
                  toast.success('معلق شد')
                  await load()
                }}
              >
                تعلیق
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function AdminManagersPage() {
  const [managers, setManagers] = useState<any[]>([])
  useEffect(() => {
    void api.get('/admin/managers/').then((r) => setManagers(unwrapList(r.data)))
  }, [])
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">مدیران</h1>
      <div className="space-y-2">
        {managers.map((m) => (
          <Card key={m.id}>
            <div className="font-bold">{m.full_name}</div>
            <div className="text-xs text-muted">
              {m.username} · {m.phone} · {m.email}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function AdminPlansPage() {
  const [plans, setPlans] = useState<any[]>([])
  const [form, setForm] = useState({
    name: '',
    description: '',
    min_apartments: 1,
    max_apartments: 10,
    monthly_price: 500000,
    yearly_price: 5000000,
    display_order: 0,
  })
  const load = async () => {
    const { data } = await api.get('/plans/')
    setPlans(unwrapList(data))
  }
  useEffect(() => {
    void load()
  }, [])
  const create = async (e: FormEvent) => {
    e.preventDefault()
    await api.post('/plans/', form)
    toast.success('پلن ساخته شد')
    await load()
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">پلن‌های اشتراک</h1>
      <Card>
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={create}>
          <div>
            <Label>نام</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <Label>ترتیب</Label>
            <Input
              type="number"
              value={form.display_order}
              onChange={(e) => setForm({ ...form, display_order: Number(e.target.value) })}
            />
          </div>
          <div>
            <Label>حداقل واحد</Label>
            <Input
              type="number"
              value={form.min_apartments}
              onChange={(e) => setForm({ ...form, min_apartments: Number(e.target.value) })}
            />
          </div>
          <div>
            <Label>حداکثر واحد</Label>
            <Input
              type="number"
              value={form.max_apartments}
              onChange={(e) => setForm({ ...form, max_apartments: Number(e.target.value) })}
            />
          </div>
          <div>
            <Label>قیمت ماهانه</Label>
            <Input
              type="number"
              value={form.monthly_price}
              onChange={(e) => setForm({ ...form, monthly_price: Number(e.target.value) })}
            />
          </div>
          <div>
            <Label>قیمت سالانه</Label>
            <Input
              type="number"
              value={form.yearly_price}
              onChange={(e) => setForm({ ...form, yearly_price: Number(e.target.value) })}
            />
          </div>
          <div className="sm:col-span-2">
            <Label>توضیح</Label>
            <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <Button type="submit">ایجاد پلن</Button>
        </form>
      </Card>
      {plans.map((p) => (
        <Card key={p.id}>
          <div className="font-bold">{p.name}</div>
          <div className="text-sm text-muted">
            {p.min_apartments}–{p.max_apartments} · ماهانه {formatToman(p.monthly_price || 0)} · سالانه{' '}
            {formatToman(p.yearly_price || 0)}
          </div>
        </Card>
      ))}
    </div>
  )
}

export function AdminPaymentsPage() {
  const [payments, setPayments] = useState<any[]>([])
  const load = async () => {
    const { data } = await api.get('/admin/subscription-payments/')
    setPayments(unwrapList(data))
  }
  useEffect(() => {
    void load()
  }, [])
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">تأیید پرداخت اشتراک</h1>
      <div className="space-y-3">
        {payments.map((p) => (
          <Card key={p.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-bold">
                  {p.building_name} — {formatToman(p.amount_toman)}
                </div>
                <div className="text-xs text-muted">
                  {p.status} · {p.payer_name} · {p.tracking_number} · {p.plan_name}
                </div>
              </div>
              {['SUBMITTED', 'UNDER_REVIEW'].includes(p.status) ? (
                <div className="flex gap-2">
                  <Button
                    className="!py-1 !text-xs"
                    onClick={async () => {
                      await api.post(`/admin/subscription-payments/${p.id}/approve/`)
                      toast.success('تأیید شد')
                      await load()
                    }}
                  >
                    تأیید
                  </Button>
                  <Button
                    className="!py-1 !text-xs !bg-rose-700"
                    onClick={async () => {
                      const reason = window.prompt('دلیل رد؟') || ''
                      if (!reason) return
                      await api.post(`/admin/subscription-payments/${p.id}/reject/`, {
                        rejection_reason: reason,
                      })
                      toast.success('رد شد')
                      await load()
                    }}
                  >
                    رد
                  </Button>
                </div>
              ) : null}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function AdminSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([])
  useEffect(() => {
    void api.get('/admin/subscriptions/').then((r) => setSubs(unwrapList(r.data)))
  }, [])
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">اشتراک‌ها</h1>
      <div className="space-y-2">
        {subs.map((s) => (
          <Card key={s.id}>
            <div className="font-bold">
              #{s.id} {s.building_detail?.name || s.building} — {s.status}
            </div>
            <div className="text-xs text-muted">
              {s.plan_name_snapshot} · {s.duration} · {formatToman(s.final_price_toman)}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function AdminSupportPage() {
  const [tickets, setTickets] = useState<any[]>([])
  useEffect(() => {
    void api.get('/support/tickets/').then((r) => setTickets(unwrapList(r.data)))
  }, [])
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">مرکز پشتیبانی</h1>
      <div className="space-y-2">
        {tickets.map((t) => (
          <Card key={t.id}>
            <div className="font-bold">
              {t.ticket_number} — {t.subject}
            </div>
            <div className="text-xs text-muted">
              {t.status} · {t.created_by_name} · {t.building_name || 'بدون ساختمان'}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function AdminSettingsPage() {
  const [form, setForm] = useState<any>(null)
  useEffect(() => {
    void api.get('/platform/settings/').then((r) => setForm(r.data))
  }, [])
  if (!form) return <div>…</div>
  const save = async (e: FormEvent) => {
    e.preventDefault()
    const { data } = await api.patch('/platform/settings/', form)
    setForm(data)
    toast.success('ذخیره شد')
  }
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">تنظیمات پلتفرم</h1>
      <Card>
        <form className="space-y-3" onSubmit={save}>
          <div>
            <Label>روزهای ارفاق</Label>
            <Input
              type="number"
              value={form.grace_period_days}
              onChange={(e) => setForm({ ...form, grace_period_days: Number(e.target.value) })}
            />
          </div>
          <div>
            <Label>شماره کارت</Label>
            <Input
              value={form.destination_card_number}
              onChange={(e) => setForm({ ...form, destination_card_number: e.target.value })}
            />
          </div>
          <div>
            <Label>نام دارنده کارت</Label>
            <Input value={form.cardholder_name} onChange={(e) => setForm({ ...form, cardholder_name: e.target.value })} />
          </div>
          <div>
            <Label>بانک</Label>
            <Input value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
          </div>
          <div>
            <Label>دستورالعمل پرداخت</Label>
            <textarea
              className="min-h-24 w-full rounded-xl border px-3 py-2 text-sm"
              value={form.payment_instructions}
              onChange={(e) => setForm({ ...form, payment_instructions: e.target.value })}
            />
          </div>
          <Button type="submit">ذخیره</Button>
        </form>
      </Card>
    </div>
  )
}
