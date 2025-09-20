#!/usr/bin/env python3
"""
Tests for community reactions functionality.
This tests the hardened reaction system with proper transaction handling.
"""
import pytest
import json
from datetime import datetime
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from psycopg2 import errors as pg_errors

# Import the app and test dependencies
from app import create_app
from models import db, User, Post, PostReaction, UserCommunityStats
from community_service import CommunityService


@pytest.fixture
def app():
    """Create test app with in-memory database"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def user(app):
    """Create test user"""
    with app.app_context():
        user = User(
            email='test@example.com',
            password_hash='hashed_password',
            username='testuser',
            display_name='Test User'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def another_user(app):
    """Create another test user"""
    with app.app_context():
        user = User(
            email='test2@example.com',
            password_hash='hashed_password',
            username='testuser2',
            display_name='Test User 2'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def post(app, user):
    """Create test post"""
    with app.app_context():
        post = Post(
            user_id=user.id,
            body='This is a test post',
            category='general',
            content_type='general'
        )
        db.session.add(post)
        db.session.commit()
        return post


@pytest.fixture
def authenticated_client(client, user):
    """Client with authenticated user"""
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['csrf_token'] = 'test_token'
    return client


class TestReactionService:
    """Test the CommunityService.add_reaction method"""

    def test_first_reaction_success(self, app, user, post):
        """Test that first reaction succeeds"""
        with app.app_context():
            reaction, message = CommunityService.add_reaction(
                user_id=user.id,
                post_id=post.id,
                reaction_type='love'
            )

            assert reaction is not None
            assert message == "Reaction saved!"

            # Verify reaction was saved
            saved_reaction = PostReaction.query.filter_by(
                post_id=post.id,
                user_id=user.id
            ).first()
            assert saved_reaction is not None
            assert saved_reaction.reaction_type == 'love'

    def test_second_reaction_fails(self, app, user, post):
        """Test that second reaction from same user fails with friendly message"""
        with app.app_context():
            # First reaction
            CommunityService.add_reaction(user.id, post.id, 'love')

            # Second reaction should fail
            reaction, message = CommunityService.add_reaction(
                user_id=user.id,
                post_id=post.id,
                reaction_type='magic'
            )

            assert reaction is None
            assert "You've already reacted with love" in message
            assert "permanent" in message

    def test_invalid_reaction_type(self, app, user, post):
        """Test that invalid reaction type fails"""
        with app.app_context():
            reaction, message = CommunityService.add_reaction(
                user_id=user.id,
                post_id=post.id,
                reaction_type='invalid_reaction'
            )

            assert reaction is None
            assert "Invalid reaction type" in message

    def test_nonexistent_post(self, app, user):
        """Test reaction to nonexistent post"""
        with app.app_context():
            reaction, message = CommunityService.add_reaction(
                user_id=user.id,
                post_id=99999,  # Nonexistent post
                reaction_type='love'
            )

            assert reaction is None
            assert "Post not found" in message

    def test_stats_updated(self, app, user, another_user, post):
        """Test that user stats are updated correctly"""
        with app.app_context():
            # React to post
            CommunityService.add_reaction(
                user_id=another_user.id,  # Different user reacting
                post_id=post.id,
                reaction_type='love'
            )

            # Check reactor stats
            reactor_stats = UserCommunityStats.query.filter_by(user_id=another_user.id).first()
            assert reactor_stats is not None
            assert reactor_stats.total_reactions_given == 1

            # Check post author stats
            author_stats = UserCommunityStats.query.filter_by(user_id=user.id).first()
            assert author_stats is not None
            assert author_stats.total_reactions_received == 1

    def test_self_reaction_no_author_stats(self, app, user, post):
        """Test that self-reactions don't increment author stats"""
        with app.app_context():
            # User reacts to their own post
            CommunityService.add_reaction(
                user_id=user.id,
                post_id=post.id,
                reaction_type='love'
            )

            # Check stats
            stats = UserCommunityStats.query.filter_by(user_id=user.id).first()
            assert stats.total_reactions_given == 1
            assert stats.total_reactions_received == 0  # No self-increment

    @patch('community_service.db.session.execute')
    def test_race_condition_handling(self, mock_execute, app, user, post):
        """Test handling of race conditions with unique violations"""
        with app.app_context():
            # Mock the first SELECT to return no existing reaction
            # Then mock the INSERT to raise a unique violation
            # Then mock the second SELECT to return the existing reaction

            mock_execute.side_effect = [
                None,  # First SELECT - no existing reaction
                None,  # Post check - post exists
                IntegrityError("", "", pg_errors.UniqueViolation()),  # INSERT fails
                type('MockRow', (), {'reaction_type': 'magic'})()  # Second SELECT - existing reaction
            ]

            reaction, message = CommunityService.add_reaction(
                user_id=user.id,
                post_id=post.id,
                reaction_type='love'
            )

            assert reaction is None
            assert "You've already reacted with magic" in message
            assert "permanent" in message


class TestReactionEndpoint:
    """Test the /community/react/<post_id> endpoint"""

    def test_successful_reaction_endpoint(self, authenticated_client, user, post):
        """Test successful reaction via HTTP endpoint"""
        response = authenticated_client.post(
            f'/community/react/{post.id}',
            json={'reaction_type': 'love'},
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['message'] == 'Reaction saved!'
        assert data['user_reacted'] is True
        assert data['reaction_type'] == 'love'

    def test_already_reacted_endpoint(self, authenticated_client, user, post):
        """Test endpoint when user already reacted"""
        # First reaction
        authenticated_client.post(
            f'/community/react/{post.id}',
            json={'reaction_type': 'love'}
        )

        # Second reaction
        response = authenticated_client.post(
            f'/community/react/{post.id}',
            json={'reaction_type': 'magic'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'already'
        assert 'already reacted with love' in data['message']

    def test_invalid_reaction_endpoint(self, authenticated_client, user, post):
        """Test endpoint with invalid reaction type"""
        response = authenticated_client.post(
            f'/community/react/{post.id}',
            json={'reaction_type': 'invalid'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Invalid reaction type' in data['message']

    def test_nonexistent_post_endpoint(self, authenticated_client, user):
        """Test endpoint with nonexistent post"""
        response = authenticated_client.post(
            '/community/react/99999',
            json={'reaction_type': 'love'}
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Post not found' in data['message']

    def test_unauthenticated_endpoint(self, client, post):
        """Test endpoint without authentication"""
        response = client.post(
            f'/community/react/{post.id}',
            json={'reaction_type': 'love'}
        )

        # Should redirect to login (302) or return 401
        assert response.status_code in [302, 401]


class TestDatabaseConstraints:
    """Test database-level constraints and integrity"""

    def test_unique_constraint_enforced(self, app, user, post):
        """Test that database unique constraint prevents duplicate reactions"""
        with app.app_context():
            # Insert first reaction directly
            reaction1 = PostReaction(
                post_id=post.id,
                user_id=user.id,
                reaction_type='love'
            )
            db.session.add(reaction1)
            db.session.commit()

            # Try to insert duplicate reaction directly
            reaction2 = PostReaction(
                post_id=post.id,
                user_id=user.id,
                reaction_type='magic'
            )
            db.session.add(reaction2)

            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_cascade_delete_on_post_delete(self, app, user, post):
        """Test that reactions are deleted when post is deleted"""
        with app.app_context():
            # Add reaction
            reaction = PostReaction(
                post_id=post.id,
                user_id=user.id,
                reaction_type='love'
            )
            db.session.add(reaction)
            db.session.commit()

            # Delete post
            db.session.delete(post)
            db.session.commit()

            # Reaction should be gone
            remaining_reactions = PostReaction.query.filter_by(post_id=post.id).count()
            assert remaining_reactions == 0

    def test_cascade_delete_on_user_delete(self, app, user, post):
        """Test that reactions are deleted when user is deleted"""
        with app.app_context():
            # Add reaction
            reaction = PostReaction(
                post_id=post.id,
                user_id=user.id,
                reaction_type='love'
            )
            db.session.add(reaction)
            db.session.commit()

            # Delete user
            db.session.delete(user)
            db.session.commit()

            # Reaction should be gone
            remaining_reactions = PostReaction.query.filter_by(user_id=user.id).count()
            assert remaining_reactions == 0


if __name__ == '__main__':
    pytest.main([__file__])