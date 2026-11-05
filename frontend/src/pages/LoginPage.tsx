import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { Button, Card, Input, Label } from '@/components/ui'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('manager')
  const [password, setPassword] = useState('Manager123!')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(username, password)
      toast.success('ورود موفق')
      navigate('/app/dashboard')
    } catch {
      toast.error('نام کاربری یا رمز عبور نادرست است')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,#ccfbf1,transparent_40%),linear-gradient(160deg,#0b3d3a_0%,#115e59_45%,#0f172a_100%)]">
      <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, #fff 1px, transparent 0)', backgroundSize: '24px 24px' }} />
      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center px-4 py-10">
        <div className="grid w-full gap-8 lg:grid-cols-2 lg:items-center">
          <div className="text-white animate-fade-up">
            <div className="text-sm text-teal-100/80">BuildingHub</div>
            <h1 className="mt-3 text-4xl font-bold leading-tight sm:text-5xl">
              مدیریت مالی و اجرایی ساختمان، یکجا و شفاف
            </h1>
            <p className="mt-4 max-w-md text-teal-50/80">
              ثبت هزینه، تقسیم هوشمند، تأیید رسید و پیگیری تعمیرات — برای مدیر و ساکنین.
            </p>
          </div>
          <Card className="animate-fade-up max-w-md lg:mr-auto">
            <h2 className="text-xl font-bold">ورود به سامانه</h2>
            <p className="mt-1 text-sm text-muted">از حساب دمو یا حساب خودتان استفاده کنید.</p>
            <form className="mt-6 space-y-4" onSubmit={onSubmit}>
              <div>
                <Label>نام کاربری</Label>
                <Input value={username} onChange={(e) => setUsername(e.target.value)} required />
              </div>
              <div>
                <Label>رمز عبور</Label>
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>
              <Button className="w-full" disabled={loading}>
                {loading ? 'در حال ورود…' : 'ورود'}
              </Button>
            </form>
            <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-muted">
              مدیر: manager / Manager123!
              <br />
              ساکن: resident1 / Resident123!
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}