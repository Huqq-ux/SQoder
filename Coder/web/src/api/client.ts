const BASE = '/api'

async function get<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`)
  if (!res.ok) throw new Error(`GET ${url} failed: ${res.status}`)
  return res.json()
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`POST ${url} failed: ${res.status}`)
  return res.json()
}

async function del<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE ${url} failed: ${res.status}`)
  return res.json()
}

async function put<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`PUT ${url} failed: ${res.status}`)
  return res.json()
}

async function uploadFiles<T>(url: string, files: File[]): Promise<T> {
  const formData = new FormData()
  for (const f of files) formData.append('files', f)
  const res = await fetch(`${BASE}${url}`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload ${url} failed: ${res.status}`)
  return res.json()
}

export const api = { get, post, del, put, uploadFiles }
