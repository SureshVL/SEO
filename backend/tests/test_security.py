from fastapi import HTTPException

from app.api.security import require_project_access


def test_require_project_access_allows_without_map():
    # no exception when no scoped key map is configured
    require_project_access("project-1", "any")


def test_require_project_access_forbidden_with_scopes(monkeypatch):
    monkeypatch.setattr("app.api.security._key_map", lambda: {"k1": {"projects": ["project-2"]}})
    try:
        require_project_access("project-1", "k1")
        assert False, "Expected forbidden"
    except HTTPException as exc:
        assert exc.status_code == 403
