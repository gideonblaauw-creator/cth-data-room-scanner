import { Link, Outlet } from 'react-router-dom'

export function Layout() {
  return (
    <div className="page">
      <header>
        <Link to="/" style={{ textDecoration: 'none' }}>
          <div className="hero">
            <h1>CTH Data Room Scanner</h1>
            <p className="tagline">Inspira. Actúa. Transforma.</p>
          </div>
        </Link>
      </header>

      <main>
        <Outlet />
      </main>

      <footer className="site-footer">CLEANTECHHUB INTERNATIONAL S.L.</footer>
    </div>
  )
}
