import { useEffect } from 'react'
import { Modal } from '@/components/ui'

type Props = {
  open: boolean
  title?: string
  url: string | null
  contentType?: string
  onClose: () => void
}

export function MediaPreview({
  open,
  title = 'مشاهده فایل',
  url,
  contentType = '',
  onClose,
}: Props) {
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  const isImage = contentType.startsWith('image/') || !contentType
  const isPdf = contentType.includes('pdf')

  return (
    <Modal open={open && !!url} title={title} onClose={onClose}>
      <div className="max-h-[70vh] overflow-auto rounded-xl bg-slate-50 p-2">
        {url && isImage ? (
          <img src={url} alt={title} className="mx-auto max-h-[65vh] w-auto rounded-lg object-contain" />
        ) : null}
        {url && isPdf ? (
          <iframe title={title} src={url} className="h-[65vh] w-full rounded-lg border-0" />
        ) : null}
        {url && !isImage && !isPdf ? (
          <div className="p-6 text-center text-sm text-muted">
            پیش‌نمایش این نوع فایل پشتیبانی نمی‌شود.
            <div className="mt-3">
              <a className="text-brand-700 underline" href={url} download>
                دانلود فایل
              </a>
            </div>
          </div>
        ) : null}
      </div>
      {url ? (
        <div className="mt-3 text-left">
          <a className="text-sm text-brand-700 hover:underline" href={url} download target="_blank" rel="noreferrer">
            دانلود / باز کردن
          </a>
        </div>
      ) : null}
    </Modal>
  )
}