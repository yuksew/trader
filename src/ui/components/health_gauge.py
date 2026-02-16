"""健全度ゲージコンポーネント - 信号機UI（緑/黄/赤）"""

import streamlit as st
import plotly.graph_objects as go


def _score_color(score: float) -> tuple[str, str, str]:
    """スコアに応じた色・ラベル・メッセージを返す"""
    if score >= 70:
        return "#2ecc71", "緑", "健全です。特にアクションは不要です"
    elif score >= 40:
        return "#f39c12", "黄", "注意が必要です。改善ポイントを確認してください"
    else:
        return "#e74c3c", "赤", "危険な状態です。具体的なアクションが必要です"


def render_health_gauge(score: float, details: dict | None = None) -> None:
    """健全度ゲージを描画する

    Args:
        score: 健全度スコア（0-100）
        details: 内訳情報（diversification, volatility, drawdown, correlation, unrealized_loss）
    """
    color, label, message = _score_color(score)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": " / 100", "font": {"size": 36}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": color, "thickness": 0.6},
                "steps": [
                    {"range": [0, 40], "color": "rgba(231,76,60,0.15)"},
                    {"range": [40, 70], "color": "rgba(243,156,18,0.15)"},
                    {"range": [70, 100], "color": "rgba(46,204,113,0.15)"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 3},
                    "thickness": 0.8,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(
        height=200,
        margin={"t": 20, "b": 20, "l": 30, "r": 30},
    )

    st.markdown(
        f"### :vertical_traffic_light: ポートフォリオ健全度 [{label}]"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**{message}**")

    if details:
        with st.expander("内訳を表示"):
            labels = {
                "diversification": "分散度",
                "volatility": "ボラティリティ",
                "drawdown": "ドローダウン",
                "correlation": "相関",
                "unrealized_loss": "含み損",
            }
            weights = {
                "diversification": 30,
                "volatility": 25,
                "drawdown": 20,
                "correlation": 15,
                "unrealized_loss": 10,
            }
            for key, name in labels.items():
                val = details.get(key, 0)
                weight = weights[key]
                st.progress(
                    val / 100,
                    text=f"{name}（配点{weight}）: {val:.0f}",
                )
