import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, unwrapList } from '@/lib/api'
import { debtStatuses, formatDate, formatToman } from '@/lib/format'
import type { Allocation } from '@/types'
import { Badge, Button, EmptyState, LoadingScreen, PageHeader, StatCard, Table, Td, Th } from '@/components/ui'

export function MyApartmentPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void api
      .get('/dashboard/resident/')
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingScreen />
  const apt = data?.apartment

  return (
    <div>
      <PageHeader title="واحد من" subtitle="اطلاعات سکونت فعلی" />
      {!apt ? (
        <EmptyState title="واحد فعالی یافت نشد" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="ساختمان" value={apt.building} />
          <StatCard label="شماره واحد" value={`واحد ${apt.number}`} />
          <StatCard label="طبقه" value={String(apt.floor)} />
          <StatCard label="متراژ" value={`${apt.area_sqm} م²`} />
        </div>
      )}
    </div>
  )
}

export function MyExpensesPage() {
  const [items, setItems] = useState<Allocation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void api
      .get('/allocations/')
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="بدهی‌های من"
        subtitle="سهم واحد از هزینه‌های ساختمان"
        actions={
          <Link to="/app/payments/submit">
            <Button>ثبت پرداخت</Button>
          </Link>
        }
      />
      {items.length === 0 ? (
        <EmptyState title="بدهی ثبت‌شده‌ای ندارید" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>عنوان هزینه</Th>
              <Th>مبلغ سهم</Th>
              <Th>پرداخت‌شده</Th>
              <Th>مانده</Th>
              <Th>سررسید</Th>
              <Th>وضعیت</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <Td>{a.expense_title}</Td>
                <Td>{formatToman(a.amount)}</Td>
                <Td>{formatToman(a.approved_paid)}</Td>
                <Td>{formatToman(a.remaining)}</Td>
                <Td>{formatDate(a.expense_due_date)}</Td>
                <Td>
                  <Badge tone={a.status === 'paid' ? 'green' : a.status === 'overdue' ? 'red' : 'amber'}>
                    {debtStatuses[a.status] || a.status}
                  </Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  )
}
