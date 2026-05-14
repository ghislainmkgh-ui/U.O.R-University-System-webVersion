import {
  BarChart3,
  BookOpenCheck,
  CalendarRange,
  CheckSquare,
  ClipboardList,
  Landmark,
  LogOut,
  Menu,
  ReceiptText,
  RefreshCw,
  UsersRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { canAccessView } from "../auth/permissions.js";
import { LastLocationTracker } from "../routes/LastLocationTracker.jsx";
import { useAuth } from "../state/AuthContext.jsx";
import { usePreferences } from "../state/PreferencesContext.jsx";

const navItems = [
  { to: "/", viewKey: "dashboard", labelKey: "dashboard", icon: BarChart3 },
  { to: "/students", viewKey: "students", labelKey: "students", icon: UsersRound },
  { to: "/access-requests", viewKey: "access_requests", labelKey: "accessRequests", icon: CheckSquare },
  { to: "/academics", viewKey: "academic_data", labelKey: "academics", icon: BookOpenCheck },
  { to: "/finance", viewKey: "finance", labelKey: "finance", icon: Landmark },
  { to: "/academic-years", viewKey: "academic_years", labelKey: "academicYears", icon: CalendarRange },
  { to: "/transfers", viewKey: "transfers", labelKey: "transfers", icon: RefreshCw },
  { to: "/access", viewKey: "access_logs", labelKey: "accessLogs", icon: ClipboardList },
  { to: "/reports", viewKey: "reports", labelKey: "reports", icon: ReceiptText },
];

export function AppShell() {
  const auth = useAuth();
  const { t } = usePreferences();
  const [isCompact, setIsCompact] = useState(() => localStorage.getItem("uor_sidebar_mode") !== "full");

  useEffect(() => {
    localStorage.setItem("uor_sidebar_mode", isCompact ? "compact" : "full");
  }, [isCompact]);

  const visibleNavItems = useMemo(() => {
    return navItems.filter((item) => canAccessView(auth.user?.role, item.viewKey));
  }, [auth.user?.role]);

  return (
    <div className={`app-shell ${isCompact ? "compact" : "full"}`}>
      <LastLocationTracker />
      <aside className={`sidebar ${isCompact ? "is-compact" : "is-full"}`}>
        <div className="brand-block">
          <strong>U.O.R</strong>
          <span>{t("appTitle")}</span>
        </div>

        <button
          className="sidebar-menu-button"
          title={isCompact ? t("modeFull") : t("modeCompact")}
          aria-label={isCompact ? t("modeFull") : t("modeCompact")}
          onClick={() => setIsCompact((value) => !value)}
        >
          <Menu size={34} />
          <span>{isCompact ? t("full") : t("compact")}</span>
        </button>
        <span className="sidebar-mode">{isCompact ? t("modeCompact") : t("modeFull")}</span>

        <nav className="nav-list" aria-label="Navigation principale">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const label = t(item.labelKey);
            return (
              <NavLink
                key={`${item.to}-${item.labelKey}`}
                to={item.to}
                end={item.to === "/"}
                title={label}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              >
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            );
          })}
        </nav>

        <button className="logout-button" onClick={auth.logout} title={t("logout")}>
          <LogOut size={18} />
          <span>{t("logout")}</span>
        </button>
      </aside>

      <main className="workspace">
        <Outlet />
      </main>
    </div>
  );
}
