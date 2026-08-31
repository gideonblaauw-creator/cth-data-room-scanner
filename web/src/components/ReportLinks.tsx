import { localReportUrl } from '../api/client'
import type { ScanResult } from '../types'

interface ReportLinksProps {
  result: ScanResult
}

export function ReportLinks({ result }: ReportLinksProps) {
  const htmlLink = result.html_url ?? localReportUrl(result.html_path)
  const pdfLink = result.pdf_url ?? localReportUrl(result.pdf_path)
  const driveFolder = result.drive_folder_url

  if (!htmlLink && !pdfLink && !driveFolder) {
    return <p className="muted">Los informes aparecerán aquí cuando el escaneo finalice.</p>
  }

  return (
    <div className="report-links">
      {htmlLink && (
        <a href={htmlLink} target="_blank" rel="noopener noreferrer">
          Ver informe HTML
        </a>
      )}
      {pdfLink && (
        <a href={pdfLink} target="_blank" rel="noopener noreferrer">
          Descargar informe PDF
        </a>
      )}
      {driveFolder && (
        <a href={driveFolder} target="_blank" rel="noopener noreferrer">
          Abrir carpeta en Google Drive
        </a>
      )}
    </div>
  )
}
