"use client";

import { useState, useEffect, useCallback } from "react";
import { Layers, Check, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchCalendars, selectCalendars } from "@/lib/calendars";

export default function CalendarPicker({ sessionToken }) {
  const [calendars, setCalendars] = useState([]);
  const [selected, setSelected] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchCalendars(sessionToken);
      setCalendars(data.calendars || []);
      setSelected(data.selected || ["primary"]);
    } catch (e) {
      console.error("Failed to load calendars:", e);
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

  useEffect(() => { load(); }, [load]);

  const toggle = (id) => {
    setSelected((prev) =>
      prev.includes(id)
        ? prev.length > 1 ? prev.filter((x) => x !== id) : prev  // always keep at least one
        : [...prev, id]
    );
  };

  const save = async () => {
    try {
      setSaving(true);
      await selectCalendars(sessionToken, selected);
    } catch (e) {
      console.error("Failed to save calendar selection:", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return null;
  if (calendars.length <= 1) return null; // only show if there's actually a choice

  const selectedCount = selected.length;
  const totalCount = calendars.length;

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2.5 text-left"
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold">Calendars</p>
            <p className="text-[10px] text-muted-foreground">
            {Math.min(selectedCount, totalCount)} of {totalCount} active
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div className="border-t px-3 pb-3 pt-2">
          <div className="flex flex-col gap-1.5">
            {calendars.map((cal) => (
              <button
                key={cal.id}
                onClick={() => toggle(cal.id)}
                className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted"
              >
                <div
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded"
                  style={{ backgroundColor: selected.includes(cal.id) ? cal.backgroundColor : "transparent", border: `2px solid ${cal.backgroundColor}` }}
                >
                  {selected.includes(cal.id) && <Check className="h-3 w-3 text-white" />}
                </div>
                <span className="truncate text-xs">{cal.name}</span>
                {cal.primary && (
                  <span className="ml-auto shrink-0 text-[9px] text-muted-foreground">primary</span>
                )}
              </button>
            ))}
          </div>
          <Button
            size="sm"
            className="mt-3 w-full h-7 text-xs"
            onClick={save}
            disabled={saving}
          >
            {saving ? (
              <RefreshCw className="mr-1.5 h-3 w-3 animate-spin" />
            ) : null}
            {saving ? "Saving…" : "Apply"}
          </Button>
        </div>
      )}
    </div>
  );
}