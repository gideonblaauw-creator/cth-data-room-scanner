export type ScanLanguage = 'es' | 'en'

export interface ScanRequest {
  drive_url: string
  company_name: string
  lang: ScanLanguage
  context_notes?: string
}

export interface ScanResult {
  summary: string
  company_name: string
  slug: string
  overall_score: number
  recommendation: string
  html_path: string
  pdf_path: string | null
  drive_folder_url: string | null
  html_url: string | null
  pdf_url: string | null
  errors: string[]
}

export interface JobStatus {
  job_id: string
  status: 'queued' | 'started' | 'finished' | 'failed' | 'deferred' | 'scheduled' | 'stopped' | 'canceled'
  result: ScanResult | null
  error: string | null
}

export interface ReportLinks {
  html: string | null
  pdf: string | null
  driveFolder: string | null
}
