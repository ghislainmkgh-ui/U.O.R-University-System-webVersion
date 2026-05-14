import { useEffect, useState } from "react";

import { getApiBaseUrl } from "../api/client.js";

export function StudentPhoto({ student, size = "medium" }) {
  const hasPhoto = Boolean(student?.has_photo || student?.passport_photo_path);
  const studentId = student?.id || student?.student_id;
  const [src, setSrc] = useState("");
  const initials = `${student?.firstname?.[0] || ""}${student?.lastname?.[0] || ""}`.trim() || "U";

  useEffect(() => {
    let objectUrl = "";
    let cancelled = false;
    setSrc("");

    if (!hasPhoto || !studentId) return undefined;

    const token = localStorage.getItem("uor_token");
    fetch(`${getApiBaseUrl()}/api/students/${studentId}/photo/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((response) => {
        if (!response.ok) throw new Error("photo_unavailable");
        return response.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setSrc("");
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [hasPhoto, studentId]);

  if (!src) {
    return <span className={`student-photo ${size}`}>{initials}</span>;
  }

  return <img className={`student-photo ${size}`} src={src} alt="" loading="lazy" />;
}
