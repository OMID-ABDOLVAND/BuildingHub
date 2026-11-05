import { useEffect, useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import { formatDate } from '@/lib/format'
import type { Unit, UnitOccupancy } from '@/types'
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
  Table,
  Td,
  Th,
} from '@/components/ui'

type OccupancyRow = UnitOccupancy & { user_detail?: { full_name: string; username: string } }

export function ResidentsPage() {
  const { activeBuildingId, isManager } = useAuth()
  const [items, setItems] = useState<OccupancyRow[]>([])
  const [units, setUnits] = useState<Unit[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    unit_id: '',
    relationship_type: 'tenant',
    occupants_count: '1',
    start_date: new Date().toISOString().slice(0, 10),
  })

  useEffect(() => {
    if (!activeBuildingId) {
      setItems([])
      setUnits([])
      setLoading(false)
      return
    }
    setLoading(true)
    void Promise.all([
      api.get('/units/', { params: { building: activeBuildingId } }),
      api.get('/occupancies/', { params: { is_current: true } }),
    ])
      .then(([unitsRes, occRes]) => {
        const unitsList = unwrapList<Unit>(unitsRes.data)
        setUnits(unitsList)
        const ids = new Set(unitsList.map((u) => u.id))
        setItems(unwrapList<OccupancyRow>(occRes.data).filter((o) => ids.has(o.unit)))
      })
      .finally(() => setLoading(false))
  }, [activeBuildingId])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/occupancies/create-resident/', {
        ...form,
        unit_id: Number(form.unit_id),
        occupants_count: Number(form.occupants_count),
      })
      toast.success('ساکن ایجاد شد')
      setOpen(false)
      if (activeBuildingId) {
        setLoading(true)
        void Promise.all([
          api.get('/units/', { params: { building: activeBuildingId } }),
          api.get('/occupancies/', { params: { is_current: true } }),
        ])
          .then(([unitsRes, occRes]) => {
            const unitsList = unwrapList<Unit>(unitsRes.data)
            setUnits(unitsList)
            const ids = new Set(unitsList.map((u) => u.id))
            setItems(unwrapList<OccupancyRow>(occRes.data).filter((o) => ids.has(o.unit)))
          })
          .finally(() => setLoading(false))
      }
    } finally {
      setSaving(false)
    }
  }

  if (!isManager) {
    return <EmptyState title="دسترسی محدود" description="این بخش فقط برای مدیر است." />
  }

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="ساکنین"
        subtitle="مدیریت سکونت و ایجاد حساب ساکن"
        actions={<Button onClick={() => setOpen(true)}>ایجاد ساکن</Button>}
      />
      {items.length === 0 ? (
        <EmptyState title="ساکن فعالی ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>نام</Th>
              <Th>نام کاربری</Th>
              <Th>واحد</Th>
              <Th>نوع</Th>
              <Th>شروع</Th>
              <Th>نفرات</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.id}>
                <Td>{o.user_detail?.full_name || '—'}</Td>
                <Td>{o.user_detail?.username}</Td>
                <Td>{o.unit_number}</Td>
                <Td>{o.relationship_type === 'owner' ? 'مالک' : 'مستأجر'}</Td>
                <Td>{formatDate(o.start_date)}</Td>
                <Td>{o.occupants_count}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="ایجاد ساکن جدید" onClose={() => setOpen(false)}>
        <form className="max-h-[70vh] space-y-3 overflow-y-auto" onSubmit={onCreate}>
          <Card className="!p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label>نام کاربری</Label>
                <Input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
              </div>
              <div>
                <Label>رمز عبور</Label>
                <Input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
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
                <Label>ایمیل</Label>
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div>
                <Label>موبایل</Label>
                <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
            </div>
          </Card>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>واحد</Label>
              <Select required value={form.unit_id} onChange={(e) => setForm({ ...form, unit_id: e.target.value })}>
                <option value="">انتخاب کنید</option>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>
                    واحد {u.number}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>نوع سکونت</Label>
              <Select value={form.relationship_type} onChange={(e) => setForm({ ...form, relationship_type: e.target.value })}>
                <option value="tenant">مستأجر</option>
                <option value="owner">مالک</option>
              </Select>
            </div>
            <div>
              <Label>تعداد نفرات</Label>
              <Input type="number" min={1} value={form.occupants_count} onChange={(e) => setForm({ ...form, occupants_count: e.target.value })} />
            </div>
            <div>
              <Label>تاریخ شروع</Label>
              <Input type="date" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </div>
          </div>
          <Button disabled={saving} className="w-full">
            {saving ? 'در حال ایجاد…' : 'ایجاد ساکن'}
          </Button>
        </form>
      </Modal>
    </div>
  )
}
