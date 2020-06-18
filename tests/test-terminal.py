import pytest
from pytestqt import qt_compat
from pytestqt.qt_compat import qt_api

from autopilot.core.terminal import Terminal

@pytest.fixture
def spawn_terminal(qtbot):
    app = qt_api.QApplication.instance()
    terminal = Terminal()
    qtbot.addWidget(terminal)
    return app, terminal

def test_terminal_launch(spawn_terminal):
    app, terminal = spawn_terminal

    assert terminal.isVisible()
