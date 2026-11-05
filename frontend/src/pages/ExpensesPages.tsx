import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import {
  allocationMethods,
  expenseCategories,
  formatDate,
  formatToman,
} from '@/lib/format'
import type { Expense, Unit } from '@/types'
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

export function ExpensesListPage() {
  const { activeBuildingId, isManager } = useAuth()
  const [items, setItems] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = activeBuildingId ? { building: activeBuildingId } : {}
    void api
      .get('/expenses/', { params })
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }, [activeBuildingId])

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="هزینه‌ها"
        subtitle="ثبت، پیش‌نمایش تقسیم و نهایی‌سازی"
        actions={
          isManager ? (
            <Link to="/app/expenses/new">
              <Button>ثبت هزینه جدید</Button>
            </Link>
          ) : null
        }
      />
      {items.length === 0 ? (
        <EmptyState title="هنوز هزینه‌ای ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>عنوان</Th>
              <Th>مبلغ</Th>
              <Th>روش تقسیم</Th>
              <Th>وضعیت</Th>
              <Th>سررسید</Th>
              <Th></Th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id}>
                <Td>{e.title}</Td>
                <Td>{formatToman(e.amount)}</Td>
                <Td>{allocationMethods[e.allocation_method] || e.allocation_method}</Td>
                <Td>
                  <Badge tone={e.status === 'finalized' ? 'green' : e.status === 'draft' ? 'amber' : 'slate'}>
                    {e.status === 'finalized' ? 'نهایی‌شده' : e.status === 'draft' ? 'پیش‌نویس' : 'باطل'}
                  </Badge>
                </Td>
                <Td>{formatDate(e.due_date)}</Td>
                <Td>
                  <Link className="text-brand-700 hover:underline" to={`/app/expenses/${e.id}`}>
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

export function ExpenseCreatePage() {
  const { activeBuildingId } = useAuth()
  const navigate = useNavigate()
  const [units, setUnits] = useState<Unit[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [form, setForm] = useState({
    title: '',
    description: '',
    category: 'other',
    amount: '',
    expense_date: new Date().toISOString().slice(0, 10),
    due_date: new Date(Date.now() + 15 * 86400000).toISOString().slice(0, 10),
    allocation_method: 'equal',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!activeBuildingId) return
    void api.get('/units/', { params: { building: activeBuildingId } }).then((r) => {
      const list = unwrapList<Unit>(r.data)
      setUnits(list)
      setSelected(list.map((u) => u.id))
    })
  }, [activeBuildingId])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!activeBuildingId) return toast.error('ساختمان فعال انتخاب نشده')
    setSaving(true)
    try {
      const { data } = await api.post('/expenses/', {
        building: activeBuildingId,
        ...form,
        amount: Number(form.amount),
        included_unit_ids: selected,
      })
      toast.success('هزینه ثبت شد')
      navigate(`/app/expenses/${data.id}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader title="ثبت هزینه جدید" />
      <Card className="max-w-3xl">
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={onSubmit}>
          <div className="sm:col-span-2">
            <Label>عنوان</Label>
            <Input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div>
            <Label>مبلغ (تومان)</Label>
            <Input required type="number" min={1} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          <div>
            <Label>دسته</Label>
            <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {Object.entries(expenseCategories).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>تاریخ هزینه</Label>
            <Input type="date" value={form.expense_date} onChange={(e) => setForm({ ...form, expense_date: e.target.value })} />
          </div>
          <div>
            <Label>سررسید</Label>
            <Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
          </div>
          <div>
            <Label>روش تقسیم</Label>
            <Select value={form.allocation_method} onChange={(e) => setForm({ ...form, allocation_method: e.target.value })}>
              {Object.entries(allocationMethods).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
          </div>
          <div className="sm:col-span-2">
            <Label>توضیحات</Label>
            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label>واحدهای مشمول</Label>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {units.map((u) => (
                <label key={u.id} className="flex items-center gap-2 rounded-xl border border-line px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.includes(u.id)}
                    onChange={(e) =>
                      setSelected((prev) =>
                        e.target.checked ? [...prev, u.id] : prev.filter((id) => id !== u.id),
                      )
                    }
                  />
                  واحد {u.number} — طبقه {u.floor} — {u.area_sqm}م — {u.resident_count} نفر
                </label>
              ))}
            </div>
          </div>
          <div className="sm:col-span-2">
            <Button disabled={saving}>{saving ? 'در حال ذخیره…' : 'ذخیره پیش‌نویس'}</Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

export function ExpenseDetailPage() {
  const { id } = useParams()
  const { isManager } = useAuth()
  const [expense, setExpense] = useState<Expense | null>(null)
  const [preview, setPreview] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get(`/expenses/${id}/`)
      setExpense(data)
      if (data.status === 'draft' || data.status === 'finalized') {
        try {
          const p = await api.post(`/expenses/${id}/preview/`, {})
          setPreview(p.data)
        } catch {
          setPreview(null)
        }
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [id])

  if (loading) return <LoadingScreen />
  if (!expense) return <EmptyState title="هزینه یافت نشد" />

  const finalize = async () => {
    await api.post(`/expenses/${id}/finalize/`, {})
    toast.success('هزینه نهایی شد و بدهی‌ها ایجاد شدند')
    await load()
  }

  const cancel = async () => {
    await api.post(`/expenses/${id}/cancel/`, {})
    toast.success('هزینه باطل شد')
    await load()
  }

  return (
    <div>
      <PageHeader
        title={expense.title}
        subtitle={`${expenseCategories[expense.category] || expense.category} • ${formatToman(expense.amount)}`}
        actions={
          isManager && expense.status === 'draft' ? (
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void finalize()}>نهایی‌سازی</Button>
              <Button variant="danger" onClick={() => void cancel()}>
                ابطال
              </Button>
            </div>
          ) : isManager && expense.status === 'finalized' ? (
            <Button variant="danger" onClick={() => void cancel()}>
              ابطال هزینه
            </Button>
          ) : null
        }
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1 space-y-2 text-sm">
          <div>وضعیت: <Badge tone="teal">{expense.status}</Badge></div>
          <div>روش تقسیم: {allocationMethods[expense.allocation_method]}</div>
          <div>تاریخ: {formatDate(expense.expense_date)}</div>
          <div>سررسید: {formatDate(expense.due_date)}</div>
          <div className="text-muted">{expense.description || 'بدون توضیحات'}</div>
        </Card>
        <Card className="lg:col-span-2">
          <h3 className="mb-3 font-semibold">پیش‌نمایش / سهم واحدها</h3>
          {!preview ? (
            <EmptyState title="پیش‌نمایش موجود نیست" description="واحد مشمول و روش تقسیم را بررسی کنید." />
          ) : (
            <>
              <div className="mb-3 text-sm text-muted">
                جمع سهم‌ها: {formatToman(preview.sum)} از {formatToman(preview.total)}
              </div>
              <Table>
                <thead>
                  <tr>
                    <Th>واحد</Th>
                    <Th>نفرات</Th>
                    <Th>متراژ</Th>
                    <Th>سهم</Th>
                  </tr>
                </thead>
                <tbody>
                  {preview.items.map((item: any) => (
                    <tr key={item.unit_id}>
                      <Td>{item.unit_number}</Td>
                      <Td>{item.resident_count}</Td>
                      <Td>{item.area_sqm}</Td>
                      <Td>{formatToman(item.amount)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}