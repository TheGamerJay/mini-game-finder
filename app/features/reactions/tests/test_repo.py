"""Integration tests for reactions repository."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.features.reactions.repo import ReactionsRepo
from app.features.reactions.dto import ReactionData, ReactionCount


class TestReactionsRepo:
    """Test ReactionsRepo with real database."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create test database session."""
        # Use in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:", echo=False)

        # Create test table
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE post_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reaction_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(post_id, user_id)
                )
            """))
            conn.commit()

        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        session.close()

    @pytest.fixture
    def repo(self, db_session):
        """Create repository instance."""
        return ReactionsRepo(db_session)

    def test_insert_and_get_user_reaction(self, repo, db_session):
        """Test inserting and retrieving a user reaction."""
        # Insert reaction
        repo.insert_reaction(post_id=1, user_id=2, reaction_type="love")
        db_session.commit()

        # Get reaction
        reaction = repo.get_user_reaction(post_id=1, user_id=2)

        assert reaction is not None
        assert reaction.post_id == 1
        assert reaction.user_id == 2
        assert reaction.reaction_type == "love"
        assert isinstance(reaction.created_at, datetime)

    def test_get_user_reaction_not_found(self, repo):
        """Test getting non-existent user reaction returns None."""
        reaction = repo.get_user_reaction(post_id=999, user_id=999)
        assert reaction is None

    def test_get_reaction_counts_single_post(self, repo, db_session):
        """Test getting reaction counts for a single post."""
        # Insert multiple reactions
        repo.insert_reaction(post_id=1, user_id=1, reaction_type="love")
        repo.insert_reaction(post_id=1, user_id=2, reaction_type="love")
        repo.insert_reaction(post_id=1, user_id=3, reaction_type="fire")
        db_session.commit()

        # Get counts
        counts = repo.get_reaction_counts(post_id=1)

        assert len(counts) == 2

        # Sort by reaction_type for consistent testing
        counts_dict = {c.reaction_type: c.count for c in counts}
        assert counts_dict["love"] == 2
        assert counts_dict["fire"] == 1

    def test_get_reaction_counts_empty_post(self, repo):
        """Test getting reaction counts for post with no reactions."""
        counts = repo.get_reaction_counts(post_id=999)
        assert counts == []

    def test_get_reaction_counts_bulk(self, repo, db_session):
        """Test getting reaction counts for multiple posts."""
        # Insert reactions for multiple posts
        repo.insert_reaction(post_id=1, user_id=1, reaction_type="love")
        repo.insert_reaction(post_id=1, user_id=2, reaction_type="fire")
        repo.insert_reaction(post_id=2, user_id=1, reaction_type="love")
        repo.insert_reaction(post_id=3, user_id=1, reaction_type="star")
        db_session.commit()

        # Get bulk counts
        counts_by_post = repo.get_reaction_counts_bulk([1, 2, 3, 4])

        # Check post 1 (2 reactions)
        assert 1 in counts_by_post
        post1_counts = {c.reaction_type: c.count for c in counts_by_post[1]}
        assert post1_counts["love"] == 1
        assert post1_counts["fire"] == 1

        # Check post 2 (1 reaction)
        assert 2 in counts_by_post
        post2_counts = {c.reaction_type: c.count for c in counts_by_post[2]}
        assert post2_counts["love"] == 1

        # Check post 3 (1 reaction)
        assert 3 in counts_by_post
        post3_counts = {c.reaction_type: c.count for c in counts_by_post[3]}
        assert post3_counts["star"] == 1

        # Check post 4 (no reactions) - should not be in results
        assert 4 not in counts_by_post

    def test_get_reaction_counts_bulk_empty(self, repo):
        """Test bulk counts with empty post list."""
        counts_by_post = repo.get_reaction_counts_bulk([])
        assert counts_by_post == {}

    def test_get_user_reactions_bulk(self, repo, db_session):
        """Test getting user reactions for multiple posts."""
        # Insert reactions
        repo.insert_reaction(post_id=1, user_id=123, reaction_type="love")
        repo.insert_reaction(post_id=2, user_id=123, reaction_type="fire")
        repo.insert_reaction(post_id=3, user_id=456, reaction_type="star")  # Different user
        db_session.commit()

        # Get user reactions
        user_reactions = repo.get_user_reactions_bulk([1, 2, 3, 4], user_id=123)

        assert user_reactions[1] == "love"
        assert user_reactions[2] == "fire"
        assert 3 not in user_reactions  # Different user
        assert 4 not in user_reactions  # No reaction

    def test_get_user_reactions_bulk_empty(self, repo):
        """Test bulk user reactions with empty post list."""
        user_reactions = repo.get_user_reactions_bulk([], user_id=123)
        assert user_reactions == {}

    def test_delete_user_reactions(self, repo, db_session):
        """Test deleting all reactions by a user."""
        # Insert reactions for multiple users
        repo.insert_reaction(post_id=1, user_id=123, reaction_type="love")
        repo.insert_reaction(post_id=2, user_id=123, reaction_type="fire")
        repo.insert_reaction(post_id=3, user_id=456, reaction_type="star")
        db_session.commit()

        # Delete reactions for user 123
        deleted_count = repo.delete_user_reactions(user_id=123)
        db_session.commit()

        assert deleted_count == 2

        # Verify deletions
        assert repo.get_user_reaction(post_id=1, user_id=123) is None
        assert repo.get_user_reaction(post_id=2, user_id=123) is None
        assert repo.get_user_reaction(post_id=3, user_id=456) is not None  # Other user unaffected

    def test_delete_post_reactions(self, repo, db_session):
        """Test deleting all reactions for a post."""
        # Insert reactions for multiple posts
        repo.insert_reaction(post_id=1, user_id=123, reaction_type="love")
        repo.insert_reaction(post_id=1, user_id=456, reaction_type="fire")
        repo.insert_reaction(post_id=2, user_id=123, reaction_type="star")
        db_session.commit()

        # Delete reactions for post 1
        deleted_count = repo.delete_post_reactions(post_id=1)
        db_session.commit()

        assert deleted_count == 2

        # Verify deletions
        assert repo.get_user_reaction(post_id=1, user_id=123) is None
        assert repo.get_user_reaction(post_id=1, user_id=456) is None
        assert repo.get_user_reaction(post_id=2, user_id=123) is not None  # Other post unaffected

    def test_get_reaction_stats(self, repo, db_session):
        """Test getting overall reaction statistics."""
        # Insert various reactions
        repo.insert_reaction(post_id=1, user_id=1, reaction_type="love")
        repo.insert_reaction(post_id=1, user_id=2, reaction_type="love")
        repo.insert_reaction(post_id=1, user_id=3, reaction_type="love")
        repo.insert_reaction(post_id=2, user_id=1, reaction_type="fire")
        repo.insert_reaction(post_id=2, user_id=2, reaction_type="fire")
        repo.insert_reaction(post_id=3, user_id=1, reaction_type="star")
        db_session.commit()

        # Get stats
        stats = repo.get_reaction_stats()

        assert stats["love"] == 3
        assert stats["fire"] == 2
        assert stats["star"] == 1

    def test_unique_constraint_violation(self, repo, db_session):
        """Test that unique constraint prevents duplicate reactions."""
        # Insert first reaction
        repo.insert_reaction(post_id=1, user_id=2, reaction_type="love")
        db_session.commit()

        # Try to insert duplicate - should raise IntegrityError
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            repo.insert_reaction(post_id=1, user_id=2, reaction_type="fire")
            db_session.commit()