import { create } from "zustand";
import type { UserMe } from "../types";

export interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: UserMe | null;
  setAuth: (token: string, refresh: string) => void;
  setUser: (user: UserMe) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: localStorage.getItem("idlex_access"),
  refreshToken: localStorage.getItem("idlex_refresh"),
  user: null,
  setAuth: (token, refresh) => {
    localStorage.setItem("idlex_access", token);
    localStorage.setItem("idlex_refresh", refresh);
    set({ token, refreshToken: refresh });
  },
  setUser: (user) => set({ user }),
  clear: () => {
    localStorage.removeItem("idlex_access");
    localStorage.removeItem("idlex_refresh");
    set({ token: null, refreshToken: null, user: null });
  },
}));

export const isLoggedIn = () => !!localStorage.getItem("idlex_access");