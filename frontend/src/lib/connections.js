import { apiFetch } from "./api";
import { getRefreshToken } from "@descope/nextjs-sdk/client";

export async function fetchCalendarConnection(token) {
  const res = await apiFetch("/api/connections", { token });
  return res.connection;
}

export async function connectCalendar(token) {
  let refreshToken = "";
  try {
    refreshToken = getRefreshToken() || "";
  } catch {
    refreshToken = "";
  }

  const res = await apiFetch("/api/connections/connect", {
    method: "POST",
    token,
    body: {
      refreshToken,
      redirectUrl: `${window.location.origin}/dashboard`,
    },
  });

  if (res && res.url) {
    window.location.href = res.url;
  }
}

export async function refreshCalendarConnection(token) {
  const res = await apiFetch("/api/connections/refresh-status", {
    method: "POST",
    token,
  });
  return res.connection;
}