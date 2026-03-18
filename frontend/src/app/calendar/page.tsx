"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import { api, Post, ContentPlanDay } from "@/lib/api";

const statusColors: Record<string, string> = {
  draft: "#9CA3AF",
  approved: "#3B82F6",
  scheduled: "#8B5CF6",
  published: "#10B981",
  failed: "#EF4444",
};

const formatLabels: Record<string, string> = {
  text: "Texte",
  carousel: "Carrousel",
  image_text: "Image + texte",
};

export default function CalendarPage() {
  const [events, setEvents] = useState<
    {
      id: string;
      title: string;
      start: string;
      backgroundColor: string;
      borderColor: string;
      extendedProps: { status: string; format: string };
    }[]
  >([]);
  const [plan, setPlan] = useState<ContentPlanDay[]>([]);
  const [generating, setGenerating] = useState(false);
  const [planDays, setPlanDays] = useState(7);
  const calendarRef = useRef<FullCalendar>(null);

  const loadEvents = async () => {
    try {
      const posts = await api.listPosts();
      const calEvents = posts
        .filter((p: Post) => p.scheduled_at || p.published_at || p.created_at)
        .map((p: Post) => ({
          id: p.id,
          title: p.hook || p.content.slice(0, 60) + "...",
          start: p.scheduled_at || p.published_at || p.created_at,
          backgroundColor: statusColors[p.status] || "#9CA3AF",
          borderColor: statusColors[p.status] || "#9CA3AF",
          extendedProps: { status: p.status, format: p.format },
        }));
      setEvents(calEvents);
    } catch {
      // Not authenticated yet
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleGeneratePlan = async () => {
    setGenerating(true);
    try {
      const result = await api.generateContentPlan(planDays);
      setPlan(result);
    } catch {
      alert("Erreur lors de la génération du plan.");
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerateDay = async (date: string) => {
    try {
      const result = await api.regenerateDay(date);
      setPlan((prev) =>
        prev.map((d) => (d.date === date ? { ...d, ...result, date } : d))
      );
    } catch {
      alert("Erreur.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          Calendrier éditorial
        </h1>
        <div className="flex gap-2">
          {Object.entries(statusColors).map(([status, color]) => (
            <Badge
              key={status}
              style={{ backgroundColor: color, color: "white" }}
            >
              {status === "draft"
                ? "Brouillon"
                : status === "approved"
                  ? "Approuvé"
                  : status === "scheduled"
                    ? "Planifié"
                    : status === "published"
                      ? "Publié"
                      : "Échoué"}
            </Badge>
          ))}
        </div>
      </div>

      {/* Smart Plan Generator */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Plan de contenu intelligent</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Horizon
              </label>
              <select
                value={planDays}
                onChange={(e) => setPlanDays(Number(e.target.value))}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value={7}>7 jours</option>
                <option value={14}>14 jours</option>
                <option value={30}>30 jours</option>
              </select>
            </div>
            <div className="pt-4">
              <button
                onClick={handleGeneratePlan}
                disabled={generating}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {generating
                  ? "Génération..."
                  : "Générer le plan IA"}
              </button>
            </div>
          </div>

          {plan.length > 0 && (
            <div className="space-y-2">
              {plan.map((day) => (
                <div
                  key={day.date}
                  className="flex items-center gap-4 py-2.5 px-3 bg-gray-50 rounded-lg"
                >
                  <div className="w-24 shrink-0">
                    <p className="text-xs font-semibold text-gray-500">
                      {day.day_name}
                    </p>
                    <p className="text-sm font-medium text-gray-800">
                      {new Date(day.date + "T12:00:00").toLocaleDateString(
                        "fr-FR",
                        { day: "numeric", month: "short" }
                      )}
                    </p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="bg-blue-100 text-blue-700 text-xs">
                        {day.pillar_name}
                      </Badge>
                      <Badge className="bg-purple-100 text-purple-700 text-xs">
                        {day.template_slug}
                      </Badge>
                      <Badge className="bg-gray-100 text-gray-600 text-xs">
                        {formatLabels[day.format] || day.format}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-700 truncate">
                      {day.topic}
                    </p>
                    {day.hook_idea && (
                      <p className="text-xs text-gray-400 truncate mt-0.5">
                        Accroche : {day.hook_idea}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleRegenerateDay(day.date)}
                    className="shrink-0 text-xs text-blue-600 hover:underline"
                  >
                    Régénérer
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Calendar */}
      <Card>
        <CardContent className="p-4">
          <FullCalendar
            ref={calendarRef}
            plugins={[dayGridPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            locale="fr"
            firstDay={1}
            headerToolbar={{
              left: "prev,next today",
              center: "title",
              right: "dayGridMonth,dayGridWeek",
            }}
            events={events}
            editable={true}
            droppable={true}
            eventClick={(info) => {
              window.location.href = `/posts?id=${info.event.id}`;
            }}
            eventDrop={async (info) => {
              const newDate = info.event.start?.toISOString();
              if (newDate && info.event.id) {
                try {
                  await api.updatePost(info.event.id, {
                    scheduled_at: newDate,
                  } as Partial<Post>);
                } catch {
                  info.revert();
                }
              }
            }}
            height="auto"
            dayMaxEvents={3}
            buttonText={{
              today: "Aujourd'hui",
              month: "Mois",
              week: "Semaine",
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
