# -*- coding: utf8 -*-
"""Environment variables parsing (variables.py is read once, at import)."""

import importlib

import pytest

import variables


@pytest.fixture
def reload(monkeypatch):
    """Reload variables.py with the given env, then restore it as it was."""
    def _reload(**env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return importlib.reload(variables)

    yield _reload

    monkeypatch.undo()
    importlib.reload(variables)


@pytest.mark.parametrize('value, expected', [
    (None, 200),    # unset: default
    ('', 200),      # empty: default
    ('50', 50),
    ('abc', 200),   # invalid: warning + default
    ('0', 200),
    ('-5', 200),
])
def test_k8s_logs_tail_lines(monkeypatch, reload, value, expected):
    monkeypatch.delenv('K8S_LOGS_TAIL_LINES', raising=False)
    env = {} if value is None else {'K8S_LOGS_TAIL_LINES': value}

    assert reload(**env).K8S_LOGS_TAIL_LINES == expected


def test_k8s_namespaces(reload):
    assert reload(K8S_NAMESPACES='default,prod').K8S_NAMESPACES == ['default', 'prod']
