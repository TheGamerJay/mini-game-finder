import atexit
from threading import Thread, Event
from time import sleep
from flask import current_app

_stop = Event()
_threads = []

def _decay_worker():
    """Background worker for boost decay"""
    while not _stop.is_set():
        try:
            with current_app.app_context():
                # Lazy import to avoid cycles
                from tasks.decay import run_decay_task
                run_decay_task()
        except Exception as e:
            current_app.logger.error(f"Decay task error: {e}")

        # Wait 18 minutes (1080 seconds) or until stop signal
        _stop.wait(1080)

def _wars_worker():
    """Background worker for finishing wars"""
    while not _stop.is_set():
        try:
            with current_app.app_context():
                # Lazy import to avoid cycles
                from tasks.wars_finish import close_expired_wars_and_award
                close_expired_wars_and_award()
        except Exception as e:
            current_app.logger.error(f"Wars finish task error: {e}")

        # Wait 5 minutes (300 seconds) or until stop signal
        _stop.wait(300)

def init_scheduler(app):
    """Initialize background scheduler"""

    def _make_decay_worker():
        """Create decay worker with app context"""
        def worker():
            with app.app_context():
                while not _stop.is_set():
                    try:
                        # Lazy import to avoid cycles
                        from tasks.decay import run_decay_task
                        run_decay_task()
                    except Exception as e:
                        app.logger.error(f"Decay task error: {e}")
                    # Wait 18 minutes (1080 seconds) or until stop signal
                    _stop.wait(1080)
        return worker

    def _make_wars_worker():
        """Create wars worker with app context"""
        def worker():
            with app.app_context():
                while not _stop.is_set():
                    try:
                        # Lazy import to avoid cycles
                        from tasks.wars_finish import close_expired_wars_and_award
                        close_expired_wars_and_award()
                    except Exception as e:
                        app.logger.error(f"Wars finish task error: {e}")
                    # Wait 5 minutes (300 seconds) or until stop signal
                    _stop.wait(300)
        return worker

    def _start_workers():
        """Start background workers"""
        if app.config.get("SCHEDULER_ENABLED", True):
            # Start decay worker
            decay_thread = Thread(target=_make_decay_worker(), daemon=True, name="DecayWorker")
            decay_thread.start()
            _threads.append(decay_thread)

            # Start wars worker
            wars_thread = Thread(target=_make_wars_worker(), daemon=True, name="WarsWorker")
            wars_thread.start()
            _threads.append(wars_thread)

            app.logger.info("Background scheduler started: decay and wars workers")

    def _stop_workers():
        """Stop all background workers"""
        _stop.set()
        with app.app_context():
            app.logger.info("Background scheduler stopped")

    # For newer Flask versions, start workers immediately since app context is available
    _start_workers()

    # Register cleanup on exit
    atexit.register(_stop_workers)