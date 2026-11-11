import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '@/lib/api'
import type { User } from '@/types'

type AuthContextValue = {
  user: User | null
  loading: boolean
  isManager: boolean
  isSuperAdmin: boolean
  activeBuildingId: number | null
  setActiveBuildingId: (id: number | null) => void
  login: (username: string, password: string) => Promise<User>
  logout: () => void
  refreshMe: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeBuildingId, setActiveBuildingId] = useState<number | null>(() => {
    const saved = localStorage.getItem('activeBuilding')
    return saved ? Number(saved) : null
  })

  const refreshMe = useCallback(async () => {
    const token = localStorage.getItem('access')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const { data } = await api.get<User>('/auth/me/')
      setUser(data)
      const buildings = data.managed_buildings.length
        ? data.managed_buildings
        : data.member_buildings
      if (buildings.length && (activeBuildingId == null || !buildings.includes(activeBuildingId))) {
        setActiveBuildingId(buildings[0])
        localStorage.setItem('activeBuilding', String(buildings[0]))
      }
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [activeBuildingId])

  useEffect(() => {
    void refreshMe()
  }, [])

  const login = async (username: string, password: string) => {
    const { data } = await api.post('/auth/login/', { username, password })
    localStorage.setItem('access', data.access)
    localStorage.setItem('refresh', data.refresh)
    const me = await api.get<User>('/auth/me/')
    setUser(me.data)
    const buildings = me.data.managed_buildings.length
      ? me.data.managed_buildings
      : me.data.member_buildings
    if (buildings.length) {
      setActiveBuildingId(buildings[0])
      localStorage.setItem('activeBuilding', String(buildings[0]))
    }
    return me.data
  }

  const logout = () => {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    setUser(null)
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      isManager:
        !!user &&
        (user.roles.includes('manager') ||
          user.roles.includes('building_manager') ||
          user.managed_buildings.length > 0),
      isSuperAdmin:
        !!user && (user.roles.includes('super_admin') || user.platform_role === 'SUPER_ADMIN'),
      activeBuildingId,
      setActiveBuildingId: (id: number | null) => {
        setActiveBuildingId(id)
        if (id != null) localStorage.setItem('activeBuilding', String(id))
      },
      login,
      logout,
      refreshMe,
    }),
    [user, loading, activeBuildingId, refreshMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}