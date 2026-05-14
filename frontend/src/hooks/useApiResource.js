import { useCallback, useEffect, useState } from "react";

import { apiRequest } from "../api/client.js";

export function useApiResource(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => {
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    let alive = true;

    if (!path) {
      setData(null);
      setLoading(false);
      setError("");
      return () => {
        alive = false;
      };
    }

    setLoading(true);
    setError("");
    apiRequest(path)
      .then((payload) => {
        if (!alive) return;
        const nextData = payload && Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
        setData(nextData);
      })
      .catch((err) => {
        if (alive) setError(err.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [path, reloadToken]);

  return { data, loading, error, reload };
}
