"""
Streamlit Cloud용 비밀번호 보호 게이트.

st.secrets에 저장된 비밀번호와 사용자 입력을 비교하여 통과 시에만
대시보드를 렌더링한다. Streamlit Community Cloud의 Secrets 관리 기능을
사용해 비밀번호를 안전하게 저장한다.

secrets.toml 형식:
    APP_PASSWORD = "your-password-here"

로컬 개발 시 .streamlit/secrets.toml에 동일하게 작성하거나,
환경변수 APP_PASSWORD로도 fallback 가능.
"""
from __future__ import annotations

import hmac
import os

import streamlit as st


def _expected_password() -> str | None:
    # st.secrets._parse() raises StreamlitSecretNotFoundError when no
    # secrets.toml exists (typical local dev). Treat that as "no password set"
    # so the gate fails open — matches documented behavior.
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD")


def check_password() -> bool:
    expected = _expected_password()

    if not expected:
        return True

    if st.session_state.get("auth_ok"):
        return True

    st.markdown("## KR 연금 자율주행 SAA 데모")
    st.caption("영상 제작 협업용 비공개 데모입니다. 비밀번호를 입력하세요.")

    pwd = st.text_input("비밀번호", type="password", key="pwd_input")

    if pwd:
        if hmac.compare_digest(pwd, expected):
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않습니다.")

    st.stop()
