import { Navigate } from "react-router-dom";

export default function Protected({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("idlex_access");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function ProtectedAdmin({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("idlex_admin_access");
  if (!token) return <Navigate to="/admin/login" replace />;
  return <>{children}</>;
}