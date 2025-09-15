import atexit
from threading import Thread, Event

_stop = Event()
_threads = []

def init_scheduler(app):
    """Start background workers with proper app context and clean shutdown."""

    def make_worker(name, interval_s, fn_path, heartbeat_name):
        def worker():
            with app.app_context():
                while not _stop.is_set():
                    try:
                        # Lazy import to avoid cycles
                        mod_name, func_name = fn_path.rsplit(".", 1)
                        mod = __import__(mod_name, fromlist=[func_name])
                        fn = getattr(mod, func_name)
                        fn()  # run task
                        # heartbeat
                        try:
                            from models import Heartbeat
                            Heartbeat.beat(heartbeat_name)
                        except Exception as hb_err:
                            app.logger.warning(f"Heartbeat error: {hb_err}")
                    except Exception as e:
                        app.logger.error(f"{name} error: {e}")
                    _stop.wait(interval_s)
        return worker

    def start_workers():
        if not app.config.get("SCHEDULER_ENABLED", True):
            app.logger.info("Scheduler disabled by config.")
            return

        import os
        FAST = os.getenv("FAST_SCHEDULE") == "1"
        specs = [
            ("DecayWorker", 5 if FAST else 1080, "tasks.decay.run_decay_task", "decay"),  # 18 min
            ("WarsWorker",  5 if FAST else 300,  "tasks.wars_finish.close_expired_wars_and_award", "wars"),  # 5 min
        ]
        for wname, interval, target, hb in specs:
            t = Thread(target=make_worker(wname, interval, target, hb), daemon=True, name=wname)
            t.start()
            _threads.append(t)
            app.logger.info(f"Started {wname} (every {interval}s)")

    def stop_workers():
        _stop.set()
        app.logger.info("Stopping background workers...")

    start_workers()
    atexit.register(stop_workers)