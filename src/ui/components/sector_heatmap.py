"""セクターヒートマップコンポーネント"""

import streamlit as st
import plotly.express as px
import pandas as pd


def render_sector_heatmap(holdings: list[dict]) -> None:
    """セクター構成（円グラフ）とセクターヒートマップを描画する

    Args:
        holdings: 保有銘柄一覧。各要素:
            - ticker (str)
            - name (str)
            - sector (str)
            - shares (float)
            - buy_price (float)
            - current_price (float)
    """
    if not holdings:
        st.info("ポートフォリオに銘柄がありません。")
        return

    df = pd.DataFrame(holdings)
    if "current_price" not in df.columns:
        df["current_price"] = df.get("buy_price", 0)

    df["market_value"] = df["shares"] * df["current_price"]
    df["pnl_pct"] = ((df["current_price"] - df["buy_price"]) / df["buy_price"] * 100).round(2)

    sector_agg = (
        df.groupby("sector")
        .agg(market_value=("market_value", "sum"), pnl_pct=("pnl_pct", "mean"))
        .reset_index()
    )

    col1, col2 = st.columns(2)

    # 円グラフ: セクター構成
    with col1:
        st.markdown("#### :file_folder: セクター構成")
        fig_pie = px.pie(
            sector_agg,
            values="market_value",
            names="sector",
            hole=0.4,
        )
        fig_pie.update_layout(
            height=300,
            margin={"t": 10, "b": 10, "l": 10, "r": 10},
            showlegend=True,
            legend={"orientation": "h", "y": -0.1},
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ヒートマップ: セクター別パフォーマンス
    with col2:
        st.markdown("#### :bar_chart: セクターヒートマップ")
        fig_tree = px.treemap(
            df,
            path=["sector", "name"],
            values="market_value",
            color="pnl_pct",
            color_continuous_scale=["#e74c3c", "#f5f5f5", "#2ecc71"],
            color_continuous_midpoint=0,
        )
        fig_tree.update_layout(
            height=300,
            margin={"t": 10, "b": 10, "l": 10, "r": 10},
        )
        st.plotly_chart(fig_tree, use_container_width=True)
