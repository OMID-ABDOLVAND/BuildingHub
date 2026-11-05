import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api, unwrapList } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { Notification } from '@/types'
import { Badge, Button, EmptyState, LoadingScreen, PageHeader, Table, Td, Th } from '@/components/ui'

export function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    void api
      .get('/notifications/')
      .then((r) => setItems(unwrapList(r.data)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const markRead = async (id: number) => {
    await api.post(`/notifications/${id}/mark_read/`)
    load()
  }

  const markAll = async () => {
    await api.post('/notifications/mark_all_read/')
    toast.success('همه اعلان‌ها خوانده شد')
    load()
  }

  if (loading) return <LoadingScreen />

  return (
    <div>
      <PageHeader
        title="اعلان‌ها"
        subtitle="رویدادهای اخیر سامانه"
        actions={
          <Button variant="secondary" onClick={() => void markAll()}>
            علامت‌گذاری همه
          </Button>
        }
      />
      {items.length === 0 ? (
        <EmptyState title="اعلانی ندارید" />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>عنوان</Th>
              <Th>متن</Th>
              <Th>زمان</Th>
              <Th>وضعیت</Th>
              <Th></Th>
            </tr>
          </thead>
          <tbody>
            {items.map((n) => (
              <tr key={n.id}>
                <Td className="font-medium">{n.title}</Td>
                <Td>{n.body}</Td>
                <Td>{formatDateTime(n.created_at)}</Td>
                <Td>
                  <Badge tone={n.is_read ? 'slate' : 'teal'}>{n.is_read ? 'خوانده' : 'جدید'}</Badge>
                </Td>
                <Td>
                  {!n.is_read ? (
                    <button className="text-brand-700 hover:underline" onClick={() => void markRead(n.id)}>
                      خواندم
                    </button>
                  ) : null}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  )
}
