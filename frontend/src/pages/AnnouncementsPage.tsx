import { useEffect, useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { Announcement } from '@/types'
import {
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  LoadingScreen,
  Modal,
  PageHeader,
  Select,
  Textarea,
} from '@/components/ui'

export function AnnouncementsPage() {
  const { isManager, activeBuildingId } = useAuth()
  const [items, setItems] = useState<Announcement[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ title: '', body: '', is_published: true })
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    const params = activeBuildingId ? { building: activeBuildingId } : {}
    void api
      .get('/announcements/', { params })
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [activeBuildingId])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!activeBuildingId) return toast.error('ساختمان انتخاب نشده')
    setSaving(true)
    try {
      await api.post('/announcements/', { ...form, building: activeBuildingId })
      toast.success('اطلاعیه منتشر شد')
      setOpen(false)
      load()
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="اطلاعیه‌ها"
        subtitle="پیام‌های ساختمان"
        actions={
          isManager ? (
            <Button onClick={() => setOpen(true)} disabled={!activeBuildingId}>
              اطلاعیه جدید
            </Button>
          ) : null
        }
      />
      {items.length === 0 ? (
        <EmptyState title="اطلاعیه‌ای وجود ندارد" />
      ) : (
        <div className="space-y-4">
          {items.map((a) => (
            <Card key={a.id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="text-lg font-semibold">{a.title}</h3>
                <div className="text-xs text-muted">{formatDateTime(a.created_at)}</div>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{a.body}</p>
              <div className="mt-3 text-xs text-muted">توسط {a.created_by_name}</div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} title="انتشار اطلاعیه" onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={onCreate}>
          <div>
            <Label>عنوان</Label>
            <Input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div>
            <Label>متن</Label>
            <Textarea required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
          </div>
          <div>
            <Label>وضعیت انتشار</Label>
            <Select
              value={form.is_published ? '1' : '0'}
              onChange={(e) => setForm({ ...form, is_published: e.target.value === '1' })}
            >
              <option value="1">منتشر شود</option>
              <option value="0">پیش‌نویس</option>
            </Select>
          </div>
          <Button disabled={saving} className="w-full">
            {saving ? 'در حال انتشار…' : 'انتشار'}
          </Button>
        </form>
      </Modal>
    </div>
  )
}
