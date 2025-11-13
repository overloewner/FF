"""Database module for storing purchase history."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict


@dataclass
class Purchase:
    """Purchase record."""
    id: Optional[int]
    user_id: int
    order_id: str
    kinguin_id: int
    product_name: str
    quantity: int
    price: float
    total_price: float
    status: str
    keys: Optional[str]  # JSON string
    created_at: str
    completed_at: Optional[str] = None


class Database:
    """Database manager for purchase history."""

    def __init__(self, db_path: str):
        """Initialize database connection."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id TEXT NOT NULL UNIQUE,
                    kinguin_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    status TEXT NOT NULL,
                    keys TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id
                ON purchases(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_id
                ON purchases(order_id)
            """)
            conn.commit()

    def add_purchase(self, purchase: Purchase) -> int:
        """Add new purchase record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO purchases (
                    user_id, order_id, kinguin_id, product_name,
                    quantity, price, total_price, status, keys,
                    created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                purchase.user_id,
                purchase.order_id,
                purchase.kinguin_id,
                purchase.product_name,
                purchase.quantity,
                purchase.price,
                purchase.total_price,
                purchase.status,
                purchase.keys,
                purchase.created_at,
                purchase.completed_at
            ))
            conn.commit()
            return cursor.lastrowid

    def update_purchase_status(
        self,
        order_id: str,
        status: str,
        keys: Optional[str] = None
    ):
        """Update purchase status and keys."""
        completed_at = datetime.now().isoformat() if status == "completed" else None

        with sqlite3.connect(self.db_path) as conn:
            if keys:
                conn.execute("""
                    UPDATE purchases
                    SET status = ?, keys = ?, completed_at = ?
                    WHERE order_id = ?
                """, (status, keys, completed_at, order_id))
            else:
                conn.execute("""
                    UPDATE purchases
                    SET status = ?, completed_at = ?
                    WHERE order_id = ?
                """, (status, completed_at, order_id))
            conn.commit()

    def get_purchase_by_order_id(self, order_id: str) -> Optional[Purchase]:
        """Get purchase by order ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM purchases WHERE order_id = ?
            """, (order_id,))
            row = cursor.fetchone()

            if row:
                return Purchase(**dict(row))
            return None

    def get_user_purchases(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Purchase]:
        """Get user's purchase history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM purchases
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))

            return [Purchase(**dict(row)) for row in cursor.fetchall()]

    def get_pending_purchases(self) -> List[Purchase]:
        """Get all pending purchases for status checking."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM purchases
                WHERE status NOT IN ('completed', 'cancelled', 'refunded')
                ORDER BY created_at DESC
            """)

            return [Purchase(**dict(row)) for row in cursor.fetchall()]
