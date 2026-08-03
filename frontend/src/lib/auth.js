const TOKEN_KEY = 'zhiwei.auth.token'
const USER_KEY = 'zhiwei.auth.user'

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
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  } catch {
    /* ignore */
  }
}

export function isAuthenticated() {
  return Boolean(getToken())
}

export function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
