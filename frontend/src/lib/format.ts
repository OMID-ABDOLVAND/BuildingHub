const faDigits = '۰۱۲۳۴۵۶۷۸۹'

export function toFaDigits(value: string | number): string {
  return String(value).replace(/\d/g, (d) => faDigits[Number(d)])
}

export function formatToman(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return '۰ تومان'
  return `${toFaDigits(Math.round(amount).toLocaleString('en-US'))} تومان`
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return toFaDigits(
      new Intl.DateTimeFormat('fa-IR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date(iso)),
    )
  } catch {
    return iso
  }
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return toFaDigits(
      new Intl.DateTimeFormat('fa-IR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(iso)),
    )
  } catch {
    return iso
  }
}

export const expenseCategories: Record<string, string> = {
  elevator: 'آسانسور',
  water: 'آب',
  electricity: 'برق',
  gas: 'گاز',
  cleaning: 'نظافت',
  repair: 'تعمیرات',
  security: 'نگهبانی',
  other: 'سایر',
}

export const allocationMethods: Record<string, string> = {
  equal: 'مساوی',
  resident: 'بر اساس نفرات',
  area: 'بر اساس متراژ',
  custom: 'سفارشی',
}

export const debtStatuses: Record<string, string> = {
  unpaid: 'پرداخت‌نشده',
  partially_paid: 'پرداخت ناقص',
  paid: 'تسویه‌شده',
  overdue: 'معوق',
}

export const paymentStatuses: Record<string, string> = {
  pending: 'در انتظار بررسی',
  approved: 'تأییدشده',
  rejected: 'ردشده',
}

export const maintenanceStatuses: Record<string, string> = {
  submitted: 'ثبت‌شده',
  under_review: 'در حال بررسی',
  needs_information: 'نیازمند اطلاعات',
  in_progress: 'در حال اقدام',
  resolved: 'حل‌شده',
  rejected: 'ردشده',
}

export const priorities: Record<string, string> = {
  low: 'کم',
  medium: 'متوسط',
  high: 'زیاد',
  urgent: 'فوری',
}