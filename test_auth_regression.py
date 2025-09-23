# test_auth_regression.py - Quick auth system regression tests
"""
Simple regression tests for auth system to prevent auth-related breakage.
Run with: python test_auth_regression.py
"""

def test_no_extra_before_request():
    """Ensure only our central auth guard is registered"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    create_app = app_module.create_app

    app = create_app()

    # Get all app-level before_request functions
    funcs = app.before_request_funcs.get(None, [])
    func_names = [f.__name__ for f in funcs if hasattr(f, '__name__')]

    # Should only have our auth function (and maybe some diagnostic/utility ones)
    expected_auth_funcs = ["require_login"]

    auth_funcs = [name for name in func_names if 'login' in name.lower() or 'auth' in name.lower()]

    print(f"Found before_request functions: {func_names}")
    print(f"Auth-related functions: {auth_funcs}")

    # We should have exactly one auth function
    assert len(auth_funcs) == 1, f"Expected 1 auth function, found {len(auth_funcs)}: {auth_funcs}"
    assert auth_funcs[0] in expected_auth_funcs, f"Unexpected auth function: {auth_funcs[0]}"

    print("Auth guard uniqueness test passed")


def test_public_endpoints_resolve():
    """Ensure all public endpoints actually exist in the URL map"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    create_app = app_module.create_app
    from config import PUBLIC_ENDPOINTS

    app = create_app()

    # Get all registered endpoints
    registered_endpoints = {r.endpoint for r in app.url_map.iter_rules()}

    # Check that all public endpoints exist
    missing_endpoints = PUBLIC_ENDPOINTS - registered_endpoints

    print(f"Public endpoints: {sorted(PUBLIC_ENDPOINTS)}")
    print(f"Registered endpoints: {len(registered_endpoints)} total")

    if missing_endpoints:
        print(f"Missing public endpoints: {missing_endpoints}")
        # This is a warning, not a failure, since "static" is special
        special_endpoints = {"static"}
        critical_missing = missing_endpoints - special_endpoints
        if critical_missing:
            raise AssertionError(f"Critical public endpoints missing: {critical_missing}")
        else:
            print("Only special endpoints missing (probably OK)")

    print("Public endpoints resolution test passed")


def test_auth_utils_import():
    """Ensure auth utilities can be imported without errors"""
    try:
        from utils.auth import public_route, is_api_path, require_auth_json, get_user_safe
        print("Auth utilities import test passed")
    except ImportError as e:
        raise AssertionError(f"Failed to import auth utilities: {e}")


def test_config_import():
    """Ensure config can be imported and has required constants"""
    try:
        from config import PUBLIC_ENDPOINTS, public_route
        assert isinstance(PUBLIC_ENDPOINTS, set), f"PUBLIC_ENDPOINTS should be a set, got {type(PUBLIC_ENDPOINTS)}"
        assert len(PUBLIC_ENDPOINTS) > 0, "PUBLIC_ENDPOINTS should not be empty"
        assert callable(public_route), "public_route should be callable"
        print("Config import test passed")
    except ImportError as e:
        raise AssertionError(f"Failed to import config: {e}")


def test_no_duplicate_endpoints():
    """Ensure no endpoint names are duplicated"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    create_app = app_module.create_app

    app = create_app()
    with app.app_context():
        by_endpoint = {}
        for rule in app.url_map.iter_rules():
            by_endpoint.setdefault(rule.endpoint, set()).add(str(rule))
        dups = {ep: rules for ep, rules in by_endpoint.items() if len(rules) > 1}

        # Helpful debug print if something's off
        if dups:
            print("\nDuplicate endpoints detected:")
            for ep, rules in dups.items():
                print(f"  - {ep}: {sorted(rules)}")

        assert not dups, f"Duplicate endpoints registered: {dups}"
        print("No duplicate endpoints test passed")


def test_essential_routes_exist():
    """Ensure critical routes exist"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    create_app = app_module.create_app

    app = create_app()

    essential_routes = {
        "core.index": "/",
        "core.login": "/login",
        "version": "/_version",
        "health": "/_health"
    }

    registered_endpoints = {r.endpoint: r.rule for r in app.url_map.iter_rules()}

    for endpoint, expected_rule in essential_routes.items():
        if endpoint not in registered_endpoints:
            raise AssertionError(f"Essential route missing: {endpoint} ({expected_rule})")

        actual_rule = registered_endpoints[endpoint]
        if actual_rule != expected_rule:
            print(f"Route rule changed: {endpoint} was {expected_rule}, now {actual_rule}")

    print("Essential routes test passed")


if __name__ == "__main__":
    print("Running auth system regression tests...\n")

    try:
        test_config_import()
        test_auth_utils_import()
        test_no_extra_before_request()
        test_public_endpoints_resolve()
        test_no_duplicate_endpoints()
        test_essential_routes_exist()

        print("\nAll auth regression tests passed!")

    except Exception as e:
        print(f"\nTest failed: {e}")
        exit(1)