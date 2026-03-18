"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, Post } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

export default function AnalyticsPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listPosts({ status: "published" })
      .then(setPosts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Build chart data from posts
  const antiAiData = posts
    .filter((p) => p.anti_ai_score !== null)
    .map((p) => ({
      date: new Date(p.created_at).toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "2-digit",
      }),
      score: p.anti_ai_score,
    }))
    .reverse();

  const formatData = posts.reduce(
    (acc, p) => {
      const fmt = p.format || "text";
      if (!acc[fmt]) acc[fmt] = { format: fmt, count: 0 };
      acc[fmt].count++;
      return acc;
    },
    {} as Record<string, { format: string; count: number }>
  );

  const wordCountData = posts
    .filter((p) => p.word_count)
    .map((p) => ({
      date: new Date(p.created_at).toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "2-digit",
      }),
      words: p.word_count,
    }))
    .reverse();

  const hasData = posts.length > 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>

      {/* KPI row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Posts publiés
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{posts.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Score anti-IA moyen
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {posts.filter((p) => p.anti_ai_score !== null).length > 0
                ? Math.round(
                    posts
                      .filter((p) => p.anti_ai_score !== null)
                      .reduce((s, p) => s + (p.anti_ai_score || 0), 0) /
                      posts.filter((p) => p.anti_ai_score !== null).length
                  )
                : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Mots moyens par post
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {posts.filter((p) => p.word_count).length > 0
                ? Math.round(
                    posts
                      .filter((p) => p.word_count)
                      .reduce((s, p) => s + (p.word_count || 0), 0) /
                      posts.filter((p) => p.word_count).length
                  )
                : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Formats utilisés
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {Object.keys(formatData).length || "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anti-AI Score Evolution */}
        <Card>
          <CardHeader>
            <CardTitle>Score anti-IA dans le temps</CardTitle>
          </CardHeader>
          <CardContent>
            {!hasData || antiAiData.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-12">
                Les données apparaîtront après les premières publications.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={antiAiData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis domain={[0, 100]} fontSize={12} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Posts by format */}
        <Card>
          <CardHeader>
            <CardTitle>Posts par format</CardTitle>
          </CardHeader>
          <CardContent>
            {!hasData ? (
              <p className="text-sm text-gray-500 text-center py-12">
                Publiez des posts pour voir la répartition par format.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={Object.values(formatData)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="format" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Word count evolution */}
        <Card>
          <CardHeader>
            <CardTitle>Nombre de mots par post</CardTitle>
          </CardHeader>
          <CardContent>
            {!hasData || wordCountData.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-12">
                Les données apparaîtront après les premières publications.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={wordCountData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="words" fill="#10B981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Placeholder for LinkedIn metrics */}
        <Card>
          <CardHeader>
            <CardTitle>Engagement LinkedIn</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 text-center py-12">
              Connectez votre compte LinkedIn dans les Réglages pour voir les
              métriques d&apos;engagement (impressions, likes, commentaires).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
