import { apiFetch } from "./api";

export async function listDocuments(token) {
  return apiFetch("/api/documents", { token });
}

export async function deleteDocument(token, docId) {
  return apiFetch(`/api/documents/${docId}`, {
    method: "DELETE",
    token,
  });
}

export async function uploadDocument(token, file) {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || "Failed to upload document.");
  }
  return data;
}