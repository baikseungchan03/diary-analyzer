"""브라우저 쿠키에 로그인 토큰을 안전하게 보관합니다. (주소창 노출 방지)"""

from streamlit_cookies_controller import CookieController

_controller = None


def _get_controller():
    global _controller
    if _controller is None:
        _controller = CookieController()
    return _controller


def get_token():
    """쿠키에 저장된 로그인 토큰을 읽습니다. 없으면 None."""
    return _get_controller().get("diary_token")


def set_token(token, max_age_days):
    """로그인 토큰을 쿠키에 저장합니다."""
    _get_controller().set(
        "diary_token",
        token,
        max_age=max_age_days * 86400,
        secure=True,
        same_site="lax",
    )


def clear_token():
    """쿠키의 로그인 토큰을 지웁니다."""
    _get_controller().remove("diary_token")