import { apiFetch } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";

export async function listThreads(token) {
  return apiFetch("/api/agent/threads", { token });
}

export async function loadThread(token, threadId) {
  return apiFetch(`/api/agent/threads/${threadId}`, { token });
}

export async function deleteThread(token, threadId) {
  return apiFetch(`/api/agent/threads/${threadId}`, {
    method: "DELETE",
    token,
  });
}

export async function streamAgentChat(token, input, onEvent) {
  const response = await fetch(`${API_URL}/api/agent/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to initialize agent streaming response.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data:")) {
        const rawJson = trimmed.slice(5).trim();
        if (rawJson) {
          try {
            const parsedEvent = JSON.parse(rawJson);
            onEvent(parsedEvent);
          } catch {
            // Ignore incomplete chunk
          }
        }
      }
    }
  }
}