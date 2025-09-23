"""
Administrative monitoring dashboard for community system health
Provides real-time insights into community activity, performance, and user behavior
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

admin_monitoring_bp = Blueprint('admin_monitoring', __name__)

def require_admin():
    """Decorator to require admin access"""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        return jsonify({'error': 'Admin access required'}), 403
    return None

@admin_monitoring_bp.route('/admin/community/health', methods=['GET'])
@login_required
def community_health():
    """Admin dashboard for community system health"""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        # Get system health overview
        health_data = db.session.execute(
            text("SELECT * FROM public.community_system_health()")
        ).fetchall()

        # Get capped users by timezone
        capped_users = db.session.execute(
            text("SELECT * FROM public.monitor_capped_users_by_timezone()")
        ).fetchall()

        # Get posts distribution
        posts_distribution = db.session.execute(
            text("SELECT * FROM public.monitor_posts_distribution()")
        ).fetchall()

        return render_template('admin/community_health.html',
                             health_data=health_data,
                             capped_users=capped_users,
                             posts_distribution=posts_distribution)

    except Exception as e:
        logger.error(f"Error loading community health dashboard: {e}")
        return jsonify({'error': 'Failed to load health data'}), 500

@admin_monitoring_bp.route('/api/admin/community/health', methods=['GET'])
@login_required
def api_community_health():
    """API endpoint for community health data"""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        # System health overview
        health_result = db.session.execute(
            text("SELECT * FROM public.community_system_health()")
        ).fetchall()

        health_data = [
            {
                'metric': row[0],
                'value': row[1],
                'description': row[2]
            }
            for row in health_result
        ]

        # Capped users by timezone
        capped_result = db.session.execute(
            text("SELECT * FROM public.monitor_capped_users_by_timezone()")
        ).fetchall()

        capped_data = [
            {
                'timezone': row[0],
                'capped_users': row[1],
                'total_users': row[2],
                'cap_percentage': float(row[3]) if row[3] else 0.0
            }
            for row in capped_result
        ]

        # Posts distribution
        distribution_result = db.session.execute(
            text("SELECT * FROM public.monitor_posts_distribution()")
        ).fetchall()

        distribution_data = [
            {
                'posts_today': row[0],
                'user_count': row[1]
            }
            for row in distribution_result
        ]

        return jsonify({
            'success': True,
            'health': health_data,
            'capped_users_by_timezone': capped_data,
            'posts_distribution': distribution_data
        })

    except Exception as e:
        logger.error(f"Error fetching community health API data: {e}")
        return jsonify({'error': 'Failed to fetch health data'}), 500

@admin_monitoring_bp.route('/api/admin/community/test-user/<int:user_id>', methods=['GET'])
@login_required
def test_user_summary(user_id):
    """Test user summary function for admin debugging"""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        # Run smoke test for specific user
        test_result = db.session.execute(
            text("SELECT * FROM public.smoke_test_user_summary(:user_id)"),
            {"user_id": user_id}
        ).fetchall()

        test_data = [
            {
                'test_name': row[0],
                'result': row[1],
                'expected_type': row[2],
                'actual_value': row[3]
            }
            for row in test_result
        ]

        # Get actual summary data
        summary_result = db.session.execute(
            text("SELECT * FROM public.get_user_community_summary_optimized(:user_id)"),
            {"user_id": user_id}
        ).fetchone()

        summary_data = None
        if summary_result:
            summary_data = {
                'total_posts': summary_result[0],
                'reactions_received': summary_result[1],
                'posts_today': summary_result[2],
                'remaining_today': summary_result[3],
                'reactions_today': summary_result[4],
                'reactions_remaining': summary_result[5]
            }

        return jsonify({
            'success': True,
            'user_id': user_id,
            'smoke_tests': test_data,
            'summary_data': summary_data
        })

    except Exception as e:
        logger.error(f"Error testing user {user_id} summary: {e}")
        return jsonify({'error': f'Failed to test user {user_id} summary'}), 500

@admin_monitoring_bp.route('/api/admin/maintenance/refresh-stats', methods=['POST'])
@login_required
def refresh_stats():
    """Refresh materialized views and update statistics"""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        # Update table statistics
        result = db.session.execute(
            text("SELECT public.update_community_stats()")
        ).scalar()

        # Try to refresh materialized view if it exists
        mv_result = None
        try:
            mv_result = db.session.execute(
                text("SELECT public.refresh_user_activity_mv()")
            ).scalar()
        except Exception as mv_e:
            logger.info(f"Materialized view not available or failed to refresh: {mv_e}")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Statistics refreshed successfully',
            'stats_update': result,
            'mv_refresh': mv_result
        })

    except Exception as e:
        logger.error(f"Error refreshing stats: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to refresh statistics'}), 500

@admin_monitoring_bp.route('/api/admin/maintenance/vacuum', methods=['POST'])
@login_required
def vacuum_tables():
    """Vacuum and analyze community tables"""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        result = db.session.execute(
            text("SELECT public.maintain_community_tables()")
        ).scalar()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': result
        })

    except Exception as e:
        logger.error(f"Error running vacuum: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to vacuum tables'}), 500

@admin_monitoring_bp.route('/api/admin/reset/test-user/<int:user_id>', methods=['POST'])
@login_required
def test_daily_reset(user_id):
    """Test daily reset function for specific user"""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        # Test the daily increment and reset function
        result = db.session.execute(
            text("SELECT * FROM public.daily_increment_with_reset(:user_id)"),
            {"user_id": user_id}
        ).fetchone()

        if result:
            response_data = {
                'user_id': user_id,
                'did_increment': result[0],
                'posts_today': result[1],
                'remaining_today': result[2],
                'next_reset_local': result[3].isoformat() if result[3] else None,
                'current_local_time': result[4].isoformat() if result[4] else None,
                'user_timezone': result[5]
            }
        else:
            response_data = {'error': 'No result from daily reset function'}

        return jsonify({
            'success': True,
            'result': response_data
        })

    except Exception as e:
        logger.error(f"Error testing daily reset for user {user_id}: {e}")
        return jsonify({'error': f'Failed to test daily reset for user {user_id}'}), 500