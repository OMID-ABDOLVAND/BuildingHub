import { useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/lib/api'
import { Button, Card, Input, Label, PageHeader } from '@/components/ui'

export function ProfilePage() {
  const { user, refreshMe } = useAuth()
  const [form, setForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    national_id: (user as { national_id?: string })?.national_id || '',
  })
  const [saving, setSaving] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.patch('/auth/me/', form)
      await refreshMe()
      toast.success('پروفایل به‌روز شد')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader title="پروفایل" subtitle="اطلاعات حساب کاربری" />
      <Card className="max-w-xl">
        <div className="mb-4 text-sm text-muted">
          نام کاربری: <span className="font-medium text-ink">{user?.username}</span>
        </div>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={onSubmit}>
          <div>
            <Label>نام</Label>
            <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          </div>
          <div>
            <Label>نام خانوادگی</Label>
            <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          </div>
          <div>
            <Label>ایمیل</Label>
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <Label>موبایل</Label>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label>کد ملی</Label>
            <Input value={form.national_id} onChange={(e) => setForm({ ...form, national_id: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Button disabled={saving}>{saving ? 'در حال ذخیره…' : 'ذخیره تغییرات'}</Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
