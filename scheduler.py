import threading
import time
import atexit
from flask import current_app
from app import app
from tasks.decay import run_decay_task
from tasks.wars_finish import close_expired_wars_and_award

class BackgroundScheduler:
    def __init__(self):
        self.threads = []
        self.running = True

    def start_decay_scheduler(self):
        def decay_worker():
            while self.running:
                try:
                    with app.app_context():
                        run_decay_task()
                except Exception as e:
                    print(f"Decay task error: {e}")
                time.sleep(1080)  # 18 minutes

        thread = threading.Thread(target=decay_worker, daemon=True)
        thread.start()
        self.threads.append(thread)

    def start_wars_scheduler(self):
        def wars_worker():
            while self.running:
                try:
                    with app.app_context():
                        close_expired_wars_and_award()
                except Exception as e:
                    print(f"Wars finish task error: {e}")
                time.sleep(300)  # 5 minutes

        thread = threading.Thread(target=wars_worker, daemon=True)
        thread.start()
        self.threads.append(thread)

    def shutdown(self):
        self.running = False
        for thread in self.threads:
            thread.join(timeout=1)

scheduler = BackgroundScheduler()

def start_background_tasks():
    scheduler.start_decay_scheduler()
    scheduler.start_wars_scheduler()
    atexit.register(scheduler.shutdown)