"""
📊 StatisticalAnalyzerTool - Advanced Data Analysis
=================================================

Highly reusable tool for statistical analysis and trend detection.
Perfect for any data analysis use case.

## Reusability
✅ Any data analysis use case
✅ Research paper analysis  
✅ Market data analysis
✅ Trend detection
✅ Performance metrics
✅ Time series analysis

## Features
- Comprehensive statistical analysis
- Trend detection and forecasting
- Outlier detection
- Correlation analysis
- Distribution analysis
- Growth rate calculations
"""

import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import math

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class StatisticalAnalyzerTool(ToolBase):
    """Advanced statistical analysis tool with trend detection and forecasting.
    
    This tool provides comprehensive statistical analysis capabilities including
    descriptive statistics, trend analysis, correlation detection, and forecasting.
    """
    
    name: str = "statistical_analyzer"
    description: str = "Advanced statistical analysis and trend detection tool"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Execute comprehensive statistical analysis.
        
        Args:
            data: Input data (list of numbers, dict with numeric values, or list of dicts)
            analysis_type: Type of analysis - 'basic', 'trend', 'correlation', 'all' (default: 'all')
            date_field: Field name for dates in time series analysis (optional)
            value_field: Field name for values in dict data (default: 'value')
            trend_window: Window size for trend analysis (default: 5)
            forecast_periods: Number of periods to forecast (default: 3)
            confidence_level: Confidence level for intervals (default: 0.95)
            
        Returns:
            Dict containing comprehensive statistical analysis results
        """
        try:
            # Extract and validate parameters
            data = kwargs.get("data")
            if not data:
                raise ValueError("Data parameter is required")
            
            analysis_type = kwargs.get("analysis_type", "all")
            date_field = kwargs.get("date_field")
            value_field = kwargs.get("value_field", "value")
            trend_window = kwargs.get("trend_window", 5)
            forecast_periods = kwargs.get("forecast_periods", 3)
            confidence_level = kwargs.get("confidence_level", 0.95)
            
            logger.info(f"Performing statistical analysis (type: {analysis_type})")
            
            # Normalize data to numeric format
            numeric_data, metadata = self._extract_numeric_data(data, value_field, date_field)
            
            if not numeric_data:
                return {
                    "error": "No numeric data found for analysis",
                    "analysis": {},
                    "timestamp": datetime.now().isoformat()
                }
            
            # Perform requested analysis
            results = {}
            
            if analysis_type in ["basic", "all"]:
                results["basic_statistics"] = self._basic_statistics(numeric_data)
            
            if analysis_type in ["trend", "all"]:
                results["trend_analysis"] = self._trend_analysis(numeric_data, trend_window)
                
            if analysis_type in ["correlation", "all"] and len(numeric_data) > 1:
                results["correlation_analysis"] = self._correlation_analysis(data, value_field)
            
            if analysis_type == "all":
                results["distribution_analysis"] = self._distribution_analysis(numeric_data)
                results["outlier_analysis"] = self._outlier_analysis(numeric_data)
                results["growth_analysis"] = self._growth_analysis(numeric_data)
                
                if forecast_periods > 0:
                    results["forecast"] = self._simple_forecast(numeric_data, forecast_periods)
            
            # Add metadata
            results["metadata"] = {
                "data_points": len(numeric_data),
                "analysis_type": analysis_type,
                "data_type": metadata["data_type"],
                "has_time_series": metadata["has_dates"],
                "parameters": {
                    "trend_window": trend_window,
                    "forecast_periods": forecast_periods,
                    "confidence_level": confidence_level
                }
            }
            
            return {
                "analysis": results,
                "summary": self._generate_summary(results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"StatisticalAnalyzerTool execution failed: {e}")
            return {
                "error": str(e),
                "analysis": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_numeric_data(self, data: Any, value_field: str, date_field: Optional[str]) -> tuple[List[float], Dict[str, Any]]:
        """Extract numeric data from various input formats."""
        numeric_data = []
        metadata = {"data_type": "unknown", "has_dates": False}
        
        if isinstance(data, list):
            if not data:
                return [], metadata
                
            # Check first element to determine data structure
            first_item = data[0]
            
            if isinstance(first_item, (int, float)):
                # Simple list of numbers
                numeric_data = [float(x) for x in data if isinstance(x, (int, float))]
                metadata["data_type"] = "numeric_list"
                
            elif isinstance(first_item, dict):
                # List of dictionaries
                for item in data:
                    if isinstance(item, dict) and value_field in item:
                        try:
                            value = float(item[value_field])
                            numeric_data.append(value)
                        except (ValueError, TypeError):
                            continue
                            
                metadata["data_type"] = "dict_list"
                metadata["has_dates"] = date_field and any(date_field in item for item in data if isinstance(item, dict))
                
        elif isinstance(data, dict):
            # Single dictionary - extract all numeric values
            for key, value in data.items():
                try:
                    numeric_data.append(float(value))
                except (ValueError, TypeError):
                    continue
            metadata["data_type"] = "single_dict"
        
        return numeric_data, metadata
    
    def _basic_statistics(self, data: List[float]) -> Dict[str, Any]:
        """Calculate basic descriptive statistics."""
        if not data:
            return {}
        
        sorted_data = sorted(data)
        n = len(data)
        
        return {
            "count": n,
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "mode": statistics.mode(data) if len(set(data)) < len(data) else None,
            "std_dev": statistics.stdev(data) if n > 1 else 0,
            "variance": statistics.variance(data) if n > 1 else 0,
            "min": min(data),
            "max": max(data),
            "range": max(data) - min(data),
            "q1": sorted_data[n//4] if n > 3 else sorted_data[0],
            "q3": sorted_data[3*n//4] if n > 3 else sorted_data[-1],
            "sum": sum(data),
            "skewness": self._calculate_skewness(data),
            "kurtosis": self._calculate_kurtosis(data)
        }
    
    def _trend_analysis(self, data: List[float], window: int) -> Dict[str, Any]:
        """Analyze trends using moving averages and regression."""
        if len(data) < window:
            return {"error": f"Insufficient data for trend analysis (need {window}, got {len(data)})"}
        
        # Moving average
        moving_avg = []
        for i in range(window - 1, len(data)):
            avg = sum(data[i-window+1:i+1]) / window
            moving_avg.append(avg)
        
        # Simple linear regression
        n = len(data)
        x_values = list(range(n))
        
        # Calculate slope and intercept
        x_mean = sum(x_values) / n
        y_mean = sum(data) / n
        
        numerator = sum((x_values[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # R-squared
        ss_res = sum((data[i] - (slope * x_values[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((data[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Trend direction
        if abs(slope) < 0.01:
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"
        
        return {
            "moving_average": moving_avg,
            "linear_regression": {
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_squared
            },
            "trend_direction": trend_direction,
            "trend_strength": abs(slope),
            "volatility": statistics.stdev(data) if len(data) > 1 else 0,
            "momentum": data[-1] - data[0] if len(data) > 1 else 0
        }
    
    def _correlation_analysis(self, data: Any, value_field: str) -> Dict[str, Any]:
        """Analyze correlations between different fields."""
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return {"error": "Correlation analysis requires list of dictionaries"}
        
        # Extract all numeric fields
        numeric_fields = {}
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    try:
                        float_val = float(value)
                        if key not in numeric_fields:
                            numeric_fields[key] = []
                        numeric_fields[key].append(float_val)
                    except (ValueError, TypeError):
                        continue
        
        # Calculate correlations between fields
        correlations = {}
        field_names = list(numeric_fields.keys())
        
        for i, field1 in enumerate(field_names):
            for field2 in field_names[i+1:]:
                if len(numeric_fields[field1]) == len(numeric_fields[field2]):
                    corr = self._calculate_correlation(numeric_fields[field1], numeric_fields[field2])
                    correlations[f"{field1}_vs_{field2}"] = corr
        
        return {
            "numeric_fields": list(numeric_fields.keys()),
            "correlations": correlations,
            "strongest_correlation": max(correlations.items(), key=lambda x: abs(x[1])) if correlations else None
        }
    
    def _distribution_analysis(self, data: List[float]) -> Dict[str, Any]:
        """Analyze the distribution of data."""
        if not data:
            return {}
        
        # Create histogram bins
        min_val, max_val = min(data), max(data)
        if min_val == max_val:
            return {"error": "All values are identical"}
        
        num_bins = min(10, len(data) // 2)  # Reasonable number of bins
        bin_width = (max_val - min_val) / num_bins
        
        bins = []
        for i in range(num_bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            count = sum(1 for x in data if bin_start <= x < bin_end)
            bins.append({
                "range": f"{bin_start:.2f}-{bin_end:.2f}",
                "count": count,
                "percentage": (count / len(data)) * 100
            })
        
        return {
            "histogram": bins,
            "is_normal_distribution": self._test_normality(data),
            "distribution_type": self._classify_distribution(data)
        }
    
    def _outlier_analysis(self, data: List[float]) -> Dict[str, Any]:
        """Detect outliers using IQR method."""
        if len(data) < 4:
            return {"error": "Insufficient data for outlier analysis"}
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        q1 = sorted_data[n//4]
        q3 = sorted_data[3*n//4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [x for x in data if x < lower_bound or x > upper_bound]
        
        return {
            "outliers": outliers,
            "outlier_count": len(outliers),
            "outlier_percentage": (len(outliers) / len(data)) * 100,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "iqr": iqr
        }
    
    def _growth_analysis(self, data: List[float]) -> Dict[str, Any]:
        """Analyze growth rates and patterns."""
        if len(data) < 2:
            return {"error": "Need at least 2 data points for growth analysis"}
        
        # Calculate period-over-period growth rates
        growth_rates = []
        for i in range(1, len(data)):
            if data[i-1] != 0:
                growth_rate = ((data[i] - data[i-1]) / data[i-1]) * 100
                growth_rates.append(growth_rate)
        
        if not growth_rates:
            return {"error": "Cannot calculate growth rates (division by zero)"}
        
        total_growth = ((data[-1] - data[0]) / data[0]) * 100 if data[0] != 0 else 0
        avg_growth = statistics.mean(growth_rates)
        
        return {
            "total_growth_percentage": total_growth,
            "average_growth_rate": avg_growth,
            "growth_rates": growth_rates,
            "growth_volatility": statistics.stdev(growth_rates) if len(growth_rates) > 1 else 0,
            "compound_annual_growth_rate": self._calculate_cagr(data) if len(data) > 1 else 0
        }
    
    def _simple_forecast(self, data: List[float], periods: int) -> Dict[str, Any]:
        """Simple forecasting using trend extrapolation."""
        if len(data) < 3:
            return {"error": "Need at least 3 data points for forecasting"}
        
        # Use linear regression for trend
        n = len(data)
        x_values = list(range(n))
        
        # Calculate slope and intercept
        x_mean = sum(x_values) / n
        y_mean = sum(data) / n
        
        numerator = sum((x_values[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Generate forecasts
        forecasts = []
        for i in range(periods):
            future_x = n + i
            forecast_value = slope * future_x + intercept
            forecasts.append(forecast_value)
        
        return {
            "forecasted_values": forecasts,
            "forecast_periods": periods,
            "trend_slope": slope,
            "confidence": "low" if abs(slope) < 0.1 else "medium" if abs(slope) < 1 else "high"
        }
    
    def _calculate_skewness(self, data: List[float]) -> float:
        """Calculate skewness of the distribution."""
        if len(data) < 3:
            return 0
        
        mean_val = statistics.mean(data)
        std_val = statistics.stdev(data)
        
        if std_val == 0:
            return 0
        
        skew = sum(((x - mean_val) / std_val) ** 3 for x in data) / len(data)
        return skew
    
    def _calculate_kurtosis(self, data: List[float]) -> float:
        """Calculate kurtosis of the distribution."""
        if len(data) < 4:
            return 0
        
        mean_val = statistics.mean(data)
        std_val = statistics.stdev(data)
        
        if std_val == 0:
            return 0
        
        kurt = sum(((x - mean_val) / std_val) ** 4 for x in data) / len(data) - 3
        return kurt
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
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
    
    def _calculate_cagr(self, data: List[float]) -> float:
        """Calculate Compound Annual Growth Rate."""
        if len(data) < 2 or data[0] <= 0:
            return 0
        
        periods = len(data) - 1
        cagr = ((data[-1] / data[0]) ** (1/periods) - 1) * 100
        return cagr
    
    def _test_normality(self, data: List[float]) -> bool:
        """Simple normality test based on skewness and kurtosis."""
        if len(data) < 8:
            return False
        
        skew = self._calculate_skewness(data)
        kurt = self._calculate_kurtosis(data)
        
        # Rough test: normal distribution has skewness ~0 and kurtosis ~0
        return abs(skew) < 1 and abs(kurt) < 1
    
    def _classify_distribution(self, data: List[float]) -> str:
        """Classify the type of distribution."""
        skew = self._calculate_skewness(data)
        kurt = self._calculate_kurtosis(data)
        
        if abs(skew) < 0.5 and abs(kurt) < 0.5:
            return "approximately_normal"
        elif skew > 1:
            return "right_skewed"
        elif skew < -1:
            return "left_skewed"
        elif kurt > 1:
            return "heavy_tailed"
        elif kurt < -1:
            return "light_tailed"
        else:
            return "unknown"
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable summary of analysis results."""
        summary = {}
        
        if "basic_statistics" in results:
            basic = results["basic_statistics"]
            summary["basic"] = f"Dataset contains {basic.get('count', 0)} points with mean {basic.get('mean', 0):.2f} and std dev {basic.get('std_dev', 0):.2f}"
        
        if "trend_analysis" in results:
            trend = results["trend_analysis"]
            direction = trend.get("trend_direction", "unknown")
            strength = trend.get("trend_strength", 0)
            summary["trend"] = f"Data shows {direction} trend with strength {strength:.3f}"
        
        if "growth_analysis" in results:
            growth = results["growth_analysis"]
            total_growth = growth.get("total_growth_percentage", 0)
            summary["growth"] = f"Total growth: {total_growth:.1f}%, Average rate: {growth.get('average_growth_rate', 0):.1f}%"
        
        if "outlier_analysis" in results:
            outliers = results["outlier_analysis"]
            count = outliers.get("outlier_count", 0)
            pct = outliers.get("outlier_percentage", 0)
            summary["outliers"] = f"Found {count} outliers ({pct:.1f}% of data)"
        
        return summary

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "data": {
                    "description": "Input data for analysis (list of numbers, dict, or list of dicts)"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["basic", "trend", "correlation", "all"],
                    "default": "all",
                    "description": "Type of analysis to perform"
                },
                "value_field": {
                    "type": "string",
                    "default": "value",
                    "description": "Field name for values in dict data"
                },
                "date_field": {
                    "type": "string", 
                    "description": "Field name for dates in time series analysis"
                },
                "trend_window": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 2,
                    "description": "Window size for moving average trend analysis"
                },
                "forecast_periods": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 0,
                    "description": "Number of periods to forecast"
                },
                "confidence_level": {
                    "type": "number",
                    "default": 0.95,
                    "minimum": 0.5,
                    "maximum": 0.99,
                    "description": "Confidence level for statistical intervals"
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
                "analysis": {
                    "type": "object",
                    "description": "Comprehensive statistical analysis results"
                },
                "summary": {
                    "type": "object",
                    "description": "Human-readable summary of key findings"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the analysis was performed"
                }
            }
        } 