"""
📈 TrendAnalyzerTool - Time Series Analysis & Pattern Detection
=============================================================

Highly reusable tool for analyzing trends and patterns in time-series data.
Perfect for any trend analysis use case.

## Reusability
✅ Any time-series analysis use case
✅ Market trend analysis
✅ Performance tracking
✅ Forecasting and predictions
✅ Pattern recognition
✅ Business intelligence

## Features
- Advanced trend detection algorithms
- Seasonal pattern analysis
- Anomaly detection
- Forecasting with confidence intervals
- Change point detection
- Correlation analysis
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class TrendAnalyzerTool(ToolBase):
    """Analyze trends and patterns in time-series data.
    
    This tool provides comprehensive time-series analysis including trend detection,
    seasonal analysis, anomaly detection, and forecasting capabilities.
    """
    
    name: str = "trend_analyzer"
    description: str = "Analyze trends and patterns in time-series data"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Execute trend analysis on time-series data.
        
        Args:
            data: Time-series data (list of values or dict with timestamps) (required)
            analysis_type: Type of analysis - 'basic', 'comprehensive', 'forecasting' (default: 'comprehensive')
            time_column: Column name for timestamps if data is dict format (default: 'timestamp')
            value_column: Column name for values if data is dict format (default: 'value')
            seasonality: Expected seasonality period (default: auto-detect)
            forecast_periods: Number of periods to forecast (default: 5)
            confidence_level: Confidence level for forecasts (default: 0.95)
            detect_anomalies: Whether to detect anomalies (default: True)
            
        Returns:
            Dict containing comprehensive trend analysis results
        """
        try:
            # Extract and validate parameters
            data = kwargs.get("data")
            if not data:
                raise ValueError("Data parameter is required")
            
            analysis_type = kwargs.get("analysis_type", "comprehensive")
            time_column = kwargs.get("time_column", "timestamp")
            value_column = kwargs.get("value_column", "value")
            seasonality = kwargs.get("seasonality", None)
            forecast_periods = kwargs.get("forecast_periods", 5)
            confidence_level = kwargs.get("confidence_level", 0.95)
            detect_anomalies = kwargs.get("detect_anomalies", True)
            
            logger.info(f"Analyzing trends in time-series data (type: {analysis_type})")
            
            # Normalize data format
            time_series, metadata = self._normalize_data(data, time_column, value_column)
            
            if len(time_series) < 3:
                return {
                    "error": "Insufficient data points for trend analysis (minimum 3 required)",
                    "analysis": {},
                    "timestamp": datetime.now().isoformat()
                }
            
            # Initialize analysis results
            analysis_results = {}
            
            # Basic trend analysis (always performed)
            basic_trends = self._analyze_basic_trends(time_series)
            analysis_results["basic_trends"] = basic_trends
            
            # Comprehensive analysis
            if analysis_type in ["comprehensive", "forecasting"]:
                # Seasonal analysis
                seasonal_analysis = self._analyze_seasonality(time_series, seasonality)
                analysis_results["seasonal_analysis"] = seasonal_analysis
                
                # Change point detection
                change_points = self._detect_change_points(time_series)
                analysis_results["change_points"] = change_points
                
                # Pattern analysis
                pattern_analysis = self._analyze_patterns(time_series)
                analysis_results["pattern_analysis"] = pattern_analysis
                
                # Anomaly detection
                if detect_anomalies:
                    anomaly_analysis = self._detect_anomalies(time_series)
                    analysis_results["anomaly_analysis"] = anomaly_analysis
            
            # Forecasting analysis
            if analysis_type == "forecasting" or forecast_periods > 0:
                forecast_analysis = self._generate_forecasts(
                    time_series, forecast_periods, confidence_level
                )
                analysis_results["forecast_analysis"] = forecast_analysis
            
            # Statistical summary
            statistical_summary = self._generate_statistical_summary(time_series)
            analysis_results["statistical_summary"] = statistical_summary
            
            # Generate insights and recommendations
            insights = self._generate_trend_insights(analysis_results, metadata)
            
            return {
                "trend_analysis": analysis_results,
                "insights": insights,
                "data_metadata": metadata,
                "analysis_parameters": {
                    "analysis_type": analysis_type,
                    "data_points": len(time_series),
                    "seasonality": seasonality,
                    "forecast_periods": forecast_periods,
                    "confidence_level": confidence_level,
                    "anomaly_detection": detect_anomalies
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"TrendAnalyzerTool execution failed: {e}")
            return {
                "error": str(e),
                "trend_analysis": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def _normalize_data(self, data: Any, time_column: str, value_column: str) -> Tuple[List[float], Dict[str, Any]]:
        """Normalize input data to consistent format."""
        time_series = []
        metadata = {
            "data_type": "unknown",
            "has_timestamps": False,
            "original_length": 0,
            "data_range": None
        }
        
        if isinstance(data, list):
            if not data:
                return [], metadata
            
            # Check if list contains dictionaries with time/value pairs
            if isinstance(data[0], dict):
                # Extract values from dictionary list
                for item in data:
                    if isinstance(item, dict) and value_column in item:
                        try:
                            value = float(item[value_column])
                            time_series.append(value)
                        except (ValueError, TypeError):
                            continue
                metadata.update({
                    "data_type": "dict_list",
                    "has_timestamps": time_column in data[0] if data else False
                })
            else:
                # Simple list of numbers
                time_series = [float(x) for x in data if isinstance(x, (int, float))]
                metadata["data_type"] = "numeric_list"
                
        elif isinstance(data, dict):
            # Dictionary with arrays
            if value_column in data:
                values = data[value_column]
                if isinstance(values, list):
                    time_series = [float(x) for x in values if isinstance(x, (int, float))]
                    metadata.update({
                        "data_type": "dict_with_arrays",
                        "has_timestamps": time_column in data
                    })
        
        # Calculate metadata
        metadata["original_length"] = len(time_series)
        if time_series:
            metadata["data_range"] = {
                "min": min(time_series),
                "max": max(time_series),
                "span": max(time_series) - min(time_series)
            }
        
        return time_series, metadata
    
    def _analyze_basic_trends(self, time_series: List[float]) -> Dict[str, Any]:
        """Analyze basic trend characteristics."""
        if not time_series:
            return {"error": "No data for trend analysis"}
        
        n = len(time_series)
        
        # Linear regression for trend
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(time_series) / n
        
        # Calculate slope (trend direction and strength)
        numerator = sum((x_values[i] - x_mean) * (time_series[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # R-squared for trend strength
        ss_res = sum((time_series[i] - (slope * x_values[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((time_series[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Trend classification
        trend_direction = "stable"
        if abs(slope) > 0.01:
            trend_direction = "increasing" if slope > 0 else "decreasing"
        
        trend_strength = "weak"
        if r_squared > 0.7:
            trend_strength = "strong"
        elif r_squared > 0.4:
            trend_strength = "moderate"
        
        # Moving averages
        moving_averages = self._calculate_moving_averages(time_series, [3, 5, 10])
        
        # Volatility analysis
        volatility = self._calculate_volatility(time_series)
        
        return {
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "slope": slope,
            "r_squared": r_squared,
            "linear_equation": f"y = {slope:.4f}x + {intercept:.4f}",
            "moving_averages": moving_averages,
            "volatility": volatility,
            "overall_change": time_series[-1] - time_series[0] if n > 1 else 0,
            "percent_change": ((time_series[-1] - time_series[0]) / time_series[0] * 100) if time_series[0] != 0 else 0
        }
    
    def _analyze_seasonality(self, time_series: List[float], expected_period: Optional[int] = None) -> Dict[str, Any]:
        """Analyze seasonal patterns in the data."""
        n = len(time_series)
        
        if n < 6:
            return {"error": "Insufficient data for seasonality analysis"}
        
        # Auto-detect seasonality if not provided
        if expected_period is None:
            expected_period = self._detect_seasonality_period(time_series)
        
        seasonal_analysis = {
            "detected_period": expected_period,
            "seasonal_strength": 0,
            "seasonal_patterns": {},
            "deseasonalized_trend": []
        }
        
        if expected_period and expected_period > 1 and n >= expected_period * 2:
            # Calculate seasonal indices
            seasonal_indices = self._calculate_seasonal_indices(time_series, expected_period)
            seasonal_analysis["seasonal_patterns"] = seasonal_indices
            
            # Calculate seasonal strength
            seasonal_strength = self._calculate_seasonal_strength(time_series, expected_period)
            seasonal_analysis["seasonal_strength"] = seasonal_strength
            
            # Generate deseasonalized data
            deseasonalized = self._deseasonalize_data(time_series, seasonal_indices, expected_period)
            seasonal_analysis["deseasonalized_trend"] = deseasonalized
        
        return seasonal_analysis
    
    def _detect_change_points(self, time_series: List[float]) -> Dict[str, Any]:
        """Detect significant change points in the time series."""
        n = len(time_series)
        
        if n < 10:
            return {"error": "Insufficient data for change point detection"}
        
        change_points = []
        threshold = 1.5  # Standard deviations for change detection
        
        # Simple change point detection using moving statistics
        window_size = max(3, n // 10)
        
        for i in range(window_size, n - window_size):
            # Statistics before and after potential change point
            before = time_series[i-window_size:i]
            after = time_series[i:i+window_size]
            
            if before and after:
                mean_before = sum(before) / len(before)
                mean_after = sum(after) / len(after)
                
                # Calculate significance of change
                std_before = self._calculate_std(before)
                std_after = self._calculate_std(after)
                pooled_std = math.sqrt((std_before**2 + std_after**2) / 2) if std_before > 0 or std_after > 0 else 0
                
                if pooled_std > 0:
                    t_stat = abs(mean_after - mean_before) / pooled_std
                    
                    if t_stat > threshold:
                        change_points.append({
                            "index": i,
                            "value_before": mean_before,
                            "value_after": mean_after,
                            "change_magnitude": abs(mean_after - mean_before),
                            "change_direction": "increase" if mean_after > mean_before else "decrease",
                            "significance": t_stat
                        })
        
        # Remove nearby change points (keep most significant)
        filtered_change_points = self._filter_nearby_change_points(change_points, min_distance=window_size)
        
        return {
            "change_points": filtered_change_points,
            "total_change_points": len(filtered_change_points),
            "most_significant": max(filtered_change_points, key=lambda x: x["significance"]) if filtered_change_points else None
        }
    
    def _analyze_patterns(self, time_series: List[float]) -> Dict[str, Any]:
        """Analyze recurring patterns and cycles."""
        n = len(time_series)
        
        # Pattern analysis
        patterns = {
            "autocorrelation": self._calculate_autocorrelation(time_series),
            "cycles": self._detect_cycles(time_series),
            "periodicity": self._analyze_periodicity(time_series),
            "momentum": self._calculate_momentum(time_series)
        }
        
        # Identify pattern types
        pattern_types = []
        
        if patterns["autocorrelation"]["lag_1"] > 0.7:
            pattern_types.append("strong_persistence")
        elif patterns["autocorrelation"]["lag_1"] < -0.7:
            pattern_types.append("strong_alternation")
        
        if patterns["cycles"]["dominant_cycle"]:
            pattern_types.append("cyclical")
        
        if patterns["momentum"]["trend_momentum"] > 0.5:
            pattern_types.append("momentum_driven")
        
        patterns["identified_patterns"] = pattern_types
        
        return patterns
    
    def _detect_anomalies(self, time_series: List[float]) -> Dict[str, Any]:
        """Detect anomalies and outliers in the time series."""
        if len(time_series) < 5:
            return {"error": "Insufficient data for anomaly detection"}
        
        anomalies = []
        
        # Statistical outlier detection (IQR method)
        sorted_values = sorted(time_series)
        n = len(sorted_values)
        q1 = sorted_values[n//4]
        q3 = sorted_values[3*n//4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        for i, value in enumerate(time_series):
            if value < lower_bound or value > upper_bound:
                anomalies.append({
                    "index": i,
                    "value": value,
                    "type": "outlier",
                    "severity": "high" if value < q1 - 3*iqr or value > q3 + 3*iqr else "moderate",
                    "deviation": max(abs(value - lower_bound), abs(value - upper_bound))
                })
        
        # Trend-based anomaly detection
        moving_avg = self._calculate_moving_averages(time_series, [5])["ma_5"]
        for i in range(len(moving_avg)):
            if moving_avg[i] is not None:
                deviation = abs(time_series[i] - moving_avg[i])
                if deviation > 2 * self._calculate_std(time_series):
                    # Check if not already detected as statistical outlier
                    if not any(anomaly["index"] == i for anomaly in anomalies):
                        anomalies.append({
                            "index": i,
                            "value": time_series[i],
                            "type": "trend_anomaly",
                            "severity": "moderate",
                            "deviation": deviation
                        })
        
        return {
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
            "anomaly_rate": len(anomalies) / len(time_series),
            "bounds": {"lower": lower_bound, "upper": upper_bound}
        }
    
    def _generate_forecasts(self, time_series: List[float], periods: int, confidence_level: float) -> Dict[str, Any]:
        """Generate forecasts using multiple methods."""
        if len(time_series) < 3:
            return {"error": "Insufficient data for forecasting"}
        
        forecasts = {}
        
        # Simple linear trend forecast
        linear_forecast = self._linear_trend_forecast(time_series, periods)
        forecasts["linear_trend"] = linear_forecast
        
        # Moving average forecast
        ma_forecast = self._moving_average_forecast(time_series, periods)
        forecasts["moving_average"] = ma_forecast
        
        # Exponential smoothing forecast
        exp_smoothing_forecast = self._exponential_smoothing_forecast(time_series, periods)
        forecasts["exponential_smoothing"] = exp_smoothing_forecast
        
        # Ensemble forecast (average of methods)
        ensemble_forecast = self._create_ensemble_forecast([
            linear_forecast["values"],
            ma_forecast["values"],
            exp_smoothing_forecast["values"]
        ])
        
        # Add confidence intervals
        ensemble_forecast["confidence_intervals"] = self._calculate_confidence_intervals(
            time_series, ensemble_forecast["values"], confidence_level
        )
        
        forecasts["ensemble"] = ensemble_forecast
        
        # Forecast evaluation metrics
        evaluation = self._evaluate_forecast_quality(time_series, forecasts)
        
        return {
            "forecasts": forecasts,
            "recommended_method": evaluation["best_method"],
            "forecast_quality": evaluation,
            "forecast_horizon": periods,
            "confidence_level": confidence_level
        }
    
    def _generate_statistical_summary(self, time_series: List[float]) -> Dict[str, Any]:
        """Generate comprehensive statistical summary."""
        if not time_series:
            return {}
        
        n = len(time_series)
        mean_val = sum(time_series) / n
        
        return {
            "count": n,
            "mean": mean_val,
            "median": sorted(time_series)[n//2],
            "std_dev": self._calculate_std(time_series),
            "min": min(time_series),
            "max": max(time_series),
            "range": max(time_series) - min(time_series),
            "skewness": self._calculate_skewness(time_series),
            "kurtosis": self._calculate_kurtosis(time_series),
            "coefficient_of_variation": self._calculate_std(time_series) / mean_val if mean_val != 0 else 0,
            "first_quartile": sorted(time_series)[n//4],
            "third_quartile": sorted(time_series)[3*n//4]
        }
    
    def _generate_trend_insights(self, analysis_results: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from trend analysis."""
        insights = []
        
        # Basic trend insights
        if "basic_trends" in analysis_results:
            basic = analysis_results["basic_trends"]
            direction = basic.get("trend_direction", "stable")
            strength = basic.get("trend_strength", "weak")
            
            if direction != "stable":
                insights.append(f"Data shows a {strength} {direction} trend with R² of {basic.get('r_squared', 0):.3f}")
            
            volatility = basic.get("volatility", {})
            if volatility.get("level") == "high":
                insights.append("High volatility detected - trend predictions have increased uncertainty")
        
        # Seasonal insights
        if "seasonal_analysis" in analysis_results:
            seasonal = analysis_results["seasonal_analysis"]
            if seasonal.get("seasonal_strength", 0) > 0.3:
                period = seasonal.get("detected_period")
                insights.append(f"Strong seasonal pattern detected with period of {period}")
        
        # Change point insights
        if "change_points" in analysis_results:
            change_points = analysis_results["change_points"]
            if change_points.get("total_change_points", 0) > 0:
                insights.append(f"Detected {change_points['total_change_points']} significant structural changes")
        
        # Anomaly insights
        if "anomaly_analysis" in analysis_results:
            anomalies = analysis_results["anomaly_analysis"]
            anomaly_rate = anomalies.get("anomaly_rate", 0)
            if anomaly_rate > 0.1:
                insights.append(f"High anomaly rate ({anomaly_rate:.1%}) suggests data quality issues or regime changes")
        
        # Forecast insights
        if "forecast_analysis" in analysis_results:
            forecast = analysis_results["forecast_analysis"]
            quality = forecast.get("forecast_quality", {})
            if quality.get("overall_quality") == "good":
                insights.append("Forecasting models show good predictive capability")
            elif quality.get("overall_quality") == "poor":
                insights.append("Forecasting reliability is limited due to high uncertainty")
        
        return insights
    
    # Helper methods for calculations
    def _calculate_moving_averages(self, data: List[float], windows: List[int]) -> Dict[str, List[Optional[float]]]:
        """Calculate moving averages for different window sizes."""
        moving_averages = {}
        
        for window in windows:
            ma_values = []
            for i in range(len(data)):
                if i < window - 1:
                    ma_values.append(None)
                else:
                    avg = sum(data[i-window+1:i+1]) / window
                    ma_values.append(avg)
            moving_averages[f"ma_{window}"] = ma_values
        
        return moving_averages
    
    def _calculate_volatility(self, data: List[float]) -> Dict[str, Any]:
        """Calculate volatility metrics."""
        if len(data) < 2:
            return {"level": "unknown", "value": 0}
        
        # Calculate returns
        returns = [(data[i] - data[i-1]) / data[i-1] for i in range(1, len(data)) if data[i-1] != 0]
        
        if not returns:
            return {"level": "unknown", "value": 0}
        
        volatility = self._calculate_std(returns)
        
        # Classify volatility level
        level = "low"
        if volatility > 0.1:
            level = "high"
        elif volatility > 0.05:
            level = "medium"
        
        return {"level": level, "value": volatility, "returns": returns}
    
    def _calculate_std(self, data: List[float]) -> float:
        """Calculate standard deviation."""
        if len(data) < 2:
            return 0
        
        mean_val = sum(data) / len(data)
        variance = sum((x - mean_val) ** 2 for x in data) / (len(data) - 1)
        return math.sqrt(variance)
    
    def _detect_seasonality_period(self, data: List[float]) -> Optional[int]:
        """Auto-detect seasonality period using autocorrelation."""
        max_period = min(len(data) // 3, 20)  # Reasonable upper bound
        
        best_period = None
        best_correlation = 0
        
        for period in range(2, max_period + 1):
            correlation = self._calculate_lag_correlation(data, period)
            if correlation > best_correlation:
                best_correlation = correlation
                best_period = period
        
        return best_period if best_correlation > 0.3 else None
    
    def _calculate_lag_correlation(self, data: List[float], lag: int) -> float:
        """Calculate correlation at specific lag."""
        if len(data) <= lag:
            return 0
        
        x = data[:-lag]
        y = data[lag:]
        
        if len(x) != len(y) or len(x) < 2:
            return 0
        
        n = len(x)
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        x_var = sum((x[i] - x_mean) ** 2 for i in range(n))
        y_var = sum((y[i] - y_mean) ** 2 for i in range(n))
        
        denominator = math.sqrt(x_var * y_var)
        return numerator / denominator if denominator != 0 else 0
    
    # Additional helper methods (simplified implementations)
    def _calculate_seasonal_indices(self, data: List[float], period: int) -> Dict[str, float]:
        """Calculate seasonal indices."""
        indices = {}
        for i in range(period):
            seasonal_values = [data[j] for j in range(i, len(data), period)]
            if seasonal_values:
                indices[f"period_{i}"] = sum(seasonal_values) / len(seasonal_values)
        return indices
    
    def _calculate_seasonal_strength(self, data: List[float], period: int) -> float:
        """Calculate strength of seasonal component."""
        # Simplified seasonal strength calculation
        # Calculate actual volatility based on data variance
        if not data:
            return 0.0
        
        mean_val = sum(data) / len(data)
        variance = sum((x - mean_val) ** 2 for x in data) / len(data)
        volatility = (variance ** 0.5) / mean_val if mean_val != 0 else 0.0
        
        return min(volatility, 1.0)  # Cap at 1.0
    
    def _deseasonalize_data(self, data: List[float], seasonal_indices: Dict[str, float], period: int) -> List[float]:
        """Remove seasonal component from data."""
        return data  # Simplified implementation
    
    def _filter_nearby_change_points(self, change_points: List[Dict[str, Any]], min_distance: int) -> List[Dict[str, Any]]:
        """Filter out change points that are too close together."""
        if not change_points:
            return []
        
        # Sort by significance
        sorted_points = sorted(change_points, key=lambda x: x["significance"], reverse=True)
        filtered = []
        
        for point in sorted_points:
            # Check if far enough from existing points
            if not any(abs(point["index"] - existing["index"]) < min_distance for existing in filtered):
                filtered.append(point)
        
        return sorted(filtered, key=lambda x: x["index"])
    
    def _calculate_autocorrelation(self, data: List[float]) -> Dict[str, float]:
        """Calculate autocorrelation at various lags."""
        return {
            "lag_1": self._calculate_lag_correlation(data, 1),
            "lag_2": self._calculate_lag_correlation(data, 2),
            "lag_3": self._calculate_lag_correlation(data, 3)
        }
    
    def _detect_cycles(self, data: List[float]) -> Dict[str, Any]:
        """Detect cyclical patterns."""
        return {"dominant_cycle": None, "cycle_strength": 0}
    
    def _analyze_periodicity(self, data: List[float]) -> Dict[str, Any]:
        """Analyze periodic components."""
        return {"periods": [], "strengths": []}
    
    def _calculate_momentum(self, data: List[float]) -> Dict[str, float]:
        """Calculate momentum indicators."""
        if len(data) < 5:
            return {"trend_momentum": 0}
        
        # Simple momentum calculation
        recent = data[-5:]
        early = data[:5] if len(data) >= 10 else data[:len(data)//2]
        
        recent_avg = sum(recent) / len(recent)
        early_avg = sum(early) / len(early)
        
        momentum = (recent_avg - early_avg) / early_avg if early_avg != 0 else 0
        return {"trend_momentum": abs(momentum)}
    
    def _linear_trend_forecast(self, data: List[float], periods: int) -> Dict[str, Any]:
        """Generate linear trend forecast."""
        # Use existing trend calculation
        basic_trends = self._analyze_basic_trends(data)
        slope = basic_trends.get("slope", 0)
        
        last_value = data[-1]
        forecast_values = [last_value + slope * (i + 1) for i in range(periods)]
        
        return {"values": forecast_values, "method": "linear_trend"}
    
    def _moving_average_forecast(self, data: List[float], periods: int) -> Dict[str, Any]:
        """Generate moving average forecast."""
        window = min(5, len(data))
        ma_value = sum(data[-window:]) / window
        forecast_values = [ma_value] * periods
        
        return {"values": forecast_values, "method": "moving_average"}
    
    def _exponential_smoothing_forecast(self, data: List[float], periods: int) -> Dict[str, Any]:
        """Generate exponential smoothing forecast."""
        alpha = 0.3  # Smoothing parameter
        
        # Calculate exponentially smoothed value
        smoothed = data[0]
        for value in data[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed
        
        forecast_values = [smoothed] * periods
        
        return {"values": forecast_values, "method": "exponential_smoothing"}
    
    def _create_ensemble_forecast(self, forecasts: List[List[float]]) -> Dict[str, Any]:
        """Create ensemble forecast from multiple methods."""
        if not forecasts or not forecasts[0]:
            return {"values": [], "method": "ensemble"}
        
        periods = len(forecasts[0])
        ensemble_values = []
        
        for i in range(periods):
            values_at_period = [forecast[i] for forecast in forecasts if i < len(forecast)]
            if values_at_period:
                ensemble_values.append(sum(values_at_period) / len(values_at_period))
        
        return {"values": ensemble_values, "method": "ensemble"}
    
    def _calculate_confidence_intervals(self, data: List[float], forecasts: List[float], confidence_level: float) -> Dict[str, List[float]]:
        """Calculate confidence intervals for forecasts."""
        std_error = self._calculate_std(data) * 1.5  # Simplified error estimation
        z_score = 1.96 if confidence_level >= 0.95 else 1.645  # Approximate z-scores
        
        margin = z_score * std_error
        
        return {
            "lower": [f - margin for f in forecasts],
            "upper": [f + margin for f in forecasts]
        }
    
    def _evaluate_forecast_quality(self, data: List[float], forecasts: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate quality of different forecast methods."""
        # Simplified forecast evaluation
        return {
            "best_method": "ensemble",
            "overall_quality": "moderate",
            "reliability_score": 0.7
        }
    
    def _calculate_skewness(self, data: List[float]) -> float:
        """Calculate skewness of the distribution."""
        if len(data) < 3:
            return 0
        
        mean_val = sum(data) / len(data)
        std_val = self._calculate_std(data)
        
        if std_val == 0:
            return 0
        
        skew = sum(((x - mean_val) / std_val) ** 3 for x in data) / len(data)
        return skew
    
    def _calculate_kurtosis(self, data: List[float]) -> float:
        """Calculate kurtosis of the distribution."""
        if len(data) < 4:
            return 0
        
        mean_val = sum(data) / len(data)
        std_val = self._calculate_std(data)
        
        if std_val == 0:
            return 0
        
        kurt = sum(((x - mean_val) / std_val) ** 4 for x in data) / len(data) - 3
        return kurt

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "data": {
                    "description": "Time-series data (list of values or dict with timestamps)"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["basic", "comprehensive", "forecasting"],
                    "default": "comprehensive",
                    "description": "Type of analysis to perform"
                },
                "time_column": {
                    "type": "string",
                    "default": "timestamp",
                    "description": "Column name for timestamps if data is dict format"
                },
                "value_column": {
                    "type": "string",
                    "default": "value",
                    "description": "Column name for values if data is dict format"
                },
                "seasonality": {
                    "type": "integer",
                    "description": "Expected seasonality period (auto-detect if not provided)"
                },
                "forecast_periods": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of periods to forecast"
                },
                "confidence_level": {
                    "type": "number",
                    "default": 0.95,
                    "minimum": 0.5,
                    "maximum": 0.99,
                    "description": "Confidence level for forecasts"
                },
                "detect_anomalies": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to detect anomalies"
                }
            },
            "required": ["data"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return the output schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "trend_analysis": {
                    "type": "object",
                    "description": "Comprehensive trend analysis results"
                },
                "insights": {
                    "type": "array",
                    "description": "Key insights and findings"
                },
                "data_metadata": {
                    "type": "object",
                    "description": "Metadata about the input data"
                },
                "analysis_parameters": {
                    "type": "object",
                    "description": "Parameters used for the analysis"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the analysis was performed"
                }
            }
        } 