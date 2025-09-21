"""Unit tests for reactions service layer."""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from psycopg2 import errors as pg_errors

from app.common.errors import ValidationError
from app.features.reactions.service import ReactionsService, VALID_REACTIONS
from app.features.reactions.dto import (
    ReactOnceInput,
    ReactOnceResult,
    ReactionData,
    ReactionCount,
    PostReactionsData,
    GetReactionsInput,
    GetReactionsResult,
)


class TestReactionsService:
    """Test ReactionsService business logic."""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository."""
        return ReactionsService(mock_repo)

    def test_react_once_success(self, service, mock_repo):
        """Test successful reaction creation."""
        # Setup
        input_data = ReactOnceInput(post_id=1, user_id=2, reaction_type="love")
        mock_repo.get_user_reaction.return_value = None  # No existing reaction

        # Execute
        result = service.react_once(input_data)

        # Verify
        mock_repo.get_user_reaction.assert_called_once_with(1, 2)
        mock_repo.insert_reaction.assert_called_once_with(1, 2, "love")

        assert result.created is True
        assert result.reaction_type == "love"
        assert result.message == "Reaction saved!"

    def test_react_once_already_exists(self, service, mock_repo):
        """Test reaction when user already reacted."""
        # Setup
        input_data = ReactOnceInput(post_id=1, user_id=2, reaction_type="love")
        existing_reaction = ReactionData(
            post_id=1, user_id=2, reaction_type="fire", created_at=datetime.now()
        )
        mock_repo.get_user_reaction.return_value = existing_reaction

        # Execute
        result = service.react_once(input_data)

        # Verify
        mock_repo.get_user_reaction.assert_called_once_with(1, 2)
        mock_repo.insert_reaction.assert_not_called()  # Should not insert

        assert result.created is False
        assert result.reaction_type == "fire"  # Returns existing reaction
        assert "You've already reacted with fire" in result.message

    def test_react_once_invalid_reaction_type(self, service, mock_repo):
        """Test reaction with invalid reaction type."""
        input_data = ReactOnceInput(post_id=1, user_id=2, reaction_type="invalid")

        with pytest.raises(ValidationError) as exc_info:
            service.react_once(input_data)

        assert "Invalid reaction type: invalid" in str(exc_info.value)
        assert exc_info.value.details["valid_reactions"] == VALID_REACTIONS

    def test_react_once_race_condition(self, service, mock_repo):
        """Test race condition handling with IntegrityError."""
        # Setup
        input_data = ReactOnceInput(post_id=1, user_id=2, reaction_type="love")
        mock_repo.get_user_reaction.side_effect = [
            None,  # First call: no existing reaction
            ReactionData(post_id=1, user_id=2, reaction_type="fire", created_at=datetime.now())  # After race condition
        ]

        # Mock IntegrityError with UniqueViolation
        mock_unique_violation = Mock(spec=pg_errors.UniqueViolation)
        mock_integrity_error = IntegrityError("statement", "params", "orig")
        mock_integrity_error.orig = mock_unique_violation
        mock_repo.insert_reaction.side_effect = mock_integrity_error

        # Execute
        result = service.react_once(input_data)

        # Verify
        assert mock_repo.get_user_reaction.call_count == 2  # Called twice
        mock_repo.insert_reaction.assert_called_once_with(1, 2, "love")

        assert result.created is False
        assert result.reaction_type == "fire"  # Returns the actual stored reaction

    def test_react_once_integrity_error_not_unique_violation(self, service, mock_repo):
        """Test IntegrityError that's not a unique violation gets re-raised."""
        # Setup
        input_data = ReactOnceInput(post_id=1, user_id=2, reaction_type="love")
        mock_repo.get_user_reaction.return_value = None

        # Mock IntegrityError without UniqueViolation
        mock_integrity_error = IntegrityError("statement", "params", "orig")
        mock_integrity_error.orig = Mock()  # Not a UniqueViolation
        mock_repo.insert_reaction.side_effect = mock_integrity_error

        # Execute & Verify
        with pytest.raises(IntegrityError):
            service.react_once(input_data)

    def test_get_reactions_with_user(self, service, mock_repo):
        """Test getting reactions with user ID."""
        # Setup
        input_data = GetReactionsInput(post_ids=[1, 2], user_id=123)

        mock_repo.get_reaction_counts_bulk.return_value = {
            1: [ReactionCount(reaction_type="love", count=3)],
            2: [ReactionCount(reaction_type="fire", count=2)]
        }
        mock_repo.get_user_reactions_bulk.return_value = {1: "love"}

        # Execute
        result = service.get_reactions(input_data)

        # Verify
        mock_repo.get_reaction_counts_bulk.assert_called_once_with([1, 2])
        mock_repo.get_user_reactions_bulk.assert_called_once_with([1, 2], 123)

        assert len(result.reactions_by_post) == 2

        post1_reactions = result.reactions_by_post[1]
        assert post1_reactions.post_id == 1
        assert post1_reactions.total_reactions == 3
        assert post1_reactions.user_reaction == "love"

        post2_reactions = result.reactions_by_post[2]
        assert post2_reactions.post_id == 2
        assert post2_reactions.total_reactions == 2
        assert post2_reactions.user_reaction is None

    def test_get_reactions_without_user(self, service, mock_repo):
        """Test getting reactions without user ID."""
        # Setup
        input_data = GetReactionsInput(post_ids=[1])

        mock_repo.get_reaction_counts_bulk.return_value = {
            1: [ReactionCount(reaction_type="love", count=3)]
        }

        # Execute
        result = service.get_reactions(input_data)

        # Verify
        mock_repo.get_reaction_counts_bulk.assert_called_once_with([1])
        mock_repo.get_user_reactions_bulk.assert_not_called()  # Should not call without user_id

        post1_reactions = result.reactions_by_post[1]
        assert post1_reactions.user_reaction is None

    def test_get_reactions_posts_with_no_reactions(self, service, mock_repo):
        """Test getting reactions for posts that have no reactions."""
        # Setup
        input_data = GetReactionsInput(post_ids=[1, 2])

        mock_repo.get_reaction_counts_bulk.return_value = {}  # No reactions found
        mock_repo.get_user_reactions_bulk.return_value = {}

        # Execute
        result = service.get_reactions(input_data)

        # Verify
        assert len(result.reactions_by_post) == 2

        post1_reactions = result.reactions_by_post[1]
        assert post1_reactions.post_id == 1
        assert post1_reactions.reaction_counts == []
        assert post1_reactions.total_reactions == 0

    def test_get_post_reactions(self, service, mock_repo):
        """Test getting reactions for a single post."""
        # Setup
        mock_repo.get_reaction_counts_bulk.return_value = {
            1: [ReactionCount(reaction_type="love", count=3)]
        }
        mock_repo.get_user_reactions_bulk.return_value = {1: "love"}

        # Execute
        result = service.get_post_reactions(post_id=1, user_id=123)

        # Verify
        mock_repo.get_reaction_counts_bulk.assert_called_once_with([1])
        mock_repo.get_user_reactions_bulk.assert_called_once_with([1], 123)

        assert result.post_id == 1
        assert result.total_reactions == 3
        assert result.user_reaction == "love"

    def test_delete_user_data(self, service, mock_repo):
        """Test deleting user reaction data."""
        # Setup
        mock_repo.delete_user_reactions.return_value = 5

        # Execute
        deleted_count = service.delete_user_data(user_id=123)

        # Verify
        mock_repo.delete_user_reactions.assert_called_once_with(123)
        assert deleted_count == 5

    def test_delete_post_data(self, service, mock_repo):
        """Test deleting post reaction data."""
        # Setup
        mock_repo.delete_post_reactions.return_value = 8

        # Execute
        deleted_count = service.delete_post_data(post_id=456)

        # Verify
        mock_repo.delete_post_reactions.assert_called_once_with(456)
        assert deleted_count == 8

    def test_get_valid_reactions(self, service, mock_repo):
        """Test getting valid reaction types."""
        valid_reactions = service.get_valid_reactions()

        assert valid_reactions == VALID_REACTIONS
        # Ensure it's a copy, not the original
        assert valid_reactions is not VALID_REACTIONS

    def test_get_reaction_statistics(self, service, mock_repo):
        """Test getting reaction statistics."""
        # Setup
        mock_repo.get_reaction_stats.return_value = {
            "love": 10,
            "fire": 5,
            "star": 3
        }

        # Execute
        stats = service.get_reaction_statistics()

        # Verify
        mock_repo.get_reaction_stats.assert_called_once()
        assert stats["love"] == 10
        assert stats["fire"] == 5
        assert stats["star"] == 3