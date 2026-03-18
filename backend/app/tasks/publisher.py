"""Celery task for publishing scheduled posts to LinkedIn."""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from app.tasks import celery_app
from app.config import get_settings
from app.models.post import Post
from app.models.user import User

settings = get_settings()


async def _publish_post(post_id: str, user_id: str):
    """Async helper to publish a single post."""
    from app.services.linkedin.publisher import publish_text_post, publish_image_post

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as db:
        post = db.get(Post, post_id)
        user = db.get(User, user_id)

        if not post or not user:
            return

        if not user.linkedin_access_token or not user.linkedin_person_id:
            post.status = "failed"
            db.commit()
            return

        try:
            if post.image_url:
                result = await publish_image_post(
                    access_token=user.linkedin_access_token,
                    person_id=user.linkedin_person_id,
                    content=post.content,
                    image_url=post.image_url,
                )
            else:
                result = await publish_text_post(
                    access_token=user.linkedin_access_token,
                    person_id=user.linkedin_person_id,
                    content=post.content,
                )

            post.linkedin_post_id = result["linkedin_post_id"]
            post.status = "published"
            post.published_at = datetime.now(timezone.utc)

        except Exception as e:
            post.status = "failed"
            if not post.generation_metadata:
                post.generation_metadata = {}
            post.generation_metadata["publish_error"] = str(e)

        db.commit()


@celery_app.task(name="app.tasks.publisher.publish_scheduled_posts")
def publish_scheduled_posts():
    """Check for posts that are due to be published and publish them."""
    engine = create_engine(settings.database_url_sync)
    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        posts = db.execute(
            select(Post).where(
                Post.status == "scheduled",
                Post.scheduled_at <= now,
            )
        ).scalars().all()

        for post in posts:
            asyncio.run(_publish_post(str(post.id), str(post.user_id)))

    return f"Checked {len(posts)} post(s) for publishing"


@celery_app.task(name="app.tasks.publisher.publish_post_now")
def publish_post_now(post_id: str, user_id: str):
    """Publish a specific post immediately."""
    asyncio.run(_publish_post(post_id, user_id))
    return f"Published post {post_id}"
