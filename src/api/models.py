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
    name: str = Field("", description="銘柄名")
    sector: str = Field("", description="セクター")
    shares: float = Field(..., gt=0, description="保有株数")
    buy_price: float = Field(..., gt=0, description="平均取得価格")
    buy_date: Optional[date] = Field(None, description="取得日")


class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    name: str
    sector: str
    shares: float
    buy_price: float
    buy_date: Optional[date] = None
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
    name: str = Field("", description="銘柄名")
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


# ---------- Glossary ----------

class GlossaryTermResponse(BaseModel):
    term: str
    reading: str = ""
    display_name: str
    description: str
    image_metaphor: str = ""
    related_features: list[str] = []


# ---------- Learning Cards ----------

class LearningCardResponse(BaseModel):
    id: int
    card_key: str
    title: str
    content: str
    category: str
    related_signal_type: Optional[str] = None


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
        pattern="^(stop_loss|concentration)$",
        description="シナリオ種別 (stop_loss or concentration)",
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
    signals_total: int = 0
    alerts_total: int = 0
    alerts_acted: int = 0
    highlights: list[str] = []


class MonthlyReviewResponse(BaseModel):
    period_start: str
    period_end: str
    signals_total: int = 0
    alerts_total: int = 0
    alerts_acted: int = 0
    highlights: list[str] = []
