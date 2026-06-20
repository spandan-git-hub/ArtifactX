import { Routes, Route } from 'react-router-dom'

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
      </Routes>
    </div>
  )
}

export default App
