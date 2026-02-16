"""投資戦略ロジックモジュール.

割安銘柄スクリーニング、モメンタムシグナル検知、
リスク指標算出、健全度スコア算出、アラート生成、
教育コンテンツ（説明テンプレート・XP管理・シミュレーション）を提供する。
"""

from src.strategy.screener import screen_value_stocks, score_stock
from src.strategy.signals import detect_signals
from src.strategy.risk import calculate_risk_metrics
from src.strategy.health import calculate_health_score
from src.strategy.alerts import generate_alerts
from src.strategy.explanations import get_signal_explanation, get_alert_explanation
from src.strategy.education import grant_xp, determine_level, check_stage_promotion, check_badge_eligibility
from src.strategy.simulation import (
    simulate_no_stop_loss,
    simulate_concentration_risk,
    simulate_stress_test,
    simulate_diversification,
)

__all__ = [
    "screen_value_stocks",
    "score_stock",
    "detect_signals",
    "calculate_risk_metrics",
    "calculate_health_score",
    "generate_alerts",
    # 教育: 説明テンプレート
    "get_signal_explanation",
    "get_alert_explanation",
    # 教育: XP・ステージ・バッジ
    "grant_xp",
    "determine_level",
    "check_stage_promotion",
    "check_badge_eligibility",
    # 教育: シミュレーション
    "simulate_no_stop_loss",
    "simulate_concentration_risk",
    "simulate_stress_test",
    "simulate_diversification",
]
