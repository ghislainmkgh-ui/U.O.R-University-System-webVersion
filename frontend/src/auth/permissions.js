const userBlockedViews = new Set(["academic_data", "academic_years", "transfers"]);

export function normalizeRole(role) {
  return String(role || "user").trim().toLowerCase();
}

export function canAccessView(role, viewKey) {
  const normalizedRole = normalizeRole(role);
  if (viewKey === "access_requests") {
    return normalizedRole === "super_admin";
  }
  if (normalizedRole === "user" && userBlockedViews.has(viewKey)) {
    return false;
  }
  return true;
}
