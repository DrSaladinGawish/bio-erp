import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { BrainProvider } from './context/BrainContext';
import { Sidebar } from './components/layout/Sidebar';
import { ThemeToggle } from './components/layout/Header';
import { ModuleNav } from './components/layout/ModuleNav';
import { VitalsBanner } from './components/dashboard/VitalsBanner';
import { OrganGrid } from './components/dashboard/OrganGrid';
import { CellStream } from './components/dashboard/CellStream';
import { PrognosisPanel } from './components/dashboard/PrognosisPanel';
import { SCMChamber } from './components/reports/SCMChamber';
import { FinancialChamber } from './components/reports/FinancialChamber';
import { PerformanceChamber } from './components/reports/PerformanceChamber';

function DashboardPage() {
  return (
    <div className="animate-fade-in">
      <VitalsBanner />
      <OrganGrid />
      <CellStream />
      <PrognosisPanel />
    </div>
  );
}

function ReportsPage() {
  return (
    <div className="animate-fade-in">
      <div className="grid grid-cols-3 gap-6">
        <SCMChamber />
        <FinancialChamber />
        <PerformanceChamber />
      </div>
    </div>
  );
}

function BodyLayout() {
  return (
    <Routes>
      <Route index element={<DashboardPage />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="comparison" element={<div className="text-slate-400 text-sm p-8 text-center">Brain Comparison view coming soon</div>} />
      <Route path="audit" element={<div className="text-slate-400 text-sm p-8 text-center">Cross-Brain Audit view coming soon</div>} />
      <Route path="reports" element={<ReportsPage />} />
      <Route path="*" element={<DashboardPage />} />
    </Routes>
  );
}

function BrainLayout() {
  return (
    <Routes>
      <Route index element={<div className="text-slate-400 text-sm p-8 text-center">Brain Directory — coming soon</div>} />
      <Route path="directory" element={<div className="text-slate-400 text-sm p-8 text-center">Brain Directory — coming soon</div>} />
      <Route path="add" element={<div className="text-slate-400 text-sm p-8 text-center">Add Company — coming soon</div>} />
      <Route path="health" element={<div className="text-slate-400 text-sm p-8 text-center">Brain Health — coming soon</div>} />
      <Route path="cross" element={<div className="text-slate-400 text-sm p-8 text-center">Cross-Brain — coming soon</div>} />
      <Route path="*" element={<div className="text-slate-400 text-sm p-8 text-center">Brain Directory — coming soon</div>} />
    </Routes>
  );
}

function OrgansLayout() {
  return (
    <Routes>
      <Route index element={<OrganGrid />} />
      <Route path="directory" element={<OrganGrid />} />
      <Route path="performance" element={<div className="text-slate-400 text-sm p-8 text-center">Organ Performance — coming soon</div>} />
      <Route path="alerts" element={<div className="text-slate-400 text-sm p-8 text-center">Organ Alerts — coming soon</div>} />
      <Route path="map" element={<div className="text-slate-400 text-sm p-8 text-center">Organ Map — coming soon</div>} />
      <Route path="*" element={<OrganGrid />} />
    </Routes>
  );
}

function CellsLayout() {
  return (
    <Routes>
      <Route index element={<CellStream />} />
      <Route path="registry" element={<CellStream />} />
      <Route path="activity" element={<CellStream />} />
      <Route path="lifecycle" element={<div className="text-slate-400 text-sm p-8 text-center">Cell Lifecycle — coming soon</div>} />
      <Route path="analytics" element={<div className="text-slate-400 text-sm p-8 text-center">Cell Analytics — coming soon</div>} />
      <Route path="*" element={<CellStream />} />
    </Routes>
  );
}

function MainContent() {
  return (
    <Routes>
      <Route path="/body/*" element={<BodyLayout />} />
      <Route path="/brain/*" element={<BrainLayout />} />
      <Route path="/organs/*" element={<OrgansLayout />} />
      <Route path="/cells/*" element={<CellsLayout />} />
      <Route path="*" element={<BodyLayout />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <BrainProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-[#0B1120] transition-colors duration-300">
          <Sidebar />
          <div className="pt-[80px]" style={{ marginLeft: 'var(--sidebar-width, 240px)' }}>
            <div className="flex items-center justify-end px-6 py-2 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
              <ThemeToggle />
            </div>
            <ModuleNav />
            <main className="p-6">
              <MainContent />
            </main>
          </div>
        </div>
      </BrainProvider>
    </BrowserRouter>
  );
}
