"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Sparkles,
  MessageSquarePlus,
  Send,
  Loader2,
  Trash2,
  Menu,
  X,
  ChevronsLeft,
  ChevronsRight,
  Paperclip,
  FileText,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import ConnectionPanel from "./connection-panel";
import CalendarPicker from "./calendar-picker";
import MarkdownMessage from "./markdown-message";
import ConfirmDialog from "./confirm-dialog";
import ThemeToggle from "@/components/theme-toggle";
import { listThreads, loadThread, streamAgentChat, deleteThread } from "@/lib/agent";
import { uploadDocument, deleteDocument } from "@/lib/documents";

const SUGGESTIONS = [
  "What's on my schedule today?",
  "Find a free 30-min slot tomorrow afternoon",
  "Create a 30-minute sync with team tomorrow at 2 PM",
];

// Parse [Attached: file1.pdf, file2.docx] suffix from persisted messages
const ATTACHMENT_SUFFIX_RE = /\n*\[Attached:\s*([^\]]+)\]\s*$/;
function splitAttachments(content) {
  if (!content) return { text: "", files: [] };
  const match = content.match(ATTACHMENT_SUFFIX_RE);
  if (!match) return { text: content, files: [] };
  const files = match[1].split(",").map((f) => f.trim()).filter(Boolean);
  const text = content.slice(0, match.index).trim();
  return { text, files };
}

export default function ChatPanel({ sessionToken, userEmail, onLogout }) {
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [threads, setThreads] = useState([]);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi! I'm Cadence, your calendar assistant. How can I help with your schedule today?",
    },
  ]);
  const [prompt, setPrompt] = useState("");
  const [running, setRunning] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [progress, setProgress] = useState(null);
  const [confirmState, setConfirmState] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);

  // Attachment tray — each entry: { localId, file, name, status, docId, reason }
  const [attachments, setAttachments] = useState([]);
  // Transient approval/rejection popup
  const [notice, setNotice] = useState(null);

  const bottomRef = useRef(null);
  const fileInputRef = useRef(null);
  const noticeTimerRef = useRef(null);

  const refreshThreads = useCallback(async () => {
    try {
      const data = await listThreads(sessionToken);
      setThreads(data.threads || []);
    } catch (e) {
      console.error("Failed to load threads:", e);
    }
  }, [sessionToken]);

  useEffect(() => { refreshThreads(); }, [refreshThreads]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, progress]);
  useEffect(() => () => { if (noticeTimerRef.current) clearTimeout(noticeTimerRef.current); }, []);

  const showNotice = (type, text) => {
    if (noticeTimerRef.current) clearTimeout(noticeTimerRef.current);
    setNotice({ type, text });
    noticeTimerRef.current = setTimeout(() => setNotice(null), 4500);
  };

  const handleStartNewChat = () => {
    if (running) return;
    setThreadId(crypto.randomUUID());
    setMessages([{
      id: "welcome",
      role: "assistant",
      content: "Started a fresh conversation. What would you like to schedule or check on your calendar?",
    }]);
    setPrompt("");
    setAttachments([]);
    setMobileSidebarOpen(false);
  };

  const handleSelectThread = async (id) => {
    if (running || loadingThread || id === threadId) return;
    try {
      setLoadingThread(true);
      const data = await loadThread(sessionToken, id);
      setThreadId(data.threadId);
      setMessages(data.messages && data.messages.length > 0 ? data.messages : []);
      setAttachments([]);
      setMobileSidebarOpen(false);
    } catch (e) {
      console.error("Failed to resume thread:", e);
    } finally {
      setLoadingThread(false);
    }
  };

  const handleDeleteThread = (e, id) => {
    e.stopPropagation();
    if (running || loadingThread) return;
    setConfirmState({ type: "delete", threadId: id });
  };

  const confirmDeleteThread = async () => {
    const id = confirmState?.threadId;
    setConfirmState(null);
    if (!id) return;
    try {
      await deleteThread(sessionToken, id);
      if (id === threadId) handleStartNewChat();
      await refreshThreads();
    } catch (err) {
      console.error("Failed to delete thread:", err);
    }
  };

  // --- Attachments ---
  const handleAttachClick = () => { if (!running) fileInputRef.current?.click(); };

  const handleFilesSelected = async (e) => {
    const files = Array.from(e.target.files || []);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (!files.length) return;

    const newEntries = files.map((file) => ({
      localId: crypto.randomUUID(),
      file,
      name: file.name,
      status: "uploading",
      docId: null,
      reason: null,
    }));
    setAttachments((prev) => [...prev, ...newEntries]);

    for (const entry of newEntries) {
      try {
        const res = await uploadDocument(sessionToken, entry.file);
        setAttachments((prev) =>
          prev.map((a) => a.localId === entry.localId
            ? { ...a, status: "approved", docId: res.document?.id || null }
            : a)
        );
        showNotice("approved", `"${entry.name}" looks good and is ready to use.`);
      } catch (err) {
        setAttachments((prev) =>
          prev.map((a) => a.localId === entry.localId
            ? { ...a, status: "rejected", reason: err.message }
            : a)
        );
        showNotice("rejected", err.message || `"${entry.name}" couldn't be used.`);
      }
    }
  };

  const handleRemoveAttachment = async (localId) => {
    const entry = attachments.find((a) => a.localId === localId);
    setAttachments((prev) => prev.filter((a) => a.localId !== localId));
    if (entry?.status === "approved" && entry.docId) {
      try { await deleteDocument(sessionToken, entry.docId); } catch (err) {
        console.error("Failed to clean up removed document:", err);
      }
    }
  };

  const uploadingCount = attachments.filter((a) => a.status === "uploading").length;
  const rejectedCount = attachments.filter((a) => a.status === "rejected").length;
  const approvedAttachments = attachments.filter((a) => a.status === "approved");
  const canSend =
    !running &&
    !loadingThread &&
    uploadingCount === 0 &&
    rejectedCount === 0 &&
    (prompt.trim().length > 0 || approvedAttachments.length > 0);

  // --- Send ---
  const handleSendMessage = async (textToSend) => {
    const text = (textToSend ?? prompt).trim();
    const fileNames = approvedAttachments.map((a) => a.name);

    if ((!text && fileNames.length === 0) || !canSend) return;

    const userMsgId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();
    const displayContent = fileNames.length
      ? `${text}\n\n[Attached: ${fileNames.join(", ")}]`.trim()
      : text;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: displayContent },
    ]);

    setPrompt("");
    setAttachments([]);
    setRunning(true);
    setProgress("Thinking...");

    try {
      await streamAgentChat(
        sessionToken,
        { message: text, threadId, attachments: fileNames.length ? fileNames : undefined },
        (event) => {
          if (event.type === "progress" && event.message) {
            setProgress(event.message);
          } else if (event.type === "token" && event.token) {
            setProgress(null);
            // Pure updater: derive "already added?" from prev itself, never from an
            // external mutable flag — React can (and in dev StrictMode, does) invoke
            // this function more than once per event, and a mutated outside variable
            // makes the second invocation silently discard the added message.
            setMessages((prev) => {
              const exists = prev.some((msg) => msg.id === assistantMsgId);
              if (!exists) {
                return [...prev, { id: assistantMsgId, role: "assistant", content: event.token }];
              }
              return prev.map((msg) =>
                msg.id === assistantMsgId ? { ...msg, content: msg.content + event.token } : msg
              );
            });
          } else if (event.type === "error") {
            setProgress(null);
            setMessages((prev) => {
              const exists = prev.some((msg) => msg.id === assistantMsgId);
              if (!exists) {
                return [...prev, { id: assistantMsgId, role: "assistant", content: `⚠️ ${event.message}` }];
              }
              return prev.map((msg) =>
                msg.id === assistantMsgId ? { ...msg, content: `⚠️ ${event.message}` } : msg
              );
            });
          }
        }
      );
      await refreshThreads();
    } catch (error) {
      setProgress(null);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: "⚠️ Something went wrong. Please try again." },
      ]);
    } finally {
      setRunning(false);
      setProgress(null);
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Mobile top bar */}
      {!mobileSidebarOpen && (
        <div className="fixed inset-x-0 top-0 z-30 flex h-14 items-center justify-between border-b bg-background/95 px-3 backdrop-blur md:hidden">
          <button onClick={() => setMobileSidebarOpen(true)} className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted">
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold tracking-tight">Cadence</span>
          <ThemeToggle />
        </div>
      )}

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setMobileSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-72 shrink-0 flex-col border-r bg-background p-4 shadow-2xl transition-transform duration-300 ease-in-out
          md:static md:translate-x-0 md:bg-muted/30 md:shadow-none md:transition-[width] md:duration-300
          ${mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"}
          ${sidebarCollapsed ? "md:w-16 md:p-2" : "md:w-72 lg:w-80"}`}
      >
        <div className="flex items-center justify-between px-1 py-1">
          <div className={`flex items-center gap-2 overflow-hidden ${sidebarCollapsed ? "md:w-0 md:opacity-0" : ""}`}>
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="whitespace-nowrap">
              <h2 className="text-sm font-bold tracking-tight">Cadence</h2>
              <p className="text-[11px] text-muted-foreground">Your calendar, sorted</p>
            </div>
          </div>
          <button onClick={() => setMobileSidebarOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted md:hidden">
            <X className="h-4 w-4" />
          </button>
          <button
            onClick={() => setSidebarCollapsed((v) => !v)}
            className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted md:flex"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          </button>
        </div>

        <Button
          onClick={handleStartNewChat}
          variant="outline"
          className={`mt-4 w-full shadow-sm ${sidebarCollapsed ? "md:justify-center md:px-0" : "justify-start gap-2"}`}
        >
          <MessageSquarePlus className="h-4 w-4 shrink-0" />
          <span className={sidebarCollapsed ? "md:hidden" : ""}>New Conversation</span>
        </Button>

        <div className={sidebarCollapsed ? "md:hidden" : "mt-4"}>
          <ConnectionPanel sessionToken={sessionToken} onConnectionChange={setCalendarConnected} />
        </div>

        {calendarConnected && (
          <div className={sidebarCollapsed ? "md:hidden" : "mt-2"}>
            <CalendarPicker sessionToken={sessionToken} />
          </div>
        )}

        <Separator className="my-4" />

        <div className={`flex-1 overflow-hidden ${sidebarCollapsed ? "md:hidden" : ""}`}>
          <p className="px-2 text-xs font-semibold text-muted-foreground">Saved Conversations</p>
          <ScrollArea className="mt-2 h-[calc(100vh-380px)]">
            <div className="flex flex-col gap-1 pr-3">
              {threads.length === 0 ? (
                <p className="px-2 py-4 text-xs text-muted-foreground">No recent conversations.</p>
              ) : (
                threads.map((t) => (
                  <div
                    key={t.id}
                    className={`group flex items-center gap-1 rounded-lg px-1 transition-colors ${t.id === threadId ? "bg-accent" : "hover:bg-muted"}`}
                  >
                    <button
                      onClick={() => handleSelectThread(t.id)}
                      className={`flex min-w-0 flex-1 flex-col overflow-hidden px-2 py-2 text-left text-xs ${t.id === threadId ? "text-accent-foreground font-medium" : ""}`}
                    >
                      <span className="truncate">{t.title}</span>
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(t.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </button>
                    <button
                      onClick={(e) => handleDeleteThread(e, t.id)}
                      className="shrink-0 rounded p-1.5 text-muted-foreground/70 transition-colors hover:bg-destructive/10 hover:text-destructive"
                      title="Delete conversation"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        <div className="mt-auto border-t pt-3">
          <div className={`flex items-center justify-between gap-1 ${sidebarCollapsed ? "md:flex-col" : ""}`}>
            <span className={`truncate text-xs text-muted-foreground ${sidebarCollapsed ? "md:hidden" : ""}`}>
              {userEmail || "Signed in"}
            </span>
            <div className="flex items-center gap-1">
              <ThemeToggle className={sidebarCollapsed ? "" : "hidden"} />
              <div className={sidebarCollapsed ? "hidden" : "block"}><ThemeToggle /></div>
              <Button size="sm" variant="ghost" onClick={() => setConfirmState({ type: "logout" })} className="h-7 text-xs">
                {sidebarCollapsed ? "⏻" : "Log out"}
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden pt-14 md:pt-0">
        <div className="flex-1 min-w-0 w-full overflow-y-auto overflow-x-hidden p-3 sm:p-6">
          <div className="mx-auto flex max-w-3xl min-w-0 w-full flex-col gap-4">
            {messages.length === 1 && messages[0].id === "welcome" && (
              <div className="my-6 flex flex-col items-center text-center sm:my-8">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h1 className="mt-3 text-lg font-bold">Meet Cadence</h1>
                <p className="mt-1 max-w-md text-xs text-muted-foreground">
                  Connect your Google Calendar, attach a work doc, and let Cadence handle the scheduling.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((suggestion) => (
                    <Button key={suggestion} variant="outline" size="sm" onClick={() => handleSendMessage(suggestion)} className="text-xs">
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => {
              const { text, files } = msg.role === "user"
                ? splitAttachments(msg.content)
                : { text: msg.content, files: [] };

              return (
                <div key={msg.id} className={`flex w-full min-w-0 gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`min-w-0 max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm break-words overflow-hidden ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : msg.role === "system"
                      ? "border border-destructive/30 bg-destructive/10 text-destructive"
                      : "border bg-card text-card-foreground"
                  }`}>
                    {msg.role === "user" ? (
                      <div className="flex flex-col gap-2">
                        {files.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {files.map((f) => (
                              <span key={f} className="flex items-center gap-1 rounded-lg bg-primary-foreground/15 px-2 py-1 text-[11px] font-medium">
                                <FileText className="h-3 w-3" />{f}
                              </span>
                            ))}
                          </div>
                        )}
                        {text && <p className="whitespace-pre-wrap break-words">{text}</p>}
                      </div>
                    ) : msg.role === "assistant" ? (
                      msg.content ? <MarkdownMessage content={msg.content} /> : (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />Thinking...
                        </div>
                      )
                    ) : (
                      <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                    )}
                  </div>
                </div>
              );
            })}

            {progress && (
              <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-primary">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />{progress}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Approval/rejection popup */}
        {notice && (
          <div className="pointer-events-none absolute inset-x-0 bottom-24 flex justify-center px-4 sm:bottom-28">
            <div className={`pointer-events-auto flex max-w-md items-start gap-2 rounded-xl border px-3 py-2 text-xs shadow-lg backdrop-blur ${
              notice.type === "rejected"
                ? "border-pink-400/40 bg-pink-500/15 text-pink-600 dark:text-pink-300"
                : "border-emerald-400/40 bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
            }`}>
              {notice.type === "rejected"
                ? <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                : <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
              <span>{notice.text}</span>
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="border-t bg-background p-3 sm:p-4 w-full min-w-0">
          <div className="mx-auto max-w-3xl min-w-0 w-full">
            {/* Attachment badge tray */}
            {attachments.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5">
                {attachments.map((a) => (
                  <span
                    key={a.localId}
                    className={`flex items-center gap-1.5 rounded-lg border px-2 py-1 text-[11px] font-medium ${
                      a.status === "rejected"
                        ? "border-pink-400/50 bg-pink-500/10 text-pink-600 dark:text-pink-300"
                        : a.status === "uploading"
                        ? "border-border bg-muted text-muted-foreground"
                        : "border-primary/30 bg-primary/10 text-primary"
                    }`}
                    title={a.status === "rejected" ? a.reason : a.name}
                  >
                    {a.status === "uploading" ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileText className="h-3 w-3" />}
                    <span className="max-w-[140px] truncate">{a.name}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveAttachment(a.localId)}
                      className="ml-0.5 rounded-full p-0.5 hover:bg-black/10 dark:hover:bg-white/10"
                      title="Remove"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
              className="flex items-end gap-2"
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFilesSelected}
                accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
                multiple
                className="hidden"
              />
              <Button
                type="button"
                size="icon"
                variant="outline"
                onClick={handleAttachClick}
                disabled={running}
                className="h-11 w-11 shrink-0"
                title="Attach a work document — PDF, DOCX, or TXT"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
                }}
                placeholder="Ask about your calendar, or attach a doc (PDF, DOCX, TXT) and ask about it..."
                rows={1}
                className="min-h-[44px] min-w-0 flex-1 resize-none"
                disabled={running}
              />
              <Button
                type="submit"
                size="icon"
                disabled={!canSend}
                className="h-11 w-11 shrink-0 shadow-sm"
                title={
                  rejectedCount > 0 ? "Remove rejected files before sending"
                  : uploadingCount > 0 ? "Waiting for uploads to finish"
                  : "Send"
                }
              >
                {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </div>
        </div>
      </main>

      <ConfirmDialog
        open={!!confirmState}
        title={confirmState?.type === "logout" ? "Log out of Cadence?" : "Delete this conversation?"}
        description={
          confirmState?.type === "logout"
            ? "You'll need to sign in again to access your calendar."
            : "This can't be undone."
        }
        confirmLabel={confirmState?.type === "logout" ? "Log out" : "Delete"}
        destructive={confirmState?.type === "delete"}
        onCancel={() => setConfirmState(null)}
        onConfirm={() => {
          if (confirmState?.type === "logout") { setConfirmState(null); onLogout(); }
          else if (confirmState?.type === "delete") { confirmDeleteThread(); }
        }}
      />
    </div>
  );
}