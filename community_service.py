"""
Enhanced Community Service Module
Based on SoulBridge AI patterns adapted for open community
"""

from datetime import datetime, date, timedelta, timezone
from sqlalchemy import text
from models import db, Post, PostReaction, PostReport, UserCommunityStats, CommunityMute, User
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class CommunityService:
    """Main service for community operations with proper rate limiting and stats tracking"""

    # Community categories for post organization
    CATEGORIES = {
        'general': 'General Discussion',
        'gratitude': 'Gratitude & Appreciation',
        'motivation': 'Motivation & Inspiration',
        'achievement': 'Achievements & Victories',
        'help': 'Help & Support',
        'celebration': 'Celebrations & Milestones'
    }

    # Content types for better post categorization
    CONTENT_TYPES = {
        'general': 'General Post',
        'tip': 'Tips & Advice',
        'question': 'Questions',
        'celebration': 'Celebrations',
        'story': 'Stories & Experiences',
        'achievement': 'Achievements'
    }

    # Rate limits (posts per day)
    RATE_LIMITS = {
        'posts_per_day': 10,
        'reactions_per_day': 50,  # Restored to reasonable limit
        'reports_per_day': 5,
        'reaction_cooldown_minutes': 1,  # 1 minute between reactions (more reasonable)
        'post_cooldown_minutes': 1  # 1 minute between posts (was hardcoded to 2 minutes)
    }

    # Progressive cooldown settings
    PROGRESSIVE_COOLDOWN = {
        'base_minutes': 2,      # Starting cooldown: 2 minutes
        'increment_minutes': 1, # +1 minute per recent action
        'max_minutes': 5,       # Cap at 5 minutes
        'reset_hours': 1        # Reset counter every hour
    }

    @staticmethod
    def get_or_create_user_stats(user_id):
        """Get or create user community statistics with production-safe fallback"""
        try:
            # Try to get existing stats
            stats = UserCommunityStats.query.get(user_id)
            if not stats:
                stats = UserCommunityStats(user_id=user_id)
                db.session.add(stats)
                # Don't commit here - let the calling function handle the commit

            # Check if progressive cooldown columns exist by trying to access them
            try:
                _ = stats.recent_actions_hour
                _ = stats.recent_actions_reset_at
                # If we get here, columns exist
                stats._has_progressive_columns = True
            except (AttributeError, Exception):
                # Columns don't exist, add them as properties with defaults
                stats._has_progressive_columns = False
                stats.recent_actions_hour = 0
                stats.recent_actions_reset_at = None

            # Reset daily counters if needed
            today = date.today()

            # Reset if last_reset_date is missing, None, or different from today
            needs_reset = (
                not hasattr(stats, 'last_reset_date') or
                stats.last_reset_date is None or
                stats.last_reset_date != today
            )

            if needs_reset:
                logger.info(f"Resetting daily counters for user {user_id} (last reset: {getattr(stats, 'last_reset_date', 'never')})")
                stats.posts_today = 0
                stats.reactions_today = 0
                stats.reports_today = 0
                stats.last_reset_date = today

            return stats
        except Exception as e:
            logger.error(f"Error getting/creating user stats for user {user_id}: {e}")
            return None

    @staticmethod
    def _calculate_progressive_cooldown(user_id):
        """Calculate cooldown time based on recent activity"""
        stats = CommunityService.get_or_create_user_stats(user_id)
        if not stats:
            return CommunityService.PROGRESSIVE_COOLDOWN['base_minutes']

        # If progressive columns don't exist, use base cooldown
        if not getattr(stats, '_has_progressive_columns', False):
            logger.info(f"Progressive cooldown columns not available, using base cooldown for user {user_id}")
            return CommunityService.PROGRESSIVE_COOLDOWN['base_minutes']

        now = datetime.now(timezone.utc)

        # Reset recent actions counter if past reset time
        if not stats.recent_actions_reset_at or now > stats.recent_actions_reset_at:
            stats.recent_actions_hour = 0
            stats.recent_actions_reset_at = now + timedelta(hours=CommunityService.PROGRESSIVE_COOLDOWN['reset_hours'])
            # Note: don't commit here - let the calling function handle commits

        # Calculate cooldown: base + (recent_actions * increment), capped at max
        base = CommunityService.PROGRESSIVE_COOLDOWN['base_minutes']
        increment = CommunityService.PROGRESSIVE_COOLDOWN['increment_minutes']
        max_cooldown = CommunityService.PROGRESSIVE_COOLDOWN['max_minutes']

        cooldown_minutes = min(
            base + (stats.recent_actions_hour * increment),
            max_cooldown
        )

        logger.info(f"Progressive cooldown for user {user_id}: {cooldown_minutes}min (base: {base}, recent: {stats.recent_actions_hour})")
        return cooldown_minutes

    @staticmethod
    def _increment_recent_actions(user_id, auto_commit=False):
        """Increment the recent actions counter for progressive cooldown"""
        stats = CommunityService.get_or_create_user_stats(user_id)
        if stats and getattr(stats, '_has_progressive_columns', False):
            stats.recent_actions_hour += 1
            if auto_commit:
                db.session.commit()
            logger.info(f"Incremented recent actions for user {user_id}: now {stats.recent_actions_hour}")
        else:
            logger.info(f"Progressive cooldown columns not available, skipping increment for user {user_id}")

    @staticmethod
    def can_post(user_id):
        """Check if user can create a new post"""
        stats = CommunityService.get_or_create_user_stats(user_id)

        # Check daily post limit
        if stats.posts_today >= CommunityService.RATE_LIMITS['posts_per_day']:
            return False, f"Daily post limit reached ({CommunityService.RATE_LIMITS['posts_per_day']} posts per day)"

        # Check progressive cooldown
        if stats.last_post_at:
            try:
                # Handle timezone-aware/naive datetime comparison
                now = datetime.now(timezone.utc)
                last_post = stats.last_post_at
                if last_post.tzinfo is None:
                    # If stored datetime is naive, assume it's UTC
                    last_post = last_post.replace(tzinfo=timezone.utc)

                time_since_last = now - last_post
                cooldown_minutes = CommunityService._calculate_progressive_cooldown(user_id)
                if time_since_last < timedelta(minutes=cooldown_minutes):
                    remaining = timedelta(minutes=cooldown_minutes) - time_since_last
                    seconds = int(remaining.total_seconds())
                    return False, f"Please wait {seconds} more seconds before posting again"
            except Exception as e:
                logger.error(f"Error calculating post cooldown for user {user_id}: {e}")
                # Allow post if calculation fails

        return True, "OK"

    @staticmethod
    def can_react(user_id):
        """Check if user can react to posts"""
        try:
            stats = CommunityService.get_or_create_user_stats(user_id)

            if not stats:
                logger.warning(f"Could not get user stats for user {user_id} - allowing reaction")
                return True, "OK"  # Allow reaction if stats unavailable

            # Log current stats for debugging
            reactions_today = getattr(stats, 'reactions_today', 0)
            last_reset_date = getattr(stats, 'last_reset_date', None)
            last_reaction_at = getattr(stats, 'last_reaction_at', None)

            logger.info(f"User {user_id} reaction check: {reactions_today}/{CommunityService.RATE_LIMITS['reactions_per_day']} today, last reset: {last_reset_date}")

            # Check daily reaction limit (with fallback)
            if reactions_today >= CommunityService.RATE_LIMITS['reactions_per_day']:
                logger.warning(f"User {user_id} hit daily reaction limit: {reactions_today}/{CommunityService.RATE_LIMITS['reactions_per_day']}")
                return False, f"Daily reaction limit reached ({CommunityService.RATE_LIMITS['reactions_per_day']} reactions per day)"

            # Check progressive reaction cooldown (with fallback)
            if last_reaction_at:
                try:
                    # Handle timezone-aware/naive datetime comparison
                    now = datetime.now(timezone.utc)
                    last_reaction = last_reaction_at
                    if last_reaction.tzinfo is None:
                        # If stored datetime is naive, assume it's UTC
                        last_reaction = last_reaction.replace(tzinfo=timezone.utc)

                    time_since_last = now - last_reaction
                    cooldown_minutes = CommunityService._calculate_progressive_cooldown(user_id)
                    if time_since_last < timedelta(minutes=cooldown_minutes):
                        remaining = timedelta(minutes=cooldown_minutes) - time_since_last
                        seconds = int(remaining.total_seconds())
                        logger.warning(f"User {user_id} in progressive cooldown: {seconds} seconds remaining (cooldown: {cooldown_minutes}min)")
                        return False, f"Please wait {seconds} more seconds before reacting again"
                except Exception as e:
                    logger.error(f"Error calculating progressive reaction cooldown for user {user_id}: {e}")
                    # Allow reaction if cooldown calculation fails

            logger.info(f"User {user_id} can react: {reactions_today} reactions today, cooldown clear")
            return True, "OK"

        except Exception as e:
            logger.error(f"Error in can_react for user {user_id}: {e}")
            # Allow reaction if entire check fails to avoid blocking users
            return True, "OK"

    @staticmethod
    def can_react_to_post(user_id, post_id):
        """Check if user has already reacted to this specific post (permanent reactions policy)"""
        try:
            # Check if user has already reacted to this post
            existing_reaction = db.session.execute(
                text("""
                    SELECT reaction_type
                    FROM post_reactions
                    WHERE user_id = :user_id AND post_id = :post_id
                    LIMIT 1
                """),
                {"user_id": user_id, "post_id": post_id}
            ).fetchone()

            if existing_reaction:
                reaction_type = existing_reaction[0]
                logger.info(f"User {user_id} already reacted to post {post_id} with {reaction_type}")
                return False, f"You've already reacted with {reaction_type}. Reactions are permanent and cannot be changed!"

            return True, "OK"

        except Exception as e:
            logger.error(f"Error checking existing reaction for user {user_id}, post {post_id}: {e}")
            # Allow reaction if check fails to avoid blocking users unnecessarily
            return True, "OK"

    @staticmethod
    def can_report(user_id):
        """Check if user can report content"""
        stats = CommunityService.get_or_create_user_stats(user_id)

        # Check daily report limit
        if stats.reports_today >= CommunityService.RATE_LIMITS['reports_per_day']:
            return False, f"Daily report limit reached ({CommunityService.RATE_LIMITS['reports_per_day']} reports per day)"

        return True, "OK"

    @staticmethod
    def create_post(user_id, body, category='general', content_type='general', image_url=None):
        """Create a new community post with proper validation and stats tracking"""

        # Validate rate limits
        can_post, message = CommunityService.can_post(user_id)
        if not can_post:
            return None, message

        # Validate category and content_type
        if category not in CommunityService.CATEGORIES:
            category = 'general'
        if content_type not in CommunityService.CONTENT_TYPES:
            content_type = 'general'

        # Create post
        post = Post(
            user_id=user_id,
            body=body,
            category=category,
            content_type=content_type,
            image_url=image_url,
            moderation_status='approved'  # For now, auto-approve. Add moderation later
        )

        db.session.add(post)

        # Update user stats
        stats = CommunityService.get_or_create_user_stats(user_id)
        stats.posts_today += 1
        stats.total_posts += 1
        stats.last_post_at = datetime.now(timezone.utc)
        stats.updated_at = datetime.now(timezone.utc)

        # Increment recent actions for progressive cooldown
        CommunityService._increment_recent_actions(user_id, auto_commit=False)

        db.session.commit()

        logger.info(f"User {user_id} created post {post.id} in category {category}")
        return post, "Post created successfully"

    @staticmethod
    def add_reaction(user_id, post_id, reaction_type):
        """Add reaction to post with proper validation and transaction handling"""
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        from psycopg2 import errors as pg_errors

        # Validate global rate limits
        can_react, message = CommunityService.can_react(user_id)
        if not can_react:
            return None, message

        # Check per-post cooldown (prevent rapid reactions to same post)
        can_react_to_post, post_message = CommunityService.can_react_to_post(user_id, post_id)
        if not can_react_to_post:
            return None, post_message

        # Validate reaction type
        valid_reactions = ['love', 'magic', 'peace', 'fire', 'gratitude', 'star', 'applause', 'support']
        if reaction_type not in valid_reactions:
            return None, "Invalid reaction type"

        try:
            # Start a new transaction
            # First check if user already reacted (for friendly message with actual emoji)
            existing = db.session.execute(
                text("""
                    SELECT reaction_type
                    FROM post_reactions
                    WHERE post_id = :post_id AND user_id = :user_id
                """),
                {"post_id": post_id, "user_id": user_id},
            ).fetchone()

            if existing:
                return None, f"You've already reacted with {existing[0]}. Reactions are permanent and cannot be changed!"

            # Check if post exists (with backward compatibility for missing columns)
            try:
                post_check = db.session.execute(
                    text("""
                        SELECT id, user_id
                        FROM posts
                        WHERE id = :post_id
                        AND (is_hidden = false OR is_hidden IS NULL)
                        AND (is_deleted = false OR is_deleted IS NULL)
                    """),
                    {"post_id": post_id}
                ).fetchone()
            except Exception as e:
                # Fallback for missing columns
                logger.warning(f"Column issue in post check for post {post_id}: {e}")
                post_check = db.session.execute(
                    text("SELECT id, user_id FROM posts WHERE id = :post_id"),
                    {"post_id": post_id}
                ).fetchone()

            if not post_check:
                return None, "Post not found"

            post_author_id = post_check[1]

            # Insert the reaction
            try:
                db.session.execute(
                    text("""
                        INSERT INTO post_reactions (post_id, user_id, reaction_type, created_at)
                        VALUES (:post_id, :user_id, :reaction_type, NOW())
                    """),
                    {"post_id": post_id, "user_id": user_id, "reaction_type": reaction_type},
                )

                # Update user stats (reactor) - gracefully handle missing stats table
                try:
                    reactor_stats = CommunityService.get_or_create_user_stats(user_id)
                    if reactor_stats:
                        reactor_stats.reactions_today += 1
                        if hasattr(reactor_stats, 'total_reactions_given'):
                            reactor_stats.total_reactions_given += 1
                        if hasattr(reactor_stats, 'last_reaction_at'):
                            reactor_stats.last_reaction_at = datetime.now(timezone.utc)
                        if hasattr(reactor_stats, 'updated_at'):
                            reactor_stats.updated_at = datetime.now(timezone.utc)

                        # Increment recent actions for progressive cooldown
                        CommunityService._increment_recent_actions(user_id, auto_commit=False)
                except Exception as e:
                    logger.warning(f"Could not update reactor stats for user {user_id}: {e}")

                # Update post author stats (receiver) - gracefully handle missing stats table
                try:
                    if post_author_id != user_id:  # Don't count self-reactions
                        author_stats = CommunityService.get_or_create_user_stats(post_author_id)
                        if author_stats and hasattr(author_stats, 'total_reactions_received'):
                            author_stats.total_reactions_received += 1
                        if author_stats and hasattr(author_stats, 'updated_at'):
                            author_stats.updated_at = datetime.now(timezone.utc)
                except Exception as e:
                    logger.warning(f"Could not update author stats for user {post_author_id}: {e}")

                db.session.commit()
                logger.info(f"User {user_id} reacted to post {post_id} with {reaction_type}")
                return {"status": "ok"}, "Reaction saved!"

            except IntegrityError as e:
                db.session.rollback()
                # Handle race condition: someone else inserted between our SELECT and INSERT
                if isinstance(e.orig, pg_errors.UniqueViolation):
                    # Query again to get the actual stored reaction
                    existing = db.session.execute(
                        text("""
                            SELECT reaction_type
                            FROM post_reactions
                            WHERE post_id = :post_id AND user_id = :user_id
                        """),
                        {"post_id": post_id, "user_id": user_id},
                    ).fetchone()
                    emoji = existing[0] if existing else "your earlier choice"
                    return None, f"You've already reacted with {emoji}. Reactions are permanent and cannot be changed!"
                else:
                    # Re-raise other integrity errors
                    raise e

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding reaction for user {user_id} to post {post_id}: {e}")

            # Check if this is a database schema issue
            if "does not exist" in str(e):
                # Graceful fallback for schema issues
                return None, "Reactions are temporarily unavailable. Please try again later."

            # For other errors, re-raise
            raise e

    @staticmethod
    def report_post(user_id, post_id, reason):
        """Report a post with proper validation and stats tracking"""

        # Validate rate limits
        can_report, message = CommunityService.can_report(user_id)
        if not can_report:
            return None, message

        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return None, "Post not found"

        # Check if user already reported this post
        existing_report = PostReport.query.filter_by(post_id=post_id, user_id=user_id).first()
        if existing_report:
            return None, "You have already reported this post"

        # Create report
        report = PostReport(
            post_id=post_id,
            user_id=user_id,
            reason=reason
        )

        db.session.add(report)

        # Update user stats
        stats = CommunityService.get_or_create_user_stats(user_id)
        stats.reports_today += 1
        stats.last_report_at = datetime.now(timezone.utc)
        stats.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        logger.info(f"User {user_id} reported post {post_id}: {reason}")
        return report, "Report submitted successfully"

    @staticmethod
    def mute_user(muter_user_id, muted_user_id, reason=None):
        """Mute a user to hide their content"""

        # Check if already muted
        existing_mute = CommunityMute.query.filter_by(
            muter_user_id=muter_user_id,
            muted_user_id=muted_user_id
        ).first()

        if existing_mute:
            return None, "User is already muted"

        # Create mute
        mute = CommunityMute(
            muter_user_id=muter_user_id,
            muted_user_id=muted_user_id,
            reason=reason
        )

        db.session.add(mute)
        db.session.commit()

        logger.info(f"User {muter_user_id} muted user {muted_user_id}")
        return mute, "User muted successfully"

    @staticmethod
    def get_community_feed(user_id=None, category=None, limit=10, offset=0):
        """Get community feed with proper filtering and mute handling"""

        # Filter posts with backward compatibility for existing posts
        query = Post.query.filter_by(is_hidden=False)

        # Only filter by is_deleted and moderation_status if they exist (for backward compatibility)
        try:
            query = query.filter_by(is_deleted=False)
        except:
            pass  # Column doesn't exist yet, skip this filter

        try:
            query = query.filter((Post.moderation_status == 'approved') | (Post.moderation_status.is_(None)))
        except:
            pass  # Column doesn't exist yet, skip this filter

        # Filter by category if specified
        if category and category in CommunityService.CATEGORIES:
            query = query.filter_by(category=category)

        # Exclude muted users if user is specified
        if user_id:
            muted_users = db.session.query(CommunityMute.muted_user_id).filter_by(muter_user_id=user_id)
            query = query.filter(~Post.user_id.in_(muted_users))

        # Order by creation time (newest first) and apply pagination
        posts = query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()

        # Get additional data for each post
        for post in posts:
            # Get user info
            post.user = User.query.get(post.user_id)

            # Get reaction counts with backward compatibility
            try:
                post.reaction_counts = db.session.execute(
                    text("SELECT reaction_type, COUNT(*) as count FROM post_reactions WHERE post_id = :post_id GROUP BY reaction_type"),
                    {"post_id": post.id}
                ).all()
            except Exception as e:
                # Transaction may be aborted, need to rollback before any new queries
                db.session.rollback()

                # Handle different database schema issues
                if "reaction_type" in str(e) or "does not exist" in str(e):
                    try:
                        post.reaction_counts = db.session.execute(
                            text("SELECT 'love' as reaction_type, COUNT(*) as count FROM post_reactions WHERE post_id = :post_id"),
                            {"post_id": post.id}
                        ).all()
                    except Exception as fallback_e:
                        # If even the fallback fails, assume table doesn't exist or has major issues
                        post.reaction_counts = []
                        logger.warning(f"Failed to get reaction counts for post {post.id}: {fallback_e}")
                else:
                    post.reaction_counts = []
                    logger.warning(f"Unexpected error getting reaction counts for post {post.id}: {e}")

            # Get user's reaction if logged in with backward compatibility
            if user_id:
                try:
                    user_reaction = PostReaction.query.filter_by(post_id=post.id, user_id=user_id).first()
                    post.user_reaction = user_reaction.reaction_type if user_reaction else None
                except Exception as e:
                    # Transaction may be aborted, need to rollback
                    db.session.rollback()

                    # Handle missing id column in post_reactions table
                    if "does not exist" in str(e) or "aborted" in str(e):
                        post.user_reaction = None
                        logger.warning(f"Failed to get user reaction for post {post.id}, user {user_id}: {e}")
                    else:
                        post.user_reaction = None
                        logger.error(f"Unexpected error getting user reaction for post {post.id}, user {user_id}: {e}")
            else:
                post.user_reaction = None

        return posts

    @staticmethod
    def get_user_community_summary(user_id):
        """Get user's community activity summary"""
        stats = CommunityService.get_or_create_user_stats(user_id)

        return {
            'posts_today': stats.posts_today,
            'reactions_today': stats.reactions_today,
            'reports_today': stats.reports_today,
            'total_posts': stats.total_posts,
            'total_reactions_given': stats.total_reactions_given,
            'total_reactions_received': stats.total_reactions_received,
            'posts_remaining_today': max(0, CommunityService.RATE_LIMITS['posts_per_day'] - stats.posts_today),
            'reactions_remaining_today': max(0, CommunityService.RATE_LIMITS['reactions_per_day'] - stats.reactions_today),
            'reports_remaining_today': max(0, CommunityService.RATE_LIMITS['reports_per_day'] - stats.reports_today)
        }

    @staticmethod
    def delete_post(post_id, user_id):
        """Delete a post while preserving permanent reactions"""
        try:
            # Get the post first to verify ownership
            post = db.session.get(Post, post_id)
            if not post:
                logger.warning(f"Attempted to delete non-existent post {post_id} by user {user_id}")
                return False

            if post.user_id != user_id:
                logger.warning(f"User {user_id} attempted to delete post {post_id} belonging to user {post.user_id}")
                return False

            # Since the permanent reactions trigger blocks ALL updates (including SET post_id = NULL),
            # we'll use soft delete approach instead of trying to modify reactions
            logger.info(f"Soft deleting post {post_id} to preserve permanent reactions")

            post.content = "[This post has been deleted by the user]"
            post.image_url = None
            if hasattr(post, 'image_data'):
                post.image_data = None
            if hasattr(post, 'image_mime_type'):
                post.image_mime_type = None
            if hasattr(post, 'is_hidden'):
                post.is_hidden = True
            if hasattr(post, 'is_deleted'):
                post.is_deleted = True

            db.session.commit()
            logger.info(f"Successfully soft-deleted post {post_id} by user {user_id}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting post {post_id} by user {user_id}: {e}")
            return False