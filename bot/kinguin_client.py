"""Kinguin API v2 client for production environment."""

import hashlib
import hmac
import time
from typing import Optional, Dict, Any, List
import requests
from dataclasses import dataclass


@dataclass
class Product:
    """Product information."""
    kinguin_id: int
    name: str
    price: float
    qty: int
    platform: str
    region: str
    offer_id: Optional[str] = None


@dataclass
class OrderKey:
    """Order key information."""
    serial: str
    name: str
    type: str


class KinguinAPIError(Exception):
    """Kinguin API error."""
    pass


class KinguinClient:
    """Production Kinguin API v2 client."""

    def __init__(
        self,
        api_key: str,
        api_secret: Optional[str] = None,
        base_url: str = "https://gateway.kinguin.net/esa/api/v2"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Api-Key": api_key
        })

    def _generate_signature(
        self,
        path: str,
        method: str,
        body: str,
        timestamp: str
    ) -> str:
        """Generate HMAC SHA256 signature for API request."""
        if not self.api_secret:
            raise ValueError("API Secret required for signature generation")

        message = f"{path}{method}{body}{timestamp}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Kinguin API."""
        url = f"{self.base_url}{path}"
        timestamp = str(int(time.time() * 1000))

        headers = {}

        # Add signature if API secret is provided
        if self.api_secret:
            body = ""
            if data:
                import json
                body = json.dumps(data)

            signature = self._generate_signature(path, method, body, timestamp)
            headers["X-Api-Signature"] = signature
            headers["X-Api-Timestamp"] = timestamp

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass

            raise KinguinAPIError(
                f"API request failed: {e.response.status_code} - "
                f"{error_data.get('message', str(e))}"
            )

        except requests.exceptions.RequestException as e:
            raise KinguinAPIError(f"Request failed: {str(e)}")

    def get_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        return self._request("GET", "/user/balance")

    def search_products(
        self,
        name: Optional[str] = None,
        kinguin_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Product]:
        """Search products in catalog."""
        params = {"limit": limit}

        if name:
            params["name"] = name
        if kinguin_id:
            params["kinguinId"] = kinguin_id

        response = self._request("GET", "/products", params=params)

        products = []
        for item in response.get("results", []):
            products.append(Product(
                kinguin_id=item["kinguinId"],
                name=item["name"],
                price=item["price"],
                qty=item["qty"],
                platform=item.get("platform", "N/A"),
                region=item.get("region", "N/A"),
                offer_id=item.get("offerId")
            ))

        return products

    def get_product(self, kinguin_id: int) -> Product:
        """Get product details by Kinguin ID."""
        response = self._request("GET", f"/products/{kinguin_id}")

        return Product(
            kinguin_id=response["kinguinId"],
            name=response["name"],
            price=response["price"],
            qty=response["qty"],
            platform=response.get("platform", "N/A"),
            region=response.get("region", "N/A"),
            offer_id=response.get("offerId")
        )

    def create_order(
        self,
        kinguin_id: int,
        quantity: int,
        price: float,
        name: str
    ) -> Dict[str, Any]:
        """Create order (purchase products)."""
        order_data = {
            "products": [
                {
                    "kinguinId": kinguin_id,
                    "qty": quantity,
                    "price": price,
                    "name": name
                }
            ]
        }

        return self._request("POST", "/order", data=order_data)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order details."""
        return self._request("GET", f"/order/{order_id}")

    def get_order_keys(self, order_id: str) -> List[OrderKey]:
        """Get keys from completed order."""
        response = self._request("GET", f"/order/{order_id}/keys")

        keys = []
        for item in response.get("keys", []):
            keys.append(OrderKey(
                serial=item.get("serial", "N/A"),
                name=item.get("name", "N/A"),
                type=item.get("type", "N/A")
            ))

        return keys

    def get_orders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of orders."""
        response = self._request("GET", "/order", params={"limit": limit})
        return response.get("results", [])
