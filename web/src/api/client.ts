import type { JobStatus, ScanRequest } from '../types'

const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

async function apiFetch(path: string, init?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.error ?? `Request failed (${response.status})`)
  }

  return response
}

export async function submitScan(payload: ScanRequest): Promise<{ job_id: string }> {
  const response = await apiFetch('/api/scan', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return response.json()
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  const response = await apiFetch(`/api/status/${jobId}`)
  return response.json()
}

export function localReportUrl(filePath: string | null | undefined): string | null {
  if (!filePath) return null
  const filename = filePath.split('/').pop()
  if (!filename) return null
  return `${API_BASE}/reports/${filename}`
}
