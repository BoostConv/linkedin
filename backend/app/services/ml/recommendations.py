"""Generate content recommendations based on ML insights."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.analytics import PostAnalytics
from app.services.ml.model import get_model_meta


async def get_recommendations(db: AsyncSession, user_id) -> list[dict]:
    """Generate recommendations based on post performance data.

    Returns a list of recommendation dicts with type, title, and detail.
    """
    recommendations = []
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)

    # Fetch published posts with 24h analytics
    result = await db.execute(
        select(Post, PostAnalytics)
        .join(PostAnalytics, PostAnalytics.post_id == Post.id)
        .where(
            Post.user_id == user_id,
            Post.status == "published",
            Post.published_at >= lookback,
            PostAnalytics.snapshot_type == "24h",
        )
    )
    rows = result.all()

    if len(rows) < 5:
        recommendations.append({
            "type": "info",
            "title": "Pas assez de données",
            "detail": f"Publiez encore {5 - len(rows)} posts pour débloquer les recommandations ML.",
        })
        return recommendations

    # Analyze by format
    format_scores = {}
    for post, analytics in rows:
        fmt = post.format
        if fmt not in format_scores:
            format_scores[fmt] = []
        format_scores[fmt].append(analytics.composite_score or 0)

    if len(format_scores) > 1:
        format_avgs = {
            fmt: sum(scores) / len(scores)
            for fmt, scores in format_scores.items()
            if len(scores) >= 2
        }
        if format_avgs:
            best_format = max(format_avgs, key=format_avgs.get)
            worst_format = min(format_avgs, key=format_avgs.get)
            if format_avgs[best_format] > 0 and format_avgs[worst_format] > 0:
                ratio = format_avgs[best_format] / format_avgs[worst_format]
                if ratio > 1.3:
                    format_labels = {"text": "texte", "carousel": "carrousel", "image_text": "image + texte"}
                    recommendations.append({
                        "type": "format",
                        "title": f"Les {format_labels.get(best_format, best_format)}s performent {ratio:.1f}x mieux",
                        "detail": f"Le format {format_labels.get(best_format, best_format)} obtient un score moyen "
                                  f"de {format_avgs[best_format]:.0f} vs {format_avgs[worst_format]:.0f} pour "
                                  f"{format_labels.get(worst_format, worst_format)}.",
                    })

    # Analyze by hook pattern
    hook_scores = {}
    for post, analytics in rows:
        if post.hook_pattern:
            if post.hook_pattern not in hook_scores:
                hook_scores[post.hook_pattern] = []
            hook_scores[post.hook_pattern].append(analytics.composite_score or 0)

    hook_avgs = {
        h: sum(s) / len(s) for h, s in hook_scores.items() if len(s) >= 2
    }
    if hook_avgs:
        best_hook = max(hook_avgs, key=hook_avgs.get)
        recommendations.append({
            "type": "hook",
            "title": f"L'accroche '{best_hook}' est la plus performante",
            "detail": f"Score moyen : {hook_avgs[best_hook]:.0f}. "
                      f"Utilisez-la plus souvent pour maximiser l'engagement.",
        })

    # Analyze by time of day
    hour_scores = {}
    for post, analytics in rows:
        pub_time = post.published_at or post.scheduled_at
        if pub_time:
            hour = pub_time.hour
            bucket = "matin (7-9h)" if 7 <= hour <= 9 else "midi (11-13h)" if 11 <= hour <= 13 else "soir (17-19h)" if 17 <= hour <= 19 else f"{hour}h"
            if bucket not in hour_scores:
                hour_scores[bucket] = []
            hour_scores[bucket].append(analytics.composite_score or 0)

    hour_avgs = {h: sum(s) / len(s) for h, s in hour_scores.items() if len(s) >= 2}
    if hour_avgs:
        best_time = max(hour_avgs, key=hour_avgs.get)
        recommendations.append({
            "type": "timing",
            "title": f"Meilleur créneau : {best_time}",
            "detail": f"Score moyen de {hour_avgs[best_time]:.0f}. "
                      f"Planifiez vos posts à ce créneau pour maximiser la portée.",
        })

    # Anti-AI score correlation
    high_ai_scores = [(post, analytics) for post, analytics in rows if (post.anti_ai_score or 0) >= 80]
    low_ai_scores = [(post, analytics) for post, analytics in rows if (post.anti_ai_score or 0) < 80]
    if len(high_ai_scores) >= 2 and len(low_ai_scores) >= 2:
        high_avg = sum(a.composite_score or 0 for _, a in high_ai_scores) / len(high_ai_scores)
        low_avg = sum(a.composite_score or 0 for _, a in low_ai_scores) / len(low_ai_scores)
        if high_avg > low_avg * 1.2:
            recommendations.append({
                "type": "quality",
                "title": "Les posts à score anti-IA élevé performent mieux",
                "detail": f"Score moyen {high_avg:.0f} (anti-IA ≥80) vs {low_avg:.0f} (anti-IA <80). "
                          f"Prenez le temps de bien valider vos posts avant publication.",
            })

    # Model-based insights
    meta = get_model_meta()
    if meta and meta.get("top_features"):
        top = meta["top_features"][:3]
        feature_labels = {
            "word_count": "longueur du post",
            "has_numbers": "présence de chiffres",
            "number_count": "nombre de chiffres",
            "sentence_length_variance": "variation de longueur des phrases",
            "paragraph_count": "nombre de paragraphes",
            "anti_ai_score": "score anti-IA",
            "has_question": "questions dans le post",
            "is_carousel": "format carrousel",
            "hour_of_day": "heure de publication",
        }
        top_labels = [feature_labels.get(f[0], f[0]) for f in top]
        recommendations.append({
            "type": "ml_insight",
            "title": "Facteurs clés de performance (ML)",
            "detail": f"Les 3 facteurs les plus importants : {', '.join(top_labels)}. "
                      f"Modèle entraîné sur {meta['sample_count']} posts (R² = {meta['train_score']:.2f}).",
        })

    return recommendations
