"use client";

import { useState, useEffect, useCallback } from "react";
import { Calendar, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchCalendarConnection, connectCalendar, refreshCalendarConnection } from "@/lib/connections";

export default function ConnectionPanel({ sessionToken, onConnectionChange }) {
  const [connection, setConnection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchCalendarConnection(sessionToken);
      setConnection(data);
      onConnectionChange?.(data?.status === "connected");
    } catch (error) {
      console.error("Failed to fetch connection status:", error);
      onConnectionChange?.(false);
    } finally {
      setLoading(false);
    }
  }, [sessionToken, onConnectionChange]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    try {
      setBusy(true);
      await connectCalendar(sessionToken);
    } catch (error) {
      console.error("Connection initiation failed:", error);
    } finally {
      setBusy(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setBusy(true);
      const updated = await refreshCalendarConnection(sessionToken);
      setConnection(updated);
      onConnectionChange?.(updated?.status === "connected");
    } catch (error) {
      console.error("Failed to refresh status:", error);
    } finally {
      setBusy(false);
    }
  };

  if (loading || !connection) {
    return <Skeleton className="h-14 w-full rounded-lg" />;
  }

  const isConnected = connection.status === "connected";

  return (
    <div className="flex items-center justify-between rounded-lg border bg-card p-3 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${isConnected ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground"}`}>
          <Calendar className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-semibold">{connection.label}</p>
          <Badge
            variant={isConnected ? "default" : "secondary"}
            className={`mt-0.5 text-[10px] ${isConnected ? "bg-emerald-600 hover:bg-emerald-700" : ""}`}
          >
            {connection.status}
          </Badge>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <Button
          size="sm"
          variant={isConnected ? "outline" : "default"}
          onClick={handleConnect}
          disabled={busy}
          className="h-7 text-xs"
        >
          {isConnected ? "Reconnect" : "Connect"}
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={handleRefresh}
          disabled={busy}
          className="h-7 w-7"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
        </Button>
      </div>
    </div>
  );
}