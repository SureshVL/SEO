"use client";

import { useState, useEffect } from "react";
import {
  ChevronLeft, ChevronRight, Clock, AlertCircle, Check, Loader2,
  Calendar as CalendarIcon, Trash2, Edit2, Play, Copy, Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CalendarEvent {
  id: number;
  title: string;
  slug: string;
  scheduled_date: string;
  status: "scheduled" | "draft" | "published" | "failed" | "cancelled";
  cms_platform: string;
  cms_url?: string;
  auto_publish: boolean;
}

interface PublishLog {
  id: number;
  event_type: string;
  http_status?: number;
  error_message?: string;
  created_at: string;
}

export default function CalendarPage() {
  const { apiKey } = useAppStore();

  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [publishLogs, setPublishLogs] = useState<PublishLog[]>([]);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  const [scheduleForm, setScheduleForm] = useState({
    title: "",
    slug: "",
    body: "",
    meta_description: "",
    scheduled_date: "",
    cms_platform: "wordpress",
    auto_publish: true,
  });

  const [scheduling, setScheduling] = useState(false);

  // Fetch calendar events
  const fetchCalendar = async () => {
    if (!apiKey) return;

    setLoading(true);
    try {
      const startOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
        .toISOString().split("T")[0];
      const endOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0)
        .toISOString().split("T")[0];

      const res = await fetch(
        `${API}/calendar?start_date=${startOfMonth}&end_date=${endOfMonth}`,
        { headers: { "X-API-KEY": apiKey } }
      );

      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
      }
    } catch (err) {
      console.error("Failed to fetch calendar:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPublishLogs = async (eventId: number) => {
    if (!apiKey) return;

    try {
      const res = await fetch(`${API}/calendar/${eventId}/logs`, {
        headers: { "X-API-KEY": apiKey },
      });

      if (res.ok) {
        const data = await res.json();
        setPublishLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    }
  };

  useEffect(() => {
    fetchCalendar();
  }, [currentDate, apiKey]);

  useEffect(() => {
    if (selectedEvent) {
      fetchPublishLogs(selectedEvent.id);
    }
  }, [selectedEvent, apiKey]);

  const handleSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !scheduleForm.scheduled_date) {
      toast.error("Missing required fields");
      return;
    }

    setScheduling(true);
    try {
      const res = await fetch(`${API}/calendar/schedule`, {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(scheduleForm),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Schedule failed");
      }

      toast.success("Article scheduled!");
      setShowScheduleModal(false);
      setScheduleForm({
        title: "",
        slug: "",
        body: "",
        meta_description: "",
        scheduled_date: "",
        cms_platform: "wordpress",
        auto_publish: true,
      });
      fetchCalendar();
    } catch (err: any) {
      toast.error(err.message || "Schedule failed");
    } finally {
      setScheduling(false);
    }
  };

  const handlePublish = async (eventId: number) => {
    if (!apiKey || !confirm("Publish this article now?")) return;

    try {
      const res = await fetch(`${API}/calendar/${eventId}/publish`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });

      if (!res.ok) throw new Error("Publish failed");
      toast.success("Article published!");
      fetchCalendar();
      if (selectedEvent?.id === eventId) {
        fetchPublishLogs(eventId);
      }
    } catch (err: any) {
      toast.error(err.message || "Publish failed");
    }
  };

  const handleReschedule = async (eventId: number, newDate: string) => {
    if (!apiKey) return;

    try {
      const res = await fetch(`${API}/calendar/${eventId}?new_date=${newDate}`, {
        method: "PATCH",
        headers: { "X-API-KEY": apiKey },
      });

      if (!res.ok) throw new Error("Reschedule failed");
      toast.success("Rescheduled!");
      fetchCalendar();
    } catch (err: any) {
      toast.error(err.message || "Reschedule failed");
    }
  };

  const handleCancel = async (eventId: number) => {
    if (!apiKey || !confirm("Cancel this scheduled article?")) return;

    try {
      const res = await fetch(`${API}/calendar/${eventId}`, {
        method: "DELETE",
        headers: { "X-API-KEY": apiKey },
      });

      if (!res.ok) throw new Error("Cancel failed");
      toast.success("Cancelled!");
      fetchCalendar();
      setSelectedEvent(null);
    } catch (err: any) {
      toast.error(err.message || "Cancel failed");
    }
  };

  // Calendar grid generation
  const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
  const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
  const prevLastDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 0).getDate();
  const nextDays = 7 - lastDay.getDay();

  const daysToDisplay: (number | null)[] = [];
  for (let i = firstDay.getDay(); i > 0; i--) {
    daysToDisplay.push(null); // prev month
  }
  for (let i = 1; i <= lastDay.getDate(); i++) {
    daysToDisplay.push(i);
  }
  for (let i = 1; i <= nextDays; i++) {
    daysToDisplay.push(null); // next month
  }

  const getEventsForDate = (day: number) => {
    const dateStr = new Date(currentDate.getFullYear(), currentDate.getMonth(), day)
      .toISOString().split("T")[0];
    return events.filter((e) => e.scheduled_date.startsWith(dateStr));
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "published":
        return "bg-emerald-500/20 text-emerald-300";
      case "scheduled":
        return "bg-cyan-500/20 text-cyan-300";
      case "failed":
        return "bg-red-500/20 text-red-300";
      case "cancelled":
        return "bg-zinc-700/50 text-zinc-400";
      default:
        return "bg-zinc-800 text-zinc-300";
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950">
      <PageHeader
        title="Editorial Calendar"
        subtitle="Schedule and publish content automatically to your CMS"
      />

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-3 gap-6">
          {/* Calendar */}
          <div className="col-span-2 space-y-4">
            {/* Month Navigation */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-zinc-100">
                {currentDate.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))}
                  className="btn-secondary p-2"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))}
                  className="btn-secondary p-2"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Day Headers */}
            <div className="grid grid-cols-7 gap-2 mb-2">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                <div key={day} className="text-center text-xs font-semibold text-zinc-500 py-2">
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-2">
              {daysToDisplay.map((day, idx) => {
                const dayEvents = day ? getEventsForDate(day) : [];
                const isToday =
                  day &&
                  day === new Date().getDate() &&
                  currentDate.getMonth() === new Date().getMonth() &&
                  currentDate.getFullYear() === new Date().getFullYear();

                return (
                  <div
                    key={idx}
                    className={cn(
                      "min-h-24 p-2 rounded-lg border transition-colors",
                      day
                        ? "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"
                        : "bg-zinc-950 border-zinc-900",
                      isToday && "border-cyan-500/50 bg-cyan-500/5"
                    )}
                  >
                    {day && (
                      <>
                        <div className={cn(
                          "text-xs font-semibold mb-1",
                          isToday ? "text-cyan-400" : "text-zinc-400"
                        )}>
                          {day}
                        </div>
                        <div className="space-y-1">
                          {dayEvents.slice(0, 2).map((event) => (
                            <div
                              key={event.id}
                              onClick={() => setSelectedEvent(event)}
                              className={cn(
                                "text-[10px] p-1 rounded truncate cursor-pointer hover:opacity-80",
                                statusColor(event.status)
                              )}
                            >
                              {event.title}
                            </div>
                          ))}
                          {dayEvents.length > 2 && (
                            <div className="text-[10px] text-zinc-500 px-1">
                              +{dayEvents.length - 2} more
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Schedule Button */}
            <button
              onClick={() => setShowScheduleModal(true)}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Schedule Article
            </button>

            {/* Event Details */}
            {selectedEvent ? (
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-zinc-100 line-clamp-2">
                    {selectedEvent.title}
                  </h3>
                  <span className={cn(
                    "text-xs px-2 py-1 rounded font-medium",
                    statusColor(selectedEvent.status)
                  )}>
                    {selectedEvent.status}
                  </span>
                </div>

                <div className="space-y-2 text-xs text-zinc-400">
                  <div className="flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    {new Date(selectedEvent.scheduled_date).toLocaleString()}
                  </div>
                  <div>Slug: <span className="text-zinc-300">{selectedEvent.slug}</span></div>
                  <div>Platform: <span className="text-zinc-300">{selectedEvent.cms_platform}</span></div>
                  {selectedEvent.cms_url && (
                    <div>
                      <a href={selectedEvent.cms_url} target="_blank" rel="noopener noreferrer"
                        className="text-cyan-400 hover:text-cyan-300 underline">
                        View on CMS →
                      </a>
                    </div>
                  )}
                </div>

                {/* Publishing Logs */}
                {publishLogs.length > 0 && (
                  <div className="space-y-2 pt-3 border-t border-zinc-700">
                    <div className="text-xs font-semibold text-zinc-300">Publishing History</div>
                    {publishLogs.slice(0, 3).map((log) => (
                      <div key={log.id} className="text-xs text-zinc-500 flex items-start gap-2">
                        <span className={cn(
                          "mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0",
                          log.event_type === "success" ? "bg-emerald-400" :
                          log.event_type === "failed" ? "bg-red-400" :
                          "bg-zinc-500"
                        )} />
                        <div>
                          <div className="text-zinc-400">{log.event_type}</div>
                          <div className="text-zinc-600">
                            {new Date(log.created_at).toLocaleString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-3 border-t border-zinc-700">
                  {selectedEvent.status === "scheduled" && (
                    <>
                      <button
                        onClick={() => handlePublish(selectedEvent.id)}
                        className="flex-1 btn-primary text-xs py-1.5 flex items-center justify-center gap-1"
                      >
                        <Play className="w-3 h-3" />
                        Publish Now
                      </button>
                      <button
                        onClick={() => handleCancel(selectedEvent.id)}
                        className="flex-1 btn-secondary text-xs py-1.5"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </>
                  )}
                  {selectedEvent.status !== "published" && selectedEvent.status !== "cancelled" && (
                    <button
                      onClick={() => handleCancel(selectedEvent.id)}
                      className="w-full btn-secondary text-xs py-1.5"
                    >
                      <Trash2 className="w-3 h-3 mr-1 inline" />
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 text-center text-sm text-zinc-500">
                Select an event to view details
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Schedule Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-zinc-900 border-b border-zinc-800 p-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-zinc-100">Schedule Article</h2>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSchedule} className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Title
                </label>
                <input
                  type="text"
                  value={scheduleForm.title}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, title: e.target.value })}
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Slug
                </label>
                <input
                  type="text"
                  value={scheduleForm.slug}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, slug: e.target.value })}
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Meta Description
                </label>
                <textarea
                  value={scheduleForm.meta_description}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, meta_description: e.target.value })}
                  className="input-field w-full h-20 resize-none text-sm"
                  maxLength={160}
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Body
                </label>
                <textarea
                  value={scheduleForm.body}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, body: e.target.value })}
                  className="input-field w-full h-32 resize-none text-sm font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Schedule Date & Time
                </label>
                <input
                  type="datetime-local"
                  value={scheduleForm.scheduled_date}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, scheduled_date: e.target.value })}
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  CMS Platform
                </label>
                <select
                  value={scheduleForm.cms_platform}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, cms_platform: e.target.value })}
                  className="input-field w-full"
                >
                  <option value="wordpress">WordPress</option>
                  <option value="shopify">Shopify</option>
                  <option value="webflow">Webflow</option>
                  <option value="custom">Custom Webhook</option>
                </select>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scheduleForm.auto_publish}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, auto_publish: e.target.checked })}
                  className="w-4 h-4 rounded border-zinc-700"
                />
                <span className="text-sm text-zinc-300">Auto-publish on scheduled date</span>
              </label>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="flex-1 btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={scheduling}
                  className="flex-1 btn-primary flex items-center justify-center gap-2"
                >
                  {scheduling ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Scheduling...
                    </>
                  ) : (
                    <>
                      <CalendarIcon className="w-4 h-4" />
                      Schedule
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
