import { Routes, Route } from 'react-router-dom';
import CaseListPage from './pages/CaseListPage';
import CaseDetailPage from './pages/CaseDetailPage';
import CaseForm from './components/cases/CaseForm';

function App() {
  return (
    <div className="min-h-screen">
      <Routes>
        <Route
          path="/"
          element={
            <div className="flex items-center justify-center min-h-screen">
              <div className="text-center">
                <h1 className="text-4xl font-bold mb-4">ArtifactX</h1>
                <p className="text-gray-600">
                  Forensic analysis platform
                </p>
                <div className="mt-8 p-4 bg-green-50 rounded-lg inline-block">
                  <p className="text-green-700 font-medium">Status: Connected</p>
                </div>
              </div>
            </div>
          }
        />
        {/* Case Management Routes */}
        <Route path="/cases" element={<CaseListPage />} />
        <Route path="/cases/create" element={<CaseForm />} />
        <Route path="/cases/:id" element={<CaseDetailPage />} />
        <Route path="/cases/:id/edit" element={<CaseForm />} />
      </Routes>
    </div>
  );
}

export default App;