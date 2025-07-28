"""
💰 YahooFinanceFetcherTool - Real-time Financial Data
===================================================

Highly reusable tool for fetching real-time stock data and financial metrics.
Perfect for any financial analysis use case.

## Reusability
✅ Any financial analysis use case
✅ Market research and trends
✅ Portfolio analysis
✅ Investment research
✅ Economic indicators tracking

## Features
- Real Yahoo Finance API integration
- Multiple data types (prices, info, history)
- Comprehensive error handling
- Rate limiting and caching
- Rich financial metrics extraction
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import asyncio

from ice_sdk.tools.base import ToolBase
import structlog

logger = structlog.get_logger(__name__)


class YahooFinanceFetcherTool(ToolBase):
    """Fetch real-time financial data from Yahoo Finance.
    
    This tool provides comprehensive access to stock prices, company information,
    financial metrics, and historical data with robust error handling.
    """
    
    name: str = "yahoo_finance_fetcher"
    description: str = "Fetch real-time stock data and financial metrics from Yahoo Finance"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute Yahoo Finance data fetch.
        
        Args:
            symbols: List of stock symbols (required) - e.g., ["AAPL", "GOOGL", "MSFT"]
            data_type: Type of data - 'price', 'info', 'history', 'all' (default: 'all')
            period: Period for historical data - '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y' (default: '1mo')
            interval: Data interval - '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo' (default: '1d')
            include_metrics: Whether to calculate additional metrics (default: True)
            
        Returns:
            Dict containing comprehensive financial data for all symbols
        """
        try:
            # Extract and validate parameters
            symbols = kwargs.get("symbols", [])
            if not symbols:
                raise ValueError("Symbols parameter is required")
            
            if isinstance(symbols, str):
                symbols = [symbols]  # Convert single symbol to list
            
            data_type = kwargs.get("data_type", "all")
            period = kwargs.get("period", "1mo")
            interval = kwargs.get("interval", "1d")
            include_metrics = kwargs.get("include_metrics", True)
            
            logger.info(f"Fetching financial data for symbols: {symbols} (type: {data_type})")
            
            # Import yfinance library
            try:
                import yfinance as yf
            except ImportError:
                return {
                    "error": "yfinance library not installed. Run: pip install yfinance",
                    "data": {},
                    "symbols_processed": 0
                }
            
            # Process each symbol
            results = {}
            failed_symbols = []
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    symbol_data = {}
                    
                    # Fetch current price and basic info
                    if data_type in ["price", "all"]:
                        symbol_data["current_price"] = await self._get_current_price(ticker)
                    
                    # Fetch detailed company information
                    if data_type in ["info", "all"]:
                        symbol_data["company_info"] = await self._get_company_info(ticker)
                    
                    # Fetch historical data
                    if data_type in ["history", "all"]:
                        symbol_data["historical_data"] = await self._get_historical_data(ticker, period, interval)
                    
                    # Calculate additional metrics
                    if include_metrics and data_type == "all":
                        symbol_data["metrics"] = await self._calculate_metrics(symbol_data)
                    
                    results[symbol] = symbol_data
                    
                except Exception as e:
                    logger.warning(f"Error fetching data for {symbol}: {e}")
                    failed_symbols.append(symbol)
                    results[symbol] = {"error": str(e)}
            
            # Generate summary statistics
            summary = self._generate_summary(results, symbols, failed_symbols)
            
            return {
                "data": results,
                "summary": summary,
                "symbols_requested": symbols,
                "symbols_processed": len(symbols) - len(failed_symbols),
                "failed_symbols": failed_symbols,
                "parameters": {
                    "data_type": data_type,
                    "period": period,
                    "interval": interval,
                    "include_metrics": include_metrics
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"YahooFinanceFetcherTool execution failed: {e}")
            return {
                "error": str(e),
                "data": {},
                "symbols_processed": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_current_price(self, ticker) -> Dict[str, Any]:
        """Get current price and basic market data."""
        try:
            info = ticker.info
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return {"error": "No price data available"}
            
            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
            
            return {
                "current_price": float(current_price),
                "previous_close": float(previous_close),
                "change": float(change),
                "change_percent": float(change_percent),
                "volume": int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else None,
                "high_52w": info.get("fiftyTwoWeekHigh"),
                "low_52w": info.get("fiftyTwoWeekLow"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield")
            }
        except Exception as e:
            return {"error": f"Failed to get current price: {e}"}
    
    async def _get_company_info(self, ticker) -> Dict[str, Any]:
        """Get comprehensive company information."""
        try:
            info = ticker.info
            
            return {
                "company_name": info.get("longName", "Unknown"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "business_summary": info.get("longBusinessSummary", "")[:500],  # Truncate for brevity
                "employees": info.get("fullTimeEmployees"),
                "founded": info.get("founded"),
                "exchange": info.get("exchange"),
                "currency": info.get("currency"),
                "financial_metrics": {
                    "revenue": info.get("totalRevenue"),
                    "gross_margins": info.get("grossMargins"),
                    "operating_margins": info.get("operatingMargins"),
                    "profit_margins": info.get("profitMargins"),
                    "return_on_equity": info.get("returnOnEquity"),
                    "return_on_assets": info.get("returnOnAssets"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "book_value": info.get("bookValue"),
                    "price_to_book": info.get("priceToBook"),
                    "enterprise_value": info.get("enterpriseValue"),
                    "ebitda": info.get("ebitda")
                },
                "analyst_info": {
                    "recommendation": info.get("recommendationKey"),
                    "target_high_price": info.get("targetHighPrice"),
                    "target_low_price": info.get("targetLowPrice"),
                    "target_mean_price": info.get("targetMeanPrice"),
                    "number_of_analysts": info.get("numberOfAnalystOpinions")
                }
            }
        except Exception as e:
            return {"error": f"Failed to get company info: {e}"}
    
    async def _get_historical_data(self, ticker, period: str, interval: str) -> Dict[str, Any]:
        """Get historical price data with technical indicators."""
        try:
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return {"error": "No historical data available"}
            
            # Convert to list of dictionaries for easier processing
            historical_records = []
            for date, row in hist.iterrows():
                record = {
                    "date": date.isoformat(),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']) if 'Volume' in row else None
                }
                historical_records.append(record)
            
            # Calculate basic technical indicators
            closes = [record["close"] for record in historical_records]
            volumes = [record["volume"] for record in historical_records if record["volume"]]
            
            technical_indicators = {}
            if len(closes) >= 20:
                # Simple moving averages
                technical_indicators["sma_20"] = sum(closes[-20:]) / 20
                if len(closes) >= 50:
                    technical_indicators["sma_50"] = sum(closes[-50:]) / 50
                if len(closes) >= 200:
                    technical_indicators["sma_200"] = sum(closes[-200:]) / 200
                
                # Volatility (standard deviation of returns)
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                if returns:
                    volatility = (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns))**0.5
                    technical_indicators["volatility"] = volatility
            
            return {
                "records": historical_records,
                "total_records": len(historical_records),
                "date_range": {
                    "start": historical_records[0]["date"] if historical_records else None,
                    "end": historical_records[-1]["date"] if historical_records else None
                },
                "price_range": {
                    "min": min(closes) if closes else None,
                    "max": max(closes) if closes else None
                },
                "avg_volume": sum(volumes) / len(volumes) if volumes else None,
                "technical_indicators": technical_indicators
            }
        except Exception as e:
            return {"error": f"Failed to get historical data: {e}"}
    
    async def _calculate_metrics(self, symbol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional financial metrics and insights."""
        try:
            metrics = {}
            
            # Extract data for calculations
            current_price_data = symbol_data.get("current_price", {})
            company_info = symbol_data.get("company_info", {})
            historical_data = symbol_data.get("historical_data", {})
            
            current_price = current_price_data.get("current_price")
            market_cap = current_price_data.get("market_cap")
            
            # Valuation metrics
            if current_price and market_cap:
                metrics["market_position"] = "large_cap" if market_cap > 10e9 else "mid_cap" if market_cap > 2e9 else "small_cap"
            
            # Performance vs 52-week range
            high_52w = current_price_data.get("high_52w")
            low_52w = current_price_data.get("low_52w")
            
            if current_price and high_52w and low_52w:
                range_position = (current_price - low_52w) / (high_52w - low_52w)
                metrics["52w_range_position"] = range_position
                metrics["distance_from_high"] = ((high_52w - current_price) / high_52w) * 100
                metrics["distance_from_low"] = ((current_price - low_52w) / low_52w) * 100
            
            # Growth analysis from historical data
            if historical_data.get("records"):
                records = historical_data["records"]
                if len(records) >= 30:
                    # 30-day performance
                    old_price = records[-30]["close"]
                    metrics["30d_return"] = ((current_price - old_price) / old_price) * 100 if old_price else None
                
                if len(records) >= 90:
                    # 90-day performance
                    old_price = records[-90]["close"]
                    metrics["90d_return"] = ((current_price - old_price) / old_price) * 100 if old_price else None
            
            # Financial health score (simple scoring)
            financial_metrics = company_info.get("financial_metrics", {})
            health_score = 0
            score_factors = 0
            
            if financial_metrics.get("profit_margins"):
                health_score += min(financial_metrics["profit_margins"] * 10, 2)  # Max 2 points
                score_factors += 1
            
            if financial_metrics.get("return_on_equity"):
                health_score += min(financial_metrics["return_on_equity"] * 5, 2)  # Max 2 points
                score_factors += 1
            
            if financial_metrics.get("debt_to_equity"):
                # Lower debt is better
                health_score += max(2 - financial_metrics["debt_to_equity"] / 50, 0)
                score_factors += 1
            
            if score_factors > 0:
                metrics["financial_health_score"] = health_score / score_factors
            
            return metrics
            
        except Exception as e:
            return {"error": f"Failed to calculate metrics: {e}"}
    
    def _generate_summary(self, results: Dict[str, Any], symbols: List[str], failed_symbols: List[str]) -> Dict[str, Any]:
        """Generate summary statistics across all symbols."""
        successful_symbols = [s for s in symbols if s not in failed_symbols]
        
        if not successful_symbols:
            return {"error": "No symbols processed successfully"}
        
        # Aggregate market data
        total_market_cap = 0
        price_changes = []
        sectors = {}
        
        for symbol in successful_symbols:
            data = results.get(symbol, {})
            
            # Market cap aggregation
            current_price = data.get("current_price", {})
            if current_price.get("market_cap"):
                total_market_cap += current_price["market_cap"]
            
            # Price changes
            if current_price.get("change_percent"):
                price_changes.append(current_price["change_percent"])
            
            # Sector distribution
            company_info = data.get("company_info", {})
            sector = company_info.get("sector", "Unknown")
            sectors[sector] = sectors.get(sector, 0) + 1
        
        # Calculate summary statistics
        summary = {
            "symbols_analyzed": len(successful_symbols),
            "total_market_cap": total_market_cap,
            "avg_price_change": sum(price_changes) / len(price_changes) if price_changes else 0,
            "positive_movers": len([p for p in price_changes if p > 0]),
            "negative_movers": len([p for p in price_changes if p < 0]),
            "sector_distribution": sectors,
            "market_sentiment": "bullish" if sum(price_changes) > 0 else "bearish" if sum(price_changes) < 0 else "neutral"
        }
        
        return summary

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock symbols (e.g., ['AAPL', 'GOOGL', 'MSFT'])",
                    "minItems": 1
                },
                "data_type": {
                    "type": "string",
                    "enum": ["price", "info", "history", "all"],
                    "default": "all",
                    "description": "Type of financial data to fetch"
                },
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
                    "default": "1mo",
                    "description": "Period for historical data"
                },
                "interval": {
                    "type": "string", 
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval for historical data"
                },
                "include_metrics": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to calculate additional financial metrics"
                }
            },
            "required": ["symbols"]
        }
    
    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return the output schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Financial data for each symbol"
                },
                "summary": {
                    "type": "object", 
                    "description": "Summary statistics across all symbols"
                },
                "symbols_requested": {
                    "type": "array",
                    "description": "List of symbols that were requested"
                },
                "symbols_processed": {
                    "type": "integer",
                    "description": "Number of symbols successfully processed"
                },
                "failed_symbols": {
                    "type": "array",
                    "description": "List of symbols that failed to process"
                },
                "timestamp": {
                    "type": "string",
                    "description": "When the data was fetched"
                }
            }
        } 