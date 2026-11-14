import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authService, ExaminerProfile } from '../services/authService';

export interface AuthContextType {
  examiner: ExaminerProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginAsGuest: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [examiner, setExaminer] = useState<ExaminerProfile | null>(null);
  const [token, setToken] = useState<string | null>(authService.getToken());
  const [loading, setLoading] = useState<boolean>(true);

  // Validate active session token on mount
  useEffect(() => {
    let isMounted = true;
    const initAuth = async () => {
      const activeToken = authService.getToken();
      if (!activeToken) {
        if (isMounted) setLoading(false);
        return;
      }
      // Instant session restore for guest demo sessions
      if (authService.isGuest()) {
        if (isMounted) {
          setExaminer(authService.getGuestExaminer());
          setToken(authService.getGuestToken());
          setLoading(false);
        }
        return;
      }
      try {
        const user = await authService.getCurrentUser();
        if (isMounted) {
          setExaminer(user);
          setToken(activeToken);
        }
      } catch (err) {
        console.warn('Session token invalid or expired:', err);
        authService.logout();
        if (isMounted) {
          setExaminer(null);
          setToken(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    initAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    try {
      const response = await authService.login(username, password);
      setToken(response.access_token);
      setExaminer(response.examiner);
    } finally {
      setLoading(false);
    }
  }, []);

  const loginAsGuest = useCallback(() => {
    const response = authService.loginAsGuest();
    setToken(response.access_token);
    setExaminer(response.examiner);
    setLoading(false);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setExaminer(null);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        examiner,
        token,
        isAuthenticated: Boolean(token),
        isGuest: authService.isGuest(),
        loading,
        login,
        loginAsGuest,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

