import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/lib/api'
import { expenseCategories, formatToman, toFaDigits } from '@/lib/format'
import {
  EmptyState,
  LoadingScreen,
  PageHeader,
  StatCard,
  Table,
  Td,
  Th,
} from '@/components/ui'

const chartColors = ['#0f766e', '#14b8a6', '#0d9488', '#115e59', '#ea580c', '#64748b']

type ReportData = {
  expenses_total: number
  approved_payments: number
  by_category: { category: string; total: number; count: number }[]
  per_unit: { unit: string; debt: number; paid: number; remaining: number }[]
  overdue_count: number
}

export function ReportsPage() {
  const { isManager, activeBuildingId } = useAuth()
  const [data, setData] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isManager || !activeBuildingId) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    void api
      .get('/reports/', { params: { building: activeBuildingId } })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [isManager, activeBuildingId])

  if (!isManager) return <EmptyState title="دسترسی محدود" description="گزارش‌ها فقط برای مدیر است." />
  if (!activeBuildingId) return <EmptyState title="ساختمان فعال انتخاب کنید" />
  if (loading) return <LoadingScreen />
  if (!data) return <EmptyState title="گزارشی یافت نشد" />

  const pieData = data.by_category.map((c) => ({
    name: expenseCategories[c.category] || c.category,
    value: c.total,
  }))

  return (
    <div>
      <PageHeader title="گزارش‌های مالی" subtitle="تحلیل هزینه و بدهی واحدها" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="مجموع هزینه‌های نهایی" value={formatToman(data.expenses_total)} />
        <StatCard label="پرداخت‌های تأییدشده" value={formatToman(data.approved_payments)} />
        <StatCard label="بدهی معوق (تعداد)" value={toFaDigits(data.overdue_count)} />
        <StatCard label="واحدهای دارای بدهی" value={toFaDigits(data.per_unit.length)} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-line bg-white p-4">
          <h3 className="mb-4 font-semibold">هزینه بر اساس دسته</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={chartColors[i % chartColors.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatToman(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-white p-4">
          <h3 className="mb-4 font-semibold">مانده بدهی واحدها</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.per_unit.slice(0, 12)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="unit" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => toFaDigits(v)} width={48} />
                <Tooltip formatter={(v: number) => formatToman(v)} />
                <Bar dataKey="remaining" fill="#0f766e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h3 className="mb-3 font-semibold">جزئیات واحدها</h3>
        <Table>
          <thead>
            <tr>
              <Th>واحد</Th>
              <Th>بدهی کل</Th>
              <Th>پرداخت‌شده</Th>
              <Th>مانده</Th>
            </tr>
          </thead>
          <tbody>
            {data.per_unit.map((u) => (
              <tr key={u.unit}>
                <Td>{u.unit}</Td>
                <Td>{formatToman(u.debt)}</Td>
                <Td>{formatToman(u.paid)}</Td>
                <Td>{formatToman(u.remaining)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  )
}
