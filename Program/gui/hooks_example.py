"""Example Streamlit hooks showing how to use `agents.py` functions from the UI.

Copy relevant parts into your Input Data tab render function or wire buttons accordingly.
"""
from __future__ import annotations

import streamlit as st
from gui import agents


def example_ui_flow(global_state: dict) -> None:
    st.button("Validate", on_click=lambda: _on_validate(global_state))
    if st.session_state.get("validated", False):
        st.success("Input valid — Run button enabled")
        if st.button("Run Pipeline"):
            _on_run(global_state)


def _on_validate(state: dict) -> None:
    valid, errors = agents.validate_state(state)
    st.session_state.validated = valid
    if not valid:
        for e in errors:
            st.error(e)
    else:
        st.success("Validasi sukses — Anda dapat menekan Run")


def _on_run(state: dict) -> None:
    if not st.session_state.get("validated", False):
        st.error("Input belum tervalidasi")
        return
    try:
        result = agents.run_pipeline(state)
        st.session_state["results"] = result
        st.success("Pipeline selesai — hasil tersedia di state")
    except Exception as exc:
        st.error(f"Pipeline gagal: {exc}")
