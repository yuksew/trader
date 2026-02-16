"""シグナル・アラートのステージ別説明テンプレート.

各シグナル種別（golden_cross, volume_spike, rsi_reversal, value_opportunity,
dividend_chance）と全アラート（W-01〜W-10）に対して Lv.1〜4 の説明テンプレートを提供する。

テンプレートは Python format string で、実際の数値を埋め込み可能。
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# シグナル説明テンプレート
# ---------------------------------------------------------------------------

SIGNAL_EXPLANATIONS: dict[str, dict[int, str]] = {
    "golden_cross": {
        1: "この銘柄、最近上がり始めています。買う人が増えてきたサインです。",
        2: (
            "{short_window}日移動平均が{long_window}日移動平均を上抜け"
            "（ゴールデンクロス）しました。短期の勢いが長期トレンドを上回り、"
            "上昇トレンドの始まりを示唆しています。"
        ),
        3: (
            "{short_window}MA/{long_window}MAゴールデンクロス発生。"
            "RSI={rsi}（中立圏から上昇中）、出来高は20日平均比{vol_ratio}倍。"
            "過去の同条件シグナル勝率: {win_rate}%（n={sample_size}）"
        ),
        4: (
            "GC発生。{short_window}MA={ma_short:.0f} > {long_window}MA={ma_long:.0f}。"
            "RSI(14)={rsi:.1f}。Vol ratio={vol_ratio:.1f}x。"
            "MACD histogram={macd_hist:.2f}。"
            "Historical win rate: {win_rate:.0f}% (n={sample_size})"
        ),
    },
    "volume_spike": {
        1: "この銘柄の取引がいつもより活発です。注目が集まっているようです。",
        2: (
            "直近の出来高が平均の{ratio:.1f}倍に急増しています。"
            "多くの投資家が売買しているサインで、大きな値動きの前兆かもしれません。"
        ),
        3: (
            "出来高急増検知。短期平均出来高={avg_volume_short:,.0f}（"
            "{long_window}日平均比{ratio:.1f}倍）。"
            "価格変動率={price_change:+.1f}%。"
            "機関投資家の動きの可能性あり。"
        ),
        4: (
            "Vol spike: {short_window}d avg={avg_volume_short:,.0f} / "
            "{long_window}d avg={avg_volume_long:,.0f} = {ratio:.2f}x。"
            "Price delta={price_change:+.2f}%。"
            "VWAP deviation={vwap_dev:+.2f}%。"
            "Institutional flow estimate: {inst_flow}"
        ),
    },
    "rsi_reversal": {
        1: "この銘柄は売られすぎた後、回復し始めています。反発のチャンスかもしれません。",
        2: (
            "売られすぎの状態（RSI={min_rsi_in_period:.0f}）から回復中です"
            "（現在RSI={current_rsi:.0f}）。"
            "過去に同様の状況では反発するケースが多く見られます。"
        ),
        3: (
            "RSI反転シグナル。RSI(14)が{min_rsi_in_period:.1f}から"
            "{current_rsi:.1f}へ回復。"
            "売られすぎ閾値={oversold_threshold}。"
            "出来高サポート: {volume_support}。"
            "過去の反転成功率: {reversal_rate:.0f}%"
        ),
        4: (
            "RSI reversal: {min_rsi_in_period:.1f} -> {current_rsi:.1f} "
            "(threshold={oversold_threshold})。"
            "Stochastic %K={stoch_k:.1f} %D={stoch_d:.1f}。"
            "BB position={bb_position:.1f}%。"
            "Reversal hit rate: {reversal_rate:.0f}% (n={sample_size})"
        ),
    },
    "value_opportunity": {
        1: "この会社はお買い得度が高いです。業界の平均よりもお手頃な価格です。",
        2: (
            "PER（お買い得度）が{per:.1f}倍で、業界平均{sector_avg_per:.1f}倍を"
            "大きく下回っています。利益に対して割安な状態です。"
        ),
        3: (
            "バリュー機会検知。PER={per:.1f}x（業種avg {sector_avg_per:.1f}x、"
            "乖離率{per_discount:+.0f}%）。"
            "PBR={pbr:.2f}x。配当利回り={div_yield:.1f}%。"
            "割安スコア={value_score:.0f}/100"
        ),
        4: (
            "Value opportunity: PER={per:.1f}x (sector={sector_avg_per:.1f}x, "
            "discount={per_discount:+.1f}%)。"
            "PBR={pbr:.2f}x。EV/EBITDA={ev_ebitda:.1f}x。"
            "DY={div_yield:.2f}%。FCF yield={fcf_yield:.1f}%。"
            "Composite value score={value_score:.0f}"
        ),
    },
    "dividend_chance": {
        1: "この会社は持っているだけでお小遣いがもらえます。年間{div_yield:.1f}%のリターンが期待できます。",
        2: (
            "配当利回りが{div_yield:.1f}%と高水準です。"
            "配当性向は{payout_ratio:.0f}%で、無理なく配当を出している状態です。"
            "{consecutive_years}年連続で配当を出しています。"
        ),
        3: (
            "高配当機会。利回り={div_yield:.2f}%（業種avg {sector_avg_yield:.1f}%）。"
            "配当性向={payout_ratio:.0f}%。連続配当={consecutive_years}年。"
            "増配率(5Y)={dividend_growth:.1f}%。"
            "減配リスク: {cut_risk}"
        ),
        4: (
            "Dividend: yield={div_yield:.2f}% (sector={sector_avg_yield:.2f}%)。"
            "Payout={payout_ratio:.0f}%。"
            "Consecutive={consecutive_years}y。"
            "DPS CAGR(5Y)={dividend_growth:.1f}%。"
            "FCF coverage={fcf_coverage:.1f}x。"
            "Cut probability={cut_prob:.0f}%"
        ),
    },
}


# ---------------------------------------------------------------------------
# アラート説明テンプレート（なぜ危険？）
# ---------------------------------------------------------------------------

ALERT_EXPLANATIONS: dict[str, dict[int, str]] = {
    "W-01": {
        1: (
            "{ticker}の株価が今日大きく下がりました（{daily_return_pct:+.1f}%）。"
            "一時的なものかもしれませんが、様子を見ましょう。"
        ),
        2: (
            "{ticker}が1日で{daily_return_pct:+.1f}%下落しました。"
            "1日に5%以上下がるのは珍しく、何か悪いニュースが出た可能性があります。"
            "原因を確認してみましょう。"
        ),
        3: (
            "{ticker}が日次{daily_return_pct:+.1f}%の急落。"
            "過去1年の日次リターン分布で下位{percentile:.0f}%に位置。"
            "出来高は通常の{vol_ratio:.1f}倍。"
            "セクター全体の動き: {sector_return:+.1f}%"
        ),
        4: (
            "{ticker}: daily return={daily_return_pct:+.2f}% "
            "(z-score={z_score:.1f}sigma)。"
            "Vol={vol_ratio:.1f}x avg。"
            "Sector={sector_return:+.2f}%。"
            "Market={market_return:+.2f}%。"
            "Implied vol change={iv_change:+.1f}pts"
        ),
    },
    "W-02": {
        1: (
            "{ticker}は買った時より{loss_pct:.0f}%下がっています。"
            "もう少し下がると損切りラインです。注意しましょう。"
        ),
        2: (
            "{ticker}が取得価格から{loss_pct:.1f}%下落し、損切りライン（-10%）に"
            "近づいています。これ以上下がると損失が大きくなるので、"
            "売却するか保有を続けるか判断が必要です。"
        ),
        3: (
            "{ticker}: 取得価格{buy_price:,.0f}円→現在{current_price:,.0f}円"
            "（{loss_pct:+.1f}%）。損切りライン接近。"
            "含み損額={unrealized_loss:,.0f}円。"
            "保有日数={holding_days}日。"
            "同業種の動き: {sector_perf:+.1f}%"
        ),
        4: (
            "{ticker}: cost={buy_price:,.0f} / current={current_price:,.0f} "
            "({loss_pct:+.2f}%)。"
            "Unrealized PnL={unrealized_loss:,.0f}。"
            "Days held={holding_days}。"
            "Sector perf={sector_perf:+.2f}%。"
            "Support level={support:,.0f}。"
            "Risk/reward={risk_reward:.1f}"
        ),
    },
    "W-03": {
        1: (
            "{ticker}がかなり下がっています（{loss_pct:.0f}%）。"
            "これ以上損が膨らまないよう、売ることを考えたほうがいいかもしれません。"
        ),
        2: (
            "{ticker}が取得価格から{loss_pct:.1f}%下落し、損切り推奨ラインを超えました。"
            "「いつか戻る」と待つのは危険です。損失を確定して次の投資に資金を回す"
            "ことも選択肢です。"
        ),
        3: (
            "{ticker}: 損切り推奨ライン突破（{loss_pct:+.1f}%）。"
            "含み損={unrealized_loss:,.0f}円。"
            "ポートフォリオ全体への影響={portfolio_impact:.1f}%。"
            "過去にこの水準から回復した確率: {recovery_rate:.0f}%"
        ),
        4: (
            "{ticker}: loss={loss_pct:+.2f}% (beyond stop-loss)。"
            "Unrealized={unrealized_loss:,.0f}。"
            "Portfolio impact={portfolio_impact:.2f}%。"
            "Historical recovery rate from this level: {recovery_rate:.0f}%。"
            "Avg recovery days={avg_recovery_days}。"
            "Opportunity cost estimate={opportunity_cost:,.0f}"
        ),
    },
    "W-04": {
        1: (
            "あなたのポートフォリオの状態が良くありません（健全度スコア: {health_score:.0f}）。"
            "改善するためのアクションが必要です。"
        ),
        2: (
            "ポートフォリオの健全度が危険水準（{health_score:.0f}/100）です。"
            "銘柄が偏りすぎている、値動きが激しすぎるなどの問題があります。"
            "分散を改善することで安全度を上げられます。"
        ),
        3: (
            "健全度スコア={health_score:.0f}/100（危険水準<40）。"
            "主な減点要因: 分散度={diversity_score:.0f}、"
            "ボラティリティ={volatility_score:.0f}、"
            "ドローダウン={drawdown_score:.0f}。"
            "改善優先度: {improvement_priority}"
        ),
        4: (
            "Health={health_score:.0f}/100 (DANGER)。"
            "Breakdown: diversity={diversity_score:.0f} vol={volatility_score:.0f} "
            "MDD={drawdown_score:.0f} corr={correlation_score:.0f} "
            "loss={loss_score:.0f}。"
            "HHI={hhi:.3f}。"
            "Portfolio vol={portfolio_vol:.1f}%。"
            "Suggested rebalance: {rebalance_suggestion}"
        ),
    },
    "W-05": {
        1: (
            "あなたのポートフォリオは少し注意が必要な状態です（健全度スコア: {health_score:.0f}）。"
            "大きな問題ではありませんが、改善できるポイントがあります。"
        ),
        2: (
            "ポートフォリオの健全度が注意水準（{health_score:.0f}/100）です。"
            "まだ危険ではありませんが、このまま放置すると悪化する可能性があります。"
            "一番改善しやすいのは{easiest_improvement}です。"
        ),
        3: (
            "健全度スコア={health_score:.0f}/100（注意水準40-70）。"
            "改善ポイント: {weak_points}。"
            "改善すれば+{potential_improvement:.0f}pt見込み。"
            "前回チェック時: {prev_score:.0f}/100"
        ),
        4: (
            "Health={health_score:.0f}/100 (CAUTION)。"
            "Weak: {weak_points}。"
            "Delta from last check: {delta:+.0f}pt。"
            "Improvement potential: +{potential_improvement:.0f}pt。"
            "Optimal allocation suggestion: {optimal_allocation}"
        ),
    },
    "W-06": {
        1: (
            "{ticker}の割合が大きすぎます（{ratio:.0f}%）。"
            "1つの銘柄に集中しすぎると、その銘柄が下がった時に大きな損失になります。"
        ),
        2: (
            "{ticker}がポートフォリオの{ratio:.1f}%を占めています。"
            "30%を超えると集中リスクが高い状態です。"
            "もし{ticker}が20%下落したら、ポートフォリオ全体で"
            "{impact:.1f}%のダメージを受けます。"
        ),
        3: (
            "{ticker}: ポートフォリオの{ratio:.1f}%（上限30%超過）。"
            "集中リスク: {ticker}が-20%で全体-{impact:.1f}%。"
            "HHI={hhi:.3f}。"
            "推奨リバランス: {ticker}を{target_ratio:.0f}%まで削減"
        ),
        4: (
            "{ticker}: weight={ratio:.2f}% (limit=30%)。"
            "Concentration HHI={hhi:.4f}。"
            "Stress scenario: -20% -> portfolio impact={impact:.2f}%。"
            "Marginal VaR contribution={marginal_var:.2f}%。"
            "Rebalance: sell {sell_amount:,.0f} units to reach {target_ratio:.0f}%"
        ),
    },
    "W-07": {
        1: (
            "{sector}関連の銘柄が多すぎます（{ratio:.0f}%）。"
            "同じ業界の銘柄が多いと、その業界全体が不調の時に大きく損をします。"
        ),
        2: (
            "{sector}セクターがポートフォリオの{ratio:.1f}%を占めています。"
            "50%を超えるとセクター集中リスクが高い状態です。"
            "異なる業種の銘柄を加えることでリスクを分散できます。"
        ),
        3: (
            "{sector}: ポートフォリオの{ratio:.1f}%（上限50%超過）。"
            "セクター内相関={sector_correlation:.2f}。"
            "直近のセクター騰落率={sector_return:+.1f}%。"
            "推奨: {recommended_sectors}への分散"
        ),
        4: (
            "{sector}: weight={ratio:.2f}% (limit=50%)。"
            "Intra-sector corr={sector_correlation:.3f}。"
            "Sector beta={sector_beta:.2f}。"
            "Sector return(1M)={sector_return:+.2f}%。"
            "Diversification benefit estimate: vol reduction={vol_reduction:.1f}%"
        ),
    },
    "W-08": {
        1: (
            "株式市場全体が大きく下がっています。"
            "こういう時は慌てて売らず、落ち着いて様子を見ることが大切です。"
        ),
        2: (
            "市場全体（{index}）が{daily_return_pct:+.1f}%急落しています。"
            "市場全体の下落時は個別銘柄も連れ安しやすいです。"
            "保有銘柄への影響を確認しましょう。"
        ),
        3: (
            "市場急落: {index} {daily_return_pct:+.1f}%。"
            "保有銘柄の推定影響: 平均{estimated_impact:+.1f}%。"
            "ポートフォリオβ={portfolio_beta:.2f}。"
            "VIX水準: {vix:.1f}"
        ),
        4: (
            "Market crash: {index}={daily_return_pct:+.2f}%。"
            "Portfolio beta={portfolio_beta:.2f}。"
            "Estimated portfolio impact={estimated_impact:+.2f}%。"
            "VIX={vix:.1f}。"
            "Implied portfolio VaR(95%)={portfolio_var:.2f}%。"
            "Historical similar events: avg recovery={avg_recovery_days}d"
        ),
    },
    "W-09": {
        1: (
            "持っている銘柄のほとんどが今日下がっています。"
            "市場全体の動きかもしれないので、焦らず確認しましょう。"
        ),
        2: (
            "保有銘柄の{drop_ratio:.0f}%が下落しています。"
            "市場全体の調整か、ポートフォリオの構成に問題があるかもしれません。"
            "相場全体の動きと比べてみましょう。"
        ),
        3: (
            "保有銘柄の{drop_ratio:.0f}%が下落（{drop_count}/{total}銘柄）。"
            "市場リターン={market_return:+.1f}%。"
            "ポートフォリオ日次リターン={portfolio_return:+.1f}%。"
            "最大下落: {worst_ticker} {worst_return:+.1f}%"
        ),
        4: (
            "Majority decline: {drop_count}/{total} stocks down ({drop_ratio:.0f}%)。"
            "Market={market_return:+.2f}%。"
            "Portfolio={portfolio_return:+.2f}%。"
            "Worst={worst_ticker} ({worst_return:+.2f}%)。"
            "Cross-correlation spike={corr_spike:.2f}。"
            "Systematic risk indicator: {systematic_risk}"
        ),
    },
    "W-10": {
        1: (
            "{ticker}は{loss_days}日間ずっと買った値段より安い状態が続いています。"
            "このまま持ち続けるか、損切りするか考えてみましょう。"
        ),
        2: (
            "{ticker}の含み損が{loss_days}日間続いています"
            "（取得価格{buy_price:,.0f}円→現在{current_price:,.0f}円）。"
            "長期間の含み損は機会費用も大きいです。"
            "もし今売って他の銘柄に投資したら？を考えてみましょう。"
        ),
        3: (
            "{ticker}: 含み損{loss_days}日継続。"
            "含み損額={unrealized_loss:,.0f}円（{loss_pct:+.1f}%）。"
            "同期間に市場は{market_perf:+.1f}%。"
            "機会費用推定={opportunity_cost:,.0f}円。"
            "テクニカル: {technical_outlook}"
        ),
        4: (
            "{ticker}: unrealized loss for {loss_days}d。"
            "Cost={buy_price:,.0f} / Current={current_price:,.0f} "
            "({loss_pct:+.2f}%)。"
            "Market perf(same period)={market_perf:+.2f}%。"
            "Opportunity cost={opportunity_cost:,.0f}。"
            "Mean reversion probability={reversion_prob:.0f}%。"
            "Tax-loss harvesting value={tax_benefit:,.0f}"
        ),
    },
}


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def get_signal_explanation(
    signal_type: str,
    stage: int,
    **kwargs: Any,
) -> str:
    """シグナルのステージ別説明を取得する.

    Args:
        signal_type: シグナル種別
            ("golden_cross", "volume_spike", "rsi_reversal",
             "value_opportunity", "dividend_chance")
        stage: ユーザーのステージ (1〜4)
        **kwargs: テンプレートに埋め込む値

    Returns:
        フォーマット済みの説明文字列。
        テンプレートが見つからない場合やフォーマットエラーの場合は
        フォールバックテキストを返す。
    """
    stage = max(1, min(4, stage))
    templates = SIGNAL_EXPLANATIONS.get(signal_type)
    if templates is None:
        return f"シグナル: {signal_type}"

    template = templates.get(stage, templates.get(1, ""))
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        # フォーマットに必要なキーが不足している場合はテンプレートをそのまま返す
        return template


def get_alert_explanation(
    alert_type: str,
    stage: int,
    **kwargs: Any,
) -> str:
    """アラートの「なぜ危険？」説明をステージ別に取得する.

    Args:
        alert_type: アラート種別 ("W-01"〜"W-10")
        stage: ユーザーのステージ (1〜4)
        **kwargs: テンプレートに埋め込む値

    Returns:
        フォーマット済みの説明文字列。
        テンプレートが見つからない場合やフォーマットエラーの場合は
        フォールバックテキストを返す。
    """
    stage = max(1, min(4, stage))
    templates = ALERT_EXPLANATIONS.get(alert_type)
    if templates is None:
        return f"アラート: {alert_type}"

    template = templates.get(stage, templates.get(1, ""))
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return template
