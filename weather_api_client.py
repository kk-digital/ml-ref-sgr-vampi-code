"""
Weather API Client with async support, retry logic, and error handling.

This module provides a WeatherAPIClient class for fetching weather data from REST APIs
with exponential backoff retry logic and comprehensive error handling.
"""

import asyncio
from typing import Any, Dict, Optional
import httpx
from enum import Enum


class WeatherAPIError(Exception):
    """Base exception for Weather API errors."""
    pass


class NetworkError(WeatherAPIError):
    """Raised when network-related errors occur."""
    pass


class InvalidResponseError(WeatherAPIError):
    """Raised when API returns invalid or unexpected response."""
    pass


class APIKeyError(WeatherAPIError):
    """Raised when API key is invalid or missing."""
    pass


class WeatherAPIClient:
    """
    Async client for fetching weather data from REST APIs.
    
    Features:
    - Async HTTP requests using httpx
    - Exponential backoff retry logic (max 3 retries)
    - Comprehensive error handling
    - Type hints throughout
    
    Attributes:
        base_url: Base URL of the weather API
        api_key: Optional API key for authentication
        max_retries: Maximum number of retry attempts (default: 3)
        initial_backoff: Initial backoff delay in seconds (default: 1)
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        timeout: float = 30.0
    ) -> None:
        """
        Initialize the Weather API Client.
        
        Args:
            base_url: Base URL of the weather API (e.g., "https://api.weather.com")
            api_key: Optional API key for authentication
            max_retries: Maximum number of retry attempts (default: 3)
            initial_backoff: Initial backoff delay in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "WeatherAPIClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers including API key if provided.
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "WeatherAPIClient/1.0"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        return headers
    
    def _build_params(self, **kwargs) -> Dict[str, Any]:
        """
        Build query parameters including API key if not in headers.
        
        Args:
            **kwargs: Additional query parameters
            
        Returns:
            Dictionary of query parameters
        """
        params = dict(kwargs)
        
        # Some APIs expect API key as query parameter
        if self.api_key and "api_key" not in params:
            params["api_key"] = self.api_key
        
        return params
    
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx request
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            NetworkError: When network-related errors occur after all retries
            InvalidResponseError: When API returns invalid response
            APIKeyError: When API key is invalid or missing
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        client = self._get_client()
        
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(method, url, **kwargs)
                
                # Check for authentication errors
                if response.status_code == 401:
                    raise APIKeyError(
                        f"Invalid or missing API key. Status code: {response.status_code}"
                    )
                
                # Check for client errors (4xx)
                if 400 <= response.status_code < 500:
                    raise InvalidResponseError(
                        f"Client error: {response.status_code} - {response.text}"
                    )
                
                # Check for server errors (5xx) - these are retryable
                if response.status_code >= 500:
                    raise NetworkError(
                        f"Server error: {response.status_code} - {response.text}"
                    )
                
                # Raise for other non-2xx status codes
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except Exception as e:
                    raise InvalidResponseError(
                        f"Failed to parse JSON response: {str(e)}"
                    ) from e
                
            except httpx.TimeoutException as e:
                last_exception = NetworkError(f"Request timeout: {str(e)}")
            except httpx.NetworkError as e:
                last_exception = NetworkError(f"Network error: {str(e)}")
            except httpx.HTTPStatusError as e:
                last_exception = NetworkError(f"HTTP error: {str(e)}")
            except (APIKeyError, InvalidResponseError):
                # Don't retry on authentication or client errors
                raise
            except Exception as e:
                last_exception = WeatherAPIError(f"Unexpected error: {str(e)}")
            
            # If this wasn't the last attempt, wait before retrying
            if attempt < self.max_retries:
                backoff_time = self.initial_backoff * (2 ** attempt)
                await asyncio.sleep(backoff_time)
            else:
                # All retries exhausted
                if last_exception:
                    raise last_exception
        
        # This should never be reached, but just in case
        raise NetworkError("All retry attempts failed")
    
    async def get_current_weather(self, city: str) -> Dict[str, Any]:
        """
        Get current weather data for a city.
        
        Args:
            city: Name of the city to get weather for
            
        Returns:
            Dictionary containing current weather data
            
        Raises:
            NetworkError: When network-related errors occur
            InvalidResponseError: When API returns invalid response
            APIKeyError: When API key is invalid or missing
            
        Example:
            >>> async with WeatherAPIClient("https://api.weather.com", "your-api-key") as client:
            ...     weather = await client.get_current_weather("London")
            ...     print(weather)
        """
        if not city or not city.strip():
            raise ValueError("City name cannot be empty")
        
        params = self._build_params(q=city)
        headers = self._build_headers()
        
        return await self._make_request_with_retry(
            method="GET",
            endpoint="/current",
            params=params,
            headers=headers
        )
    
    async def get_forecast(self, city: str, days: int) -> Dict[str, Any]:
        """
        Get weather forecast for a city.
        
        Args:
            city: Name of the city to get forecast for
            days: Number of days to forecast (must be positive)
            
        Returns:
            Dictionary containing forecast data
            
        Raises:
            ValueError: When days is not positive
            NetworkError: When network-related errors occur
            InvalidResponseError: When API returns invalid response
            APIKeyError: When API key is invalid or missing
            
        Example:
            >>> async with WeatherAPIClient("https://api.weather.com", "your-api-key") as client:
            ...     forecast = await client.get_forecast("Paris", days=5)
            ...     print(forecast)
        """
        if not city or not city.strip():
            raise ValueError("City name cannot be empty")
        
        if days <= 0:
            raise ValueError("Number of days must be positive")
        
        params = self._build_params(q=city, days=days)
        headers = self._build_headers()
        
        return await self._make_request_with_retry(
            method="GET",
            endpoint="/forecast",
            params=params,
            headers=headers
        )
    
    async def close(self) -> None:
        """
        Close the HTTP client and cleanup resources.
        
        Should be called when done using the client if not using context manager.
        """
        if self._client:
            await self._client.aclose()
            self._client = None


# Example usage
async def main():
    """Example usage of WeatherAPIClient."""
    
    # Using context manager (recommended)
    async with WeatherAPIClient(
        base_url="https://api.weatherapi.com/v1",
        api_key="your-api-key-here"
    ) as client:
        try:
            # Get current weather
            current = await client.get_current_weather("London")
            print(f"Current weather: {current}")
            
            # Get 5-day forecast
            forecast = await client.get_forecast("Paris", days=5)
            print(f"Forecast: {forecast}")
            
        except APIKeyError as e:
            print(f"API Key error: {e}")
        except InvalidResponseError as e:
            print(f"Invalid response: {e}")
        except NetworkError as e:
            print(f"Network error: {e}")
        except WeatherAPIError as e:
            print(f"Weather API error: {e}")
    
    # Alternative: Manual resource management
    client = WeatherAPIClient(
        base_url="https://api.weatherapi.com/v1",
        api_key="your-api-key-here"
    )
    try:
        current = await client.get_current_weather("Tokyo")
        print(f"Current weather: {current}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
