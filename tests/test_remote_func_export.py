import importlib
import sys
import types


def test_remote_func_reexport(monkeypatch):
    """
    Ensure ndp_ep.remote_func re-exports the underlying SciDx-rexec decorator.
    """

    class StubRemoteFunc:
        marker = "stub"

        def __init__(self, func=None):
            self.func = func

        def __call__(self, *args, **kwargs):
            return ("called", args, kwargs)

    # Provide a fake rexec.client_api module with our stub remote_func
    rexec_module = types.ModuleType("rexec")
    rexec_client_api = types.ModuleType("rexec.client_api")
    rexec_client_api.remote_func = StubRemoteFunc

    monkeypatch.setitem(sys.modules, "rexec", rexec_module)
    monkeypatch.setitem(sys.modules, "rexec.client_api", rexec_client_api)

    # Reload ndp_ep to pick up the stubbed module
    monkeypatch.delitem(sys.modules, "ndp_ep", raising=False)
    ndp_ep = importlib.import_module("ndp_ep")

    assert ndp_ep.remote_func is StubRemoteFunc

    # Verify it can be used as a decorator/callable
    @ndp_ep.remote_func
    def foo(x):
        return x + 1

    assert foo("bar")[0] == "called"
