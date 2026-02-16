# 統合仕様書 - ずぼら×低リスク 株式投資ツール「traders-tool」

## 0. プロダクトコンセプト

- **ターゲット**: ずぼらな個人投資家（毎日5分以上は使いたくない）
- **思想**: 守りを固めた上で、攻めのチャンスを逃さない
- **原則**: ゼロコンフィグ、自動化、1アクション、信号機UI

---

## 1. 技術スタック

| レイヤー | 技術 | 理由 |
|----------|------|------|
| 言語 | Python 3.11+ | エコシステムの豊富さ |
| データ取得 | yfinance | 無料で日米株価取得可能 |
| バックエンド | FastAPI | 軽量・高速・非同期対応 |
| フロントエンド | Streamlit | 最速でダッシュボード構築 |
| DB | SQLite | セットアップ不要・軽量 |
| スケジューラ | APScheduler | FastAPI統合が容易 |

---

## 2. アーキテクチャ概要

```
[Streamlit UI] ←→ [FastAPI Backend] ←→ [SQLite DB]
                         ↓
                   [APScheduler]
                         ↓
                   [yfinance API]
```

### ディレクトリ構成

```
traders/
├── requirements/           # 要件定義書
├── src/
│   ├── data/               # データ取得・加工モジュール
│   │   ├── __init__.py
│   │   ├── fetcher.py      # yfinanceからのデータ取得
│   │   ├── indicators.py   # テクニカル指標算出
│   │   └── cache.py        # SQLiteキャッシュ
│   ├── strategy/           # 投資戦略ロジック
│   │   ├── __init__.py
│   │   ├── screener.py     # 銘柄スクリーニング（攻め）
│   │   ├── signals.py      # シグナル検知（攻め）
│   │   ├── risk.py         # リスク指標算出（守り）
│   │   ├── health.py       # 健全度スコア算出（守り）
│   │   └── alerts.py       # アラート生成（守り）
│   ├── api/                # FastAPI バックエンド
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPIアプリ本体
│   │   ├── routers/
│   │   │   ├── portfolio.py
│   │   │   ├── screening.py
│   │   │   ├── signals.py
│   │   │   ├── alerts.py
│   │   │   └── risk.py
│   │   ├── models.py       # Pydanticモデル
│   │   ├── database.py     # DB接続・初期化
│   │   └── scheduler.py    # 定期実行タスク
│   └── ui/                 # Streamlit フロントエンド
│       ├── app.py          # メインアプリ
│       ├── pages/
│       │   ├── dashboard.py    # ダッシュボード（メイン画面）
│       │   ├── portfolio.py    # ポートフォリオ管理
│       │   ├── screening.py    # スクリーニング結果
│       │   └── settings.py     # 設定画面
│       └── components/
│           ├── health_gauge.py # 健全度ゲージ
│           ├── alert_banner.py # アラートバナー
│           ├── sector_heatmap.py
│           └── signal_card.py
├── tests/
├── pyproject.toml
└── README.md
```

---

## 3. SQLite データベース設計

### portfolios テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | ポートフォリオID |
| name | TEXT | ポートフォリオ名 |
| created_at | DATETIME | 作成日時 |

### holdings テーブル（保有銘柄）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | 保有ID |
| portfolio_id | INTEGER FK | ポートフォリオID |
| ticker | TEXT | 銘柄コード（例: 7203.T） |
| name | TEXT | 銘柄名 |
| sector | TEXT | セクター |
| shares | REAL | 保有株数 |
| buy_price | REAL | 平均取得価格 |
| buy_date | DATE | 取得日 |
| created_at | DATETIME | 作成日時 |

### watchlist テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | ウォッチリストID |
| ticker | TEXT | 銘柄コード |
| name | TEXT | 銘柄名 |
| reason | TEXT | 追加理由 |
| added_at | DATETIME | 追加日時 |

### screening_results テーブル（日次スクリーニング結果）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | 結果ID |
| date | DATE | スクリーニング日 |
| ticker | TEXT | 銘柄コード |
| name | TEXT | 銘柄名 |
| sector | TEXT | セクター |
| score | REAL | 総合スコア |
| per | REAL | PER |
| pbr | REAL | PBR |
| dividend_yield | REAL | 配当利回り |
| momentum_score | REAL | モメンタムスコア |
| value_score | REAL | バリュースコア |

### signals テーブル（攻めシグナル）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | シグナルID |
| ticker | TEXT | 銘柄コード |
| signal_type | TEXT | シグナル種別（golden_cross, volume_spike, rsi_reversal, value_opportunity, dividend_chance） |
| priority | TEXT | 優先度（high/medium/low） |
| message | TEXT | シグナルメッセージ |
| detail | TEXT | 詳細情報（JSON） |
| is_valid | BOOLEAN | 有効フラグ |
| expires_at | DATETIME | 有効期限 |
| created_at | DATETIME | 検知日時 |

### alerts テーブル（守りアラート）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | アラートID |
| portfolio_id | INTEGER FK | ポートフォリオID |
| ticker | TEXT | 銘柄コード（NULLならポートフォリオ全体） |
| alert_type | TEXT | アラート種別（W-01〜W-10） |
| level | INTEGER | 警告レベル（1〜4） |
| message | TEXT | 通知メッセージ |
| action_suggestion | TEXT | 推奨アクション（1行） |
| is_read | BOOLEAN | 既読フラグ |
| is_resolved | BOOLEAN | 解消フラグ |
| created_at | DATETIME | 作成日時 |
| resolved_at | DATETIME | 解消日時 |

### risk_metrics テーブル（日次リスク指標）
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | メトリクスID |
| portfolio_id | INTEGER FK | ポートフォリオID |
| date | DATE | 算出日 |
| health_score | REAL | 健全度スコア（0〜100） |
| max_drawdown | REAL | 最大ドローダウン |
| portfolio_volatility | REAL | ポートフォリオ全体のボラティリティ |
| sharpe_ratio | REAL | シャープレシオ |
| hhi | REAL | 集中度指数 |
| var_95 | REAL | 95% VaR |

### stop_loss_rules テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER PK | ルールID |
| portfolio_id | INTEGER FK | ポートフォリオID |
| ticker | TEXT | 銘柄コード |
| buy_price | REAL | 取得価格 |
| stop_loss_pct | REAL | 損切り閾値（デフォルト: -10%） |
| trailing_stop | BOOLEAN | トレーリングストップ有効フラグ |
| highest_price | REAL | 最高値（トレーリング用） |
| is_active | BOOLEAN | 有効フラグ |

### price_cache テーブル（株価キャッシュ）
| カラム | 型 | 説明 |
|--------|-----|------|
| ticker | TEXT | 銘柄コード |
| date | DATE | 日付 |
| open | REAL | 始値 |
| high | REAL | 高値 |
| low | REAL | 安値 |
| close | REAL | 終値 |
| volume | INTEGER | 出来高 |
| PRIMARY KEY | (ticker, date) | 複合主キー |

---

## 4. MVP機能（Phase 1）

### 攻守の矛盾調整方針

| 矛盾点 | 攻めの主張 | 守りの主張 | 統合方針 |
|---------|-----------|-----------|----------|
| 集中 vs 分散 | 確信度高い銘柄に比重を | 常に分散を | **基本は分散。集中度30%超で警告、ただしブロックはしない** |
| 通知頻度 | チャンスを逃さず通知 | 通知疲れを防ぐ | **1日上限5件。高優先度のみ即時、他は日次まとめ** |
| ダッシュボード情報量 | 多くの指標を表示 | シンプルに | **守りの健全度を最上部、攻めの注目銘柄を2番目** |
| リスクテイク | シグナル発生時に即行動 | 慎重に確認 | **シグナルに有効期限を設定し、焦らなくてよい設計** |

### MVP機能一覧

#### 攻め機能（4件）
| ID | 機能 | 概要 |
|----|------|------|
| F-O1 | 割安銘柄スクリーニング | PER/PBR/配当利回りベースの日次自動スクリーニング |
| F-O2 | モメンタムシグナル検知 | ゴールデンクロス、出来高急増、RSI反転の検知 |
| F-O3 | ダッシュボード（攻め部分） | 今日の注目銘柄トップ5、シグナル一覧 |
| F-O4 | 買い時通知 | 割安+モメンタムが重なった時の通知 |

#### 守り機能（4件）
| ID | 機能 | 概要 |
|----|------|------|
| F-D1 | 損切りアラート | -10%/-15%/-20%の3段階自動通知 |
| F-D2 | ポートフォリオ健全度スコア | 0〜100のスコア、信号機UI表示 |
| F-D3 | 集中リスク警告 | 単一銘柄30%超、セクター50%超で警告 |
| F-D4 | 暴落アラート | 個別-5%/日、インデックス-3%/日で検知 |

---

## 5. 健全度スコア算出ロジック（攻守統合）

```
健全度スコア = 分散度(30%) + ボラティリティ(25%) + ドローダウン(20%) + 相関(15%) + 含み損(10%)
```

| 要素 | 配点 | 100点の条件 | 0点の条件 |
|------|------|------------|----------|
| 分散度 | 30 | HHI < 0.1（十分に分散） | HHI > 0.5（1銘柄に集中） |
| ボラティリティ | 25 | 年率σ < 15% | 年率σ > 40% |
| ドローダウン | 20 | MDD < 5% | MDD > 30% |
| 相関 | 15 | 平均相関 < 0.3 | 平均相関 > 0.8 |
| 含み損 | 10 | 含み損銘柄 0% | 含み損銘柄 > 50% |

### 信号機表示
- **緑（70〜100）**: 健全。特にアクション不要。
- **黄（40〜69）**: 注意。改善ポイントを表示。
- **赤（0〜39）**: 危険。具体的なアクションを提示。

---

## 6. 銘柄スコアリング（攻め用統合スコア）

```
銘柄スコア = バリュー(40%) + モメンタム(30%) + 成長性(20%) + 安全性(10%)
```

| 要素 | 配点 | 使用指標 |
|------|------|----------|
| バリュー | 40% | PER（業種平均比）、PBR、配当利回り |
| モメンタム | 30% | RSI、MACD、移動平均乖離率 |
| 成長性 | 20% | 売上成長率、EPS成長率 |
| 安全性 | 10% | 自己資本比率、配当性向 |

---

## 7. 通知ルール（攻守統合）

### 通知優先度

| 優先度 | 攻め | 守り | 配信方法 |
|--------|------|------|----------|
| 即時 | 割安+モメンタム合致 | Level 3-4アラート | アプリ内バナー |
| 日次まとめ | 新規スクリーニング結果 | Level 1-2情報 | ダッシュボード |
| 週次 | 週次レポート | リスクサマリー | ダッシュボード |

### 共通ルール
- **1日の通知上限**: 5件（攻め+守り合算）
- **守り優先**: 上限内で守り通知を優先配信
- **同一銘柄制限**: 同一銘柄の通知は24時間に1回まで
- **シグナル有効期限**: 攻めシグナルには有効期限（デフォルト7日）を設定

---

## 8. API エンドポイント一覧

### ポートフォリオ管理
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/portfolios` | ポートフォリオ一覧 |
| POST | `/api/portfolios` | ポートフォリオ作成 |
| GET | `/api/portfolios/{id}` | ポートフォリオ詳細 |
| POST | `/api/portfolios/{id}/holdings` | 保有銘柄追加 |
| DELETE | `/api/portfolios/{id}/holdings/{ticker}` | 保有銘柄削除 |

### 攻め機能
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/screening/value` | 割安銘柄スクリーニング結果 |
| GET | `/api/screening/momentum` | モメンタムシグナル一覧 |
| GET | `/api/signals` | 直近シグナル一覧 |
| POST | `/api/watchlist` | ウォッチリスト追加 |
| DELETE | `/api/watchlist/{ticker}` | ウォッチリスト削除 |
| GET | `/api/watchlist` | ウォッチリスト一覧 |

### 守り機能
| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/portfolios/{id}/health` | 健全度スコア |
| GET | `/api/portfolios/{id}/alerts` | アラート一覧 |
| PUT | `/api/alerts/{id}/read` | アラート既読化 |
| GET | `/api/portfolios/{id}/risk-metrics` | リスク指標 |
| GET | `/api/portfolios/{id}/concentration` | 集中度分析 |
| POST | `/api/portfolios/{id}/stop-loss` | 損切りルール設定 |

### 共通
| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/jobs/daily-check` | 日次チェック手動実行 |
| GET | `/api/notifications` | 通知一覧（攻め+守り統合） |

---

## 9. ダッシュボード画面構成

### メイン画面（1画面で完結）

```
┌─────────────────────────────────────────────────┐
│ 🚦 ポートフォリオ健全度: 72/100 [緑]            │  ← 守り：最重要
│    「健全です。特にアクションは不要です」          │
├─────────────────────────────────────────────────┤
│ ⚠️ アラート (2件)                                │  ← 守り：警告
│  [黄] A社が取得価格から-8%下落中                  │
│  [青] テックセクターが40%を占めています            │
├─────────────────────────────────────────────────┤
│ 📈 今日の注目銘柄 TOP5                           │  ← 攻め：チャンス
│  1. B社 (スコア: 85) - ゴールデンクロス発生       │
│  2. C社 (スコア: 78) - 割安+高配当               │
│  ...                                             │
├─────────────────────────────────────────────────┤
│ 💼 ポートフォリオ                                 │  ← 保有状況
│  銘柄 | 保有数 | 取得価格 | 現在値 | 損益 | 損益率│
│  A社  | 100   | 1,500   | 1,380 | -12K | -8.0% │
│  D社  | 200   | 3,200   | 3,500 | +60K | +9.4% │
│  ...                                             │
├─────────────────────────────────────────────────┤
│ 🗂️ セクター構成         │ 📊 セクターヒートマップ │
│  [円グラフ]              │  [ヒートマップ]         │
└─────────────────────────────────────────────────┘
```

### 画面優先順位（上から下）
1. **守り**: 健全度スコア（常に最上部）
2. **守り**: アラート（あれば表示）
3. **攻め**: 注目銘柄・シグナル
4. **情報**: ポートフォリオ一覧
5. **情報**: セクター構成・ヒートマップ

---

## 10. 開発タスク割り振り

### data-engineer（タスク#4）
- `src/data/fetcher.py`: yfinanceからの株価・銘柄情報取得
- `src/data/indicators.py`: テクニカル指標算出（MA, RSI, MACD, ボリンジャーバンド）
- `src/data/cache.py`: SQLiteへの株価キャッシュ
- `src/api/database.py`: DB初期化・マイグレーション

### strategy-dev（タスク#5）
- `src/strategy/screener.py`: 割安銘柄スクリーニング + スコアリング
- `src/strategy/signals.py`: モメンタムシグナル検知
- `src/strategy/risk.py`: リスク指標算出（ボラティリティ, MDD, シャープレシオ, 相関, β, HHI, VaR）
- `src/strategy/health.py`: 健全度スコア算出
- `src/strategy/alerts.py`: アラート生成（W-01〜W-10）

### backend-dev（タスク#6）
- `src/api/main.py`: FastAPIアプリ本体
- `src/api/routers/`: 全ルーター実装
- `src/api/models.py`: Pydanticモデル定義
- `src/api/scheduler.py`: APSchedulerによる日次/週次バッチ

### frontend-dev（タスク#7）
- `src/ui/app.py`: Streamlitメインアプリ
- `src/ui/pages/`: 全ページ実装
- `src/ui/components/`: 共通コンポーネント
- 信号機UI、アラートバナー、セクターヒートマップ
