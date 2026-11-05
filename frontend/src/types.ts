export type User = {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  national_id?: string
  managed_buildings: number[]
  member_buildings: number[]
  roles: string[]
}

export type Building = {
  id: number
  name: string
  address: string
  description: string
  manager: number
  manager_name: string
  contact_phone: string
  contact_email: string
  is_active: boolean
  units_count: number
}

export type Unit = {
  id: number
  building: number
  building_name: string
  number: string
  floor: number
  area_sqm: number
  resident_count: number
  description: string
  is_active: boolean
}

export type UnitOccupancy = {
  id: number
  unit: number
  unit_number: string
  user: number
  relationship_type: string
  start_date: string
  end_date?: string | null
  occupants_count: number
  is_current: boolean
}

export type Expense = {
  id: number
  building: number
  title: string
  description: string
  category: string
  amount: number
  expense_date: string
  due_date: string
  invoice_image?: string | null
  allocation_method: string
  status: string
  included_unit_ids?: number[]
  allocations_count?: number
}

export type Allocation = {
  id: number
  expense: number
  expense_title: string
  expense_due_date: string
  unit: number
  unit_number: string
  building: number
  amount: number
  status: string
  approved_paid: number
  remaining: number
}

export type Payment = {
  id: number
  allocation: number
  amount: number
  description: string
  status: string
  rejection_reason: string
  unit_number: string
  expense_title: string
  allocation_remaining: number
  created_at: string
  receipt?: { id: number; file: string; original_name: string } | null
}

export type Maintenance = {
  id: number
  building: number
  unit: number
  unit_number: string
  title: string
  category: string
  description: string
  priority: string
  status: string
  tracking_code: string
  image?: string | null
  resolution_notes: string
  rejection_reason: string
  action_taken: string
  messages: {
    id: number
    body: string
    sender_name: string
    is_internal: boolean
    created_at: string
  }[]
  created_at: string
}

export type Announcement = {
  id: number
  building: number
  title: string
  body: string
  created_by_name: string
  created_at: string
}

export type Notification = {
  id: number
  title: string
  body: string
  type: string
  is_read: boolean
  link: string
  created_at: string
}