import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.websocket import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


class TestConnectionManager:
    def test_initial_state(self, manager):
        assert manager.active_connections == {}

    def test_disconnect_nonexistent(self, manager):
        ws = MagicMock()
        manager.disconnect(ws, "nonexistent-channel")
        assert "nonexistent-channel" not in manager.active_connections

    def test_active_connections_tracking(self, manager):
        ws1 = MagicMock()
        ws2 = MagicMock()
        channel = "test-channel"

        manager.active_connections[channel] = {ws1, ws2}
        assert len(manager.active_connections[channel]) == 2

        manager.disconnect(ws1, channel)
        assert len(manager.active_connections[channel]) == 1
        assert ws2 in manager.active_connections[channel]

    def test_disconnect_removes_empty_channel(self, manager):
        ws = MagicMock()
        channel = "empty-channel"
        manager.active_connections[channel] = {ws}

        manager.disconnect(ws, channel)
        assert channel not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        ws1 = MagicMock()
        ws1.send_json = MagicMock(return_value=None)
        ws2 = MagicMock()
        ws2.send_json = MagicMock(return_value=None)
        channel = "broadcast-test"

        manager.active_connections[channel] = {ws1, ws2}
        await manager.broadcast(channel, {"message": "hello"})

        ws1.send_json.assert_called_once_with({"message": "hello"})
        ws2.send_json.assert_called_once_with({"message": "hello"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, manager):
        ws_ok = MagicMock()
        ws_ok.send_json = AsyncMock(return_value=None)
        ws_dead = MagicMock()
        ws_dead.send_json = AsyncMock(side_effect=Exception("connection closed"))
        channel = "dead-test"

        manager.active_connections[channel] = {ws_ok, ws_dead}
        await manager.broadcast(channel, {"message": "test"})

        assert ws_dead not in manager.active_connections[channel]
        assert ws_ok in manager.active_connections[channel]

    @pytest.mark.asyncio
    async def test_broadcast_empty_channel(self, manager):
        await manager.broadcast("nonexistent-channel", {"message": "test"})
