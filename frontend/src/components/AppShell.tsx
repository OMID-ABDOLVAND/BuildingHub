import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Bell,
  Building2,
  ClipboardList,
  FileText,
  Home,
  LogOut,
  Menu,
  Receipt,
  Settings,
  Shield,
  Users,
  Wrench,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { api, unwrapList } from '@/lib/api'
import type { Building } from '@/types'
import { cn } from './ui'

export function AppShell() {
  const { user, isManager, logout, activeBuildingId, setActiveBuildingId } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [buildings, setBuildings] = useState<Building[]>([])
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    void api.get('/buildings/').then((r) => setBuildings(unwrapList(r.data)))
    void api.get('/notifications/unread_count/').then((r) => setUnread(r.data.count || 0))
  }, [])

  const managerLinks = [
    { to: '/app/dashboard', label: 'داشبورد', icon: Home },
    { to: '/app/buildings', label: 'ساختمان‌ها', icon: Building2 },
    { to: '/app/units', label: 'واحدها', icon: Building2 },
    { to: '/app/residents', label: 'ساکنین', icon: Users },
    { to: '/app/expenses', label: 'هزینه‌ها', icon: Receipt },
    { to: '/app/payments', label: 'رسیدها', icon: FileText },
    { to: '/app/maintenance', label: 'تعمیرات', icon: Wrench },
    { to: '/app/announcements', label: 'اطلاعیه‌ها', icon: ClipboardList },
    { to: '/app/reports', label: 'گزارش‌ها', icon: FileText },
    { to: '/app/audit', label: 'تاریخچه', icon: Shield },
    { to: '/app/notifications', label: 'اعلان‌ها', icon: Bell },
    { to: '/app/profile', label: 'پروفایل', icon: Settings },
  ]

  const residentLinks = [
    { to: '/app/dashboard', label: 'داشبورد', icon: Home },
    { to: '/app/my-apartment', label: 'واحد من', icon: Building2 },
    { to: '/app/my-expenses', label: 'بدهی‌های من', icon: Receipt },
    { to: '/app/payments/submit', label: 'ثبت پرداخت', icon: Receipt },
    { to: '/app/my-payments', label: 'تاریخچه پرداخت', icon: FileText },
    { to: '/app/maintenance', label: 'تعمیرات', icon: Wrench },
    { to: '/app/announcements', label: 'اطلاعیه‌ها', icon: ClipboardList },
    { to: '/app/notifications', label: 'اعلان‌ها', icon: Bell },
    { to: '/app/profile', label: 'پروفایل', icon: Settings },
  ]

  const links = isManager ? managerLinks : residentLinks

  return (
    <div className="min-h-screen bg-surface lg:grid lg:grid-cols-[260px_1fr]">
      <aside
        className={cn(
          'fixed inset-y-0 right-0 z-40 w-[260px] border-l border-line bg-[#0b3d3a] text-teal-50 transition lg:static lg:translate-x-0',
          open ? 'translate-x-0' : 'translate-x-full lg:translate-x-0',
        )}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <div>
            <div className="text-lg font-bold tracking-tight">BuildingHub</div>
            <div className="text-xs text-teal-200/80">سامانه مدیریت ساختمان</div>
          </div>
          <button className="lg:hidden" onClick={() => setOpen(false)}>
            <X size={18} />
          </button>
        </div>
        <nav className="space-y-1 px-3 pb-6">
          {links.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition',
                  isActive ? 'bg-white/15 text-white' : 'text-teal-100/80 hover:bg-white/10 hover:text-white',
                )
              }
            >
              <item.icon size={18} />
              <span className="flex-1">{item.label}</span>
              {item.to.includes('notifications') && unread > 0 ? (
                <span className="rounded-md bg-accent px-1.5 py-0.5 text-[10px] text-white">
                  {unread}
                </span>
              ) : null}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-line bg-white/90 px-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <button className="rounded-lg border border-line p-2 lg:hidden" onClick={() => setOpen(true)}>
              <Menu size={18} />
            </button>
            {buildings.length > 0 ? (
              <select
                className="rounded-xl border border-line bg-white px-3 py-2 text-sm"
                value={activeBuildingId ?? ''}
                onChange={(e) => setActiveBuildingId(Number(e.target.value))}
              >
                {buildings.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-left sm:block">
              <div className="text-sm font-medium">{user?.full_name}</div>
              <div className="text-xs text-muted">{isManager ? 'مدیر ساختمان' : 'ساکن'}</div>
            </div>
            <button
              className="rounded-xl border border-line p-2 text-muted hover:text-danger"
              onClick={() => {
                logout()
                navigate('/login')
              }}
              title="خروج"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}