import { useEffect, useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import { debtStatuses, formatDateTime, formatToman, paymentStatuses } from '@/lib/format'
import { MediaPreview } from '@/components/MediaPreview'
import { openProtectedMedia } from '@/lib/media'
import type { Allocation, Payment } from '@/types'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  LoadingScreen,
  Modal,
  PageHeader,
  Select,
  Table,
  Td,
  Textarea,
  Th,
} from '@/components/ui'

function statusTone(status: string) {
  if (status === 'approved') return 'green'
  if (status === 'pending') return 'amber'
  if (status === 'rejected') return 'red'
  return 'slate'
}

export function ManagerPaymentsPage() {
  const { isManager, activeBuildingId } = useAuth()
  const [items, setItems] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [rejectId, setRejectId] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewType, setPreviewType] = useState('image/png')

  const showReceipt = (id: number) => {
    void openProtectedMedia('receipt', id, (url, contentType) => {
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return url
      })
      setPreviewType(contentType)
    })
  }

  const load = () => {
    setLoading(true)
    void api
      .get('/payments/', { params: { status: 'pending' } })
      .then((r) => {
        let list = unwrapList<Payment>(r.data)
        if (activeBuildingId) {
          list = list.filter(() => true)
        }
        setItems(list)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [activeBuildingId])

  const review = async (id: number, action: 'approve' | 'reject', rejection_reason?: string) => {
    await api.post(`/payments/${id}/review/`, { action, rejection_reason })
    toast.success(action === 'approve' ? 'پرداخت تأیید شد' : 'پرداخت رد شد')
    setRejectId(null)
    setReason('')
    load()
  }

  if (!isManager) {
    return <EmptyState title="دسترسی محدود" description="بررسی رسید فقط برای مدیر است." />
  }

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader title="بررسی رسیدها" subtitle="پرداخت‌های در انتظار تأیید" />
      {items.length === 0 ? (
        <EmptyState title="رسیدی در انتظار نیست" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>واحد</Th>
              <Th>هزینه</Th>
              <Th>مبلغ</Th>
              <Th>تاریخ</Th>
              <Th>رسید</Th>
              <Th>عملیات</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id}>
                <Td>{p.unit_number}</Td>
                <Td>{p.expense_title}</Td>
                <Td>{formatToman(p.amount)}</Td>
                <Td>{formatDateTime(p.created_at)}</Td>
                <Td>
                  <button
                    type="button"
                    className="text-brand-700 hover:underline"
                    onClick={() => showReceipt(p.id)}
                  >
                    مشاهده
                  </button>
                </Td>
                <Td className="space-x-2 space-x-reverse">
                  <Button variant="secondary" onClick={() => void review(p.id, 'approve')}>
                    تأیید
                  </Button>
                  <Button variant="danger" onClick={() => setRejectId(p.id)}>
                    رد
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={rejectId != null} title="رد پرداخت" onClose={() => setRejectId(null)}>
        <div className="space-y-3">
          <div>
            <Label>دلیل رد</Label>
            <Textarea required value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          <Button
            variant="danger"
            className="w-full"
            onClick={() => rejectId != null && reason.trim() && void review(rejectId, 'reject', reason)}
          >
            ثبت رد
          </Button>
        </div>
      </Modal>
      <MediaPreview
        open={!!previewUrl}
        title="رسید پرداخت"
        url={previewUrl}
        contentType={previewType}
        onClose={() => {
          if (previewUrl) URL.revokeObjectURL(previewUrl)
          setPreviewUrl(null)
        }}
      />
    </div>
  )
}

export function ResidentPaymentsPage() {
  const [items, setItems] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewType, setPreviewType] = useState('image/png')

  const showReceipt = (id: number) => {
    void openProtectedMedia('receipt', id, (url, contentType) => {
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return url
      })
      setPreviewType(contentType)
    })
  }

  useEffect(() => {
    void api
      .get('/payments/')
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader title="تاریخچه پرداخت" subtitle="وضعیت رسیدهای ارسالی" />
      {items.length === 0 ? (
        <EmptyState title="پرداختی ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>هزینه</Th>
              <Th>مبلغ</Th>
              <Th>وضعیت</Th>
              <Th>تاریخ</Th>
              <Th>رسید</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id}>
                <Td>{p.expense_title}</Td>
                <Td>{formatToman(p.amount)}</Td>
                <Td>
                  <Badge tone={statusTone(p.status)}>{paymentStatuses[p.status] || p.status}</Badge>
                </Td>
                <Td>{formatDateTime(p.created_at)}</Td>
                <Td>
                  {p.receipt ? (
                    <button
                      type="button"
                      className="text-brand-700 hover:underline"
                      onClick={() => showReceipt(p.id)}
                    >
                      مشاهده
                    </button>
                  ) : (
                    '—'
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <MediaPreview
        open={!!previewUrl}
        title="رسید پرداخت"
        url={previewUrl}
        contentType={previewType}
        onClose={() => {
          if (previewUrl) URL.revokeObjectURL(previewUrl)
          setPreviewUrl(null)
        }}
      />
    </div>
  )
}

export function PaymentSubmitPage() {
  const [allocations, setAllocations] = useState<Allocation[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    allocation_id: '',
    amount: '',
    description: '',
    receipt: null as File | null,
  })

  useEffect(() => {
    void api
      .get('/allocations/')
      .then((r) => {
        const list = unwrapList<Allocation>(r.data).filter((a) => a.remaining > 0)
        setAllocations(list)
        if (list[0]) setForm((f) => ({ ...f, allocation_id: String(list[0].id), amount: String(list[0].remaining) }))
      })
      .finally(() => setLoading(false))
  }, [])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.receipt) return toast.error('فایل رسید الزامی است')
    setSaving(true)
    try {
      const body = new FormData()
      body.append('allocation_id', form.allocation_id)
      body.append('amount', form.amount)
      body.append('description', form.description)
      body.append('receipt', form.receipt)
      await api.post('/payments/', body, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success('رسید ارسال شد')
      setForm({ allocation_id: '', amount: '', description: '', receipt: null })
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader title="ثبت پرداخت" subtitle="ارسال رسید برای تأیید مدیر" />
      <Card className="max-w-xl">
        {allocations.length === 0 ? (
          <EmptyState title="بدهی قابل پرداخت ندارید" />
        ) : (
          <form className="space-y-4" onSubmit={onSubmit}>
            <div>
              <Label>بدهی</Label>
              <Select
                required
                value={form.allocation_id}
                onChange={(e) => {
                  const id = e.target.value
                  const row = allocations.find((a) => String(a.id) === id)
                  setForm({
                    ...form,
                    allocation_id: id,
                    amount: row ? String(row.remaining) : form.amount,
                  })
                }}
              >
                {allocations.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.expense_title} — واحد {a.unit_number} — مانده {a.remaining.toLocaleString('en-US')}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>مبلغ (تومان)</Label>
              <Input required type="number" min={1} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div>
              <Label>توضیحات</Label>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div>
              <Label>فایل رسید</Label>
              <Input
                required
                type="file"
                accept="image/*,.pdf"
                onChange={(e) => setForm({ ...form, receipt: e.target.files?.[0] || null })}
              />
            </div>
            <Button disabled={saving}>{saving ? 'در حال ارسال…' : 'ارسال رسید'}</Button>
          </form>
        )}
      </Card>
    </div>
  )
}
