import { api } from '@/lib/api'
import toast from 'react-hot-toast'

export type MediaKind = 'receipt' | 'invoice' | 'maintenance'

async function fetchMediaBlob(kind: MediaKind, id: number): Promise<Blob> {
  const response = await api.get(`/media/${kind}/${id}/`, {
    responseType: 'blob',
    validateStatus: () => true,
  })

  const contentType = String(response.headers['content-type'] || '')
  const blob: Blob = response.data

  // DRF errors come back as JSON even with responseType blob
  if (response.status >= 400 || contentType.includes('application/json')) {
    let message = 'دسترسی به فایل ممکن نشد'
    try {
      const text = await blob.text()
      const parsed = JSON.parse(text) as { detail?: string }
      if (parsed.detail) message = String(parsed.detail)
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }

  return blob
}

/** Load protected media and return an object URL. Caller must revoke it. */
export async function loadProtectedMediaUrl(kind: MediaKind, id: number): Promise<string> {
  const blob = await fetchMediaBlob(kind, id)
  return URL.createObjectURL(blob)
}

/**
 * Open media without relying on window.open after await (popup blockers).
 * Prefer in-app preview via onPreview; otherwise trigger a same-tab download.
 */
export async function openProtectedMedia(
  kind: MediaKind,
  id: number,
  onPreview?: (url: string, contentType: string) => void,
) {
  try {
    const blob = await fetchMediaBlob(kind, id)
    const url = URL.createObjectURL(blob)

    if (onPreview) {
      onPreview(url, blob.type || 'application/octet-stream')
      return
    }

    // Fallback: programmatic download (not blocked like window.open)
    const a = document.createElement('a')
    a.href = url
    a.download = `${kind}-${id}`
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    toast.success('فایل آماده شد')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'دسترسی به فایل ممکن نشد')
  }
}