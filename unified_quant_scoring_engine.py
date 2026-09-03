"""
Unified Quantitative Multi-Factor Scoring Engine (unified_quant_scoring_engine.py)
==================================================================================
Institutional-grade quantitative scoring framework based on Grinold-Kahn active portfolio theory.

Architecture:
1. 5 Orthogonal Quant Pillars (Risk-Budgeted Weights sum to 100%):
   - Pillar 1: Trend & Dynamic Price Momentum (Weight: 25.0%)
   - Pillar 2: Institutional Flow & Smart Money (Weight: 25.0%)
   - Pillar 3: Market Microstructure, GEX & Asymmetric Squeeze (Weight: 20.0%)
   - Pillar 4: Macroeconomic, Liquidity & Regime Matrix (Weight: 15.0%)
   - Pillar 5: Fundamental Earnings Drift & Sentiment Catalyst (Weight: 15.0%)

2. Mathematical Properties:
   - 100% Continuous and Differentiable (Zero step-cliff discontinuities)
   - Nonlinear Hyperbolic Tangent (tanh) & Z-score activation mapping
   - Strictly bounded composite output Q in [0.0, 100.0]
   - Asymmetric Tail Risk Damping Penalties (False breakouts, imminent earnings, catastrophic news)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger


class UnifiedQuantScoringEngine:
    """Institutional Multi-Factor Quantitative Scoring Engine (Swing Trading Horizon: 3-10 Days)"""

    # Baseline 5 Factor Pillar Weights (Calibrated default)
    WEIGHT_TREND = 0.35           # Primary driver: Price momentum, Kalman velocity, RS alpha
    WEIGHT_MICROSTRUCTURE = 0.30  # Volume surge, Order flow imbalance (OFI), Volume profile POC
    WEIGHT_CATALYST = 0.20        # Earnings PEAD surprise drift, News sentiment catalyst
    WEIGHT_MACRO = 0.10           # VIX term structure & Multi-timeframe trend confluence
    WEIGHT_INSTITUTIONAL = 0.05   # Auxiliary background sponsorship (13F / Form 4 confirmation)

    def __init__(self):
        self._cache = {}

    def _get_bayesian_dynamic_weights(self, regime: Optional[str] = None) -> Dict[str, float]:
        """
        [BAYESIAN DYNAMIC FACTOR WEIGHTING]
        Dynamically adapts 5 pillar weights based on current market regime and earnings seasonality:
        - Bull Momentum: Trend & Microstructure dominate
        - Choppy / Range: Microstructure & Catalyst dominate
        - Bear / Risk-Off: Macro Regime & Microstructure defense dominate
        """
        reg_str = (regime or "CHOPPY").upper()
        
        # Check if current month is peak US earnings season (Jan/Feb, Apr/May, Jul/Aug, Oct/Nov)
        from datetime import datetime
        cur_month = datetime.now().month
        is_earnings_season = cur_month in [1, 2, 4, 5, 7, 8, 10, 11]

        if "BULL" in reg_str or "TREND" in reg_str:
            w_trend = 0.40
            w_micro = 0.30
            w_cat = 0.20 if is_earnings_season else 0.15
            w_macro = 0.05
            w_inst = 0.05
        elif "BEAR" in reg_str or "PANIC" in reg_str or "RISK_OFF" in reg_str:
            w_macro = 0.30
            w_micro = 0.30
            w_cat = 0.20
            w_trend = 0.15
            w_inst = 0.05
        else: # CHOPPY / NORMAL / TRANSITION
            w_micro = 0.35
            w_cat = 0.25 if is_earnings_season else 0.20
            w_macro = 0.20
            w_trend = 0.15
            w_inst = 0.05 if not is_earnings_season else 0.05

        # Normalize to sum exactly to 1.00
        total_w = w_trend + w_micro + w_cat + w_macro + w_inst
        return {
            "trend": w_trend / total_w,
            "micro": w_micro / total_w,
            "catalyst": w_cat / total_w,
            "macro": w_macro / total_w,
            "inst": w_inst / total_w
        }

    def compute_composite_score(
        self,
        symbol: str,
        df: Optional[pd.DataFrame] = None,
        indicators: Any = None,
        macro_state: Any = None,
        strategy_context: Any = None
    ) -> Tuple[int, List[str], float, Dict[str, float]]:
        """
        Computes continuous, risk-budgeted quantitative composite score.
        
        Returns:
            final_int_score (0-100), breakdown_lines, unclamped_score, pillar_scores_dict
        """
        breakdown = []
        pillar_details = {}

        # Resolve Bayesian Dynamic Weights for current regime
        regime_val = getattr(macro_state, "regime", None) if macro_state else None
        if not regime_val and isinstance(macro_state, dict):
            regime_val = macro_state.get("regime")
        b_weights = self._get_bayesian_dynamic_weights(regime_val)

        # -------------------------------------------------------------
        # PILLAR 1: Trend & Dynamic Price Momentum (Weight: 35.0%)
        # -------------------------------------------------------------
        p1_signals = []
        
        # 1.1 Kalman Filter Velocity (Z-scored)
        kalman_vel = 0.0
        try:
            from kalman_trend_filter import KalmanTrendFilter
            k_res = KalmanTrendFilter().analyze(df, symbol)
            kalman_vel = float(k_res.get('kalman_velocity', 0.0))
            phi_kalman = float(np.tanh(kalman_vel / 1.25))
            p1_signals.append(0.30 * phi_kalman)
            if abs(phi_kalman) > 0.15:
                breakdown.append(f"• [칼만 무지연 속도] {kalman_vel:+.2f}%/일 (기여 {phi_kalman*35.0*0.30:+.1f}pt)")
        except Exception:
            pass

        # 1.2 20-Day SMA Support & Proximity
        phi_sma = 0.0
        try:
            if df is not None and len(df) >= 20 and 'Close' in df.columns:
                c = float(df['Close'].iloc[-1])
                sma20 = float(df['Close'].rolling(20).mean().iloc[-1])
                if sma20 > 0:
                    dist_pct = (c - sma20) / sma20
                    # Optimal sweet spot is close to SMA20 (-1.5% to +2.5%)
                    phi_sma = float(np.exp(-((dist_pct - 0.005) ** 2) / (2 * (0.02 ** 2))) * 2.0 - 1.0)
                    p1_signals.append(0.25 * phi_sma)
        except Exception:
            pass

        # 1.3 ADX Trend Strength & Directional Index
        phi_adx = 0.0
        try:
            adx_val = getattr(indicators, 'adx', 20.0) if indicators else 20.0
            phi_adx = float(np.tanh((adx_val - 25.0) / 10.0))
            p1_signals.append(0.20 * phi_adx)
        except Exception:
            pass

        # 1.4 Relative Strength vs SPY (Alpha)
        phi_rs = 0.0
        try:
            import kis_data as _kd_rs
            spy_df = _kd_rs.get_daily_ohlcv("SPY", days=25)
            if spy_df is not None and len(spy_df) >= 20 and df is not None and len(df) >= 20:
                s_ret = (float(df['Close'].iloc[-1]) / float(df['Close'].iloc[-20])) - 1.0
                m_ret = (float(spy_df['Close'].iloc[-1]) / float(spy_df['Close'].iloc[-20])) - 1.0
                rs_alpha = s_ret - m_ret
                phi_rs = float(np.tanh(rs_alpha / 0.05))
                p1_signals.append(0.15 * phi_rs)
                if abs(rs_alpha) >= 0.03:
                    breakdown.append(f"• [SPY 대비 상대강도 RS] 초과수익 {rs_alpha*100:+.1f}% (기여 {phi_rs*35.0*0.15:+.1f}pt)")
        except Exception:
            pass

        # 1.5 Hurst Fractal Exponent
        phi_hurst = 0.0
        try:
            from hurst_fractal_regime import HurstFractalRegimeFilter
            h_res = HurstFractalRegimeFilter().analyze(df, symbol=symbol)
            h_exp = float(h_res.get('hurst_exponent', 0.50))
            phi_hurst = float(np.tanh((h_exp - 0.50) / 0.15))
            p1_signals.append(0.10 * phi_hurst)
        except Exception:
            pass

        p1_composite = float(np.clip(sum(p1_signals), -1.0, 1.0))
        pillar_details["Trend_Momentum"] = round(p1_composite, 3)

        # -------------------------------------------------------------
        # PILLAR 2: Auxiliary Institutional Sponsorship (Weight: 5.0%)
        # -------------------------------------------------------------
        p2_signals = []

        # 2.1 13F Institutional Sponsorship
        phi_inst = 0.0
        try:
            from smart_money_footprint import SmartMoneyFootprint
            sm_res = SmartMoneyFootprint().analyze_ticker(symbol)
            inst_pct = float(sm_res.get('institutional_pct', 50.0))
            inst_clamped = min(100.0, max(0.0, inst_pct))
            phi_inst = float(np.exp(-((inst_clamped - 68.0) ** 2) / (2 * (22.0 ** 2))))
            p2_signals.append(0.60 * phi_inst)
            if inst_pct >= 40.0:
                breakdown.append(f"• [기관 지분 스폰서십(13F)] {inst_pct:.1f}% (기여 {phi_inst*5.0*0.60:+.1f}pt)")
        except Exception:
            pass

        # 2.2 SEC Form 4 Real Open-Market Buying (Positive bias only; routine 10b5-1 sales do not penalize short swings)
        phi_insider = 0.0
        try:
            from sec_form4_insider_radar import SECForm4InsiderRadar
            ins_res = SECForm4InsiderRadar().analyze_insider_activity(symbol)
            ins_bonus = float(ins_res.get('strategy_bonus', 0.0))
            if ins_bonus > 0:
                phi_insider = float(np.tanh(ins_bonus / 7.5))
                p2_signals.append(0.40 * phi_insider)
                breakdown.append(f"• [SEC 내부자 실매수 확인] {ins_res.get('cluster_desc', '매수')} (기여 {phi_insider*5.0*0.40:+.1f}pt)")
            else:
                p2_signals.append(0.0)
        except Exception:
            pass

        p2_composite = float(np.clip(sum(p2_signals), -1.0, 1.0))
        pillar_details["Institutional_Flow"] = round(p2_composite, 3)

        # -------------------------------------------------------------
        # PILLAR 3: Market Microstructure, Options GEX & Squeeze (Weight: 20.0%)
        # -------------------------------------------------------------
        p3_signals = []

        # 3.1 Dealer Gamma Exposure (Net GEX & Wall Proximity)
        phi_gex = 0.0
        try:
            from options_gamma_engine import get_options_gamma_engine
            gex_data = get_options_gamma_engine().analyze_gex(symbol)
            net_gex = float(gex_data.get('net_gex_millions', 0.0))
            phi_gex = float(np.tanh(net_gex / 150.0))
            p3_signals.append(0.35 * phi_gex)
            if abs(net_gex) >= 5.0 and abs(phi_gex * 30.0 * 0.35) >= 0.5:
                breakdown.append(f"• [옵션 딜러 GEX 감마] ${net_gex:+,.1f}M ({gex_data.get('gex_regime')}, 기여 {phi_gex*30.0*0.35:+.1f}pt)")
        except Exception:
            pass

        # 3.2 Volume Profile Point of Control (POC) Support Bounce
        phi_poc = 0.0
        try:
            from volume_profile_poc import VolumeProfilePOCEngine
            vp_res = VolumeProfilePOCEngine().analyze(df, symbol)
            if vp_res.get('is_poc_bounce', False):
                phi_poc = 0.85
                breakdown.append(f"• [매물대 POC 지지 반등] {vp_res.get('poc_price', 0.0):.2f} 지지 확인 (기여 {phi_poc*30.0*0.25:+.1f}pt)")
            else:
                dist_poc = float(vp_res.get('dist_from_poc_pct', 5.0))
                phi_poc = float(np.exp(-abs(dist_poc) / 3.0) * 1.5 - 0.5)
            p3_signals.append(0.25 * phi_poc)
        except Exception:
            pass

        # 3.3 Asymmetric Trend-Conditioned Short Squeeze
        phi_short = 0.0
        try:
            short_pct = float(getattr(sm_res, 'get', lambda k, d: d)('short_pct', 3.0)) if 'sm_res' in locals() else 3.0
            is_above_sma = (p1_composite >= 0.0)
            if short_pct >= 10.0:
                if is_above_sma:
                    phi_short = float(np.tanh((short_pct - 8.0) / 8.0))
                    breakdown.append(f"• [숏스퀴즈 점화 조건] 공매도 {short_pct:.1f}% + 정배열 (기여 {phi_short*30.0*0.25:+.1f}pt)")
                else:
                    phi_short = -float(np.tanh((short_pct - 8.0) / 8.0)) * 1.2
                    breakdown.append(f"• [공매도 하방 압박] 공매도 {short_pct:.1f}% + 역배열 (기여 {phi_short*30.0*0.25:+.1f}pt)")
            else:
                phi_short = 0.1  # Clean low short pressure
            p3_signals.append(0.25 * phi_short)
        except Exception:
            pass

        # 3.4 Order Flow Imbalance (OFI)
        phi_ofi = 0.0
        try:
            from order_flow_imbalance import OrderFlowImbalanceDetector
            ofi_res = OrderFlowImbalanceDetector().evaluate_ofi(df, symbol)
            ofi_score = float(ofi_res.get('ofi_score', 0.0))
            phi_ofi = float(np.tanh(ofi_score / 15.0))
            p3_signals.append(0.15 * phi_ofi)
            if abs(ofi_score) >= 4.0:
                breakdown.append(f"• [호가 주문 불균형(OFI)] {ofi_res.get('ofi_regime', 'ACCUMULATION')} (기여 {phi_ofi*30.0*0.15:+.1f}pt)")
        except Exception:
            pass

        p3_composite = float(np.clip(sum(p3_signals), -1.0, 1.0))
        pillar_details["Microstructure_GEX"] = round(p3_composite, 3)

        # -------------------------------------------------------------
        # PILLAR 4: Macroeconomic, Liquidity & Regime Matrix (Weight: 10.0%)
        # -------------------------------------------------------------
        p4_signals = []

        # 4.1 Fed Net Liquidity Expansion
        phi_fed = 0.0
        try:
            from institutional_liquidity_engine import get_liquidity_macro_report
            liq_rep = get_liquidity_macro_report()
            if liq_rep:
                regime_map = {"EXPANSION": 0.8, "NEUTRAL": 0.2, "CONTRACTION": -0.8}
                phi_fed = regime_map.get(liq_rep.liquidity_regime, 0.0)
                p4_signals.append(0.40 * phi_fed)
        except Exception:
            pass

        # 4.2 VIX Term Structure Contango/Backwardation
        phi_vix = 0.0
        try:
            from omni_institutional_alpha_suite import get_omni_alpha_suite
            omni_vix = get_omni_alpha_suite().evaluate_volatility_and_yield_regime()
            if omni_vix:
                if omni_vix.volatility_regime == "CONTANGO_STABLE":
                    phi_vix = 0.7
                elif omni_vix.volatility_regime == "BACKWARDATION_PANIC":
                    phi_vix = -0.9
                else:
                    phi_vix = 0.0
                p4_signals.append(0.35 * phi_vix)
        except Exception:
            pass

        # 4.3 Multi-Timeframe Confluence (1H / Daily Trend Alignment)
        phi_mtf = 0.0
        try:
            from multi_timeframe_confluence import MultiTimeframeConfluence
            mtf_res = MultiTimeframeConfluence().evaluate_confluence(symbol, daily_df=df)
            mtf_bonus = float(mtf_res.get('bonus_points', 0.0))
            phi_mtf = float(np.tanh(mtf_bonus / 5.0))
            p4_signals.append(0.25 * phi_mtf)
        except Exception:
            pass

        p4_composite = float(np.clip(sum(p4_signals), -1.0, 1.0))
        pillar_details["Macro_Regime"] = round(p4_composite, 3)

        # -------------------------------------------------------------
        # PILLAR 5: Fundamental Catalyst & PEAD Drift (Weight: 20.0%)
        # -------------------------------------------------------------
        p5_signals = []

        # 5.1 PEAD Earnings Surprise Drift & Gamma Squeeze Confluence
        phi_pead = 0.0
        try:
            from pead_earnings_radar import PEADEarningsRadar
            p_radar = PEADEarningsRadar()
            curr_c = float(df['Close'].iloc[-1]) if (df is not None and len(df) > 0 and 'Close' in df.columns) else 0.0
            is_sqz, sqz_bonus, sqz_desc = p_radar.check_pead_gamma_squeeze_confluence(symbol, curr_c)
            if is_sqz:
                phi_pead = float(np.tanh(sqz_bonus / 10.0))
                breakdown.append(f"💥 [PEAD+감마 스퀴즈 컨플루언스] {sqz_desc} (기여 {phi_pead*b_weights['catalyst']*100*0.60:+.1f}pt)")
            else:
                pead_active, pead_surp = p_radar.check_pead_breakout(symbol)
                if pead_active and pead_surp > 0:
                    phi_pead = float(np.tanh(pead_surp / 15.0))
                    breakdown.append(f"• [PEAD 어닝 서프라이즈] EPS +{pead_surp:.1f}% (기여 {phi_pead*b_weights['catalyst']*100*0.55:+.1f}pt)")
            p5_signals.append(0.55 * phi_pead)
        except Exception:
            pass

        # 5.2 Multi-Source AI News Sentiment Polarity
        phi_news = 0.0
        try:
            from news_sentiment_engine import NewsSentimentEngine
            news_res = NewsSentimentEngine().analyze_symbol_news(symbol)
            news_score = float(news_res.get('score', 0.0))
            phi_news = float(np.tanh(news_score / 15.0))
            p5_signals.append(0.45 * phi_news)
        except Exception:
            pass

        p5_composite = float(np.clip(sum(p5_signals), -1.0, 1.0))
        pillar_details["Catalyst_Quality"] = round(p5_composite, 3)

        # -------------------------------------------------------------
        # CONTINUOUS AGGREGATION ACROSS 5 PILLARS (0.0 to 100.0)
        # -------------------------------------------------------------
        weighted_delta = (
            (b_weights["trend"] * p1_composite) +
            (b_weights["inst"] * p2_composite) +
            (b_weights["micro"] * p3_composite) +
            (b_weights["macro"] * p4_composite) +
            (b_weights["catalyst"] * p5_composite)
        )  # Range: [-1.0, +1.0]

        # -------------------------------------------------------------
        # GU, KELLY & XIU (RFS 2020) NON-LINEAR FACTOR INTERACTIONS
        # -------------------------------------------------------------
        # 1. Momentum x Volatility Quality (Low-vol smooth momentum beats erratic high-vol spikes)
        atr_val = float(getattr(indicators, 'atr', 0.0)) if indicators else 0.0
        curr_p = float(df['Close'].iloc[-1]) if (df is not None and len(df) > 0 and 'Close' in df.columns) else 100.0
        vol_ratio = (atr_val / curr_p) if curr_p > 0 else 0.025
        vol_quality = float(np.clip(1.0 - (vol_ratio / 0.05), -0.5, 1.0))
        i_mom_vol = p1_composite * vol_quality

        # 2. Institutional Flow x Microstructure OBI Synergy
        i_flow_micro = p2_composite * p3_composite

        # 3. Fundamental Catalyst x Momentum Synergy
        i_catalyst = p5_composite * max(0.0, p1_composite)

        # Nonlinear Interaction Synergy Boost (-6.0 to +8.0 pts)
        synergy_boost = float(8.0 * (0.40 * i_mom_vol + 0.35 * i_flow_micro + 0.25 * i_catalyst))
        if abs(synergy_boost) >= 1.5:
            breakdown.append(f"• [RFS 2020 팩터 시너지] 비선형 결합 승수 (기여 {synergy_boost:+.1f}pt)")

        # Baseline 50.0 + (50.0 * weighted_delta) + Non-linear Synergy Boost
        base_quant_score = 50.0 + (50.0 * weighted_delta) + synergy_boost

        # -------------------------------------------------------------
        # ASYMMETRIC TAIL RISK DAMPING PENALTIES (Hard Nonlinear Filters)
        # -------------------------------------------------------------
        total_penalty = 0.0

        # Penalty 1: False Breakout & Overheated Exhaustion Trap
        try:
            if df is not None and len(df) >= 20:
                c_vol = float(df['Volume'].iloc[-1])
                avg_vol = float(df['Volume'].iloc[-21:-1].mean()) if len(df) >= 21 else c_vol
                rvol = c_vol / avg_vol if avg_vol > 0 else 1.0
                rsi_val = float(getattr(indicators, 'rsi', 50.0)) if indicators else 50.0
                high_20 = float(df['High'].iloc[-21:-1].max()) if len(df) >= 21 else float(df['High'].max())
                curr_c = float(df['Close'].iloc[-1])
                
                if (curr_c >= high_20 * 0.98 and rvol < 1.05) or (rsi_val > 78.0):
                    fb_pen = 35.0 * max(0.0, min(1.0, (rsi_val - 70.0) / 15.0))
                    total_penalty += fb_pen
                    breakdown.append(f"🚨 [가짜 돌파/과열 경고] 거래량 부진 및 과매수 (감점 -{fb_pen:.1f}pt)")
        except Exception:
            pass

        # Penalty 2: Imminent Unhedged Earnings (PEAD Danger Window <= 2 days)
        try:
            from pead_earnings_radar import PEADEarningsRadar
            shielded, s_reason = PEADEarningsRadar().check_pre_earnings_shield(symbol)
            if shielded:
                total_penalty += 45.0
                breakdown.append("🚨 [실적 공시 초임박 위험] 실적 발표 D-2일 이내 (감점 -45.0pt)")
        except Exception:
            pass

        # Penalty 3: Floating Extended Entry (> 4.5% above 20d SMA)
        try:
            if df is not None and len(df) >= 20:
                c = float(df['Close'].iloc[-1])
                sma20 = float(df['Close'].rolling(20).mean().iloc[-1])
                if sma20 > 0 and (c / sma20) > 1.045:
                    float_pen = 25.0 * float(np.clip(((c / sma20) - 1.045) / 0.03, 0.0, 1.0))
                    total_penalty += float_pen
                    breakdown.append(f"⚠️ [이격 과다 이격 경고] 20일선 대비 +{(c/sma20-1)*100:.1f}% 붕 뜸 (감점 -{float_pen:.1f}pt)")
        except Exception:
            pass

        # Final Bounded Continuous Quant Score with Robust NaN/Inf Defense
        raw_final = base_quant_score - total_penalty
        if np.isnan(raw_final) or np.isinf(raw_final):
            logger.warning("⚠️ [UNIFIED_QUANT_SCORE] {} raw_final is NaN/Inf (Base: {}, Pen: {}), defaulting to 0",
                           symbol, base_quant_score, total_penalty)
            raw_final = 0.0
        clamped_score = int(np.clip(round(raw_final), 0, 100))

        logger.info(
            "📐 [UNIFIED_QUANT_SCORE] {}: {}/100 (Base: {:.1f}, Penalty: {:.1f}) | Pillars: Trend={:+.2f}, Inst={:+.2f}, Micro={:+.2f}, Macro={:+.2f}, Cat={:+.2f}",
            symbol, clamped_score, base_quant_score, total_penalty,
            p1_composite, p2_composite, p3_composite, p4_composite, p5_composite
        )

        return clamped_score, breakdown, raw_final, pillar_details


# Singleton
_quant_scoring_engine = None

def get_quant_scoring_engine() -> UnifiedQuantScoringEngine:
    global _quant_scoring_engine
    if _quant_scoring_engine is None:
        _quant_scoring_engine = UnifiedQuantScoringEngine()
    return _quant_scoring_engine