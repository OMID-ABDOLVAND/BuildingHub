import { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/lib/api'
import { formatDate, formatToman, maintenanceStatuses } from '@/lib/format'
import { Badge, EmptyState, LoadingScreen, PageHeader, StatCard, Table, Td, Th } from '@/components/ui'

export function DashboardPage() {
  const { isManager, activeBuildingId } = useAuth()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const url = isManager
      ? `/dashboard/manager/${activeBuildingId ? `?building=${activeBuildingId}` : ''}`
      : '/dashboard/resident/'
    void api
      .get(url)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [isManager, activeBuildingId])

  if (loading) return <LoadingScreen />
  if (!data) return <EmptyState title="داده‌ای یافت نشد" />

  if (isManager) {
    return (
      <div>
        <PageHeader title="داشبورد مدیر" subtitle="خلاصه وضعیت مالی و اجرایی ساختمان" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="مجموع هزینه‌ها" value={formatToman(data.total_expenses)} />
          <StatCard label="پرداخت‌های تأییدشده" value={formatToman(data.total_approved_payments)} />
          <StatCard label="مانده بدهی" value={formatToman(data.total_outstanding)} />
          <StatCard label="بدهی معوق" value={formatToman(data.total_overdue)} />
          <StatCard label="واحدها" value={String(data.units_count)} />
          <StatCard label="ساکنین" value={String(data.residents_count)} />
          <StatCard label="درخواست‌های باز" value={String(data.open_maintenance)} />
          <StatCard label="رسیدهای در انتظار" value={String(data.pending_payments)} />
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div>
            <h2 className="mb-3 font-semibold">آخرین هزینه‌ها</h2>
            <Table>
              <thead>
                <tr>
                  <Th>عنوان</Th>
                  <Th>مبلغ</Th>
                  <Th>تاریخ</Th>
                </tr>
              </thead>
              <tbody>
                {(data.recent_expenses || []).map((e: any) => (
                  <tr key={e.id}>
                    <Td>{e.title}</Td>
                    <Td>{formatToman(e.amount)}</Td>
                    <Td>{formatDate(e.expense_date)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <div>
            <h2 className="mb-3 font-semibold">آخرین درخواست‌ها</h2>
            <Table>
              <thead>
                <tr>
                  <Th>عنوان</Th>
                  <Th>کد</Th>
                  <Th>وضعیت</Th>
                </tr>
              </thead>
              <tbody>
                {(data.recent_maintenance || []).map((m: any) => (
                  <tr key={m.id}>
                    <Td>{m.title}</Td>
                    <Td>{m.tracking_code}</Td>
                    <Td>
                      <Badge tone="teal">{maintenanceStatuses[m.status] || m.status}</Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="داشبورد ساکن" subtitle="وضعیت واحد، بدهی‌ها و درخواست‌ها" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="واحد من"
          value={data.apartment ? `واحد ${data.apartment.number}` : '—'}
          hint={data.apartment?.building}
        />
        <StatCard label="مانده بدهی" value={formatToman(data.outstanding_debts)} />
        <StatCard label="پرداخت‌شده" value={formatToman(data.total_paid)} />
        <StatCard label="اعلان خوانده‌نشده" value={String(data.unread_notifications)} />
      </div>
      <div className="mt-6">
        <h2 className="mb-3 font-semibold">سررسیدهای نزدیک</h2>
        {(data.upcoming_deadlines || []).length === 0 ? (
          <EmptyState title="بدهی فعالی ندارید" />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>عنوان</Th>
                <Th>مانده</Th>
                <Th>سررسید</Th>
              </tr>
            </thead>
            <tbody>
              {data.upcoming_deadlines.map((d: any) => (
                <tr key={d.id}>
                  <Td>{d.title}</Td>
                  <Td>{formatToman(d.remaining)}</Td>
                  <Td>{formatDate(d.due_date)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
    </div>
  )
}