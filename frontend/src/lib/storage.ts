const ACCESS_TOKEN_KEY = "aap_access_token";
const REFRESH_TOKEN_KEY = "aap_refresh_token";
const SESSION_EXPIRES_AT_KEY = "aap_session_expires_at";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    return;
  }
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function getSessionExpiresAt(): number | null {
  const raw = localStorage.getItem(SESSION_EXPIRES_AT_KEY);
  if (!raw) {
    return null;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

export function setSessionExpiresAt(value: number | null): void {
  if (!value) {
    localStorage.removeItem(SESSION_EXPIRES_AT_KEY);
    return;
  }
  localStorage.setItem(SESSION_EXPIRES_AT_KEY, String(value));
}

export function clearSessionStorage(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(SESSION_EXPIRES_AT_KEY);
}
