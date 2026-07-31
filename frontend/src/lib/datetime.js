/** 展示用时间格式化：本地时区，避免 ISO 原串。 */

function pad(n) {
  return String(n).padStart(2, '0')
}

/**
 * @param {string | number | Date | null | undefined} value
 * @param {{ withSeconds?: boolean }} [opts]
 * @returns {string}
 */
export function formatDateTime(value, { withSeconds = false } = {}) {
  if (value == null || value === '') return '—'
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return '—'
    return formatLocal(value, withSeconds)
  }

  const raw = String(value).trim()
  if (!raw) return '—'

  // 仅日期（趋势/突增预警等）原样展示
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw

  const d = new Date(raw)
  if (!Number.isNaN(d.getTime())) return formatLocal(d, withSeconds)

  // 解析失败时做轻量清洗
  return (
    raw
      .replace('T', ' ')
      .replace(/\.\d+/, '')
      .replace(/([+-]\d{2}:?\d{2}|Z)$/i, '')
      .trim()
      .slice(0, withSeconds ? 19 : 16) || '—'
  )
}

function formatLocal(d, withSeconds) {
  const base = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  return withSeconds ? `${base}:${pad(d.getSeconds())}` : base
}
