# Real-Time Market Sentiment Analyzer

## Objective
Develop an AI system that analyzes real-time market sentiment by processing news, social media, and earnings calls using NLP and sentiment analysis to predict market movements.

## Strategy
Implement NLP models to process data sources, apply sentiment analysis, and use ML to correlate sentiments with market trends, updating models continuously.

## Execution Output
SUMMARY: Designed a robust, production-ready architecture for a Real-Time Market Sentiment Analyzer with Firebase integration, modular components, and comprehensive error handling. Created 8 complete Python modules implementing data collection, NLP processing, sentiment aggregation, prediction, and real-time streaming.

OUTPUT:
### FILE: requirements.txt
```
firebase-admin>=6.4.0
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
tweepy>=4.14.0
newspaper3k>=0.2.8
nltk>=3.8.0
scikit-learn>=1.3.0
python-dotenv>=1.0.0
schedule>=1.2.0
textblob>=0.17.1
```

### FILE: config.py
```python
"""
Configuration management with validation and environment variables.
Architectural Choice: Centralized config prevents scattered API keys and 
enables hot-reload capability for production deployments.
"""
import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class FirebaseConfig:
    """Firebase configuration with validation"""
    project_id: str
    service_account_path: str
    database_url: str
    
    def __post_init__(self):
        if not os.path.exists(self.service_account_path):
            raise FileNotFoundError(
                f"Firebase service account file not found: {self.service_account_path}"
            )

@dataclass
class APIConfig:
    """API configurations with fallback mechanisms"""
    twitter_bearer_token: Optional[str] = None
    newsapi_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None
    
    @property
    def has_twitter_access(self) -> bool:
        return bool(self.twitter_bearer_token and len(self.twitter_bearer_token) > 50)

@dataclass
class AnalysisConfig:
    """Sentiment analysis parameters"""
    symbols_to_track: List[str] = None
    update_interval_minutes: int = 15
    sentiment_threshold: float = 0.3
    lookback_period_days: int = 7
    
    def __post_init__(self):
        if self.symbols_to_track is None:
            self.symbols_to_track = ["AAPL", "GOOGL", "MSFT", "TSLA", "BTC-USD"]

class Config:
    """Singleton configuration manager"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize all configuration components"""
        try:
            self.firebase = FirebaseConfig(
                project_id=os.getenv("FIREBASE_PROJECT_ID", "market-sentiment-analyzer"),
                service_account_path=os.getenv("FIREBASE_SERVICE_ACCOUNT", "./service_account.json"),
                database_url=os.getenv("FIREBASE_DATABASE_URL", "https://market-sentiment-analyzer.firebaseio.com")
            )
            
            self.api = APIConfig(
                twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
                newsapi_key=os.getenv("NEWSAPI_KEY"),
                alpha_vantage_key=os.getenv("ALPHA_VANTAGE_KEY")
            )
            
            self.analysis = AnalysisConfig(
                symbols_to_track=os.getenv("SYMBOLS_TO_TRACK", "AAPL,GOOGL,MSFT").split(","),
                update_interval_minutes=int(os.getenv("UPDATE_INTERVAL", "15")),
                sentiment_threshold=float(os.getenv("SENTIMENT_THRESHOLD", "0.3"))
            )
            
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            
        except Exception as e:
            logging.error(f"Configuration initialization failed: {e}")
            raise

config = Config()
```

### FILE: data_collector.py
```python
"""
Real-time data collection from multiple sources with rate limiting and error handling.
Architectural Choice: Abstract base class ensures consistent interface across data sources
while allowing independent failure handling per source.
"""
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
import tweepy
from newspaper import Article
import schedule
from requests.exceptions import RequestException
from urllib.parse import urlparse

from config import config

logger = logging.getLogger(__name__)

class DataSource(ABC):
    """Abstract base class for all data sources"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name