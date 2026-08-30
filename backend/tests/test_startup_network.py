import importlib


def test_live_results_import_does_not_fetch_espn(monkeypatch):
    import app.services.data_collectors.live_results as live_results

    calls = []
    monkeypatch.setattr(live_results.requests, "get", lambda *args, **kwargs: calls.append(True))
    importlib.reload(live_results)

    assert calls == []
