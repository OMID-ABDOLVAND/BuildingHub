import { useEffect, useState, type FormEvent } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import type { Building } from '@/types'
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
  Table,
  Td,
  Textarea,
  Th,
} from '@/components/ui'

export function BuildingsPage() {
  const { isManager } = useAuth()
  const [items, setItems] = useState<Building[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', address: '', description: '', contact_phone: '', contact_email: '' })
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    void api
      .get('/buildings/')
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/buildings/', form)
      toast.success('ساختمان ایجاد شد')
      setOpen(false)
      setForm({ name: '', address: '', description: '', contact_phone: '', contact_email: '' })
      load()
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="ساختمان‌ها"
        subtitle="مدیریت اطلاعات ساختمان و تماس"
        actions={
          isManager ? (
            <Button onClick={() => setOpen(true)}>ساختمان جدید</Button>
          ) : null
        }
      />
      {items.length === 0 ? (
        <EmptyState title="ساختمانی ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>نام</Th>
              <Th>آدرس</Th>
              <Th>واحدها</Th>
              <Th>مدیر</Th>
              <Th>وضعیت</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((b) => (
              <tr key={b.id}>
                <Td className="font-medium">{b.name}</Td>
                <Td>{b.address || '—'}</Td>
                <Td>{b.units_count}</Td>
                <Td>{b.manager_name}</Td>
                <Td>
                  <Badge tone={b.is_active ? 'green' : 'slate'}>{b.is_active ? 'فعال' : 'غیرفعال'}</Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="ثبت ساختمان جدید" onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={onCreate}>
          <div>
            <Label>نام ساختمان</Label>
            <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <Label>آدرس</Label>
            <Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <div>
            <Label>توضیحات</Label>
            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label>تلفن</Label>
              <Input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
            </div>
            <div>
              <Label>ایمیل</Label>
              <Input type="email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
            </div>
          </div>
          <Button disabled={saving} className="w-full">
            {saving ? 'در حال ذخیره…' : 'ذخیره'}
          </Button>
        </form>
      </Modal>
    </div>
  )
}
