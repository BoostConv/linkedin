"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, Comment, Post } from "@/lib/api";

const statusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  suggested: "bg-blue-100 text-blue-700",
  approved: "bg-yellow-100 text-yellow-700",
  sent: "bg-green-100 text-green-700",
  skipped: "bg-gray-100 text-gray-400",
};

const statusLabels: Record<string, string> = {
  pending: "En attente",
  suggested: "Suggéré",
  approved: "Approuvé",
  sent: "Envoyé",
  skipped: "Ignoré",
};

export default function CommentsPage() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [selectedPost, setSelectedPost] = useState<string>("");
  const [filter, setFilter] = useState<string>("");
  const [editingReply, setEditingReply] = useState<string | null>(null);
  const [editedText, setEditedText] = useState("");
  const [loading, setLoading] = useState(false);

  const loadComments = () => {
    const params: Record<string, string> = {};
    if (filter) params.status = filter;
    if (selectedPost) params.post_id = selectedPost;
    api.listComments(params).then(setComments).catch(() => {});
  };

  useEffect(() => {
    api.listPosts({ status: "published" }).then(setPosts).catch(() => {});
    loadComments();
  }, []);

  useEffect(() => {
    loadComments();
  }, [filter, selectedPost]);

  const handleFetch = async () => {
    if (!selectedPost) return;
    setLoading(true);
    try {
      const result = await api.fetchPostComments(selectedPost);
      loadComments();
      alert(`${result.new_comments} nouveaux commentaires importés.`);
    } catch {
      alert("Erreur lors de la récupération des commentaires.");
    } finally {
      setLoading(false);
    }
  };

  const handleSuggest = async (commentId: string) => {
    try {
      const result = await api.suggestReply(commentId);
      loadComments();
    } catch {
      alert("Erreur lors de la suggestion.");
    }
  };

  const handleSuggestBatch = async () => {
    if (!selectedPost) return;
    setLoading(true);
    try {
      const result = await api.suggestBatchReplies(selectedPost);
      loadComments();
      alert(`${result.suggested} réponses suggérées.`);
    } catch {
      alert("Erreur.");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (commentId: string) => {
    try {
      await api.approveReply(commentId, editedText);
      setEditingReply(null);
      setEditedText("");
      loadComments();
    } catch {
      alert("Erreur.");
    }
  };

  const handleSend = async (commentId: string) => {
    try {
      await api.sendReply(commentId);
      loadComments();
    } catch {
      alert("Erreur lors de l'envoi.");
    }
  };

  const handleSkip = async (commentId: string) => {
    try {
      await api.skipComment(commentId);
      loadComments();
    } catch {
      alert("Erreur.");
    }
  };

  const startEditing = (comment: Comment) => {
    setEditingReply(comment.id);
    setEditedText(comment.suggested_reply || comment.approved_reply || "");
  };

  const pendingCount = comments.filter(
    (c) => c.reply_status === "pending"
  ).length;
  const prospectCount = comments.filter((c) => c.is_prospect).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Commentaires</h1>
        <div className="flex gap-2 text-sm">
          <span className="text-gray-500">
            {pendingCount} en attente | {prospectCount} prospects
          </span>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Post
              </label>
              <select
                value={selectedPost}
                onChange={(e) => setSelectedPost(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value="">Tous les posts</option>
                {posts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {(p.hook || p.content.slice(0, 60)).slice(0, 60)}...
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Statut
              </label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value="">Tous</option>
                <option value="pending">En attente</option>
                <option value="suggested">Suggéré</option>
                <option value="approved">Approuvé</option>
                <option value="sent">Envoyé</option>
              </select>
            </div>
            <button
              onClick={handleFetch}
              disabled={!selectedPost || loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "..." : "Importer depuis LinkedIn"}
            </button>
            <button
              onClick={handleSuggestBatch}
              disabled={!selectedPost || loading}
              className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 disabled:opacity-50"
            >
              Suggérer toutes les réponses
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Comment list */}
      {comments.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-gray-500">
              Aucun commentaire.{" "}
              {!selectedPost
                ? "Sélectionnez un post publié et importez les commentaires."
                : "Cliquez sur 'Importer depuis LinkedIn'."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {comments.map((c) => (
            <Card
              key={c.id}
              className={c.is_prospect ? "border-l-4 border-l-yellow-400" : ""}
            >
              <CardContent className="py-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-800">
                      {c.author_name}
                    </span>
                    {c.author_headline && (
                      <span className="text-xs text-gray-400 truncate max-w-xs">
                        {c.author_headline}
                      </span>
                    )}
                    {c.is_prospect && (
                      <Badge className="bg-yellow-100 text-yellow-700 text-xs">
                        Prospect
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      className={`text-xs ${statusColors[c.reply_status] || ""}`}
                    >
                      {statusLabels[c.reply_status] || c.reply_status}
                    </Badge>
                    {c.commented_at && (
                      <span className="text-xs text-gray-400">
                        {new Date(c.commented_at).toLocaleDateString("fr-FR", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    )}
                  </div>
                </div>

                {/* Comment content */}
                <p className="text-sm text-gray-700 mb-3 bg-gray-50 rounded-lg p-3">
                  {c.content}
                </p>

                {/* Suggested/Approved reply */}
                {(c.suggested_reply || c.approved_reply) &&
                  editingReply !== c.id && (
                    <div className="bg-blue-50 rounded-lg p-3 mb-3">
                      <p className="text-xs font-medium text-blue-600 mb-1">
                        {c.reply_status === "approved"
                          ? "Réponse approuvée"
                          : "Suggestion IA"}
                      </p>
                      <p className="text-sm text-gray-700">
                        {c.approved_reply || c.suggested_reply}
                      </p>
                    </div>
                  )}

                {/* Editing reply */}
                {editingReply === c.id && (
                  <div className="mb-3">
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-2"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(c.id)}
                        className="px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
                      >
                        Approuver
                      </button>
                      <button
                        onClick={() => {
                          setEditingReply(null);
                          setEditedText("");
                        }}
                        className="px-3 py-1.5 border border-gray-200 rounded text-xs hover:bg-gray-50"
                      >
                        Annuler
                      </button>
                    </div>
                  </div>
                )}

                {/* Actions */}
                {editingReply !== c.id && (
                  <div className="flex gap-2">
                    {c.reply_status === "pending" && (
                      <button
                        onClick={() => handleSuggest(c.id)}
                        className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700"
                      >
                        Générer une réponse
                      </button>
                    )}
                    {(c.reply_status === "suggested" ||
                      c.reply_status === "pending") && (
                      <button
                        onClick={() => startEditing(c)}
                        className="px-3 py-1.5 border border-gray-200 rounded text-xs hover:bg-gray-50"
                      >
                        Éditer et approuver
                      </button>
                    )}
                    {c.reply_status === "approved" && (
                      <button
                        onClick={() => handleSend(c.id)}
                        className="px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
                      >
                        Envoyer sur LinkedIn
                      </button>
                    )}
                    {c.reply_status !== "sent" &&
                      c.reply_status !== "skipped" && (
                        <button
                          onClick={() => handleSkip(c.id)}
                          className="px-3 py-1.5 text-gray-400 hover:text-gray-600 text-xs"
                        >
                          Ignorer
                        </button>
                      )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
