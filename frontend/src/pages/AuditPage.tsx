import { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { EmptyState, LoadingScreen, PageHeader, Table, Td, Th } from '@/components/ui'

type AuditRow = {
  id: number
  user: string | null
  building: number
  action: string
  entity_type: string
  entity_id: number
  changes: Record<string, unknown>
  created_at: string
}

export function AuditPage() {
  const { isManager, activeBuildingId } = useAuth()
  const [items, setItems] = useState<AuditRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isManager) {
      setLoading(false)
      return
    }
    setLoading(true)
    const params = activeBuildingId ? { building: activeBuildingId } : {}
    void api
      .get('/audit-logs/', { params })
      .then((r) => setItems(r.data.results || []))
      .finally(() => setLoading(false))
  }, [isManager, activeBuildingId])

  if (!isManager) return <EmptyState title="دسترسی محدود" description="تاریخچه فقط برای مدیر است." />
  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader title="تاریخچه عملیات" subtitle="آخرین رویدادهای ثبت‌شده در سامانه" />
      {items.length === 0 ? (
        <EmptyState title="رویدادی ثبت نشده" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>زمان</Th>
              <Th>کاربر</Th>
              <Th>عملیات</Th>
              <Th>موجودیت</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <Td>{formatDateTime(a.created_at)}</Td>
                <Td>{a.user || 'سیستم'}</Td>
                <Td>{a.action}</Td>
                <Td>
                  {a.entity_type} #{a.entity_id}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  )
}
