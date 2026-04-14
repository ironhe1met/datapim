import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth-store';
import { showError } from '@/lib/toast';
import type { UserRole } from '@/types/api';
import type { ReactNode } from 'react';

interface PrivateRouteProps {
  children: ReactNode;
  allowedRoles?: UserRole[];
}

export function PrivateRoute({ children, allowedRoles }: PrivateRouteProps) {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    showError('Доступ заборонено');
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
