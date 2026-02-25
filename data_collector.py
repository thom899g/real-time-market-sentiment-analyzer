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