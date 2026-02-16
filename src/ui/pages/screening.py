"""スクリーニング結果表示 - ステージ別表示制御対応"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000"


def _api_get(path: str, default=None):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


# ステージ別の平易な表現マッピング
_SIGNAL_PLAIN_MESSAGES = {
    "golden_cross": "上がり始めています",
    "volume_spike": "注目が集まっています",
    "rsi_reversal": "売られすぎから戻り始めています",
}


def render() -> None:
    """スクリーニング結果ページを描画"""
    st.title("スクリーニング結果")

    user_stage = st.session_state.get("user_stage", 1)

    tab_value, tab_momentum = st.tabs(["割安銘柄", "モメンタムシグナル"])

    # --- 割安銘柄スクリーニング ---
    with tab_value:
        st.subheader("割安銘柄スクリーニング")
        if user_stage <= 1:
            st.caption("お買い得な銘柄を自動で見つけています")
        else:
            st.caption("PER/PBR/配当利回りベースの日次自動スクリーニング結果")

        value_results = _api_get("/api/screening/value", [])
        if value_results:
            rows = []
            for r in value_results:
                if user_stage <= 1:
                    # Lv.1: 銘柄名 + スコアのみ、平易な表現
                    rows.append({
                        "銘柄": r.get("name", r.get("ticker", "")),
                        "コード": r.get("ticker", ""),
                        "おすすめ度": f"{r.get('score', 0):.0f}点",
                    })
                elif user_stage == 2:
                    # Lv.2: + 主要指標（平易な名前付き）
                    rows.append({
                        "銘柄": r.get("name", r.get("ticker", "")),
                        "コード": r.get("ticker", ""),
                        "セクター": r.get("sector", ""),
                        "スコア": f"{r.get('score', 0):.1f}",
                        "お買い得度(PER)": f"{r.get('per', 0):.1f}",
                        "お小遣い率(配当)": f"{r.get('dividend_yield', 0):.2f}%",
                    })
                elif user_stage == 3:
                    # Lv.3: 全指標表示
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
                else:
                    # Lv.4: 全指標 + カスタムフィルタ
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

        # Lv.4: カスタムフィルタ
        if user_stage >= 4:
            with st.expander("カスタムフィルタ条件"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.number_input("PER上限", value=20.0, step=1.0, key="filter_per_max")
                with col2:
                    st.number_input("PBR上限", value=1.5, step=0.1, key="filter_pbr_max")
                with col3:
                    st.number_input("配当利回り下限(%)", value=2.0, step=0.5, key="filter_div_min")
                if st.button("フィルタ適用"):
                    st.info("カスタムフィルタを適用しました。")

    # --- モメンタムシグナル ---
    with tab_momentum:
        st.subheader("モメンタムシグナル")
        if user_stage <= 1:
            st.caption("値動きに注目すべき銘柄です")
        else:
            st.caption("ゴールデンクロス、出来高急増、RSI反転の検知結果")

        momentum_results = _api_get("/api/screening/momentum", [])
        if momentum_results:
            for sig in momentum_results:
                signal_type = sig.get("signal_type", "")
                priority = sig.get("priority", "low")
                priority_colors = {
                    "high": ":red_circle:",
                    "medium": ":orange_circle:",
                    "low": ":large_blue_circle:",
                }
                icon = priority_colors.get(priority, ":large_blue_circle:")

                # ステージ別メッセージ
                if user_stage <= 1:
                    msg = _SIGNAL_PLAIN_MESSAGES.get(signal_type, sig.get("message", ""))
                    st.markdown(f"{icon} **{sig.get('ticker', '')}** - {msg}")
                else:
                    st.markdown(
                        f"{icon} **{sig.get('ticker', '')}** - {sig.get('message', '')}"
                    )
                    if user_stage >= 3 and sig.get("detail"):
                        with st.expander("詳細"):
                            st.json(sig["detail"])
        else:
            st.info("モメンタムシグナルがまだありません。")

    # --- 手動実行 ---
    st.divider()
    if user_stage >= 2:
        if st.button("日次チェックを手動実行"):
            try:
                resp = requests.post(f"{API_BASE}/api/jobs/daily-check", timeout=60)
                resp.raise_for_status()
                st.success("日次チェックを実行しました。ページを再読み込みしてください。")
            except Exception as e:
                st.error(f"実行に失敗しました: {e}")
    else:
        st.caption("日次チェックは毎日自動で実行されます。")
