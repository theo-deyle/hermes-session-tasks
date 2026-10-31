"""Hermes entry point for the session task board plugin."""

from .session_tasks.wiring import register

__all__ = ["register"]
