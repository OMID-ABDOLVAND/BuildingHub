import { useEffect, useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { api, unwrapList } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Badge, Button, Card, Input, Label } from '@/components/ui'
import { formatToman } from '@/lib/format'

export function SubscriptionPage() {
  const { activeBuildingId } = useAuth()
  const [subs, setSubs] = useState<any[]>([])
  const [gate, setGate] = useState<any>(null)

  const load = async () => {
    if (!activeBuildingId) return
    const [s, g] = await Promise.all([
      api.get(`/subscriptions/mine/?building=${activeBuildingId}`),
      api.get(`/subscriptions/gate/?building=${activeBuildingId}`),
    ])
    setSubs(unwrapList(s.data))
    setGate(g.data)
  }

  useEffect(() => {
    void load()
  }, [activeBuildingId])

  const current = subs[0]

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">اشتراک ساختمان</h1>
      {gate && !gate.management_allowed ? (
        <Card className="border-amber-300 bg-amber-50">
          <div className="font-bold text-amber-900">هشدار اشتراک</div>
          <p className="mt-1 text-sm text-amber-800">
            وضعیت اشتراک: {gate.subscription_status || 'نامشخص'} — عملیات مدیریتی محدود است. می‌توانید تمدید کنید یا
            تیکت پشتیبانی باز کنید.
          </p>
          {gate.grace_ends_at ? (
            <p className="mt-1 text-xs text-amber-700">پایان دوره ارفاق: {new Date(gate.grace_ends_at).toLocaleString('fa-IR')}</p>
          ) : null}
        </Card>
      ) : null}
      {current ? (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-lg font-bold">{current.plan_name_snapshot}</div>
              <div className="text-sm text-muted">
                {current.duration === 'YEARLY' ? 'سالانه' : 'ماهانه'} · {formatToman(current.final_price_toman)}
              </div>
            </div>
            <Badge>{current.status}</Badge>
          </div>
          <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div>شروع: {current.starts_at ? new Date(current.starts_at).toLocaleDateString('fa-IR') : '—'}</div>
            <div>انقضا: {current.expires_at ? new Date(current.expires_at).toLocaleDateString('fa-IR') : '—'}</div>
            <div>ظرفیت: {current.apartment_capacity_snapshot} واحد</div>
            <div>مدیریت فعال: {current.management_allowed ? 'بله' : 'خیر'}</div>
          </div>
          <div className="mt-4">
            <a href="/onboarding">
              <Button>تمدید / پرداخت مجدد</Button>
            </a>
          </div>
        </Card>
      ) : (
        <Card>
          <p className="text-muted">اشتراکی یافت نشد.</p>
          <a href="/onboarding">
            <Button className="mt-3">شروع آنبوردینگ</Button>
          </a>
        </Card>
      )}
    </div>
  )
}

export function InvitationsPage() {
  const { activeBuildingId } = useAuth()
  const [invites, setInvites] = useState<any[]>([])
  const [units, setUnits] = useState<any[]>([])
  const [form, setForm] = useState({
    unit_id: '',
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    relationship_type: 'tenant',
    start_date: new Date().toISOString().slice(0, 10),
    occupants_count: 1,
  })

  const load = async () => {
    if (!activeBuildingId) return
    const [i, u] = await Promise.all([
      api.get(`/invitations/?building=${activeBuildingId}`),
      api.get(`/units/?building=${activeBuildingId}`),
    ])
    setInvites(unwrapList(i.data))
    setUnits(unwrapList(u.data))
  }

  useEffect(() => {
    void load()
  }, [activeBuildingId])

  const createInvite = async (e: FormEvent) => {
    e.preventDefault()
    if (!activeBuildingId) return
    const { data } = await api.post('/invitations/', {
      building_id: activeBuildingId,
      unit_id: Number(form.unit_id),
      first_name: form.first_name,
      last_name: form.last_name,
      phone: form.phone,
      email: form.email,
      relationship_type: form.relationship_type,
      start_date: form.start_date,
      occupants_count: form.occupants_count,
    })
    toast.success('دعوت ساخته شد')
    if (data.invite_url) {
      await navigator.clipboard.writeText(data.invite_url)
      toast.success('لینک دعوت کپی شد')
    }
    await load()
  }

  const revoke = async (id: number) => {
    await api.post(`/invitations/${id}/revoke/`)
    toast.success('دعوت باطل شد')
    await load()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">دعوت ساکنین</h1>
      <Card>
        <h2 className="font-bold">دعوت جدید</h2>
        <form className="mt-3 grid gap-3 sm:grid-cols-2" onSubmit={createInvite}>
          <div>
            <Label>واحد</Label>
            <select
              className="w-full rounded-xl border border-line px-3 py-2 text-sm"
              value={form.unit_id}
              onChange={(e) => setForm({ ...form, unit_id: e.target.value })}
              required
            >
              <option value="">انتخاب کنید</option>
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  واحد {u.number}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>نسبت</Label>
            <select
              className="w-full rounded-xl border border-line px-3 py-2 text-sm"
              value={form.relationship_type}
              onChange={(e) => setForm({ ...form, relationship_type: e.target.value })}
            >
              <option value="owner">مالک</option>
              <option value="tenant">مستأجر</option>
            </select>
          </div>
          <div>
            <Label>نام</Label>
            <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          </div>
          <div>
            <Label>نام خانوادگی</Label>
            <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          </div>
          <div>
            <Label>موبایل</Label>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <Label>ایمیل</Label>
            <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <Label>شروع سکونت</Label>
            <Input
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              required
            />
          </div>
          <div>
            <Label>تعداد نفرات</Label>
            <Input
              type="number"
              value={form.occupants_count}
              onChange={(e) => setForm({ ...form, occupants_count: Number(e.target.value) })}
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="submit">ایجاد لینک دعوت</Button>
          </div>
        </form>
      </Card>
      <Card>
        <h2 className="font-bold">دعوت‌های اخیر</h2>
        <div className="mt-3 space-y-2">
          {invites.map((inv) => (
            <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3 text-sm">
              <div>
                <div>
                  {inv.first_name} {inv.last_name} — واحد {inv.unit_number}
                </div>
                <div className="text-xs text-muted">
                  {inv.status} · {inv.phone || inv.email}
                </div>
              </div>
              <div className="flex gap-2">
                {inv.invite_url ? (
                  <Button
                    className="!py-1 !text-xs"
                    type="button"
                    onClick={() => navigator.clipboard.writeText(inv.invite_url)}
                  >
                    کپی لینک
                  </Button>
                ) : null}
                {inv.status === 'PENDING' ? (
                  <Button className="!py-1 !text-xs !bg-rose-700" type="button" onClick={() => revoke(inv.id)}>
                    ابطال
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
          {!invites.length ? <p className="text-muted">دعوتی نیست.</p> : null}
        </div>
      </Card>
    </div>
  )
}

export function AcceptInvitePage({ token }: { token: string }) {
  const [info, setInfo] = useState<any>(null)
  const [form, setForm] = useState({
    username: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
  })

  useEffect(() => {
    void api.get(`/invitations/public/${token}/`).then((r) => {
      setInfo(r.data)
      setForm((f) => ({
        ...f,
        username: r.data.phone || '',
        first_name: r.data.first_name || '',
        last_name: r.data.last_name || '',
      }))
    })
  }, [token])

  const accept = async (e: FormEvent) => {
    e.preventDefault()
    await api.post('/invitations/accept/', { token, ...form })
    toast.success('ثبت‌نام کامل شد — وارد شوید')
    window.location.href = '/login'
  }

  if (!info) return <div className="p-8">در حال بارگذاری…</div>
  if (!info.valid) {
    return (
      <div className="mx-auto max-w-md p-8">
        <Card>
          <h1 className="text-xl font-bold">دعوت‌نامه معتبر نیست</h1>
          <p className="mt-2 text-sm text-muted">وضعیت: {info.status}</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-md p-8">
      <Card>
        <h1 className="text-xl font-bold">پذیرش دعوت</h1>
        <p className="mt-2 text-sm text-muted">
          {info.building_name} — واحد {info.unit_number}
        </p>
        <form className="mt-4 space-y-3" onSubmit={accept}>
          <div>
            <Label>نام کاربری</Label>
            <Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
          </div>
          <div>
            <Label>نام</Label>
            <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          </div>
          <div>
            <Label>نام خانوادگی</Label>
            <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          </div>
          <div>
            <Label>رمز عبور</Label>
            <Input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          <div>
            <Label>تکرار رمز</Label>
            <Input
              type="password"
              value={form.password_confirm}
              onChange={(e) => setForm({ ...form, password_confirm: e.target.value })}
              required
            />
          </div>
          <Button className="w-full">تکمیل ثبت‌نام</Button>
        </form>
      </Card>
    </div>
  )
}
