from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def build_instance_key(root_path: str | Path) -> str:
    resolved = str(Path(root_path).resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:12]
    return f"okx_flash_earn_reminder_{digest}"


class SingleInstanceGuard(QObject):
    def __init__(self, root_path: str | Path, on_restore: Callable[[], None]) -> None:
        super().__init__()
        self._server_name = build_instance_key(root_path)
        self._on_restore = on_restore
        self._server: QLocalServer | None = None

    def activate_or_become_primary(self) -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(self._server_name)
        if socket.waitForConnected(300):
            socket.write(b"RESTORE")
            socket.flush()
            socket.waitForBytesWritten(300)
            socket.disconnectFromServer()
            return False

        QLocalServer.removeServer(self._server_name)
        server = QLocalServer(self)
        if not server.listen(self._server_name):
            return True
        server.newConnection.connect(self._handle_new_connection)
        self._server = server
        return True

    def _handle_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self._handle_socket_message(s))
            socket.disconnected.connect(socket.deleteLater)

    def _handle_socket_message(self, socket: QLocalSocket) -> None:
        payload = bytes(socket.readAll()).decode("utf-8", errors="ignore").strip()
        if payload == "RESTORE":
            self._on_restore()
        socket.disconnectFromServer()
