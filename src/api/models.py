"""Pydantic models for request/response definitions."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Portfolio ----------

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="ポートフォリオ名")


class HoldingAdd(BaseModel):
    ticker: str = Field(..., description="銘柄コード (例: 7203.T)")
    name: str = Field(..., description="銘柄名")
    sector: str = Field("", description="セクター")
    shares: float = Field(..., gt=0, description="保有株数")
    buy_price: float = Field(..., gt=0, description="平均取得価格")
    buy_date: date = Field(..., description="取得日")


class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    name: str
    sector: str
    shares: float
    buy_price: float
    buy_date: date
    created_at: datetime


class PortfolioResponse(BaseModel):
    id: int
    name: str
    created_at: datetime


class PortfolioDetailResponse(PortfolioResponse):
    holdings: list[HoldingResponse] = []


# ---------- Watchlist ----------

class WatchlistAdd(BaseModel):
    ticker: str = Field(..., description="銘柄コード")
    name: str = Field(..., description="銘柄名")
    reason: str = Field("", description="追加理由")


class WatchlistResponse(BaseModel):
    id: int
    ticker: str
    name: str
    reason: str
    added_at: datetime


# ---------- Screening ----------

class ScreeningResultResponse(BaseModel):
    id: int
    date: date
    ticker: str
    name: str
    sector: str
    score: float
    per: Optional[float] = None
    pbr: Optional[float] = None
    dividend_yield: Optional[float] = None
    momentum_score: Optional[float] = None
    value_score: Optional[float] = None


# ---------- Signals ----------

class SignalResponse(BaseModel):
    id: int
    ticker: str
    signal_type: str
    priority: str
    message: str
    detail: Optional[str] = None
    is_valid: bool
    expires_at: Optional[datetime] = None
    created_at: datetime


# ---------- Alerts ----------

class AlertResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: Optional[str] = None
    alert_type: str
    level: int
    message: str
    action_suggestion: Optional[str] = None
    is_read: bool
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None


# ---------- Risk Metrics ----------

class RiskMetricsResponse(BaseModel):
    id: int
    portfolio_id: int
    date: date
    health_score: float
    max_drawdown: float
    portfolio_volatility: float
    sharpe_ratio: Optional[float] = None
    hhi: float
    var_95: Optional[float] = None


class HealthResponse(BaseModel):
    health_score: float = Field(..., ge=0, le=100)
    level: str = Field(..., description="green / yellow / red")
    message: str
    breakdown: dict[str, float] = Field(default_factory=dict)


class ConcentrationResponse(BaseModel):
    hhi: float
    top_holdings: list[dict]
    sector_weights: dict[str, float]
    warnings: list[str]


# ---------- Stop Loss ----------

class StopLossCreate(BaseModel):
    ticker: str
    buy_price: float = Field(..., gt=0)
    stop_loss_pct: float = Field(default=-10.0, description="損切り閾値 (%, 例: -10)")
    trailing_stop: bool = Field(default=False, description="トレーリングストップ有効フラグ")


class StopLossResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    buy_price: float
    stop_loss_pct: float
    trailing_stop: bool
    highest_price: Optional[float] = None
    is_active: bool


# ---------- Notifications ----------

class NotificationResponse(BaseModel):
    id: int
    source: str = Field(..., description="signal or alert")
    ticker: Optional[str] = None
    priority: str
    message: str
    created_at: datetime


# ---------- Jobs ----------

class JobTriggerResponse(BaseModel):
    status: str
    message: str


# ---------- Education: User Profile ----------

class UserProfileResponse(BaseModel):
    id: int
    stage: int
    level: int
    xp: int
    safe_mode: bool
    login_streak: int
    total_login_days: int
    last_login_date: Optional[str] = None
    stage_upgraded_at: Optional[str] = None
    created_at: str


class XPAddRequest(BaseModel):
    action_type: str = Field(..., description="XP獲得アクション種別")
    context: str = Field("", description="発生コンテキスト")


class XPAddResponse(BaseModel):
    xp_earned: int
    total_xp: int
    level: int
    level_up: bool = False
    new_level_name: Optional[str] = None


class BadgeResponse(BaseModel):
    badge_id: str
    earned_at: str


class UserProgressResponse(BaseModel):
    stage: int
    stage_name: str
    level: int
    level_name: str
    xp: int
    xp_to_next_level: int
    total_login_days: int
    login_streak: int
    badges_count: int
    cards_viewed: int
    signals_explained: int
    simulations_run: int


class SafeModeRequest(BaseModel):
    enabled: bool = Field(..., description="セーフモード有効/無効")


class SafeModeResponse(BaseModel):
    safe_mode: bool


class GuardrailsResponse(BaseModel):
    stage: int
    safe_mode: bool
    stop_loss_editable: bool
    stop_loss_range: list[float]
    concentration_limit: float
    concentration_action: str
    low_health_action: str
    high_volatility_action: str
    settings_editable: str


# ---------- Education: Glossary ----------

class GlossaryTermResponse(BaseModel):
    term: str
    reading: str = ""
    display_name_lv1: str
    description_lv1: str
    description_lv2: str
    description_lv3: str
    description_lv4: str
    image_metaphor: str = ""
    related_features: list[str] = []


# ---------- Education: Learning Cards ----------

class LearningCardResponse(BaseModel):
    id: int
    card_key: str
    title: str
    content: str
    category: str
    related_signal_type: Optional[str] = None
    viewed: bool = False


class CardViewedResponse(BaseModel):
    card_id: int
    xp_earned: int


# ---------- Education: Explanations ----------

class SignalExplanationResponse(BaseModel):
    signal_id: int
    signal_type: str
    ticker: str
    explanation: str
    stage: int


class AlertExplanationResponse(BaseModel):
    alert_id: int
    alert_type: str
    ticker: Optional[str] = None
    explanation: str
    stage: int


# ---------- Simulation ----------

class PaperTradeRequest(BaseModel):
    ticker: str = Field(..., description="銘柄コード")
    action: str = Field(..., pattern="^(buy|sell)$", description="buy or sell")
    price: float = Field(..., gt=0, description="約定価格")
    quantity: int = Field(..., gt=0, description="数量")


class PaperTradeResponse(BaseModel):
    id: int
    ticker: str
    action: str
    price: float
    quantity: int
    virtual_balance: float
    created_at: str


class PaperHoldingItem(BaseModel):
    ticker: str
    quantity: int
    avg_price: float
    current_value: Optional[float] = None


class PaperPortfolioResponse(BaseModel):
    virtual_balance: float
    holdings: list[PaperHoldingItem]
    total_value: float


class WhatIfRequest(BaseModel):
    scenario_type: str = Field(
        ...,
        pattern="^(stop_loss|concentration|stress_test|diversification)$",
        description="シナリオ種別",
    )
    parameters: dict = Field(default_factory=dict, description="シナリオパラメータ (JSON)")


class SimulationResultResponse(BaseModel):
    id: int
    scenario_type: str
    parameters: dict
    result_summary: str
    result_data: dict
    created_at: str


# ---------- Review ----------

class WeeklyReviewResponse(BaseModel):
    period_start: str
    period_end: str
    signal_accuracy: Optional[float] = None
    signals_total: int = 0
    signals_hit: int = 0
    alerts_total: int = 0
    alerts_acted: int = 0
    xp_earned: int = 0
    cards_viewed: int = 0
    highlights: list[str] = []


class MonthlyReviewResponse(BaseModel):
    period_start: str
    period_end: str
    signal_accuracy: Optional[float] = None
    alert_response_rate: Optional[float] = None
    xp_earned: int = 0
    level_change: int = 0
    badges_earned: list[str] = []
    simulations_run: int = 0
    if_followed_pnl: Optional[float] = None
    highlights: list[str] = []


class SignalOutcomeResponse(BaseModel):
    signal_id: int
    ticker: str
    signal_type: str
    user_action: str
    price_at_signal: Optional[float] = None
    price_after_7d: Optional[float] = None
    price_after_30d: Optional[float] = None
    is_success: Optional[bool] = None
    pnl_7d_pct: Optional[float] = None
    pnl_30d_pct: Optional[float] = None


class AlertOutcomeResponse(BaseModel):
    alert_id: int
    alert_type: str
    ticker: Optional[str] = None
    user_action: str
    action_detail: Optional[str] = None
    price_at_alert: Optional[float] = None
    price_after_7d: Optional[float] = None
    price_after_30d: Optional[float] = None
    portfolio_impact: Optional[float] = None
