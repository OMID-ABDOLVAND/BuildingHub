import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import {
  formatDateTime,
  maintenanceStatuses,
  priorities,
} from '@/lib/format'
import { MediaPreview } from '@/components/MediaPreview'
import { openProtectedMedia } from '@/lib/media'
import type { Maintenance, Unit } from '@/types'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  LoadingScreen,
  PageHeader,
  Select,
  Table,
  Td,
  Textarea,
  Th,
} from '@/components/ui'

const maintenanceCategories: Record<string, string> = {
  plumbing: 'لوله‌کشی',
  electrical: 'برق',
  elevator: 'آسانسور',
  structural: 'سازه‌ای',
  cleaning: 'نظافت',
  other: 'سایر',
}

function priorityTone(p: string) {
  if (p === 'urgent') return 'red'
  if (p === 'high') return 'amber'
  return 'slate'
}

export function MaintenanceListPage() {
  const { isManager, activeBuildingId } = useAuth()
  const [items, setItems] = useState<Maintenance[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = activeBuildingId ? { building: activeBuildingId } : {}
    void api
      .get('/maintenance/', { params })
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }, [activeBuildingId])

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="درخواست‌های تعمیر"
        subtitle="پیگیری وضعیت و گفتگو"
        actions={
          !isManager ? (
            <Link to="/app/maintenance/new">
              <Button>درخواست جدید</Button>
            </Link>
          ) : null
        }
      />
      {items.length === 0 ? (
        <EmptyState title="درخواستی ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>عنوان</Th>
              <Th>کد پیگیری</Th>
              <Th>واحد</Th>
              <Th>اولویت</Th>
              <Th>وضعیت</Th>
              <Th></Th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id}>
                <Td>{m.title}</Td>
                <Td>{m.tracking_code}</Td>
                <Td>{m.unit_number}</Td>
                <Td>
                  <Badge tone={priorityTone(m.priority)}>{priorities[m.priority] || m.priority}</Badge>
                </Td>
                <Td>
                  <Badge tone="teal">{maintenanceStatuses[m.status] || m.status}</Badge>
                </Td>
                <Td>
                  <Link className="text-brand-700 hover:underline" to={`/app/maintenance/${m.id}`}>
                    جزئیات
                  </Link>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  )
}

export function MaintenanceCreatePage() {
  const { activeBuildingId } = useAuth()
  const navigate = useNavigate()
  const [units, setUnits] = useState<Unit[]>([])
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    unit: '',
    title: '',
    category: 'other',
    priority: 'medium',
    description: '',
    image: null as File | null,
  })

  useEffect(() => {
    void api.get('/units/').then((r) => {
      const list = unwrapList<Unit>(r.data)
      setUnits(list)
      if (list[0]) setForm((f) => ({ ...f, unit: String(list[0].id) }))
    })
  }, [])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const unit = units.find((u) => String(u.id) === form.unit)
    if (!unit) return toast.error('واحد انتخاب نشده')
    setSaving(true)
    try {
      const body = new FormData()
      body.append('building', String(unit.building))
      body.append('unit', form.unit)
      body.append('title', form.title)
      body.append('category', form.category)
      body.append('priority', form.priority)
      body.append('description', form.description)
      if (form.image) body.append('image', form.image)
      const { data } = await api.post('/maintenance/', body, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success('درخواست ثبت شد')
      navigate(`/app/maintenance/${data.id}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader title="ثبت درخواست تعمیر" />
      <Card className="max-w-2xl">
        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <Label>واحد</Label>
            <Select required value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.building_name} — واحد {u.number}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>عنوان</Label>
            <Input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>دسته</Label>
              <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {Object.entries(maintenanceCategories).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>اولویت</Label>
              <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {Object.entries(priorities).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </Select>
            </div>
          </div>
          <div>
            <Label>شرح مشکل</Label>
            <Textarea required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <Label>تصویر (اختیاری)</Label>
            <Input type="file" accept="image/*" onChange={(e) => setForm({ ...form, image: e.target.files?.[0] || null })} />
          </div>
          <Button disabled={saving}>{saving ? 'در حال ثبت…' : 'ثبت درخواست'}</Button>
        </form>
      </Card>
    </div>
  )
}

export function MaintenanceDetailPage() {
  const { id } = useParams()
  const { isManager } = useAuth()
  const [item, setItem] = useState<Maintenance | null>(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewType, setPreviewType] = useState('image/png')
  const [statusForm, setStatusForm] = useState({
    status: 'under_review',
    resolution_notes: '',
    rejection_reason: '',
    action_taken: '',
  })

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get(`/maintenance/${id}/`)
      setItem(data)
      setStatusForm((s) => ({ ...s, status: data.status }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [id])

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return
    await api.post(`/maintenance/${id}/add_message/`, { body: message })
    setMessage('')
    toast.success('پیام ارسال شد')
    await load()
  }

  const setStatus = async (e: FormEvent) => {
    e.preventDefault()
    await api.post(`/maintenance/${id}/set_status/`, statusForm)
    toast.success('وضعیت به‌روز شد')
    await load()
  }

  if (loading) return <LoadingScreen />
  if (!item) return <EmptyState title="درخواست یافت نشد" />

  return (
    <div>
      <PageHeader
        title={item.title}
        subtitle={`${item.tracking_code} • واحد ${item.unit_number}`}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="space-y-2 text-sm lg:col-span-1">
          <div>
            وضعیت:{' '}
            <Badge tone="teal">{maintenanceStatuses[item.status] || item.status}</Badge>
          </div>
          <div>دسته: {maintenanceCategories[item.category] || item.category}</div>
          <div>اولویت: {priorities[item.priority]}</div>
          <div className="text-muted">{item.description}</div>
          {item.image ? (
            <button
              type="button"
              className="text-brand-700 hover:underline"
              onClick={() =>
                void openProtectedMedia('maintenance', item.id, (url, contentType) => {
                  setPreviewUrl((prev) => {
                    if (prev) URL.revokeObjectURL(prev)
                    return url
                  })
                  setPreviewType(contentType)
                })
              }
            >
              مشاهده تصویر
            </button>
          ) : null}
        </Card>
        <Card className="lg:col-span-2">
          <h3 className="mb-3 font-semibold">گفتگو</h3>
          <div className="mb-4 max-h-80 space-y-3 overflow-y-auto">
            {(item.messages || []).map((m) => (
              <div key={m.id} className="rounded-xl border border-line bg-slate-50 p-3 text-sm">
                <div className="mb-1 flex items-center justify-between text-xs text-muted">
                  <span>{m.sender_name}</span>
                  <span>{formatDateTime(m.created_at)}</span>
                </div>
                {m.is_internal ? <Badge tone="amber">داخلی</Badge> : null}
                <p className="mt-1">{m.body}</p>
              </div>
            ))}
          </div>
          <form className="flex gap-2" onSubmit={sendMessage}>
            <Input
              className="flex-1"
              placeholder="پیام خود را بنویسید…"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
            <Button type="submit">ارسال</Button>
          </form>
        </Card>
      </div>

      {isManager ? (
        <Card className="mt-4 max-w-2xl">
          <h3 className="mb-3 font-semibold">تغییر وضعیت (مدیر)</h3>
          <form className="space-y-3" onSubmit={setStatus}>
            <div>
              <Label>وضعیت</Label>
              <Select value={statusForm.status} onChange={(e) => setStatusForm({ ...statusForm, status: e.target.value })}>
                {Object.entries(maintenanceStatuses).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>اقدام انجام‌شده</Label>
              <Textarea value={statusForm.action_taken} onChange={(e) => setStatusForm({ ...statusForm, action_taken: e.target.value })} />
            </div>
            <div>
              <Label>یادداشت حل</Label>
              <Textarea value={statusForm.resolution_notes} onChange={(e) => setStatusForm({ ...statusForm, resolution_notes: e.target.value })} />
            </div>
            <div>
              <Label>دلیل رد (در صورت رد)</Label>
              <Textarea value={statusForm.rejection_reason} onChange={(e) => setStatusForm({ ...statusForm, rejection_reason: e.target.value })} />
            </div>
            <Button type="submit">ذخیره وضعیت</Button>
          </form>
        </Card>
      ) : null}
      <MediaPreview
        open={!!previewUrl}
        title="تصویر درخواست"
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
