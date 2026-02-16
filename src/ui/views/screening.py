"""スクリーニング結果表示"""

import streamlit as st
import requests
import pandas as pd

from src.ui.config import API_BASE


def _api_get(path: str, default=None):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


def render() -> None:
    """スクリーニング結果ページを描画"""
    st.title("スクリーニング結果")

    tab_value, tab_momentum = st.tabs(["割安銘柄", "モメンタムシグナル"])

    # --- 割安銘柄スクリーニング ---
    with tab_value:
        st.subheader("割安銘柄スクリーニング")
        st.caption("PER/PBR/配当利回りベースの日次自動スクリーニング結果")

        value_results = _api_get("/api/screening/value", [])
        if value_results:
            rows = []
            for r in value_results:
                rows.append({
                    "銘柄": r.get("name", r.get("ticker", "")),
                    "コード": r.get("ticker", ""),
                    "セクター": r.get("sector", ""),
                    "スコア": f"{r.get('score', 0):.1f}",
                    "PER": f"{r.get('per', 0):.1f}",
                    "PBR": f"{r.get('pbr', 0):.2f}",
                    "配当利回り": f"{r.get('dividend_yield', 0):.2f}%",
                    "バリュー": f"{r.get('value_score', 0):.1f}",
                    "モメンタム": f"{r.get('momentum_score', 0):.1f}",
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("スクリーニング結果がまだありません。日次チェックの実行後に表示されます。")

    # --- モメンタムシグナル ---
    with tab_momentum:
        st.subheader("モメンタムシグナル")
        st.caption("ゴールデンクロス、出来高急増、RSI反転の検知結果")

        momentum_results = _api_get("/api/screening/momentum", [])
        if momentum_results:
            for sig in momentum_results:
                priority = sig.get("priority", "low")
                msg = sig.get("message", "")
                ticker = sig.get("ticker", "")

                body = f"**{ticker}** - {msg}"
                detail = sig.get("detail")
                if detail:
                    body += f"\n\n詳細: {detail}"

                if priority == "high":
                    st.error(body)
                elif priority == "medium":
                    st.warning(body)
                else:
                    st.info(body)
        else:
            st.info("モメンタムシグナルがまだありません。")

    # --- 手動実行 ---
    st.divider()
    if st.button("日次チェックを手動実行"):
        try:
            resp = requests.post(f"{API_BASE}/api/jobs/daily-check", timeout=60)
            resp.raise_for_status()
            st.success("日次チェックを実行しました。ページを再読み込みしてください。")
        except Exception as e:
            st.error(f"実行に失敗しました: {e}")
