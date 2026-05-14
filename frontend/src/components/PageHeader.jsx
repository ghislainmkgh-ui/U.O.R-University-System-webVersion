import { usePreferences } from "../state/PreferencesContext.jsx";

export function PageHeader({ title, subtitle, children }) {
  const { tx } = usePreferences();

  return (
    <header className={`page-header${children ? " has-actions" : ""}`}>
      <div className="page-header-copy">
        <h1>{tx(title)}</h1>
        {subtitle && <p>{tx(subtitle)}</p>}
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </header>
  );
}
