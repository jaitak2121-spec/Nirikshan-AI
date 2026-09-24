import { Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import { RoleProvider } from './hooks/useRole'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetails from './pages/ProjectDetails'
import InvestigationQueue from './pages/InvestigationQueue'
import CaseDetail from './pages/CaseDetail'
import Agencies from './pages/Agencies'
import AgencyProfile from './pages/AgencyProfile'
import Compliance from './pages/Compliance'
import Trends from './pages/Trends'
import Watchlist from './pages/Watchlist'
import About from './pages/About'

export default function App() {
  return (
    <RoleProvider>
      <div className="flex min-h-screen bg-ink-50">
        <Sidebar />

        <div className="flex min-w-0 flex-1 flex-col">
          <Header />

          <main className="min-w-0 flex-1 px-5 py-5">
            <Routes>
              {/* The application opens directly on the dashboard: no login screen
                  and no landing page between the user and the data. */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:projectId" element={<ProjectDetails />} />
              <Route path="/investigation-queue" element={<InvestigationQueue />} />
              <Route path="/cases/:caseId" element={<CaseDetail />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/compliance" element={<Compliance />} />
              <Route path="/trends" element={<Trends />} />
              <Route path="/agencies" element={<Agencies />} />
              {/* An agency name is free text and contains spaces and commas, so
                  it is matched as a wildcard rather than a single segment. */}
              <Route path="/agencies/*" element={<AgencyProfile />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </RoleProvider>
  )
}
