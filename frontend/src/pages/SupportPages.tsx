import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, unwrapList } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button, Card, Input, Label } from '@/components/ui'

export function SupportListPage() {
  const { activeBuildingId } = useAuth()
  const [tickets, setTickets] = useState<any[]>([])
  const [form, setForm] = useState({
    subject: '',
    category: 'OTHER',
    priority: 'NORMAL',
    description: '',
  })

  const load = async () => {
    const { data } = await api.get('/support/tickets/')
    setTickets(unwrapList(data))
  }

  useEffect(() => {
    void load()
  }, [])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    await api.post('/support/tickets/', {
      ...form,
      building: activeBuildingId,
    })
    toast.success('تیکت ثبت شد')
    setForm({ subject: '', category: 'OTHER', priority: 'NORMAL', description: '' })
    await load()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">پشتیبانی پلتفرم</h1>
      <Card>
        <h2 className="font-bold">تیکت جدید</h2>
        <form className="mt-3 space-y-3" onSubmit={create}>
          <div>
            <Label>موضوع</Label>
            <Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>دسته</Label>
              <select
                className="w-full rounded-xl border px-3 py-2 text-sm"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                <option value="TECHNICAL">فنی</option>
                <option value="SUBSCRIPTION">اشتراک</option>
                <option value="PAYMENT">پرداخت</option>
                <option value="ACCOUNT_ACCESS">دسترسی حساب</option>
                <option value="BUG_REPORT">باگ</option>
                <option value="FEATURE_REQUEST">ویژگی</option>
                <option value="OTHER">سایر</option>
              </select>
            </div>
            <div>
              <Label>اولویت</Label>
              <select
                className="w-full rounded-xl border px-3 py-2 text-sm"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              >
                <option value="LOW">کم</option>
                <option value="NORMAL">عادی</option>
                <option value="HIGH">بالا</option>
                <option value="URGENT">فوری</option>
              </select>
            </div>
          </div>
          <div>
            <Label>شرح</Label>
            <textarea
              className="min-h-24 w-full rounded-xl border px-3 py-2 text-sm"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
            />
          </div>
          <Button type="submit">ثبت تیکت</Button>
        </form>
      </Card>
      <Card>
        <h2 className="font-bold">تیکت‌های من</h2>
        <div className="mt-3 space-y-2">
          {tickets.map((t) => (
            <Link
              key={t.id}
              to={`/app/support/${t.id}`}
              className="block rounded-xl border p-3 text-sm hover:bg-slate-50"
            >
              <div className="font-medium">
                {t.ticket_number} — {t.subject}
              </div>
              <div className="text-xs text-muted">
                {t.status} · {t.priority}
              </div>
            </Link>
          ))}
          {!tickets.length ? <p className="text-muted">تیکتی نیست.</p> : null}
        </div>
      </Card>
    </div>
  )
}

export function SupportDetailPage() {
  const { id } = useParams()
  const [ticket, setTicket] = useState<any>(null)
  const [body, setBody] = useState('')

  const load = async () => {
    const { data } = await api.get(`/support/tickets/${id}/`)
    setTicket(data)
  }

  useEffect(() => {
    void load()
  }, [id])

  const reply = async (e: FormEvent) => {
    e.preventDefault()
    await api.post(`/support/tickets/${id}/reply/`, { body })
    setBody('')
    toast.success('پیام ارسال شد')
    await load()
  }

  if (!ticket) return <div>در حال بارگذاری…</div>

  return (
    <div className="space-y-4">
      <div>
        <Link to="/app/support" className="text-sm text-teal-700">
          بازگشت
        </Link>
        <h1 className="text-2xl font-bold">
          {ticket.ticket_number} — {ticket.subject}
        </h1>
        <p className="text-sm text-muted">
          {ticket.status} · {ticket.category} · {ticket.priority}
        </p>
      </div>
      <Card>
        <div className="space-y-3">
          {(ticket.messages || [])
            .filter((m: any) => !m.is_internal)
            .map((m: any) => (
              <div key={m.id} className="rounded-xl bg-slate-50 p-3 text-sm">
                <div className="font-medium">{m.sender_name}</div>
                <div className="mt-1 whitespace-pre-wrap">{m.body}</div>
              </div>
            ))}
        </div>
        {ticket.status !== 'CLOSED' ? (
          <form className="mt-4 space-y-3" onSubmit={reply}>
            <textarea
              className="min-h-24 w-full rounded-xl border px-3 py-2 text-sm"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
            />
            <Button type="submit">ارسال پاسخ</Button>
          </form>
        ) : null}
      </Card>
    </div>
  )
}
