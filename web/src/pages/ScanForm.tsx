import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitScan } from '../api/client'
import type { ScanLanguage } from '../types'

export function ScanForm() {
  const navigate = useNavigate()
  const [driveUrl, setDriveUrl] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [lang, setLang] = useState<ScanLanguage>('es')
  const [contextNotes, setContextNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const { job_id } = await submitScan({
        drive_url: driveUrl.trim(),
        company_name: companyName.trim(),
        lang,
        context_notes: contextNotes.trim() || undefined,
      })
      navigate(`/status/${job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar el escaneo')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="card">
      <h2>Nuevo escaneo</h2>
      <p className="muted">Introduce la URL de la carpeta de Drive y los datos de la empresa.</p>

      <form onSubmit={handleSubmit} style={{ marginTop: '1.25rem' }}>
        <div className="form-group">
          <label htmlFor="drive_url">Enlace carpeta Google Drive</label>
          <input
            id="drive_url"
            type="url"
            required
            placeholder="https://drive.google.com/drive/folders/..."
            value={driveUrl}
            onChange={(e) => setDriveUrl(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="company_name">Nombre de la empresa</label>
          <input
            id="company_name"
            type="text"
            required
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="lang">Idioma del informe</label>
          <select id="lang" value={lang} onChange={(e) => setLang(e.target.value as ScanLanguage)}>
            <option value="es">Español</option>
            <option value="en">English</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="context_notes">Contexto adicional (opcional)</label>
          <textarea
            id="context_notes"
            placeholder="Ronda, etapa, notas del founder..."
            value={contextNotes}
            onChange={(e) => setContextNotes(e.target.value)}
          />
        </div>

        {error && <div className="error-box">{error}</div>}

        <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
          {submitting ? 'Enviando…' : 'Iniciar escaneo'}
        </button>
      </form>
    </section>
  )
}
