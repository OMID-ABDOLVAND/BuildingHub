import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, unwrapList } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button, Card, Input, Label } from '@/components/ui'
import { formatToman } from '@/lib/format'

type Plan = {
  id: number
  name: string
  description: string
  min_apartments: number
  max_apartments: number
  monthly_price: number | null
  yearly_price: number | null
  monthly_features: string[]
  yearly_features: string[]
}

function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#99f6e4,transparent_35%),linear-gradient(165deg,#ecfdf5_0%,#f8fafc_45%,#ccfbf1_100%)]">
      <header className="border-b border-line/60 bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link to="/" className="text-xl font-bold text-teal-900">
            BuildingHub
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            <Link to="/pricing" className="text-muted hover:text-teal-800">
              تعرفه‌ها
            </Link>
            <Link to="/login" className="text-muted hover:text-teal-800">
              ورود
            </Link>
            <Link to="/register">
              <Button className="!py-2">ثبت‌نام مدیر</Button>
            </Link>
          </nav>
        </div>
      </header>
      {children}
    </div>
  )
}

export function LandingPage() {
  return (
    <PublicShell>
      <main className="mx-auto grid max-w-6xl gap-10 px-4 py-16 lg:grid-cols-2 lg:items-center">
        <div className="animate-fade-up">
          <p className="text-sm font-medium text-teal-700">پلتفرم SaaS مدیریت ساختمان</p>
          <h1 className="mt-3 text-4xl font-bold leading-tight text-teal-950 sm:text-5xl">BuildingHub</h1>
          <p className="mt-4 max-w-lg text-lg text-slate-600">
            ثبت‌نام ساختمان، اشتراک ماهانه/سالانه، دعوت ساکن، هزینه‌ها، رسیدها و پشتیبانی — همه در یک سامانه فارسی.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register">
              <Button>شروع رایگان ثبت‌نام</Button>
            </Link>
            <Link to="/pricing">
              <Button className="!bg-white !text-teal-900 border border-line">مشاهده تعرفه‌ها</Button>
            </Link>
          </div>
        </div>
        <div className="rounded-3xl border border-teal-100 bg-teal-900 p-8 text-teal-50 shadow-xl animate-fade-up">
          <h2 className="text-2xl font-bold">چرا BuildingHub؟</h2>
          <ul className="mt-6 space-y-3 text-teal-100/90">
            <li>جداسازی کامل داده‌های هر ساختمان</li>
            <li>پرداخت کارت‌به‌کارت اشتراک با تأیید سوپرادمین</li>
            <li>دعوت امن ساکنین با لینک یک‌بارمصرف</li>
            <li>مدیریت مالی، تعمیرات و اعلان‌ها</li>
          </ul>
        </div>
      </main>
    </PublicShell>
  )
}

export function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  useEffect(() => {
    void api.get('/subscriptions/plans/public/').then((r) => setPlans(unwrapList(r.data) as Plan[]))
  }, [])
  return (
    <PublicShell>
      <main className="mx-auto max-w-6xl px-4 py-12">
        <h1 className="text-3xl font-bold text-teal-950">تعرفه‌های اشتراک</h1>
        <p className="mt-2 text-muted">قیمت‌ها از تنظیمات پلتفرم خوانده می‌شوند و در فرانت هاردکد نیستند.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {plans.map((p) => (
            <Card key={p.id}>
              <h2 className="text-xl font-bold">{p.name}</h2>
              <p className="mt-1 text-sm text-muted">{p.description}</p>
              <p className="mt-3 text-sm">
                ظرفیت: {p.min_apartments} تا {p.max_apartments} واحد
              </p>
              <div className="mt-4 space-y-1 text-sm">
                <div>ماهانه: {p.monthly_price != null ? formatToman(p.monthly_price) : '—'}</div>
                <div>سالانه: {p.yearly_price != null ? formatToman(p.yearly_price) : '—'}</div>
              </div>
              <Link to="/register" className="mt-5 inline-block">
                <Button className="w-full">انتخاب و ثبت‌نام</Button>
              </Link>
            </Card>
          ))}
          {!plans.length ? <p className="text-muted">هنوز پلنی تعریف نشده است.</p> : null}
        </div>
      </main>
    </PublicShell>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    password: '',
    password_confirm: '',
  })
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/auth/register-manager/', form)
      await login(form.phone, form.password)
      toast.success('ثبت‌نام موفق — ادامه آنبوردینگ')
      navigate('/onboarding')
    } catch {
      /* toast from interceptor */
    } finally {
      setLoading(false)
    }
  }

  return (
    <PublicShell>
      <main className="mx-auto max-w-lg px-4 py-12">
        <Card>
          <h1 className="text-2xl font-bold">ثبت‌نام مدیر ساختمان</h1>
          <form className="mt-6 space-y-3" onSubmit={onSubmit}>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>نام</Label>
                <Input
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>نام خانوادگی</Label>
                <Input
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <Label>موبایل</Label>
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
            </div>
            <div>
              <Label>ایمیل</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
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
            <Button className="w-full" disabled={loading}>
              {loading ? 'در حال ثبت…' : 'ثبت‌نام و ادامه'}
            </Button>
          </form>
        </Card>
      </main>
    </PublicShell>
  )
}

export function PasswordRecoveryPage() {
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [step, setStep] = useState<'request' | 'confirm'>('request')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')

  const requestReset = async (e: FormEvent) => {
    e.preventDefault()
    const { data } = await api.post('/auth/password-reset/', { email })
    toast.success(data.detail || 'درخواست ثبت شد')
    if (data.reset_token) {
      setToken(data.reset_token)
      setStep('confirm')
    }
  }

  const confirmReset = async (e: FormEvent) => {
    e.preventDefault()
    await api.post('/auth/password-reset/confirm/', {
      token,
      new_password: password,
      new_password_confirm: passwordConfirm,
    })
    toast.success('رمز عبور تغییر کرد')
    setStep('request')
  }

  return (
    <PublicShell>
      <main className="mx-auto max-w-md px-4 py-12">
        <Card>
          <h1 className="text-xl font-bold">بازیابی رمز عبور</h1>
          {step === 'request' ? (
            <form className="mt-4 space-y-3" onSubmit={requestReset}>
              <div>
                <Label>ایمیل</Label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <Button className="w-full">ارسال لینک بازیابی</Button>
            </form>
          ) : (
            <form className="mt-4 space-y-3" onSubmit={confirmReset}>
              <div>
                <Label>توکن</Label>
                <Input value={token} onChange={(e) => setToken(e.target.value)} required />
              </div>
              <div>
                <Label>رمز جدید</Label>
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>
              <div>
                <Label>تکرار رمز</Label>
                <Input
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  required
                />
              </div>
              <Button className="w-full">ثبت رمز جدید</Button>
            </form>
          )}
        </Card>
      </main>
    </PublicShell>
  )
}
