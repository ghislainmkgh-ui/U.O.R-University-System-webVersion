import { usePreferences } from "../state/PreferencesContext.jsx";

export function AsyncState({ loading, error, children }) {
  const { t } = usePreferences();

  if (loading) {
    return <div className="surface state-line">{t("loading")}</div>;
  }

  if (error) {
    return <div className="surface state-line error-text">{error}</div>;
  }

  return children;
}
