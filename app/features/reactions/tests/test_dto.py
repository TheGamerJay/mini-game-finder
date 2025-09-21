"""Unit tests for reactions DTOs."""
import pytest
from datetime import datetime

from app.features.reactions.dto import (
    ReactOnceInput,
    ReactOnceResult,
    ReactionData,
    ReactionCount,
    PostReactionsData,
    GetReactionsInput,
    GetReactionsResult,
)


class TestReactOnceInput:
    """Test ReactOnceInput DTO."""

    def test_valid_input(self):
        """Test valid input creates object successfully."""
        input_data = ReactOnceInput(post_id=1, user_id=2, reaction_type="love")
        assert input_data.post_id == 1
        assert input_data.user_id == 2
        assert input_data.reaction_type == "love"

    def test_invalid_post_id(self):
        """Test invalid post_id raises ValueError."""
        with pytest.raises(ValueError, match="post_id must be positive"):
            ReactOnceInput(post_id=0, user_id=2, reaction_type="love")

        with pytest.raises(ValueError, match="post_id must be positive"):
            ReactOnceInput(post_id=-1, user_id=2, reaction_type="love")

    def test_invalid_user_id(self):
        """Test invalid user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be positive"):
            ReactOnceInput(post_id=1, user_id=0, reaction_type="love")

        with pytest.raises(ValueError, match="user_id must be positive"):
            ReactOnceInput(post_id=1, user_id=-1, reaction_type="love")

    def test_invalid_reaction_type(self):
        """Test invalid reaction_type raises ValueError."""
        with pytest.raises(ValueError, match="reaction_type cannot be empty"):
            ReactOnceInput(post_id=1, user_id=2, reaction_type="")

        with pytest.raises(ValueError, match="reaction_type cannot be empty"):
            ReactOnceInput(post_id=1, user_id=2, reaction_type="   ")


class TestReactOnceResult:
    """Test ReactOnceResult DTO."""

    def test_success_result(self):
        """Test success factory method."""
        result = ReactOnceResult.success("love")
        assert result.created is True
        assert result.reaction_type == "love"
        assert result.message == "Reaction saved!"

    def test_already_exists_result(self):
        """Test already_exists factory method."""
        result = ReactOnceResult.already_exists("fire")
        assert result.created is False
        assert result.reaction_type == "fire"
        assert "You've already reacted with fire" in result.message
        assert "Reactions are permanent" in result.message


class TestReactionData:
    """Test ReactionData DTO."""

    def test_valid_reaction_data(self):
        """Test valid reaction data creation."""
        created_at = datetime.now()
        reaction = ReactionData(
            post_id=1, user_id=2, reaction_type="love", created_at=created_at
        )
        assert reaction.post_id == 1
        assert reaction.user_id == 2
        assert reaction.reaction_type == "love"
        assert reaction.created_at == created_at


class TestReactionCount:
    """Test ReactionCount DTO."""

    def test_valid_reaction_count(self):
        """Test valid reaction count creation."""
        count = ReactionCount(reaction_type="love", count=5)
        assert count.reaction_type == "love"
        assert count.count == 5


class TestPostReactionsData:
    """Test PostReactionsData DTO."""

    def test_total_reactions_calculation(self):
        """Test total reactions is calculated from counts."""
        counts = [
            ReactionCount(reaction_type="love", count=3),
            ReactionCount(reaction_type="fire", count=2),
        ]
        post_reactions = PostReactionsData(
            post_id=1, reaction_counts=counts, user_reaction="love"
        )
        assert post_reactions.total_reactions == 5

    def test_manual_total_reactions(self):
        """Test manually provided total reactions is preserved."""
        counts = [ReactionCount(reaction_type="love", count=3)]
        post_reactions = PostReactionsData(
            post_id=1, reaction_counts=counts, total_reactions=10
        )
        assert post_reactions.total_reactions == 10  # Manual value preserved

    def test_empty_counts(self):
        """Test empty reaction counts."""
        post_reactions = PostReactionsData(post_id=1, reaction_counts=[])
        assert post_reactions.total_reactions == 0


class TestGetReactionsInput:
    """Test GetReactionsInput DTO."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = GetReactionsInput(post_ids=[1, 2, 3], user_id=123)
        assert input_data.post_ids == [1, 2, 3]
        assert input_data.user_id == 123

    def test_valid_input_no_user(self):
        """Test valid input without user_id."""
        input_data = GetReactionsInput(post_ids=[1, 2, 3])
        assert input_data.post_ids == [1, 2, 3]
        assert input_data.user_id is None

    def test_empty_post_ids(self):
        """Test empty post_ids raises ValueError."""
        with pytest.raises(ValueError, match="post_ids cannot be empty"):
            GetReactionsInput(post_ids=[])

    def test_invalid_post_ids(self):
        """Test invalid post_ids raise ValueError."""
        with pytest.raises(ValueError, match="All post_ids must be positive"):
            GetReactionsInput(post_ids=[1, 0, 3])

        with pytest.raises(ValueError, match="All post_ids must be positive"):
            GetReactionsInput(post_ids=[1, -1, 3])


class TestGetReactionsResult:
    """Test GetReactionsResult DTO."""

    def test_get_post_reactions_existing(self):
        """Test getting existing post reactions."""
        counts = [ReactionCount(reaction_type="love", count=3)]
        post_reactions = PostReactionsData(
            post_id=1, reaction_counts=counts, user_reaction="love"
        )
        reactions_by_post = {1: post_reactions}
        result = GetReactionsResult(reactions_by_post=reactions_by_post)

        retrieved = result.get_post_reactions(1)
        assert retrieved.post_id == 1
        assert retrieved.total_reactions == 3
        assert retrieved.user_reaction == "love"

    def test_get_post_reactions_missing(self):
        """Test getting non-existent post reactions returns empty data."""
        result = GetReactionsResult(reactions_by_post={})
        retrieved = result.get_post_reactions(999)

        assert retrieved.post_id == 999
        assert retrieved.reaction_counts == []
        assert retrieved.total_reactions == 0
        assert retrieved.user_reaction is None