import { useEffect, useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import type { Unit } from '@/types'
import {
  Badge,
  Button,
  EmptyState,
  Input,
  Label,
  LoadingScreen,
  Modal,
  PageHeader,
  Table,
  Td,
  Textarea,
  Th,
} from '@/components/ui'

export function UnitsPage() {
  const { activeBuildingId, isManager } = useAuth()
  const [items, setItems] = useState<Unit[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    number: '',
    floor: '0',
    area_sqm: '',
    resident_count: '1',
    description: '',
  })
  const [saving, setSaving] = useState(false)

  const load = () => {
    if (!activeBuildingId) {
      setItems([])
      setLoading(false)
      return
    }
    setLoading(true)
    void api
      .get('/units/', { params: { building: activeBuildingId } })
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
      await api.post('/units/', {
        building: activeBuildingId,
        number: form.number,
        floor: Number(form.floor),
        area_sqm: Number(form.area_sqm),
        resident_count: Number(form.resident_count),
        description: form.description,
      })
      toast.success('واحد ثبت شد')
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
        title="واحدها"
        subtitle="لیست واحدهای ساختمان فعال"
        actions={
          isManager ? (
            <Button onClick={() => setOpen(true)} disabled={!activeBuildingId}>
              واحد جدید
            </Button>
          ) : null
        }
      />
      {!activeBuildingId ? (
        <EmptyState title="ساختمان فعال انتخاب کنید" />
      ) : items.length === 0 ? (
        <EmptyState title="واحدی ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>شماره</Th>
              <Th>طبقه</Th>
              <Th>متراژ</Th>
              <Th>نفرات</Th>
              <Th>وضعیت</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((u) => (
              <tr key={u.id}>
                <Td className="font-medium">{u.number}</Td>
                <Td>{u.floor}</Td>
                <Td>{u.area_sqm} م²</Td>
                <Td>{u.resident_count}</Td>
                <Td>
                  <Badge tone={u.is_active ? 'green' : 'slate'}>{u.is_active ? 'فعال' : 'غیرفعال'}</Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="ثبت واحد جدید" onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={onCreate}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>شماره واحد</Label>
              <Input required value={form.number} onChange={(e) => setForm({ ...form, number: e.target.value })} />
            </div>
            <div>
              <Label>طبقه</Label>
              <Input type="number" value={form.floor} onChange={(e) => setForm({ ...form, floor: e.target.value })} />
            </div>
            <div>
              <Label>متراژ (م²)</Label>
              <Input required type="number" min={1} value={form.area_sqm} onChange={(e) => setForm({ ...form, area_sqm: e.target.value })} />
            </div>
            <div>
              <Label>تعداد ساکنین</Label>
              <Input type="number" min={1} value={form.resident_count} onChange={(e) => setForm({ ...form, resident_count: e.target.value })} />
            </div>
          </div>
          <div>
            <Label>توضیحات</Label>
            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <Button disabled={saving} className="w-full">
            {saving ? 'در حال ذخیره…' : 'ذخیره'}
          </Button>
        </form>
      </Modal>
    </div>
  )
}
