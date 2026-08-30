import { apiFetch } from "./api";

export async function fetchCalendars(token) {
  return apiFetch("/api/calendars", { token });
}

export async function selectCalendars(token, calendarIds) {
  return apiFetch("/api/calendars/select", {
    method: "POST",
    token,
    body: { calendar_ids: calendarIds },
  });
}