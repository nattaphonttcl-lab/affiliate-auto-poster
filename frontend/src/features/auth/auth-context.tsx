import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { login as loginApi } from "../../lib/api";
import {
  clearSessionStorage,
  getAccessToken,
  getRefreshToken,
  getSessionExpiresAt,
  setAccessToken,
  setRefreshToken,
  setSessionExpiresAt,
} from "../../lib/storage";

type AuthUser = {
  email: string;
  role: "admin" | "editor" | "viewer";
  mustChangePassword: boolean;
};

type AuthContextValue = {
  isAuthenticated: boolean;
  user: AuthUser | null;
  mustChangePassword: boolean;
  login: (email: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const SESSION_MS = 1000 * 60 * 30;

function getRoleFromToken(token: string): AuthUser["role"] {
  try {
    const payloadBase64 = token.split(".")[1];
    const payload = JSON.parse(atob(payloadBase64));
    const role = payload.role;
    if (role === "admin" || role === "editor" || role === "viewer") {
      return role;
    }
  } catch {
    // Best-effort parsing for optional role claim.
  }
  return "admin";
}

function getMustChangePasswordFromToken(token: string): boolean {
  try {
    const payloadBase64 = token.split(".")[1];
    const payload = JSON.parse(atob(payloadBase64));
    return payload.must_change_password === true;
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => getAccessToken());

  const user = useMemo<AuthUser | null>(() => {
    if (!token) {
      return null;
    }
    return {
      email: "authenticated@local",
      role: getRoleFromToken(token),
      mustChangePassword: getMustChangePasswordFromToken(token),
    };
  }, [token]);

  const logout = useCallback(() => {
    clearSessionStorage();
    setToken(null);
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }

    const expiresAt = getSessionExpiresAt();
    if (expiresAt && Date.now() > expiresAt) {
      window.setTimeout(() => {
        logout();
      }, 0);
      return;
    }

    const onActivity = () => {
      setSessionExpiresAt(Date.now() + SESSION_MS);
    };

    const events: Array<keyof WindowEventMap> = [
      "click",
      "keydown",
      "mousemove",
      "scroll",
    ];

    for (const event of events) {
      window.addEventListener(event, onActivity);
    }

    const timer = window.setInterval(() => {
      const deadline = getSessionExpiresAt();
      if (deadline && Date.now() > deadline) {
        logout();
      }
    }, 5000);

    return () => {
      window.clearInterval(timer);
      for (const event of events) {
        window.removeEventListener(event, onActivity);
      }
    };
  }, [token, logout]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginApi(email, password);
    setAccessToken(response.access_token);
    setRefreshToken(getRefreshToken());
    setSessionExpiresAt(Date.now() + SESSION_MS);
    setToken(response.access_token);
    void email;
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const { changePassword: changePasswordApi } = await import("../../lib/api");
    await changePasswordApi(currentPassword, newPassword);
    clearSessionStorage();
    setToken(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(token),
      user,
      mustChangePassword: user?.mustChangePassword ?? false,
      login,
      changePassword,
      logout,
    }),
    [token, user, login, changePassword, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
