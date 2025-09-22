# tools/which_rule.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import importlib.util
spec = importlib.util.spec_from_file_location("app", os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)

from werkzeug.routing import RequestRedirect
from werkzeug.exceptions import MethodNotAllowed, NotFound

app = app_module.create_app()
adapter = app.url_map.bind("localhost")

def check(path, method="GET"):
    try:
        ep, args = adapter.match(path, method=method)
        print(f"{method} {path} -> endpoint={ep} args={args}")
    except RequestRedirect as rr:
        print(f"{method} {path} -> redirect to {rr.new_url}")
    except MethodNotAllowed as e:
        print(f"{method} {path} -> method not allowed; allowed={list(e.valid_methods)}")
    except NotFound:
        print(f"{method} {path} -> NOT FOUND")

for p in [
    "/api/word-finder/_ping",
    "/api/word-finder/puzzle",
    "/api/_ping",
    "/game/api/quota",
]:
    check(p)