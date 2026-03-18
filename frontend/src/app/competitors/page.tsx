"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  api,
  Competitor,
  CompetitorPost,
  Trend,
  Recommendation,
} from "@/lib/api";

const Spinner = () => (
  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [topPosts, setTopPosts] = useState<CompetitorPost[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [watchRunning, setWatchRunning] = useState(false);
  const [watchResult, setWatchResult] = useState<{ generated: number; saved: number; sources_searched: string[] } | null>(null);
  const [activeTab, setActiveTab] = useState<
    "trends" | "top-posts" | "competitors" | "ml"
  >("trends");

  const handleMultiWatch = async () => {
    setWatchRunning(true);
    setWatchResult(null);
    try {
      const result = await api.multiWatch({ save: true });
      setWatchResult({ generated: result.generated, saved: result.saved, sources_searched: result.sources_searched });
    } catch (err) {
      console.error(err);
    } finally {
      setWatchRunning(false);
    }
  };

  const loadData = () => {
    Promise.allSettled([
      api.listCompetitors(),
      api.getCompetitorTrends(14),
      api.getTopCompetitorPosts(14, 10),
      api.getRecommendations(),
    ]).then(([compR, trendR, postsR, recsR]) => {
      if (compR.status === "fulfilled") setCompetitors(compR.value);
      if (trendR.status === "fulfilled") setTrends(trendR.value);
      if (postsR.status === "fulfilled") setTopPosts(postsR.value);
      if (recsR.status === "fulfilled") setRecommendations(recsR.value);
    });
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAdd = async () => {
    if (!newName.trim() || !newUrl.trim()) return;
    setAdding(true);
    try {
      await api.createCompetitor({ name: newName, linkedin_url: newUrl });
      setNewName("");
      setNewUrl("");
      loadData();
    } catch {
      alert("Erreur lors de l'ajout.");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteCompetitor(id);
      loadData();
    } catch {
      alert("Erreur lors de la suppression.");
    }
  };

  const tabs = [
    { id: "trends" as const, label: "Tendances" },
    { id: "top-posts" as const, label: "Top posts" },
    { id: "competitors" as const, label: "Concurrents" },
    { id: "ml" as const, label: "Recommandations ML" },
  ];

  const recTypeIcons: Record<string, string> = {
    format: "bg-blue-100 text-blue-700",
    hook: "bg-purple-100 text-purple-700",
    timing: "bg-yellow-100 text-yellow-700",
    quality: "bg-green-100 text-green-700",
    ml_insight: "bg-indigo-100 text-indigo-700",
    info: "bg-gray-100 text-gray-600",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          Veille concurrentielle
        </h1>
        <Button
          onClick={handleMultiWatch}
          disabled={watchRunning}
          className="bg-purple-600 hover:bg-purple-700 text-white"
        >
          {watchRunning ? <><Spinner /> Veille en cours...</> : "Lancer la veille multi-sources"}
        </Button>
      </div>

      {watchResult && (
        <div className="bg-purple-50 rounded-lg px-4 py-3 text-sm text-purple-700 flex items-center justify-between">
          <span>
            Veille terminée : {watchResult.generated} idées trouvées sur {watchResult.sources_searched.join(", ")} — ajoutées dans la Boîte à idées
          </span>
          <Button variant="ghost" size="sm" onClick={() => setWatchResult(null)}>Fermer</Button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Trends tab */}
      {activeTab === "trends" && (
        <Card>
          <CardHeader>
            <CardTitle>Sujets tendance (14 jours)</CardTitle>
          </CardHeader>
          <CardContent>
            {trends.length === 0 ? (
              <p className="text-sm text-gray-500">
                Ajoutez des concurrents et attendez le prochain scraping pour
                voir les tendances.
              </p>
            ) : (
              <div className="space-y-3">
                {trends.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-gray-400 w-6">
                        {i + 1}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-gray-800">
                          {t.topic}
                        </p>
                        <p className="text-xs text-gray-500">
                          {t.post_count} posts | Engagement total:{" "}
                          {t.total_engagement}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        className={
                          t.avg_relevance >= 0.7
                            ? "bg-green-100 text-green-700"
                            : t.avg_relevance >= 0.4
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-600"
                        }
                      >
                        Pertinence {Math.round(t.avg_relevance * 100)}%
                      </Badge>
                      <span className="text-xs text-gray-400">
                        Score: {t.trend_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Top posts tab */}
      {activeTab === "top-posts" && (
        <Card>
          <CardHeader>
            <CardTitle>Top posts concurrents (14 jours)</CardTitle>
          </CardHeader>
          <CardContent>
            {topPosts.length === 0 ? (
              <p className="text-sm text-gray-500">
                Aucun post scrapé pour le moment.
              </p>
            ) : (
              <div className="space-y-4">
                {topPosts.map((p) => (
                  <div
                    key={p.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {p.competitor_name && (
                          <span className="text-xs font-semibold text-blue-600">
                            {p.competitor_name}
                          </span>
                        )}
                        {p.detected_topic && (
                          <Badge className="bg-gray-100 text-gray-600 text-xs">
                            {p.detected_topic}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span>{p.likes} likes</span>
                        <span>{p.comments} comm.</span>
                        <span>{p.shares} partages</span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 line-clamp-3">
                      {p.content}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {p.detected_template && (
                        <Badge className="bg-purple-50 text-purple-600 text-xs">
                          {p.detected_template}
                        </Badge>
                      )}
                      {p.relevance_score !== null && (
                        <span className="text-xs text-gray-400">
                          Pertinence: {Math.round(p.relevance_score * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Competitors tab */}
      {activeTab === "competitors" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ajouter un concurrent</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Nom"
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
                <input
                  type="text"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="URL LinkedIn (ex: https://linkedin.com/in/...)"
                  className="flex-[2] px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
                <button
                  onClick={handleAdd}
                  disabled={adding || !newName.trim() || !newUrl.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {adding ? "..." : "Ajouter"}
                </button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Concurrents suivis</CardTitle>
            </CardHeader>
            <CardContent>
              {competitors.length === 0 ? (
                <p className="text-sm text-gray-500">
                  Aucun concurrent ajouté.
                </p>
              ) : (
                <div className="space-y-2">
                  {competitors.map((c) => (
                    <div
                      key={c.id}
                      className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-800">
                          {c.name}
                        </p>
                        <p className="text-xs text-gray-500 truncate max-w-md">
                          {c.linkedin_url}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          className={
                            c.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-gray-100 text-gray-500"
                          }
                        >
                          {c.is_active ? "Actif" : "Inactif"}
                        </Badge>
                        <button
                          onClick={() => handleDelete(c.id)}
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          Supprimer
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ML Recommendations tab */}
      {activeTab === "ml" && (
        <Card>
          <CardHeader>
            <CardTitle>Recommandations ML</CardTitle>
          </CardHeader>
          <CardContent>
            {recommendations.length === 0 ? (
              <p className="text-sm text-gray-500">
                Publiez plus de posts pour débloquer les recommandations
                intelligentes.
              </p>
            ) : (
              <div className="space-y-4">
                {recommendations.map((r, i) => (
                  <div
                    key={i}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Badge
                        className={`text-xs ${recTypeIcons[r.type] || "bg-gray-100 text-gray-600"}`}
                      >
                        {r.type}
                      </Badge>
                      <h4 className="text-sm font-semibold text-gray-800">
                        {r.title}
                      </h4>
                    </div>
                    <p className="text-sm text-gray-600">{r.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
