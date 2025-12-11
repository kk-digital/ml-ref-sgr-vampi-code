"""
Weather API Client with async support, retry logic, and error handling.

This module provides a WeatherAPIClient class for fetching weather data
from REST APIs with built-in retry logic and exponential backoff.
"""

import asyncio
from typing import Any, Dict, Optional
import httpx
from datetime import datetime


class WeatherAPIError(Exception):
    """Base exception for Weather API errors."""
    pass


class NetworkError(WeatherAPIError):
    """Raised when network-related errors occur."""
    pass


class InvalidResponseError(WeatherAPIError):
    """Raised when API returns invalid or unexpected response."""
    pass


class WeatherAPIClient:
    """
    Async client for fetching weather data from REST APIs.
    
    Features:
    - Async HTTP requests using httpx
    - Retry logic with exponential backoff (max 3 retries)
    - Proper error handling for network and response errors
    - Type hints throughout
    
    Attributes:
        base_url: The base URL of the weather API
        api_key: Optional API key for authentication
        max_retries: Maximum number of retry attempts (default: 3)
        timeout: Request timeout in seconds (default: 30)
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 30.0
    ) -> None:
        """
        Initialize the WeatherAPIClient.
        
        Args:
            base_url: The base URL of the weather API (e.g., "https://api.weather.com")
            api_key: Optional API key for authentication
            max_retries: Maximum number of retry attempts (default: 3)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
    
    async def _make_request_with_retry(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic and exponential backoff.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            NetworkError: When network-related errors occur after all retries
            InvalidResponseError: When API returns invalid response
        """
        if params is None:
            params = {}
        
        # Add API key to params if provided
        if self.api_key:
            params['apikey'] = self.api_key
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url, params=params)
                    
                    # Check for HTTP errors
                    if response.status_code == 404:
                        raise InvalidResponseError(
                            f"Resource not found: {url}"
                        )
                    elif response.status_code == 401:
                        raise InvalidResponseError(
                            "Authentication failed. Check your API key."
                        )
                    elif response.status_code == 429:
                        # Rate limit - wait longer before retry
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** (attempt + 2)  # 4, 8, 16 seconds
                            await asyncio.sleep(wait_time)
                            continue
                        raise NetworkError("Rate limit exceeded")
                    
                    response.raise_for_status()
                    
                    # Parse JSON response
                    try:
                        data = response.json()
                        return data
                    except ValueError as e:
                        raise InvalidResponseError(
                            f"Invalid JSON response: {str(e)}"
                        )
                
                except httpx.TimeoutException as e:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError(
                        f"Request timeout after {self.max_retries} attempts: {str(e)}"
                    )
                
                except httpx.NetworkError as e:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError(
                        f"Network error after {self.max_retries} attempts: {str(e)}"
                    )
                
                except httpx.HTTPStatusError as e:
                    # Don't retry on client errors (4xx except 429)
                    if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                        raise InvalidResponseError(
                            f"HTTP {e.response.status_code}: {str(e)}"
                        )
                    
                    # Retry on server errors (5xx)
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError(
                        f"HTTP error after {self.max_retries} attempts: {str(e)}"
                    )
        
        # Should never reach here, but for type safety
        raise NetworkError("Request failed unexpectedly")
    
    async def get_current_weather(self, city: str) -> Dict[str, Any]:
        """
        Fetch current weather data for a specific city.
        
        Args:
            city: Name of the city (e.g., "London", "New York")
            
        Returns:
            Dictionary containing current weather data
            
        Raises:
            NetworkError: When network-related errors occur
            InvalidResponseError: When API returns invalid response
            ValueError: When city parameter is empty
            
        Example:
            >>> client = WeatherAPIClient("https://api.weather.com", api_key="your_key")
            >>> weather = await client.get_current_weather("London")
            >>> print(weather)
        """
        if not city or not city.strip():
            raise ValueError("City parameter cannot be empty")
        
        params = {
            'q': city.strip(),
            'type': 'current'
        }
        
        try:
            data = await self._make_request_with_retry('weather', params)
            return data
        except (NetworkError, InvalidResponseError) as e:
            # Re-raise with additional context
            raise type(e)(f"Failed to fetch current weather for '{city}': {str(e)}")
    
    async def get_forecast(self, city: str, days: int) -> Dict[str, Any]:
        """
        Fetch weather forecast for a specific city.
        
        Args:
            city: Name of the city (e.g., "London", "New York")
            days: Number of days for the forecast (typically 1-14)
            
        Returns:
            Dictionary containing weather forecast data
            
        Raises:
            NetworkError: When network-related errors occur
            InvalidResponseError: When API returns invalid response
            ValueError: When city is empty or days is invalid
            
        Example:
            >>> client = WeatherAPIClient("https://api.weather.com", api_key="your_key")
            >>> forecast = await client.get_forecast("London", days=5)
            >>> print(forecast)
        """
        if not city or not city.strip():
            raise ValueError("City parameter cannot be empty")
        
        if days < 1:
            raise ValueError("Days parameter must be at least 1")
        
        if days > 14:
            raise ValueError("Days parameter cannot exceed 14")
        
        params = {
            'q': city.strip(),
            'days': days,
            'type': 'forecast'
        }
        
        try:
            data = await self._make_request_with_retry('forecast', params)
            return data
        except (NetworkError, InvalidResponseError) as e:
            # Re-raise with additional context
            raise type(e)(
                f"Failed to fetch {days}-day forecast for '{city}': {str(e)}"
            )
    
    async def __aenter__(self) -> 'WeatherAPIClient':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # Cleanup if needed
        pass


# Example usage
async def main():
    """Example usage of WeatherAPIClient."""
    # Initialize client
    client = WeatherAPIClient(
        base_url="https://api.weatherapi.com/v1",
        api_key="your_api_key_here"
    )
    
    try:
        # Fetch current weather
        print("Fetching current weather for London...")
        current = await client.get_current_weather("London")
        print(f"Current weather: {current}")
        
        # Fetch 5-day forecast
        print("\nFetching 5-day forecast for New York...")
        forecast = await client.get_forecast("New York", days=5)
        print(f"Forecast: {forecast}")
        
    except WeatherAPIError as e:
        print(f"Weather API error: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")
    
    # Using context manager
    async with WeatherAPIClient(
        base_url="https://api.weatherapi.com/v1",
        api_key="your_api_key_here"
    ) as client:
        weather = await client.get_current_weather("Paris")
        print(f"\nParis weather: {weather}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
