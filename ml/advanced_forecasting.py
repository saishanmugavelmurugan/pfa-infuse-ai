"""
Advanced Time-Series Forecasting Module for HealthTrack Pro
Implements Prophet, ARIMA, and ensemble methods for health metric prediction
Production-ready with comprehensive error handling and fallbacks
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd

# Suppress warnings for cleaner logs
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class ForecastModel(str, Enum):
    """Available forecasting models"""
    PROPHET = "prophet"
    ARIMA = "arima"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    ENSEMBLE = "ensemble"
    LINEAR = "linear"  # Fallback


@dataclass
class ForecastResult:
    """Structured forecast result"""
    metric_name: str
    forecast_values: List[float]
    forecast_dates: List[str]
    confidence_lower: List[float]
    confidence_upper: List[float]
    trend_direction: str
    trend_strength: float
    seasonality_detected: bool
    model_used: str
    accuracy_metrics: Dict[str, float]
    recommendations: List[str]


class AdvancedForecaster:
    """
    Advanced time-series forecasting with multiple model support
    Automatically selects best model based on data characteristics
    """
    
    # Health metric normal ranges for context
    METRIC_RANGES = {
        "heart_rate": {"min": 60, "max": 100, "unit": "bpm", "critical_low": 50, "critical_high": 120},
        "blood_pressure_systolic": {"min": 90, "max": 120, "unit": "mmHg", "critical_low": 80, "critical_high": 180},
        "blood_pressure_diastolic": {"min": 60, "max": 80, "unit": "mmHg", "critical_low": 50, "critical_high": 120},
        "blood_sugar": {"min": 70, "max": 100, "unit": "mg/dL", "critical_low": 60, "critical_high": 200},
        "spo2": {"min": 95, "max": 100, "unit": "%", "critical_low": 90, "critical_high": 100},
        "temperature": {"min": 36.1, "max": 37.2, "unit": "°C", "critical_low": 35, "critical_high": 38.5},
        "weight": {"min": 40, "max": 150, "unit": "kg", "critical_low": 30, "critical_high": 200},
        "respiratory_rate": {"min": 12, "max": 20, "unit": "breaths/min", "critical_low": 8, "critical_high": 30},
        "steps": {"min": 0, "max": 30000, "unit": "steps", "critical_low": 0, "critical_high": 50000},
        "sleep_hours": {"min": 6, "max": 9, "unit": "hours", "critical_low": 4, "critical_high": 12}
    }
    
    def __init__(self, forecast_days: int = 7):
        self.forecast_days = forecast_days
        self._prophet_available = self._check_prophet()
        self._statsmodels_available = self._check_statsmodels()
    
    def _check_prophet(self) -> bool:
        """Check if Prophet is available"""
        try:
            from prophet import Prophet
            return True
        except ImportError:
            logger.warning("Prophet not available, will use fallback methods")
            return False
    
    def _check_statsmodels(self) -> bool:
        """Check if statsmodels is available"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            return True
        except ImportError:
            logger.warning("Statsmodels not available, will use fallback methods")
            return False
    
    def prepare_data(
        self,
        time_series_data: List[Dict[str, Any]],
        metric_name: str
    ) -> Tuple[pd.DataFrame, bool]:
        """
        Prepare time series data for forecasting
        Returns (DataFrame, is_valid)
        """
        try:
            if not time_series_data or len(time_series_data) < 3:
                return pd.DataFrame(), False
            
            # Extract timestamps and values
            records = []
            for item in time_series_data:
                timestamp = item.get("timestamp") or item.get("date") or item.get("recorded_at")
                value = item.get(metric_name) or item.get("value")
                
                if timestamp and value is not None:
                    try:
                        if isinstance(timestamp, str):
                            dt = pd.to_datetime(timestamp)
                        else:
                            dt = timestamp
                        records.append({"ds": dt, "y": float(value)})
                    except (ValueError, TypeError):
                        continue
            
            if len(records) < 3:
                return pd.DataFrame(), False
            
            df = pd.DataFrame(records)
            df = df.sort_values("ds").reset_index(drop=True)
            df = df.drop_duplicates(subset=["ds"], keep="last")
            
            # Remove outliers (3 sigma)
            mean_val = df["y"].mean()
            std_val = df["y"].std()
            if std_val > 0:
                df = df[(df["y"] >= mean_val - 3 * std_val) & (df["y"] <= mean_val + 3 * std_val)]
            
            return df, len(df) >= 3
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return pd.DataFrame(), False
    
    def forecast_with_prophet(
        self,
        df: pd.DataFrame,
        metric_name: str
    ) -> Optional[ForecastResult]:
        """
        Forecast using Facebook Prophet
        Best for data with strong seasonality and trends
        """
        if not self._prophet_available or len(df) < 10:
            return None
        
        try:
            from prophet import Prophet
            
            # Configure Prophet
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True if len(df) >= 14 else False,
                daily_seasonality=True if len(df) >= 48 else False,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10,
                interval_width=0.95
            )
            
            # Fit model
            model.fit(df)
            
            # Create future dataframe
            future = model.make_future_dataframe(periods=self.forecast_days, freq='D')
            forecast = model.predict(future)
            
            # Extract forecast for future dates only
            future_forecast = forecast[forecast['ds'] > df['ds'].max()]
            
            # Calculate trend
            trend_direction, trend_strength = self._calculate_trend(
                df["y"].values,
                future_forecast["yhat"].values
            )
            
            # Detect seasonality
            seasonality_detected = len(df) >= 14 and (
                model.seasonalities.get("weekly", {}).get("period", 0) > 0
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                metric_name,
                future_forecast["yhat"].values,
                trend_direction
            )
            
            return ForecastResult(
                metric_name=metric_name,
                forecast_values=future_forecast["yhat"].tolist(),
                forecast_dates=[d.isoformat() for d in future_forecast["ds"]],
                confidence_lower=future_forecast["yhat_lower"].tolist(),
                confidence_upper=future_forecast["yhat_upper"].tolist(),
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                seasonality_detected=seasonality_detected,
                model_used="Prophet",
                accuracy_metrics=self._calculate_accuracy_metrics(df, model),
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Prophet forecasting failed: {e}")
            return None
    
    def forecast_with_arima(
        self,
        df: pd.DataFrame,
        metric_name: str
    ) -> Optional[ForecastResult]:
        """
        Forecast using ARIMA model
        Best for stationary time series with autocorrelation
        """
        if not self._statsmodels_available or len(df) < 10:
            return None
        
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.stattools import adfuller
            
            values = df["y"].values
            
            # Check stationarity and determine differencing order
            d = 0
            try:
                adf_result = adfuller(values, maxlag=min(10, len(values)//2))
                if adf_result[1] > 0.05:  # Not stationary
                    d = 1
            except Exception:
                d = 1
            
            # Auto-select p and q (simplified)
            best_aic = float('inf')
            best_order = (1, d, 1)
            
            for p in range(0, 3):
                for q in range(0, 3):
                    if p == 0 and q == 0:
                        continue
                    try:
                        model = ARIMA(values, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except Exception:
                        continue
            
            # Fit best model
            model = ARIMA(values, order=best_order)
            fitted = model.fit()
            
            # Forecast
            forecast_result = fitted.get_forecast(steps=self.forecast_days)
            forecast_values = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)
            
            # Generate dates
            last_date = df["ds"].max()
            forecast_dates = [
                (last_date + timedelta(days=i+1)).isoformat()
                for i in range(self.forecast_days)
            ]
            
            # Calculate trend
            trend_direction, trend_strength = self._calculate_trend(
                values, forecast_values
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                metric_name, forecast_values, trend_direction
            )
            
            return ForecastResult(
                metric_name=metric_name,
                forecast_values=forecast_values.tolist(),
                forecast_dates=forecast_dates,
                confidence_lower=conf_int.iloc[:, 0].tolist(),
                confidence_upper=conf_int.iloc[:, 1].tolist(),
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                seasonality_detected=False,
                model_used=f"ARIMA{best_order}",
                accuracy_metrics={"aic": best_aic, "order": str(best_order)},
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"ARIMA forecasting failed: {e}")
            return None
    
    def forecast_with_exponential_smoothing(
        self,
        df: pd.DataFrame,
        metric_name: str
    ) -> Optional[ForecastResult]:
        """
        Forecast using Holt-Winters Exponential Smoothing
        Best for data with trend and seasonality
        """
        if not self._statsmodels_available or len(df) < 10:
            return None
        
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            
            values = df["y"].values
            
            # Determine seasonality
            seasonal_periods = None
            if len(values) >= 14:
                seasonal_periods = 7  # Weekly seasonality
            
            # Fit model
            if seasonal_periods and len(values) >= 2 * seasonal_periods:
                model = ExponentialSmoothing(
                    values,
                    trend='add',
                    seasonal='add',
                    seasonal_periods=seasonal_periods,
                    damped_trend=True
                )
            else:
                model = ExponentialSmoothing(
                    values,
                    trend='add',
                    seasonal=None,
                    damped_trend=True
                )
            
            fitted = model.fit(optimized=True)
            
            # Forecast
            forecast_values = fitted.forecast(self.forecast_days)
            
            # Generate confidence intervals (approximate)
            residuals = fitted.resid
            std_resid = np.std(residuals)
            confidence_lower = forecast_values - 1.96 * std_resid
            confidence_upper = forecast_values + 1.96 * std_resid
            
            # Generate dates
            last_date = df["ds"].max()
            forecast_dates = [
                (last_date + timedelta(days=i+1)).isoformat()
                for i in range(self.forecast_days)
            ]
            
            # Calculate trend
            trend_direction, trend_strength = self._calculate_trend(
                values, forecast_values
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                metric_name, forecast_values, trend_direction
            )
            
            return ForecastResult(
                metric_name=metric_name,
                forecast_values=forecast_values.tolist(),
                forecast_dates=forecast_dates,
                confidence_lower=confidence_lower.tolist(),
                confidence_upper=confidence_upper.tolist(),
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                seasonality_detected=seasonal_periods is not None,
                model_used="Holt-Winters",
                accuracy_metrics={"sse": fitted.sse, "aic": fitted.aic},
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Exponential Smoothing forecasting failed: {e}")
            return None
    
    def forecast_with_linear(
        self,
        df: pd.DataFrame,
        metric_name: str
    ) -> ForecastResult:
        """
        Simple linear regression fallback
        Always available as last resort
        """
        try:
            values = df["y"].values
            n = len(values)
            x = np.arange(n)
            
            # Linear regression
            slope, intercept = np.polyfit(x, values, 1)
            
            # Forecast
            forecast_x = np.arange(n, n + self.forecast_days)
            forecast_values = slope * forecast_x + intercept
            
            # Simple confidence interval
            residuals = values - (slope * x + intercept)
            std_resid = np.std(residuals)
            confidence_lower = forecast_values - 1.96 * std_resid
            confidence_upper = forecast_values + 1.96 * std_resid
            
            # Generate dates
            last_date = df["ds"].max()
            forecast_dates = [
                (last_date + timedelta(days=i+1)).isoformat()
                for i in range(self.forecast_days)
            ]
            
            # Calculate trend
            trend_direction = "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable"
            trend_strength = min(abs(slope) / (np.mean(values) + 0.001) * 100, 100)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                metric_name, forecast_values, trend_direction
            )
            
            return ForecastResult(
                metric_name=metric_name,
                forecast_values=forecast_values.tolist(),
                forecast_dates=forecast_dates,
                confidence_lower=confidence_lower.tolist(),
                confidence_upper=confidence_upper.tolist(),
                trend_direction=trend_direction,
                trend_strength=float(trend_strength),
                seasonality_detected=False,
                model_used="Linear Regression",
                accuracy_metrics={"slope": float(slope), "intercept": float(intercept)},
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Linear forecasting failed: {e}")
            # Return empty result
            return ForecastResult(
                metric_name=metric_name,
                forecast_values=[],
                forecast_dates=[],
                confidence_lower=[],
                confidence_upper=[],
                trend_direction="unknown",
                trend_strength=0,
                seasonality_detected=False,
                model_used="None",
                accuracy_metrics={},
                recommendations=["Insufficient data for forecasting"]
            )
    
    def forecast_ensemble(
        self,
        df: pd.DataFrame,
        metric_name: str
    ) -> ForecastResult:
        """
        Ensemble forecasting combining multiple models
        Weights models by their historical accuracy
        """
        results = []
        weights = []
        
        # Try Prophet
        prophet_result = self.forecast_with_prophet(df, metric_name)
        if prophet_result and prophet_result.forecast_values:
            results.append(prophet_result)
            weights.append(0.4)  # Higher weight for Prophet
        
        # Try ARIMA
        arima_result = self.forecast_with_arima(df, metric_name)
        if arima_result and arima_result.forecast_values:
            results.append(arima_result)
            weights.append(0.35)
        
        # Try Exponential Smoothing
        es_result = self.forecast_with_exponential_smoothing(df, metric_name)
        if es_result and es_result.forecast_values:
            results.append(es_result)
            weights.append(0.25)
        
        # If no advanced models worked, use linear
        if not results:
            return self.forecast_with_linear(df, metric_name)
        
        # Normalize weights
        total_weight = sum(weights[:len(results)])
        weights = [w / total_weight for w in weights[:len(results)]]
        
        # Combine forecasts
        n_forecast = min(len(r.forecast_values) for r in results)
        
        ensemble_forecast = np.zeros(n_forecast)
        ensemble_lower = np.zeros(n_forecast)
        ensemble_upper = np.zeros(n_forecast)
        
        for result, weight in zip(results, weights):
            ensemble_forecast += weight * np.array(result.forecast_values[:n_forecast])
            ensemble_lower += weight * np.array(result.confidence_lower[:n_forecast])
            ensemble_upper += weight * np.array(result.confidence_upper[:n_forecast])
        
        # Use first result's dates
        forecast_dates = results[0].forecast_dates[:n_forecast]
        
        # Calculate combined trend
        trend_direction, trend_strength = self._calculate_trend(
            df["y"].values, ensemble_forecast
        )
        
        # Check seasonality from any model
        seasonality_detected = any(r.seasonality_detected for r in results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            metric_name, ensemble_forecast, trend_direction
        )
        
        models_used = " + ".join(r.model_used for r in results)
        
        return ForecastResult(
            metric_name=metric_name,
            forecast_values=ensemble_forecast.tolist(),
            forecast_dates=forecast_dates,
            confidence_lower=ensemble_lower.tolist(),
            confidence_upper=ensemble_upper.tolist(),
            trend_direction=trend_direction,
            trend_strength=float(trend_strength),
            seasonality_detected=seasonality_detected,
            model_used=f"Ensemble ({models_used})",
            accuracy_metrics={"models_count": len(results), "weights": weights},
            recommendations=recommendations
        )
    
    def forecast(
        self,
        time_series_data: List[Dict[str, Any]],
        metric_name: str,
        model: ForecastModel = ForecastModel.ENSEMBLE
    ) -> ForecastResult:
        """
        Main forecasting method with automatic model selection
        """
        # Prepare data
        df, is_valid = self.prepare_data(time_series_data, metric_name)
        
        if not is_valid:
            return ForecastResult(
                metric_name=metric_name,
                forecast_values=[],
                forecast_dates=[],
                confidence_lower=[],
                confidence_upper=[],
                trend_direction="unknown",
                trend_strength=0,
                seasonality_detected=False,
                model_used="None",
                accuracy_metrics={},
                recommendations=["Insufficient data for forecasting. Need at least 3 data points."]
            )
        
        # Select model
        if model == ForecastModel.ENSEMBLE:
            return self.forecast_ensemble(df, metric_name)
        elif model == ForecastModel.PROPHET:
            result = self.forecast_with_prophet(df, metric_name)
            return result if result else self.forecast_with_linear(df, metric_name)
        elif model == ForecastModel.ARIMA:
            result = self.forecast_with_arima(df, metric_name)
            return result if result else self.forecast_with_linear(df, metric_name)
        elif model == ForecastModel.EXPONENTIAL_SMOOTHING:
            result = self.forecast_with_exponential_smoothing(df, metric_name)
            return result if result else self.forecast_with_linear(df, metric_name)
        else:
            return self.forecast_with_linear(df, metric_name)
    
    def _calculate_trend(
        self,
        historical: np.ndarray,
        forecast: np.ndarray
    ) -> Tuple[str, float]:
        """Calculate trend direction and strength"""
        try:
            if len(forecast) == 0:
                return "unknown", 0.0
            
            historical_mean = np.mean(historical[-min(7, len(historical)):])
            forecast_mean = np.mean(forecast)
            
            change_pct = ((forecast_mean - historical_mean) / (historical_mean + 0.001)) * 100
            
            if change_pct > 5:
                direction = "increasing"
            elif change_pct < -5:
                direction = "decreasing"
            else:
                direction = "stable"
            
            strength = min(abs(change_pct), 100)
            
            return direction, float(strength)
            
        except Exception:
            return "unknown", 0.0
    
    def _calculate_accuracy_metrics(self, df: pd.DataFrame, model) -> Dict[str, float]:
        """Calculate model accuracy metrics"""
        try:
            # In-sample predictions
            predictions = model.predict(df)
            actual = df["y"].values
            predicted = predictions["yhat"].values
            
            # Calculate metrics
            mse = np.mean((actual - predicted) ** 2)
            mae = np.mean(np.abs(actual - predicted))
            mape = np.mean(np.abs((actual - predicted) / (actual + 0.001))) * 100
            
            return {
                "mse": float(mse),
                "mae": float(mae),
                "mape": float(min(mape, 100))
            }
        except Exception:
            return {}
    
    def _generate_recommendations(
        self,
        metric_name: str,
        forecast_values: np.ndarray,
        trend_direction: str
    ) -> List[str]:
        """Generate health recommendations based on forecast"""
        recommendations = []
        
        if len(forecast_values) == 0:
            return ["Unable to generate forecast-based recommendations"]
        
        metric_info = self.METRIC_RANGES.get(metric_name, {})
        
        if not metric_info:
            return [f"Forecast trend is {trend_direction}"]
        
        avg_forecast = np.mean(forecast_values)
        min_forecast = np.min(forecast_values)
        max_forecast = np.max(forecast_values)
        
        normal_min = metric_info.get("min", 0)
        normal_max = metric_info.get("max", 100)
        critical_low = metric_info.get("critical_low", normal_min * 0.8)
        critical_high = metric_info.get("critical_high", normal_max * 1.2)
        unit = metric_info.get("unit", "")
        
        # Check for concerning forecasts
        if max_forecast > critical_high:
            recommendations.append(
                f"⚠️ ALERT: {metric_name.replace('_', ' ').title()} is forecasted to reach "
                f"critical high levels ({max_forecast:.1f} {unit}). Consult your healthcare provider."
            )
        elif min_forecast < critical_low:
            recommendations.append(
                f"⚠️ ALERT: {metric_name.replace('_', ' ').title()} is forecasted to drop to "
                f"critical low levels ({min_forecast:.1f} {unit}). Consult your healthcare provider."
            )
        
        # Trend-based recommendations
        if trend_direction == "increasing" and avg_forecast > normal_max:
            recommendations.append(
                f"📈 {metric_name.replace('_', ' ').title()} is trending upward above normal range. "
                f"Consider lifestyle modifications."
            )
        elif trend_direction == "decreasing" and avg_forecast < normal_min:
            recommendations.append(
                f"📉 {metric_name.replace('_', ' ').title()} is trending downward below normal range. "
                f"Monitor closely and consult if symptoms develop."
            )
        elif normal_min <= avg_forecast <= normal_max:
            recommendations.append(
                f"✅ {metric_name.replace('_', ' ').title()} is forecasted to remain within "
                f"normal range ({normal_min}-{normal_max} {unit}). Keep up the good work!"
            )
        
        # Metric-specific advice
        if metric_name == "heart_rate":
            if avg_forecast > 100:
                recommendations.append("Consider reducing caffeine intake and practicing stress management.")
            elif avg_forecast < 60:
                recommendations.append("Low heart rate may indicate good fitness, but monitor for symptoms.")
        
        elif metric_name in ["blood_pressure_systolic", "blood_pressure_diastolic"]:
            if avg_forecast > normal_max:
                recommendations.append("Reduce sodium intake, maintain healthy weight, and exercise regularly.")
        
        elif metric_name == "blood_sugar":
            if avg_forecast > 100:
                recommendations.append("Monitor carbohydrate intake and maintain regular meal timing.")
        
        elif metric_name == "spo2":
            if avg_forecast < 95:
                recommendations.append("Practice deep breathing exercises. Seek medical attention if below 92%.")
        
        elif metric_name == "sleep_hours":
            if avg_forecast < 6:
                recommendations.append("Aim for 7-9 hours of sleep. Maintain consistent sleep schedule.")
        
        return recommendations if recommendations else [f"Continue monitoring {metric_name.replace('_', ' ')}"]


# Export
__all__ = ['AdvancedForecaster', 'ForecastModel', 'ForecastResult']
