import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchJobStatus } from '../api/client'
import { ReportLinks } from '../components/ReportLinks'
import type { JobStatus as JobStatusType } from '../types'

const POLL_MS = 4000
const TERMINAL = new Set(['finished', 'failed', 'stopped', 'canceled'])

export function JobStatus() {
  const { jobId } = useParams<{ jobId: string }>()
  const [data, setData] = useState<JobStatusType | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!jobId) return
    try {
      const status = await fetchJobStatus(jobId)
      setData(status)
      setFetchError(null)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Error al consultar el estado')
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (!data || TERMINAL.has(data.status)) return
    const timer = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(timer)
  }, [data, refresh])

  if (!jobId) {
    return <div className="error-box">Falta el identificador del trabajo.</div>
  }

  return (
    <section className="card">
      <h2>Estado del escaneo</h2>

      {loading && !data && <p className="muted">Cargando estado…</p>}

      {fetchError && <div className="error-box">{fetchError}</div>}

      {data && (
        <>
          <p>
            Job ID: <span className="job-id">{data.job_id}</span>{' '}
            <span className={`badge badge-${data.status}`}>{data.status}</span>
          </p>

          {data.status === 'finished' && data.result && (
            <>
              <div className="score-block">
                <span className="score-value">{data.result.overall_score}</span>
                <span className="muted">/ 5.0 — {data.result.recommendation}</span>
              </div>
              <p className="muted" style={{ marginTop: '0.5rem' }}>
                {data.result.company_name}
              </p>

              <h3 style={{ marginTop: '1.25rem', color: 'var(--cth-deep)' }}>Informes</h3>
              <p className="muted">
                Se abre el HTML/PDF existente (Drive o servidor). No se modifica la plantilla del
                informe.
              </p>
              <ReportLinks result={data.result} />

              {data.result.errors.length > 0 && (
                <div className="error-box" style={{ marginTop: '1rem' }}>
                  <strong>Advertencias:</strong>
                  <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem' }}>
                    {data.result.errors.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {data.status === 'failed' && (
            <div className="error-box">{data.error ?? 'El escaneo falló.'}</div>
          )}

          {!TERMINAL.has(data.status) && (
            <p className="muted" style={{ marginTop: '1rem' }}>
              El escaneo está en curso. Esta página se actualiza automáticamente.
            </p>
          )}
        </>
      )}

      <div className="actions">
        <button className="btn btn-secondary" type="button" onClick={refresh}>
          Actualizar
        </button>
        <Link className="btn btn-outline" to="/scan">
          Nuevo escaneo
        </Link>
      </div>
    </section>
  )
}
