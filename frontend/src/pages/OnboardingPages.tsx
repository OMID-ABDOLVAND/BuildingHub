import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, unwrapList } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button, Card, Input, Label } from '@/components/ui'
import { formatToman } from '@/lib/format'

type Plan = {
  id: number
  name: string
  min_apartments: number
  max_apartments: number
  monthly_price: number | null
  yearly_price: number | null
}

type PaySettings = {
  destination_card_number: string
  cardholder_name: string
  bank_name: string
  payment_instructions: string
}

export function OnboardingPage() {
  const { refreshMe, activeBuildingId, setActiveBuildingId } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [buildingId, setBuildingId] = useState<number | null>(activeBuildingId)
  const [subscriptionId, setSubscriptionId] = useState<number | null>(null)
  const [plans, setPlans] = useState<Plan[]>([])
  const [paySettings, setPaySettings] = useState<PaySettings | null>(null)
  const [building, setBuilding] = useState({
    name: '',
    address: '',
    floors_count: 1,
    apartments_count: 10,
    description: '',
    contact_phone: '',
    contact_email: '',
  })
  const [planId, setPlanId] = useState<number | null>(null)
  const [duration, setDuration] = useState<'MONTHLY' | 'YEARLY'>('MONTHLY')
  const [selectedSub, setSelectedSub] = useState<any>(null)
  const [payment, setPayment] = useState({
    payer_name: '',
    tracking_number: '',
    payment_date: new Date().toISOString().slice(0, 10),
    description: '',
  })
  const [receipt, setReceipt] = useState<File | null>(null)
  const [status, setStatus] = useState<any>(null)

  useEffect(() => {
    void api.get('/subscriptions/payment-settings/public/').then((r) => setPaySettings(r.data))
  }, [])

  useEffect(() => {
    if (building.apartments_count) {
      void api
        .get(`/subscriptions/plans/public/?apartments=${building.apartments_count}`)
        .then((r) => {
          const list = unwrapList(r.data) as Plan[]
          setPlans(list)
          if (list[0]) setPlanId(list[0].id)
        })
    }
  }, [building.apartments_count])

  const createBuilding = async (e: FormEvent) => {
    e.preventDefault()
    const { data } = await api.post('/onboarding/building/', building)
    setBuildingId(data.id)
    setActiveBuildingId(data.id)
    await refreshMe()
    toast.success('ساختمان ثبت شد')
    setStep(2)
  }

  const selectPlan = async (e: FormEvent) => {
    e.preventDefault()
    if (!buildingId || !planId) return
    const { data } = await api.post('/onboarding/select-plan/', {
      building_id: buildingId,
      plan_id: planId,
      duration,
    })
    setSubscriptionId(data.id)
    setSelectedSub(data)
    toast.success('پلن انتخاب شد')
    setStep(3)
  }

  const submitPayment = async (e: FormEvent) => {
    e.preventDefault()
    if (!subscriptionId || !receipt || !selectedSub) return
    const fd = new FormData()
    fd.append('subscription_id', String(subscriptionId))
    fd.append('amount_toman', String(selectedSub.final_price_toman))
    fd.append('payer_name', payment.payer_name)
    fd.append('tracking_number', payment.tracking_number)
    fd.append('payment_date', payment.payment_date)
    fd.append('description', payment.description)
    fd.append('receipt', receipt)
    const { data } = await api.post('/onboarding/submit-payment/', fd)
    setStatus(data)
    toast.success('پرداخت ارسال شد — در انتظار تأیید')
    setStep(4)
  }

  const copyCard = async () => {
    if (!paySettings?.destination_card_number) return
    await navigator.clipboard.writeText(paySettings.destination_card_number.replace(/\s/g, ''))
    toast.success('شماره کارت کپی شد')
  }

  return (
    <div className="min-h-screen bg-surface px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <div className="text-sm text-muted">آنبوردینگ BuildingHub</div>
            <h1 className="text-2xl font-bold">راه‌اندازی ساختمان</h1>
          </div>
          <Link to="/app/dashboard" className="text-sm text-teal-700">
            رفتن به پنل
          </Link>
        </div>
        <div className="mb-4 flex gap-2 text-xs">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`rounded-full px-3 py-1 ${step >= s ? 'bg-teal-800 text-white' : 'bg-white text-muted border'}`}
            >
              مرحله {s}
            </div>
          ))}
        </div>

        {step === 1 ? (
          <Card>
            <h2 className="font-bold">اطلاعات ساختمان</h2>
            <form className="mt-4 space-y-3" onSubmit={createBuilding}>
              <div>
                <Label>نام ساختمان</Label>
                <Input
                  value={building.name}
                  onChange={(e) => setBuilding({ ...building, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>آدرس کامل</Label>
                <Input
                  value={building.address}
                  onChange={(e) => setBuilding({ ...building, address: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>تعداد طبقات</Label>
                  <Input
                    type="number"
                    value={building.floors_count}
                    onChange={(e) => setBuilding({ ...building, floors_count: Number(e.target.value) })}
                    required
                  />
                </div>
                <div>
                  <Label>تعداد واحدها</Label>
                  <Input
                    type="number"
                    value={building.apartments_count}
                    onChange={(e) => setBuilding({ ...building, apartments_count: Number(e.target.value) })}
                    required
                  />
                </div>
              </div>
              <div>
                <Label>توضیحات</Label>
                <Input
                  value={building.description}
                  onChange={(e) => setBuilding({ ...building, description: e.target.value })}
                />
              </div>
              <Button className="w-full">ادامه</Button>
            </form>
          </Card>
        ) : null}

        {step === 2 ? (
          <Card>
            <h2 className="font-bold">انتخاب اشتراک</h2>
            <form className="mt-4 space-y-3" onSubmit={selectPlan}>
              {plans.map((p) => (
                <label key={p.id} className="flex cursor-pointer items-start gap-3 rounded-xl border p-3">
                  <input type="radio" checked={planId === p.id} onChange={() => setPlanId(p.id)} />
                  <div>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted">
                      {p.min_apartments}–{p.max_apartments} واحد · ماهانه{' '}
                      {p.monthly_price != null ? formatToman(p.monthly_price) : '—'} · سالانه{' '}
                      {p.yearly_price != null ? formatToman(p.yearly_price) : '—'}
                    </div>
                  </div>
                </label>
              ))}
              <div className="flex gap-3">
                <Button
                  type="button"
                  className={duration === 'MONTHLY' ? '' : '!bg-white !text-teal-900 border'}
                  onClick={() => setDuration('MONTHLY')}
                >
                  ماهانه
                </Button>
                <Button
                  type="button"
                  className={duration === 'YEARLY' ? '' : '!bg-white !text-teal-900 border'}
                  onClick={() => setDuration('YEARLY')}
                >
                  سالانه
                </Button>
              </div>
              <Button className="w-full">ثبت انتخاب</Button>
            </form>
          </Card>
        ) : null}

        {step === 3 && selectedSub ? (
          <Card>
            <h2 className="font-bold">پرداخت کارت‌به‌کارت</h2>
            <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm">
              <div>پلن: {selectedSub.plan_name_snapshot}</div>
              <div>مدت: {selectedSub.duration === 'YEARLY' ? 'سالانه' : 'ماهانه'}</div>
              <div>مبلغ قابل پرداخت: {formatToman(selectedSub.final_price_toman)}</div>
            </div>
            {paySettings ? (
              <div className="mt-3 space-y-1 rounded-xl border p-3 text-sm">
                <div>بانک: {paySettings.bank_name}</div>
                <div>به‌نام: {paySettings.cardholder_name}</div>
                <div className="flex items-center gap-2">
                  <span>شماره کارت: {paySettings.destination_card_number}</span>
                  <Button type="button" className="!py-1 !text-xs" onClick={copyCard}>
                    کپی
                  </Button>
                </div>
                <p className="text-muted">{paySettings.payment_instructions}</p>
              </div>
            ) : null}
            <form className="mt-4 space-y-3" onSubmit={submitPayment}>
              <div>
                <Label>نام پرداخت‌کننده</Label>
                <Input
                  value={payment.payer_name}
                  onChange={(e) => setPayment({ ...payment, payer_name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>شماره پیگیری</Label>
                <Input
                  value={payment.tracking_number}
                  onChange={(e) => setPayment({ ...payment, tracking_number: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>تاریخ پرداخت</Label>
                <Input
                  type="date"
                  value={payment.payment_date}
                  onChange={(e) => setPayment({ ...payment, payment_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>رسید پرداخت</Label>
                <Input type="file" accept="image/*,.pdf" onChange={(e) => setReceipt(e.target.files?.[0] || null)} required />
              </div>
              <Button className="w-full">ارسال برای تأیید</Button>
            </form>
          </Card>
        ) : null}

        {step === 4 ? (
          <Card>
            <h2 className="font-bold">وضعیت پرداخت</h2>
            <p className="mt-3 text-sm text-muted">
              پرداخت شما ثبت شد و در انتظار بررسی سوپرادمین است. تا زمان تأیید، امکانات مدیریتی ساختمان محدود است.
            </p>
            {status ? (
              <div className="mt-4 rounded-xl bg-amber-50 p-3 text-sm">
                وضعیت: {status.status}
                <br />
                مبلغ: {formatToman(status.amount_toman)}
              </div>
            ) : null}
            <div className="mt-4 flex gap-3">
              <Button onClick={() => navigate('/app/subscription')}>صفحه اشتراک</Button>
              <Button className="!bg-white !text-teal-900 border" onClick={() => navigate('/app/support')}>
                پشتیبانی
              </Button>
            </div>
          </Card>
        ) : null}
      </div>
    </div>
  )
}
