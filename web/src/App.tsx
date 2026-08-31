import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { JobStatus } from './pages/JobStatus'
import { Landing } from './pages/Landing'
import { ScanForm } from './pages/ScanForm'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="scan" element={<ScanForm />} />
          <Route path="status/:jobId" element={<JobStatus />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
