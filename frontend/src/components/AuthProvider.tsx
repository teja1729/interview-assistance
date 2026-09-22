"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, type AuthSession } from "@/lib/api";

type AuthState = {
  session: AuthSession | null;
  loading: boolean;
  refresh: () => Promise<void>;
};
const AuthContext = createContext<AuthState>({
  session: null,
  loading: true,
  refresh: async () => {},
});
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      setSession(await api.session());
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    api
      .session()
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setLoading(false));
    const expired = () => setSession(null);
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, [refresh]);
  return (
    <AuthContext.Provider value={{ session, loading, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
