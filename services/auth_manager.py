"""
Authentication management for Clio API.

This module provides utilities to retrieve and manage Clio authentication tokens
from the local database or environment variables.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from loguru import logger
from pydantic import BaseModel


class AuthSession(BaseModel):
    """Model for Clio authentication session."""
    session_id: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class ClioAuthManager:
    """Manager for Clio authentication tokens."""

    def __init__(self, db_path: str = "/home/sysadmin01/custom-fields-manager/clio_auth.db"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            logger.warning(f"Clio auth database not found at {db_path}")

    def get_active_token(self) -> Optional[str]:
        """
        Get the active Clio authentication token.

        Tries multiple sources in order:
        1. Environment variable CLIO_AUTH_TOKEN
        2. Most recent valid session from database
        3. Most recent session regardless of expiration

        Returns:
            Active access token or None if not found
        """
        # Try environment variable first
        env_token = os.getenv("CLIO_AUTH_TOKEN")
        if env_token:
            logger.info("Using Clio auth token from environment variable")
            return env_token

        # Try database
        db_token = self._get_token_from_db()
        if db_token:
            logger.info("Using Clio auth token from database")
            return db_token

        logger.error("No Clio auth token found in environment or database")
        return None

    def _get_token_from_db(self) -> Optional[str]:
        """Get the most recent auth token from the database."""
        if not self.db_path.exists():
            return None

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # First try to get a non-expired token
                cursor.execute("""
                    SELECT session_id, access_token, refresh_token, expires_at, user_id, user_name
                    FROM auth_sessions
                    WHERE expires_at > datetime('now')
                    ORDER BY created_at DESC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    session = AuthSession(
                        session_id=row['session_id'],
                        access_token=row['access_token'],
                        refresh_token=row['refresh_token'],
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        user_id=row['user_id'],
                        user_name=row['user_name']
                    )
                    logger.info(f"Found valid auth session for user: {session.user_name}")
                    return session.access_token

                # If no valid token, get the most recent one anyway
                cursor.execute("""
                    SELECT session_id, access_token, refresh_token, expires_at, user_id, user_name
                    FROM auth_sessions
                    ORDER BY created_at DESC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    session = AuthSession(
                        session_id=row['session_id'],
                        access_token=row['access_token'],
                        refresh_token=row['refresh_token'],
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        user_id=row['user_id'],
                        user_name=row['user_name']
                    )

                    if session.expires_at and session.expires_at < datetime.now():
                        logger.warning(f"Most recent auth session for {session.user_name} is expired")
                    else:
                        logger.info(f"Found auth session for user: {session.user_name}")

                    return session.access_token

                return None

        except sqlite3.Error as e:
            logger.error(f"Database error retrieving auth token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving auth token: {e}")
            return None

    def get_session_info(self) -> Optional[AuthSession]:
        """Get full session information for the active token."""
        if not self.db_path.exists():
            return None

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT session_id, access_token, refresh_token, expires_at, user_id, user_name
                    FROM auth_sessions
                    ORDER BY created_at DESC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    return AuthSession(
                        session_id=row['session_id'],
                        access_token=row['access_token'],
                        refresh_token=row['refresh_token'],
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        user_id=row['user_id'],
                        user_name=row['user_name']
                    )

                return None

        except Exception as e:
            logger.error(f"Error retrieving session info: {e}")
            return None

    def is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        session = self.get_session_info()
        if not session or not session.expires_at:
            return True

        return session.expires_at < datetime.now()

    def refresh_token_if_needed(self) -> Optional[str]:
        """
        Refresh the token if it's expired and a refresh token is available.

        Note: This is a placeholder - actual token refresh would require
        implementing OAuth2 refresh flow with Clio's API.
        """
        session = self.get_session_info()
        if not session:
            return None

        if not self.is_token_expired():
            return session.access_token

        if session.refresh_token:
            logger.warning("Token is expired and refresh token is available, but refresh logic not implemented")
            # TODO: Implement actual token refresh logic
            return session.access_token
        else:
            logger.warning("Token is expired and no refresh token available")
            return session.access_token

    def list_all_sessions(self) -> list[AuthSession]:
        """List all authentication sessions in the database."""
        if not self.db_path.exists():
            return []

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT session_id, access_token, refresh_token, expires_at, user_id, user_name
                    FROM auth_sessions
                    ORDER BY created_at DESC
                """)

                sessions = []
                for row in cursor.fetchall():
                    sessions.append(AuthSession(
                        session_id=row['session_id'],
                        access_token=row['access_token'],
                        refresh_token=row['refresh_token'],
                        expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                        user_id=row['user_id'],
                        user_name=row['user_name']
                    ))

                return sessions

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []


# Global instance for easy access
auth_manager = ClioAuthManager()


def get_clio_auth_token() -> Optional[str]:
    """Convenience function to get the active Clio auth token."""
    return auth_manager.get_active_token()


def get_clio_session_info() -> Optional[AuthSession]:
    """Convenience function to get full session information."""
    return auth_manager.get_session_info()