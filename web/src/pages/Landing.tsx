import { Link } from 'react-router-dom'

export function Landing() {
  return (
    <>
      <section className="card">
        <h2>Due diligence automatizado</h2>
        <p className="muted">
          Escanea una carpeta de Google Drive y genera un informe de due diligence alineado al
          marco de 8 pilares de CTH Growth Services — HTML y PDF listos para el equipo.
        </p>

        <ul className="pill-list">
          <li>Drive URL + metadatos</li>
          <li>Escaneo en servidor CTH</li>
          <li>Informe HTML / PDF existente</li>
        </ul>

        <div className="actions">
          <Link className="btn btn-primary" to="/scan">
            Iniciar escaneo
          </Link>
        </div>
      </section>

      <section className="card">
        <h2>Arquitectura Lane A</h2>
        <p className="muted">
          Esta interfaz pública envía solo la URL de Drive y metadatos al backend Flask+RQ en el
          pod CTH. El navegador nunca accede directamente a Google Drive.
        </p>
        <p className="muted" style={{ marginTop: '0.75rem' }}>
          URL pública:{' '}
          <strong>
            <a
              href="https://apps.cleantechhub.net/dataroom-scanner"
              target="_blank"
              rel="noopener noreferrer"
            >
              apps.cleantechhub.net/dataroom-scanner
            </a>
          </strong>
        </p>
      </section>
    </>
  )
}
