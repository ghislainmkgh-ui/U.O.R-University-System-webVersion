const LAST_APP_LOCATION_KEY = "uor_last_app_location";

const RESTORABLE_PATHS = new Set([
  "/",
  "/students",
  "/finance",
  "/academics",
  "/academic-years",
  "/access",
  "/access-requests",
  "/reports",
  "/transfers",
]);

export function saveLastAppLocation(location) {
  const path = locationToPath(location);
  if (!isRestorableAppPath(path)) return;
  localStorage.setItem(LAST_APP_LOCATION_KEY, path);
}

export function getLastAppLocation() {
  const path = localStorage.getItem(LAST_APP_LOCATION_KEY) || "";
  return isRestorableAppPath(path) ? path : "/";
}

export function resolvePostLoginLocation(fromLocation) {
  const fromPath = locationToPath(fromLocation);
  if (isRestorableAppPath(fromPath)) return fromPath;
  return getLastAppLocation();
}

export function locationToPath(location) {
  if (!location) return "";
  if (typeof location === "string") return location;
  const pathname = location.pathname || "";
  const search = location.search || "";
  const hash = location.hash || "";
  return `${pathname}${search}${hash}`;
}

function isRestorableAppPath(path) {
  if (!path || typeof path !== "string") return false;
  if (!path.startsWith("/") || path.startsWith("//")) return false;

  const pathname = path.split(/[?#]/)[0] || "/";
  if (pathname === "/login") return false;
  return RESTORABLE_PATHS.has(pathname);
}
