"""Shared test fixtures."""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.post import Post

# Use SQLite for tests (lightweight, no Postgres needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """FastAPI test client with overridden DB dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from passlib.hash import bcrypt

    user = User(
        id=uuid.uuid4(),
        email="test@boost.com",
        hashed_password=bcrypt.hash("testpass123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(test_user: User) -> str:
    """Generate a JWT for the test user."""
    from jose import jwt
    from app.config import get_settings

    settings = get_settings()
    payload = {
        "sub": str(test_user.id),
        "exp": datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def test_pillar(db_session: AsyncSession) -> Pillar:
    pillar = Pillar(
        id=uuid.uuid4(),
        name="CRO & Optimisation",
        slug="cro-optimisation",
        description="Test pillar",
        weight=25,
        is_active=True,
        display_order=1,
    )
    db_session.add(pillar)
    await db_session.commit()
    await db_session.refresh(pillar)
    return pillar


@pytest_asyncio.fixture
async def test_template(db_session: AsyncSession) -> PostTemplate:
    template = PostTemplate(
        id=uuid.uuid4(),
        name="Opinion tranchée",
        slug="opinion-tranchee",
        description="Test template",
        structure=[
            {"step": 1, "label": "Accroche provocante"},
            {"step": 2, "label": "Développement"},
            {"step": 3, "label": "CTA"},
        ],
        prompt_instructions="Write a bold opinion post.",
        when_to_use="When taking a strong stance.",
        is_active=True,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_post(db_session: AsyncSession, test_user: User, test_pillar: Pillar) -> Post:
    post = Post(
        id=uuid.uuid4(),
        user_id=test_user.id,
        content="Mon premier test post sur LinkedIn. Le CRO est sous-estimé par 90% des marques DTC.",
        hook="Le CRO est sous-estimé",
        format="text",
        pillar_id=test_pillar.id,
        status="draft",
        word_count=15,
        anti_ai_score=85,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post
