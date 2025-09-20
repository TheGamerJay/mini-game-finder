"""
Enhanced Community Service Module
Based on SoulBridge AI patterns adapted for open community
"""

from datetime import datetime, date, timedelta
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
        'reactions_per_day': 50,
        'reports_per_day': 5,
        'reaction_cooldown_minutes': 2
    }

    @staticmethod
    def get_or_create_user_stats(user_id):
        """Get or create user community statistics"""
        stats = UserCommunityStats.query.get(user_id)
        if not stats:
            stats = UserCommunityStats(user_id=user_id)
            db.session.add(stats)
            db.session.commit()

        # Reset daily counters if needed
        today = date.today()
        if stats.last_reset_date != today:
            stats.posts_today = 0
            stats.reactions_today = 0
            stats.reports_today = 0
            stats.last_reset_date = today
            db.session.commit()

        return stats

    @staticmethod
    def can_post(user_id):
        """Check if user can create a new post"""
        stats = CommunityService.get_or_create_user_stats(user_id)

        # Check daily post limit
        if stats.posts_today >= CommunityService.RATE_LIMITS['posts_per_day']:
            return False, f"Daily post limit reached ({CommunityService.RATE_LIMITS['posts_per_day']} posts per day)"

        # Check post cooldown (2 minutes between posts)
        if stats.last_post_at:
            time_since_last = datetime.utcnow() - stats.last_post_at
            if time_since_last < timedelta(minutes=2):
                remaining = timedelta(minutes=2) - time_since_last
                seconds = int(remaining.total_seconds())
                return False, f"Please wait {seconds} more seconds before posting again"

        return True, "OK"

    @staticmethod
    def can_react(user_id):
        """Check if user can react to posts"""
        stats = CommunityService.get_or_create_user_stats(user_id)

        # Check daily reaction limit
        if stats.reactions_today >= CommunityService.RATE_LIMITS['reactions_per_day']:
            return False, f"Daily reaction limit reached ({CommunityService.RATE_LIMITS['reactions_per_day']} reactions per day)"

        # Check reaction cooldown
        if stats.last_reaction_at:
            time_since_last = datetime.utcnow() - stats.last_reaction_at
            cooldown_minutes = CommunityService.RATE_LIMITS['reaction_cooldown_minutes']
            if time_since_last < timedelta(minutes=cooldown_minutes):
                remaining = timedelta(minutes=cooldown_minutes) - time_since_last
                seconds = int(remaining.total_seconds())
                return False, f"Please wait {seconds} more seconds before reacting again"

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
        stats.last_post_at = datetime.utcnow()
        stats.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"User {user_id} created post {post.id} in category {category}")
        return post, "Post created successfully"

    @staticmethod
    def add_reaction(user_id, post_id, reaction_type):
        """Add reaction to post with proper validation and stats tracking"""

        # Validate rate limits
        can_react, message = CommunityService.can_react(user_id)
        if not can_react:
            return None, message

        # Check if post exists and is not hidden (with backward compatibility)
        query = Post.query.filter_by(id=post_id, is_hidden=False)

        # Only filter by is_deleted if column exists (for backward compatibility)
        try:
            query = query.filter_by(is_deleted=False)
        except:
            pass  # Column doesn't exist yet, skip this filter

        post = query.first()
        if not post:
            return None, "Post not found"

        # Check if user already reacted to this post
        existing_reaction = PostReaction.query.filter_by(post_id=post_id, user_id=user_id).first()
        if existing_reaction:
            return None, f"You've already reacted with {existing_reaction.reaction_type}. Reactions are permanent!"

        # Create reaction
        reaction = PostReaction(
            post_id=post_id,
            user_id=user_id,
            reaction_type=reaction_type
        )

        db.session.add(reaction)

        # Update user stats (reactor)
        reactor_stats = CommunityService.get_or_create_user_stats(user_id)
        reactor_stats.reactions_today += 1
        reactor_stats.total_reactions_given += 1
        reactor_stats.last_reaction_at = datetime.utcnow()
        reactor_stats.updated_at = datetime.utcnow()

        # Update post author stats (receiver)
        if post.user_id != user_id:  # Don't count self-reactions
            author_stats = CommunityService.get_or_create_user_stats(post.user_id)
            author_stats.total_reactions_received += 1
            author_stats.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"User {user_id} reacted to post {post_id} with {reaction_type}")
        return reaction, "Reaction added successfully"

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
        stats.last_report_at = datetime.utcnow()
        stats.updated_at = datetime.utcnow()

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
            muted_users = db.session.query(CommunityMute.muted_user_id).filter_by(muter_user_id=user_id).subquery()
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
                # Fallback for databases without reaction_type column
                if "reaction_type" in str(e):
                    post.reaction_counts = db.session.execute(
                        text("SELECT 'love' as reaction_type, COUNT(*) as count FROM post_reactions WHERE post_id = :post_id"),
                        {"post_id": post.id}
                    ).all()
                else:
                    post.reaction_counts = []

            # Get user's reaction if logged in with backward compatibility
            if user_id:
                try:
                    user_reaction = PostReaction.query.filter_by(post_id=post.id, user_id=user_id).first()
                    post.user_reaction = user_reaction.reaction_type if user_reaction else None
                except Exception as e:
                    # Handle missing id column in post_reactions table
                    if "does not exist" in str(e):
                        post.user_reaction = None
                    else:
                        raise e
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