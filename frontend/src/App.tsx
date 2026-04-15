import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '@/components/layout/app-layout';
import { PrivateRoute } from '@/components/private-route';
import { LoginPage } from '@/pages/login-page';
import { DashboardPage } from '@/pages/dashboard-page';
import { ProductsPage } from '@/pages/products-page';
import { ProductDetailPage } from '@/pages/product-detail-page';
import { CategoriesPage } from '@/pages/categories-page';
import { UsersPage } from '@/pages/users-page';
import { ImportPage } from '@/pages/import-page';
import { SettingsPage } from '@/pages/settings-page';
import { NotFoundPage } from '@/pages/not-found-page';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <AppLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="products/:id" element={<ProductDetailPage />} />
        <Route path="categories" element={<CategoriesPage />} />
        <Route
          path="users"
          element={
            <PrivateRoute allowedRoles={['admin', 'manager']}>
              <UsersPage />
            </PrivateRoute>
          }
        />
        <Route
          path="import"
          element={
            <PrivateRoute allowedRoles={['admin', 'manager']}>
              <ImportPage />
            </PrivateRoute>
          }
        />
        <Route
          path="settings"
          element={
            <PrivateRoute allowedRoles={['admin']}>
              <SettingsPage />
            </PrivateRoute>
          }
        />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default App;
