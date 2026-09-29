import { create } from "zustand";

interface AuthState {
  token: string | null;
  // v2.2：role 可為 null。後端先前在帳號沒有角色時會回傳 "viewer"，
  // 但資料庫裡從來沒有這個角色；現在誠實回 null。
  user: { id: string; full_name: string; role: string | null } | null;
  setAuth: (token: string, user: AuthState["user"]) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("erp_token") : null,
  user: typeof window !== "undefined"
    ? (() => { try { return JSON.parse(localStorage.getItem("erp_user") || "null"); } catch { return null; } })()
    : null,
  setAuth: (token, user) => {
    localStorage.setItem("erp_token", token);
    localStorage.setItem("erp_user", JSON.stringify(user));
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem("erp_token");
    localStorage.removeItem("erp_user");
    set({ token: null, user: null });
    // 登出刻意使用整頁重新載入而非 router.push：這裡是 zustand store，
    // 不在 React 渲染樹內，拿不到 useRouter；更重要的是登出時我們「想要」
    // 整頁重載，藉此清掉所有 TanStack Query 快取與各頁面殘留的客戶資料，
    // 避免下一位使用者在同一台現場平板上看到前一位的資料。
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  },
  isAuthenticated: () => !!get().token,
}));
