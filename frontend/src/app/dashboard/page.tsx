"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, Post, Idea, Recommendation } from "@/lib/api";

interface PillarBalance {
  pillar_name: string;
  weight: number;
  target_pct: number;
  actual_pct: number;
  deficit_pct: number;
  post_count_14d: number;
}

export default function DashboardPage() {
  const [scheduledPosts, setScheduledPosts] = useState<Post[]>([]);
  const [draftPosts, setDraftPosts] = useState<Post[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [nextPillar, setNextPillar] = useState<string | null>(null);
  const [balance, setBalance] = useState<PillarBalance[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  useEffect(() => {
    Promise.allSettled([
      api.listPosts({ status: "scheduled" }),
      api.listPosts({ status: "draft" }),
      api.listIdeas({ status: "new" }),
      fetch("/api/ai/next-pillar").then((r) =>
        r.ok ? r.json() : null
      ),
      fetch("/api/ai/pillar-balance").then(
        (r) => (r.ok ? r.json() : [])
      ),
      api.getRecommendations().catch(() => []),
    ]).then(([schedR, draftR, ideasR, pillarR, balanceR, recsR]) => {
      if (schedR.status === "fulfilled") setScheduledPosts(schedR.value);
      if (draftR.status === "fulfilled") setDraftPosts(draftR.value);
      if (ideasR.status === "fulfilled") setIdeas(ideasR.value);
      if (pillarR.status === "fulfilled" && pillarR.value)
        setNextPillar(pillarR.value.pillar_name);
      if (balanceR.status === "fulfilled" && Array.isArray(balanceR.value))
        setBalance(balanceR.value);
      if (recsR.status === "fulfilled" && Array.isArray(recsR.value))
        setRecommendations(recsR.value);
    });
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Posts planifiés
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{scheduledPosts.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Idées en attente
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{ideas.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Prochain pilier suggéré
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold text-blue-600">
              {nextPillar || "Connectez-vous"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Brouillons à valider
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{draftPosts.length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pillar Balance */}
        <Card>
          <CardHeader>
            <CardTitle>Équilibre des piliers (14 jours)</CardTitle>
          </CardHeader>
          <CardContent>
            {balance.length === 0 ? (
              <p className="text-sm text-gray-500">
                Publiez vos premiers posts pour voir l&apos;équilibre des
                piliers.
              </p>
            ) : (
              <div className="space-y-3">
                {balance.map((b) => (
                  <div key={b.pillar_name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium truncate mr-2">
                        {b.pillar_name}
                      </span>
                      <span className="text-gray-500 whitespace-nowrap">
                        {b.post_count_14d} posts ({b.actual_pct}% / cible{" "}
                        {b.target_pct}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          b.deficit_pct > 5
                            ? "bg-red-400"
                            : b.deficit_pct > 0
                              ? "bg-yellow-400"
                              : "bg-green-400"
                        }`}
                        style={{
                          width: `${Math.min(100, b.target_pct > 0 ? (b.actual_pct / b.target_pct) * 100 : 0)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Upcoming scheduled posts */}
        <Card>
          <CardHeader>
            <CardTitle>Prochains posts planifiés</CardTitle>
          </CardHeader>
          <CardContent>
            {scheduledPosts.length === 0 ? (
              <p className="text-sm text-gray-500">
                Aucun post planifié. Générez un post et planifiez-le.
              </p>
            ) : (
              <div className="space-y-3">
                {scheduledPosts.slice(0, 5).map((post) => (
                  <div
                    key={post.id}
                    className="flex items-start gap-3 text-sm"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-800 line-clamp-2">
                        {post.hook || post.content.slice(0, 100)}
                      </p>
                      {post.scheduled_at && (
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(post.scheduled_at).toLocaleDateString(
                            "fr-FR",
                            {
                              weekday: "short",
                              day: "numeric",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            }
                          )}
                        </p>
                      )}
                    </div>
                    {post.anti_ai_score !== null && (
                      <Badge
                        className={
                          post.anti_ai_score >= 80
                            ? "bg-green-100 text-green-700"
                            : "bg-yellow-100 text-yellow-700"
                        }
                      >
                        {post.anti_ai_score}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent ideas */}
        <Card>
          <CardHeader>
            <CardTitle>Dernières idées</CardTitle>
          </CardHeader>
          <CardContent>
            {ideas.length === 0 ? (
              <p className="text-sm text-gray-500">
                Ajoutez des idées dans la boîte à idées.
              </p>
            ) : (
              <div className="space-y-3">
                {ideas.slice(0, 5).map((idea) => (
                  <div key={idea.id} className="text-sm">
                    <p className="text-gray-800 line-clamp-2">
                      {idea.raw_input}
                    </p>
                    {idea.suggested_angle && (
                      <p className="text-xs text-blue-500 mt-1 line-clamp-1">
                        Angle: {idea.suggested_angle}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ML Recommendations */}
        <Card>
          <CardHeader>
            <CardTitle>Recommandations ML</CardTitle>
          </CardHeader>
          <CardContent>
            {recommendations.length === 0 ? (
              <p className="text-sm text-gray-500">
                Publiez plus de posts pour débloquer les recommandations.
              </p>
            ) : (
              <div className="space-y-3">
                {recommendations.slice(0, 3).map((r, i) => (
                  <div key={i} className="text-sm">
                    <p className="font-medium text-gray-800">{r.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{r.detail}</p>
                  </div>
                ))}
                {recommendations.length > 3 && (
                  <a
                    href="/competitors"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Voir toutes les recommandations
                  </a>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick actions */}
        <Card>
          <CardHeader>
            <CardTitle>Actions rapides</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a
              href="/posts"
              className="block w-full text-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Générer un post avec IA
            </a>
            <a
              href="/carousel"
              className="block w-full text-center px-4 py-2 border border-blue-200 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50"
            >
              Créer un carrousel
            </a>
            <a
              href="/ideas"
              className="block w-full text-center px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Ajouter une idée
            </a>
            <a
              href="/calendar"
              className="block w-full text-center px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Générer un plan IA
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
