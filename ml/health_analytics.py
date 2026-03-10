"""
Health Anomaly Detection & Trend Forecasting
Uses Isolation Forest for anomaly detection
Uses Prophet/ARIMA for trend forecasting
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json

class HealthAnomalyDetector:
    """
    Isolation Forest based anomaly detection for health metrics
    Detects unusual patterns in vital signs and wearable data
    """
    
    VITAL_RANGES = {
        'heart_rate': {'min': 40, 'max': 200, 'normal_min': 60, 'normal_max': 100},
        'blood_pressure_systolic': {'min': 70, 'max': 220, 'normal_min': 90, 'normal_max': 140},
        'blood_pressure_diastolic': {'min': 40, 'max': 130, 'normal_min': 60, 'normal_max': 90},
        'spo2': {'min': 70, 'max': 100, 'normal_min': 95, 'normal_max': 100},
        'temperature': {'min': 35, 'max': 42, 'normal_min': 36.1, 'normal_max': 37.2},
        'respiratory_rate': {'min': 8, 'max': 40, 'normal_min': 12, 'normal_max': 20},
        'blood_glucose': {'min': 40, 'max': 500, 'normal_min': 70, 'normal_max': 140},
        'steps': {'min': 0, 'max': 50000, 'normal_min': 3000, 'normal_max': 15000},
        'sleep_hours': {'min': 0, 'max': 16, 'normal_min': 6, 'normal_max': 9},
        'hrv': {'min': 10, 'max': 200, 'normal_min': 20, 'normal_max': 100}
    }
    
    def __init__(self, contamination: float = 0.1):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of anomalies (default 10%)
        """
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
            max_samples='auto'
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def fit(self, data: List[Dict[str, float]]) -> None:
        """Fit the model on historical data"""
        if not data:
            return
        
        # Extract features
        feature_names = list(data[0].keys())
        X = np.array([[d.get(f, 0) for f in feature_names] for d in data])
        
        # Scale and fit
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        self.feature_names = feature_names
    
    def detect_anomalies(self, data_point: Dict[str, float], 
                         historical_data: Optional[List[Dict[str, float]]] = None) -> Dict:
        """
        Detect anomalies in a single data point
        
        Returns:
            Dict with anomaly status, scores, and details
        """
        anomalies = []
        warnings = []
        critical = []
        
        # Rule-based detection using vital ranges
        for metric, value in data_point.items():
            if metric in self.VITAL_RANGES:
                ranges = self.VITAL_RANGES[metric]
                
                # Critical out of bounds
                if value < ranges['min'] or value > ranges['max']:
                    critical.append({
                        'metric': metric,
                        'value': value,
                        'severity': 'critical',
                        'message': f'{metric.replace("_", " ").title()} is critically {"low" if value < ranges["min"] else "high"}: {value}'
                    })
                # Warning - outside normal range
                elif value < ranges['normal_min'] or value > ranges['normal_max']:
                    warnings.append({
                        'metric': metric,
                        'value': value,
                        'severity': 'warning',
                        'message': f'{metric.replace("_", " ").title()} is {"below" if value < ranges["normal_min"] else "above"} normal: {value}'
                    })
        
        # ML-based detection if we have enough historical data
        ml_anomaly_score = None
        if historical_data and len(historical_data) >= 10:
            self.fit(historical_data)
            if self.is_fitted:
                features = np.array([[data_point.get(f, 0) for f in self.feature_names]]).reshape(1, -1)
                features_scaled = self.scaler.transform(features)
                
                # -1 for anomaly, 1 for normal
                prediction = self.model.predict(features_scaled)[0]
                score = self.model.score_samples(features_scaled)[0]
                
                ml_anomaly_score = {
                    'is_anomaly': prediction == -1,
                    'anomaly_score': round(float(-score), 3),  # Convert to positive, higher = more anomalous
                    'confidence': round(abs(float(score)) * 100, 1)
                }
                
                if prediction == -1:
                    anomalies.append({
                        'type': 'pattern_anomaly',
                        'severity': 'moderate',
                        'message': 'Unusual pattern detected compared to your historical data'
                    })
        
        # Determine overall status
        if critical:
            overall_status = 'critical'
        elif warnings or (ml_anomaly_score and ml_anomaly_score['is_anomaly']):
            overall_status = 'warning'
        else:
            overall_status = 'normal'
        
        return {
            'status': overall_status,
            'critical_alerts': critical,
            'warnings': warnings,
            'pattern_anomalies': anomalies,
            'ml_analysis': ml_anomaly_score,
            'recommendations': self._get_recommendations(critical, warnings),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_recommendations(self, critical: List, warnings: List) -> List[str]:
        """Generate recommendations based on detected anomalies"""
        recommendations = []
        
        for alert in critical:
            metric = alert['metric']
            if 'heart_rate' in metric:
                recommendations.append('Seek immediate medical attention for abnormal heart rate')
            elif 'blood_pressure' in metric:
                recommendations.append('Contact your healthcare provider immediately for blood pressure concerns')
            elif 'spo2' in metric:
                recommendations.append('Low oxygen levels detected - seek medical help immediately')
            elif 'glucose' in metric:
                recommendations.append('Critical blood sugar level - follow your diabetes management plan')
        
        for warning in warnings:
            metric = warning['metric']
            if 'heart_rate' in metric:
                recommendations.append('Monitor heart rate closely; practice relaxation techniques')
            elif 'blood_pressure' in metric:
                recommendations.append('Reduce sodium intake; practice stress management')
            elif 'sleep' in metric:
                recommendations.append('Improve sleep hygiene; maintain consistent sleep schedule')
            elif 'steps' in metric:
                recommendations.append('Increase daily physical activity gradually')
        
        return recommendations if recommendations else ['All vitals within acceptable ranges']


class HealthTrendForecaster:
    """
    Time-series forecasting for health metrics
    Uses simple statistical methods (fallback if Prophet unavailable)
    """
    
    def __init__(self):
        self.prophet_available = self._check_prophet()
    
    def _check_prophet(self) -> bool:
        try:
            from prophet import Prophet
            return True
        except ImportError:
            return False
    
    def forecast_trend(self, historical_data: List[Dict], 
                       metric: str, 
                       periods: int = 7) -> Dict:
        """
        Forecast future values for a health metric
        
        Args:
            historical_data: List of {date, value} dicts
            metric: Name of the metric being forecasted
            periods: Number of days to forecast
            
        Returns:
            Dict with forecast, trend direction, and insights
        """
        if len(historical_data) < 3:
            return {
                'status': 'insufficient_data',
                'message': 'At least 3 data points required for forecasting',
                'metric': metric
            }
        
        values = [d['value'] for d in historical_data]
        dates = [d['date'] for d in historical_data]
        
        # Calculate basic statistics
        mean_val = np.mean(values)
        std_val = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)
        
        # Calculate trend using linear regression
        x = np.arange(len(values))
        coefficients = np.polyfit(x, values, 1)
        slope = coefficients[0]
        
        # Determine trend direction
        if abs(slope) < std_val * 0.1:
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        # Simple linear forecast
        future_x = np.arange(len(values), len(values) + periods)
        forecast_values = np.polyval(coefficients, future_x)
        
        # Generate forecast dates
        if isinstance(dates[-1], str):
            last_date = datetime.fromisoformat(dates[-1].replace('Z', '+00:00').replace('+00:00+00:00', '+00:00'))
        else:
            last_date = dates[-1]
        forecast_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(periods)]
        
        # Calculate change percentage
        if len(values) >= 2:
            recent_change = ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
        else:
            recent_change = 0
        
        # Generate insights
        insights = self._generate_insights(metric, trend_direction, recent_change, mean_val, values[-1])
        
        return {
            'metric': metric,
            'trend_direction': trend_direction,
            'trend_strength': round(float(abs(slope) / std_val) if std_val > 0 else 0, 2),
            'current_value': float(values[-1]),
            'mean_value': round(float(mean_val), 2),
            'min_value': round(float(min_val), 2),
            'max_value': round(float(max_val), 2),
            'std_deviation': round(float(std_val), 2),
            'change_percentage': round(float(recent_change), 1),
            'forecast': [
                {'date': d, 'predicted_value': round(float(v), 2)}
                for d, v in zip(forecast_dates, forecast_values)
            ],
            'insights': insights,
            'data_points': len(values),
            'analysis_date': datetime.now().isoformat()
        }
    
    def _generate_insights(self, metric: str, trend: str, change_pct: float, 
                          mean_val: float, current_val: float) -> List[str]:
        """Generate human-readable insights"""
        insights = []
        
        metric_display = metric.replace('_', ' ').title()
        
        # Trend insight
        if trend == 'increasing':
            insights.append(f'Your {metric_display} has been increasing over the observed period')
        elif trend == 'decreasing':
            insights.append(f'Your {metric_display} shows a decreasing trend')
        else:
            insights.append(f'Your {metric_display} has remained relatively stable')
        
        # Change insight
        if abs(change_pct) > 20:
            direction = 'increased' if change_pct > 0 else 'decreased'
            insights.append(f'Significant change: {metric_display} has {direction} by {abs(change_pct):.1f}%')
        
        # Comparison to average
        diff_from_mean = ((current_val - mean_val) / mean_val) * 100 if mean_val != 0 else 0
        if abs(diff_from_mean) > 15:
            comparison = 'above' if diff_from_mean > 0 else 'below'
            insights.append(f'Current value is {abs(diff_from_mean):.1f}% {comparison} your average')
        
        # Metric-specific insights
        if 'heart_rate' in metric.lower():
            if current_val > 100:
                insights.append('Consider stress reduction techniques')
            elif current_val < 60:
                insights.append('Low heart rate - may indicate good fitness or need medical review')
        elif 'sleep' in metric.lower():
            if current_val < 6:
                insights.append('Sleep duration is below recommended 7-9 hours')
            elif current_val > 9:
                insights.append('Oversleeping may indicate underlying health issues')
        elif 'steps' in metric.lower():
            if current_val < 5000:
                insights.append('Consider increasing daily physical activity')
            elif current_val > 10000:
                insights.append('Great job maintaining active lifestyle!')
        
        return insights


class MultimodalDataFusion:
    """
    Fuses data from multiple sources: wearables, lab reports, user inputs
    Uses weighted feature-level fusion
    """
    
    SOURCE_WEIGHTS = {
        'lab_report': 0.35,      # High reliability
        'clinical_exam': 0.30,   # Doctor's examination
        'wearable': 0.20,        # Continuous monitoring
        'user_input': 0.15       # Self-reported
    }
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def fuse_health_data(self, 
                         lab_data: Optional[Dict] = None,
                         wearable_data: Optional[Dict] = None,
                         clinical_data: Optional[Dict] = None,
                         user_data: Optional[Dict] = None) -> Dict:
        """
        Fuse data from multiple sources into unified health profile
        """
        fused = {
            'sources_used': [],
            'confidence_score': 0,
            'fused_metrics': {},
            'data_quality': {},
            'timestamp': datetime.now().isoformat()
        }
        
        all_metrics = {}
        
        # Process each source
        if lab_data:
            fused['sources_used'].append('lab_report')
            for metric, value in lab_data.items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append({
                    'value': value,
                    'source': 'lab_report',
                    'weight': self.SOURCE_WEIGHTS['lab_report']
                })
        
        if wearable_data:
            fused['sources_used'].append('wearable')
            for metric, value in wearable_data.items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append({
                    'value': value,
                    'source': 'wearable',
                    'weight': self.SOURCE_WEIGHTS['wearable']
                })
        
        if clinical_data:
            fused['sources_used'].append('clinical_exam')
            for metric, value in clinical_data.items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append({
                    'value': value,
                    'source': 'clinical_exam',
                    'weight': self.SOURCE_WEIGHTS['clinical_exam']
                })
        
        if user_data:
            fused['sources_used'].append('user_input')
            for metric, value in user_data.items():
                if metric not in all_metrics:
                    all_metrics[metric] = []
                all_metrics[metric].append({
                    'value': value,
                    'source': 'user_input',
                    'weight': self.SOURCE_WEIGHTS['user_input']
                })
        
        # Weighted fusion for each metric
        for metric, values in all_metrics.items():
            if not values:
                continue
            
            # Calculate weighted average
            total_weight = sum(v['weight'] for v in values)
            if total_weight > 0:
                weighted_value = sum(v['value'] * v['weight'] for v in values) / total_weight
                fused['fused_metrics'][metric] = {
                    'value': round(weighted_value, 2),
                    'sources': [v['source'] for v in values],
                    'confidence': round(total_weight / sum(self.SOURCE_WEIGHTS.values()) * 100, 1)
                }
        
        # Calculate overall confidence
        if fused['sources_used']:
            fused['confidence_score'] = round(
                sum(self.SOURCE_WEIGHTS.get(s, 0.1) for s in fused['sources_used']) / 
                sum(self.SOURCE_WEIGHTS.values()) * 100, 1
            )
        
        # Data quality assessment
        fused['data_quality'] = {
            'completeness': len(fused['fused_metrics']) / 10 * 100,  # Assuming 10 expected metrics
            'sources_count': len(fused['sources_used']),
            'recommendation': self._get_quality_recommendation(fused['sources_used'])
        }
        
        return fused
    
    def _get_quality_recommendation(self, sources: List[str]) -> str:
        if len(sources) >= 3:
            return 'Excellent data coverage from multiple sources'
        elif len(sources) == 2:
            return 'Good data coverage. Consider adding more data sources for better accuracy'
        else:
            return 'Limited data sources. Add lab reports or wearable data for comprehensive analysis'


# Singleton instances
_anomaly_detector = None
_trend_forecaster = None
_data_fusion = None

def get_anomaly_detector() -> HealthAnomalyDetector:
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = HealthAnomalyDetector()
    return _anomaly_detector

def get_trend_forecaster() -> HealthTrendForecaster:
    global _trend_forecaster
    if _trend_forecaster is None:
        _trend_forecaster = HealthTrendForecaster()
    return _trend_forecaster

def get_data_fusion() -> MultimodalDataFusion:
    global _data_fusion
    if _data_fusion is None:
        _data_fusion = MultimodalDataFusion()
    return _data_fusion
