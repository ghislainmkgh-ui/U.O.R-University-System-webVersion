import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { saveLastAppLocation } from "./lastLocation.js";

export function LastLocationTracker() {
  const location = useLocation();

  useEffect(() => {
    saveLastAppLocation(location);
  }, [location]);

  return null;
}
