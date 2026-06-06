import pytest

from src.backend.repositories.user_repository import UserRepository
from src.backend.services.auth_service import AuthError, AuthService


def _svc(temp_db):
    return AuthService(UserRepository(temp_db))


def test_register_login_token(temp_db):
    svc = _svc(temp_db)
    user, token = svc.register("nongyou", "pass1234", "老张")
    assert user.username == "nongyou" and user.display_name == "老张"
    assert "pwd_hash" not in user.to_public()  # 不泄露哈希
    # token 能解析回用户
    assert svc.user_by_token(token).id == user.id


def test_login_wrong_password(temp_db):
    svc = _svc(temp_db)
    svc.register("u1", "rightpass")
    with pytest.raises(AuthError):
        svc.login("u1", "wrongpass")


def test_duplicate_username(temp_db):
    svc = _svc(temp_db)
    svc.register("dup", "pass1234")
    with pytest.raises(AuthError):
        svc.register("dup", "other123")


def test_short_inputs_rejected(temp_db):
    svc = _svc(temp_db)
    with pytest.raises(AuthError):
        svc.register("x", "pass1234")     # 用户名太短
    with pytest.raises(AuthError):
        svc.register("okname", "12")      # 密码太短


def test_logout_invalidates_token(temp_db):
    svc = _svc(temp_db)
    _, token = svc.register("bye", "pass1234")
    assert svc.user_by_token(token) is not None
    svc.logout(token)
    assert svc.user_by_token(token) is None


def test_unknown_token_is_none(temp_db):
    assert _svc(temp_db).user_by_token("nope") is None
