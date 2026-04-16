import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';

import { useAuth } from '../auth/useAuth';

function ProtectedRoute({ children, requiredPermission = null }) {
  const location = useLocation();
  const { loading, isAuthenticated, hasPermission } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/forbidden" replace />;
  }

  return children;
}

export default ProtectedRoute;
