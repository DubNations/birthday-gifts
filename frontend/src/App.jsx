import { Routes, Route } from 'react-router-dom'
import Layout from './components/common/Layout'
import ErrorBoundary from './components/common/ErrorBoundary'
import HomePage from './pages/HomePage'
import DrawPage from './pages/DrawPage'
import MyGiftsPage from './pages/MyGiftsPage'
import AdminPage from './pages/AdminPage'
import { DrawProvider } from './store/drawStore'

function App() {
  return (
    <ErrorBoundary>
      <DrawProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<ErrorBoundary><HomePage /></ErrorBoundary>} />
            <Route path="/draw" element={<ErrorBoundary><DrawPage /></ErrorBoundary>} />
            <Route path="/my-gifts" element={<ErrorBoundary><MyGiftsPage /></ErrorBoundary>} />
            <Route path="/admin" element={<ErrorBoundary><AdminPage /></ErrorBoundary>} />
          </Routes>
        </Layout>
      </DrawProvider>
    </ErrorBoundary>
  )
}

export default App
