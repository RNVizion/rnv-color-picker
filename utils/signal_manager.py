"""
Signal Connection Manager - Prevents memory leaks in Qt applications
Tracks and properly cleans up signal connections

Usage Examples:
    # In __init__:
    self.signal_manager = SignalConnectionManager()
    
    # Connect with tracking:
    self.signal_manager.connect(widget, widget.clicked, self.on_click)
    
    # Disconnect widget:
    self.signal_manager.disconnect_widget(widget)
    
    # On close:
    self.signal_manager.disconnect_all()
"""

from typing import Any
from PyQt6.QtCore import QObject, pyqtSignal

from utils.logger import Logger

logger = Logger("SignalManager")


class SignalConnectionManager:
    """
    Track and manage signal connections to prevent memory leaks.
    
    Problem:
        Qt signals that aren't properly disconnected can cause:
        - Memory leaks (widgets not garbage collected)
        - Crashes (callbacks to deleted objects)
        - Unexpected behavior (old slots still firing)
    
    Solution:
        This manager tracks all connections and ensures proper cleanup.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self._connections: dict[int, list[tuple[Any, Any]]] = {}
        # widget_id -> list of (signal, slot) tuples
        
        self._connection_count = 0
        self._disconnection_count = 0
    
    def connect(
        self, 
        widget: QObject, 
        signal: pyqtSignal, 
        slot: callable,
        track_as: str | None = None
    ) -> pyqtSignal:
        """
        Connect signal and track the connection.
        
        Args:
            widget: Widget/object that owns the signal
            signal: Signal to connect
            slot: Slot/callback to connect to
            track_as: Optional label for debugging
        
        Returns:
            The signal (for chaining)
        
        Example:
            self.signal_manager.connect(
                button, 
                button.clicked, 
                self.on_button_click,
                track_as="upload_button"
            )
        """
        widget_id = id(widget)
        
        # Connect the signal
        try:
            signal.connect(slot)
            self._connection_count += 1
        except Exception as e:
            if logger:
                logger.error(f"Failed to connect signal: {e}")
            return signal
        
        # Track the connection
        if widget_id not in self._connections:
            self._connections[widget_id] = []
        
        self._connections[widget_id].append((signal, slot, track_as))
        
        # Debug logging
        if track_as and logger:
            logger.debug(f"Connected: {track_as} (total: {self.get_connection_count()})")
        
        return signal
    
    def disconnect_widget(self, widget: QObject, quiet: bool = False) -> int:
        """
        Disconnect all signals for a specific widget.
        
        Args:
            widget: Widget to disconnect
            quiet: If True, suppress error messages
        
        Returns:
            Number of connections disconnected
        
        Example:
            # When removing a widget:
            self.signal_manager.disconnect_widget(widget)
        """
        widget_id = id(widget)
        
        if widget_id not in self._connections:
            if not quiet and logger:
                logger.warning(f"No connections found for widget {widget_id}")
            return 0
        
        connections = self._connections[widget_id]
        disconnected = 0
        
        for signal, slot, track_as in connections:
            try:
                signal.disconnect(slot)
                disconnected += 1
                self._disconnection_count += 1
                
                if track_as and not quiet and logger:
                    logger.debug(f"Disconnected: {track_as}")
            except TypeError:
                # Signal wasn't connected (may have been manually disconnected)
                if not quiet and logger:
                    logger.warning(f"Signal was not connected: {track_as or 'unknown'}")
            except Exception as e:
                if not quiet and logger:
                    logger.error(f"Failed to disconnect signal: {e}")
        
        # Remove from tracking
        del self._connections[widget_id]
        
        if not quiet and logger:
            logger.success(f"Disconnected {disconnected} connections from widget")
        
        return disconnected
    
    def disconnect_all(self, quiet: bool = False) -> int:
        """
        Disconnect ALL tracked connections.
        
        Args:
            quiet: If True, suppress logging
        
        Returns:
            Total number of connections disconnected
        
        Example:
            # In closeEvent:
            def closeEvent(self, event):
                total = self.signal_manager.disconnect_all()
                super().closeEvent(event)
        """
        total_disconnected = 0
        widget_ids = list(self._connections.keys())
        
        for widget_id in widget_ids:
            disconnected = self.disconnect_widget_by_id(widget_id, quiet=True)
            total_disconnected += disconnected
        
        self._connections.clear()
        
        if not quiet and logger:
            logger.success(f"Disconnected all {total_disconnected} tracked connections")
        
        return total_disconnected
    
    def disconnect_widget_by_id(self, widget_id: int, quiet: bool = False) -> int:
        """Disconnect widget by ID (used internally)."""
        if widget_id not in self._connections:
            return 0
        
        connections = self._connections[widget_id]
        disconnected = 0
        
        for signal, slot, track_as in connections:
            try:
                signal.disconnect(slot)
                disconnected += 1
                self._disconnection_count += 1
            except Exception:
                pass  # Ignore errors during bulk disconnect
        
        del self._connections[widget_id]
        return disconnected
    
    def get_connection_count(self) -> int:
        """Get total number of currently tracked connections."""
        return sum(len(conns) for conns in self._connections.values())
    
    def get_widget_connection_count(self, widget: QObject) -> int:
        """Get number of connections for a specific widget."""
        widget_id = id(widget)
        if widget_id not in self._connections:
            return 0
        return len(self._connections[widget_id])
    
    def get_stats(self) -> dict[str, int]:
        """
        Get connection statistics.
        
        Returns:
            Dictionary with stats:
            - active: Currently active connections
            - widgets: Number of widgets being tracked
            - total_connected: Total connections made
            - total_disconnected: Total disconnections
        """
        return {
            'active': self.get_connection_count(),
            'widgets': len(self._connections),
            'total_connected': self._connection_count,
            'total_disconnected': self._disconnection_count
        }
    
    def print_stats(self) -> None:
        """Print connection statistics to console."""
        stats = self.get_stats()
        if logger:
            logger.separator()
            logger.info("Signal Connection Statistics:")
            logger.indent(f"Active Connections: {stats['active']}")
            logger.indent(f"Tracked Widgets:    {stats['widgets']}")
            logger.indent(f"Total Connected:    {stats['total_connected']}")
            logger.indent(f"Total Disconnected: {stats['total_disconnected']}")
            logger.separator()
    
    def list_connections(self) -> list[str]:
        """
        Get list of all tracked connections (for debugging).
        
        Returns:
            List of connection descriptions
        """
        connections = []
        for widget_id, conn_list in self._connections.items():
            for signal, slot, track_as in conn_list:
                label = track_as or f"widget_{widget_id}"
                connections.append(f"{label}: {signal} -> {slot.__name__ if hasattr(slot, '__name__') else 'lambda'}")
        return connections
    
    def verify_cleanup(self) -> bool:
        """
        Verify all connections have been cleaned up.
        
        Returns:
            True if no connections remain, False otherwise
        
        Use this in tests or before app exit.
        """
        remaining = self.get_connection_count()
        if remaining > 0:
            if logger:
                logger.warning(f"{remaining} connections not cleaned up!")
                logger.debug("Remaining connections:")
                for conn in self.list_connections():
                    logger.indent(f"- {conn}")
            return False
        else:
            if logger:
                logger.success("All connections properly cleaned up")
            return True


class SignalMixin:
    """
    Mixin class to add signal management to any QObject.
    
    Usage:
        class ColorSwatch(QWidget, SignalMixin):
            def __init__(self):
                super().__init__()
                self.init_signal_tracking()
                
                # Now use managed connections:
                self.track_connection(
                    self.button, 
                    self.button.clicked,
                    self.on_click
                )
    """
    
    def init_signal_tracking(self):
        """Initialize signal tracking for this object."""
        if not hasattr(self, '_signal_manager'):
            self._signal_manager = SignalConnectionManager()
    
    def track_connection(self, widget, signal, slot, label=None):
        """Track a signal connection."""
        if not hasattr(self, '_signal_manager'):
            self.init_signal_tracking()
        return self._signal_manager.connect(widget, signal, slot, label)
    
    def cleanup_signals(self):
        """Clean up all tracked signals."""
        if hasattr(self, '_signal_manager'):
            self._signal_manager.disconnect_all(quiet=True)


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

# Global singleton instance
_signal_manager_instance: SignalConnectionManager | None = None


def get_signal_manager() -> SignalConnectionManager:
    """
    Get the global SignalConnectionManager singleton.
    
    Use this for app-wide signal tracking, or create your own
    instance for component-specific tracking.
    
    Returns:
        Global SignalConnectionManager instance
    """
    global _signal_manager_instance
    if _signal_manager_instance is None:
        _signal_manager_instance = SignalConnectionManager()
    return _signal_manager_instance


def reset_signal_manager() -> None:
    """Reset the global signal manager (for testing or app restart)."""
    global _signal_manager_instance
    if _signal_manager_instance is not None:
        _signal_manager_instance.disconnect_all(quiet=True)
        _signal_manager_instance = None
