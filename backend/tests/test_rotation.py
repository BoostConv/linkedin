"""Tests for pillar rotation algorithm."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pillar import Pillar
from app.models.user import User
from app.services.ai.rotation import get_next_pillar, get_pillar_balance


@pytest.mark.asyncio
class TestPillarRotation:
    async def test_get_next_pillar_returns_pillar(
        self, db_session: AsyncSession, test_user: User, test_pillar: Pillar
    ):
        """Should return a pillar when at least one exists."""
        pillar = await get_next_pillar(db_session, test_user.id)
        assert pillar is not None
        assert pillar.id == test_pillar.id

    async def test_get_pillar_balance_structure(
        self, db_session: AsyncSession, test_user: User, test_pillar: Pillar
    ):
        """Balance should return proper structure."""
        balance = await get_pillar_balance(db_session, test_user.id)
        assert isinstance(balance, list)
        assert len(balance) >= 1
        b = balance[0]
        assert "pillar_name" in b
        assert "weight" in b
        assert "target_pct" in b
        assert "actual_pct" in b
        assert "deficit_pct" in b

    async def test_multiple_pillars_deficit_ordering(
        self, db_session: AsyncSession, test_user: User, test_pillar: Pillar
    ):
        """With multiple pillars and no posts, should pick highest weight first."""
        pillar2 = Pillar(
            id=uuid.uuid4(),
            name="Landing Pages",
            slug="landing-pages",
            weight=40,  # Higher weight than test_pillar (25)
            is_active=True,
            display_order=2,
        )
        db_session.add(pillar2)
        await db_session.commit()

        next_p = await get_next_pillar(db_session, test_user.id)
        # With no posts, the highest weight pillar should have the biggest deficit
        assert next_p.id == pillar2.id
