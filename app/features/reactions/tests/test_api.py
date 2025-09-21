"""Integration tests for reactions API endpoints."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from app.features.reactions.api import reactions_bp
from app.features.reactions.dto import ReactOnceResult, PostReactionsData, ReactionCount


class TestReactionsAPI:
    """Test reactions API endpoints."""

    @pytest.fixture
    def app(self):
        """Create Flask test app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(reactions_bp)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication."""
        user = Mock()
        user.id = 123
        return user

    def test_react_once_success(self, client):
        """Test successful reaction creation."""
        with patch("app.features.reactions.api.require_auth") as mock_auth, \
             patch("app.features.reactions.api.get_db_session") as mock_session, \
             patch("app.features.reactions.api.ReactionsService") as mock_service_class:

            # Setup mocks
            mock_user = Mock()
            mock_user.id = 123
            mock_auth.return_value = lambda f: f  # Bypass auth decorator

            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.react_once.return_value = ReactOnceResult.success("love")

            # Make request with mock authentication
            with client.application.test_request_context():
                with patch("flask.request") as mock_request:
                    mock_request.current_user = mock_user
                    mock_request.get_json.return_value = {
                        "post_id": 1,
                        "reaction_type": "love"
                    }

                    response = client.post("/api/v1/reactions/react",
                                         json={"post_id": 1, "reaction_type": "love"})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["data"]["created"] is True
            assert data["data"]["reaction_type"] == "love"
            assert data["data"]["message"] == "Reaction saved!"

    def test_react_once_missing_body(self, client):
        """Test reaction creation with missing request body."""
        with patch("app.features.reactions.api.require_auth") as mock_auth:
            mock_auth.return_value = lambda f: f

            with client.application.test_request_context():
                with patch("flask.request") as mock_request:
                    mock_request.current_user = Mock()
                    mock_request.get_json.return_value = None

                    response = client.post("/api/v1/reactions/react")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Request body is required" in data["error"]

    def test_react_once_missing_fields(self, client):
        """Test reaction creation with missing fields."""
        with patch("app.features.reactions.api.require_auth") as mock_auth:
            mock_auth.return_value = lambda f: f

            with client.application.test_request_context():
                with patch("flask.request") as mock_request:
                    mock_request.current_user = Mock()
                    mock_request.get_json.return_value = {"post_id": 1}  # Missing reaction_type

                    response = client.post("/api/v1/reactions/react",
                                         json={"post_id": 1})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "reaction_type is required" in data["error"]

    def test_get_reactions_success(self, client):
        """Test successful bulk reactions retrieval."""
        with patch("app.features.reactions.api.get_db_session") as mock_session, \
             patch("app.features.reactions.api.ReactionsService") as mock_service_class:

            # Setup mocks
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # Mock service response
            post_reactions = PostReactionsData(
                post_id=1,
                reaction_counts=[ReactionCount(reaction_type="love", count=3)],
                user_reaction="love"
            )
            mock_result = Mock()
            mock_result.reactions_by_post = {1: post_reactions}
            mock_service.get_reactions.return_value = mock_result

            response = client.get("/api/v1/reactions/posts?post_ids=1&user_id=123")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "1" in data["data"]["reactions_by_post"]
            assert data["data"]["reactions_by_post"]["1"]["total_reactions"] == 3
            assert data["data"]["reactions_by_post"]["1"]["user_reaction"] == "love"

    def test_get_reactions_missing_post_ids(self, client):
        """Test bulk reactions retrieval with missing post_ids."""
        response = client.get("/api/v1/reactions/posts")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "post_ids parameter is required" in data["error"]

    def test_get_reactions_invalid_post_ids(self, client):
        """Test bulk reactions retrieval with invalid post_ids."""
        response = client.get("/api/v1/reactions/posts?post_ids=1,invalid,3")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "post_ids must be comma-separated integers" in data["error"]

    def test_get_post_reactions_success(self, client):
        """Test single post reactions retrieval."""
        with patch("app.features.reactions.api.get_db_session") as mock_session, \
             patch("app.features.reactions.api.ReactionsService") as mock_service_class:

            # Setup mocks
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # Mock service response
            post_reactions = PostReactionsData(
                post_id=1,
                reaction_counts=[ReactionCount(reaction_type="love", count=5)],
                user_reaction=None
            )
            mock_service.get_post_reactions.return_value = post_reactions

            response = client.get("/api/v1/reactions/posts/1")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["data"]["post_id"] == 1
            assert data["data"]["total_reactions"] == 5

    def test_get_valid_reactions(self, client):
        """Test getting valid reaction types."""
        with patch("app.features.reactions.api.get_db_session") as mock_session, \
             patch("app.features.reactions.api.ReactionsService") as mock_service_class:

            # Setup mocks
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_valid_reactions.return_value = ["love", "fire", "star"]

            response = client.get("/api/v1/reactions/types")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["data"]["valid_reactions"] == ["love", "fire", "star"]

    def test_get_reaction_statistics(self, client):
        """Test getting reaction statistics."""
        with patch("app.features.reactions.api.get_db_session") as mock_session, \
             patch("app.features.reactions.api.ReactionsService") as mock_service_class:

            # Setup mocks
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_reaction_statistics.return_value = {
                "love": 10, "fire": 5, "star": 3
            }

            response = client.get("/api/v1/reactions/stats")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["data"]["reaction_stats"]["love"] == 10

    def test_delete_user_reactions_success(self, client):
        """Test successful user reactions deletion."""
        with patch("app.features.reactions.api.require_auth") as mock_auth, \
             patch("app.features.reactions.api.get_db_session") as mock_session, \
             patch("app.features.reactions.api.ReactionsService") as mock_service_class:

            # Setup mocks
            mock_user = Mock()
            mock_user.id = 123
            mock_auth.return_value = lambda f: f

            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.delete_user_data.return_value = 5

            with client.application.test_request_context():
                with patch("flask.request") as mock_request:
                    mock_request.current_user = mock_user

                    response = client.delete("/api/v1/reactions/users/123")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["data"]["deleted_count"] == 5

    def test_delete_user_reactions_unauthorized(self, client):
        """Test user reactions deletion for different user."""
        with patch("app.features.reactions.api.require_auth") as mock_auth:
            # Setup mocks
            mock_user = Mock()
            mock_user.id = 123  # User 123 trying to delete user 456's reactions
            mock_auth.return_value = lambda f: f

            with client.application.test_request_context():
                with patch("flask.request") as mock_request:
                    mock_request.current_user = mock_user

                    response = client.delete("/api/v1/reactions/users/456")

            assert response.status_code == 403
            data = json.loads(response.data)
            assert data["success"] is False
            assert "You can only delete your own reactions" in data["error"]