const TOKEN_KEY = 'zhiwei.auth.token'
const USER_KEY = 'zhiwei.auth.user'
export const AUTH_CHANGED_EVENT = 'zhiwei-auth-changed'

function notifyAuthChanged() {
  try {
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
  } catch {
    /* ignore (SSR / non-DOM) */
  }
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function getUsername() {
  try {
    return localStorage.getItem(USER_KEY) || ''
  } catch {
    return ''
  }
}

export function setSession({ accessToken, username }) {
  try {
    if (accessToken) localStorage.setItem(TOKEN_KEY, accessToken)
    if (username) localStorage.setItem(USER_KEY, username)
  } catch {
    /* ignore */
  }
  notifyAuthChanged()
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  } catch {
    /* ignore */
  }
  notifyAuthChanged()
}

export function isAuthenticated() {
  return Boolean(getToken())
}

/** 仅允许站内相对路径，拒绝 `//evil` 等协议相对 URL */
export function safeInternalPath(redirect) {
  if (typeof redirect !== 'string') return ''
  return redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : ''
}

export function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
