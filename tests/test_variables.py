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


@pytest.mark.parametrize('name', ['DISCORD_TOKEN', 'DISCORD_ROLE'])
@pytest.mark.parametrize('empty', [False, True])
def test_mandatory_variable_missing_exits(monkeypatch, reload, name, empty):
    if empty:
        monkeypatch.setenv(name, '')
    else:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(SystemExit) as exit:
        reload()
    assert exit.value.code == 1


def test_mandatory_variables_set(reload):
    module = reload(DISCORD_TOKEN='token', DISCORD_ROLE='role')
    assert (module.DISCORD_TOKEN, module.DISCORD_ROLE) == ('token', 'role')


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
