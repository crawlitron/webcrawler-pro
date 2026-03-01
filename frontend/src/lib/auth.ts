// JWT Token Management — v0.8.0
const TOKEN_KEY = 'wcp_access_token';
const USER_KEY  = 'wcp_user';

// Empty string = relative URLs via Nginx proxy (works on any host/domain)
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  last_login?: string;
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function storeUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function login(email: string, password: string): Promise<{ token: string; user: User }> {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  setToken(data.access_token);
  const user = await fetchMe(data.access_token);
  storeUser(user);
  return { token: data.access_token, user };
}

export async function fetchMe(token?: string): Promise<User> {
  const t = token || getToken();
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${t}` },
  });
  if (!res.ok) throw new Error('Not authenticated');
  return res.json();
}

export async function register(email: string, password: string, full_name?: string): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function logout(): Promise<void> {
  const token = getToken();
  if (token) {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      headers: authHeaders(),
    }).catch(() => {});
  }
  clearAuth();
}
