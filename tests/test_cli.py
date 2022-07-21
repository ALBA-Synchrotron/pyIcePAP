import sys
import pytest
from click.testing import CliRunner
from patch_socket import mock_socket, EXPECTED_VER

min_requirement = sys.version_info >= (3, 6)

pytestmark = pytest.mark.skipif(
    not min_requirement,
    reason="requires python3.6 or higher"
)

if min_requirement:
    from icepap.cli import cli


def test_mode():
    runner = CliRunner()
    with mock_socket():
        result = runner.invoke(cli, ['-u', 'icepaptest', 'mode'])
        assert result.exit_code == 0
        assert result.output == 'OPER\n'


def test_ver():
    runner = CliRunner()
    with mock_socket():
        result = runner.invoke(cli, ['-u', 'icepaptest', 'ver'])
        assert result.exit_code == 0
        assert result.output == repr(EXPECTED_VER) + "\n"


def test_rinfo():
    runner = CliRunner()
    args = ['-u', 'icepaptest', 'rinfo', '--racks=0,15', '--table-style=box']
    with mock_socket():
        result = runner.invoke(cli, args)
        assert result.exit_code == 0
        expected = """┌────────┬────────────────┬───────┐
│ Rack # │            RID │ Temp. │
├────────┼────────────────┼───────┤
│      0 │ 0008.0153.F797 │  30.1 │
├────────┼────────────────┼───────┤
│     15 │ 0008.020B.1028 │  29.5 │
└────────┴────────────────┴───────┘
"""
        assert result.output == expected
