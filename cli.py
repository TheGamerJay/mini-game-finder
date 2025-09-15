import click
from flask import current_app

def register_cli(app):
    """Register CLI commands for the app"""

    @app.cli.command("jobs.decay")
    def jobs_decay():
        """Run boost decay task manually"""
        with current_app.app_context():
            from tasks.decay import run_decay_task
            run_decay_task()
            click.echo("✅ Boost decay task executed")

    @app.cli.command("jobs.wars")
    def jobs_wars():
        """Run war finishing task manually"""
        with current_app.app_context():
            from tasks.wars_finish import close_expired_wars_and_award
            close_expired_wars_and_award()
            click.echo("✅ War finishing task executed")

    @app.cli.command("jobs.all")
    def jobs_all():
        """Run all background tasks manually"""
        with current_app.app_context():
            from tasks.decay import run_decay_task
            from tasks.wars_finish import close_expired_wars_and_award

            run_decay_task()
            click.echo("✅ Boost decay task executed")

            close_expired_wars_and_award()
            click.echo("✅ War finishing task executed")

            click.echo("🎉 All background tasks completed")