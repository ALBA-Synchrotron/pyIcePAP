import click
import beautifultable
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from .progress_bar import DEFAULT_FORMATTERS, PLAIN_FORMATTERS, \
    SIMPLE_FORMATTERS, _move, _rmove, _rmove_multiple
from .tables import Table, StateTable, StatusTable, PositionTable
from ..group import Group
from ..controller import IcePAPController


class ProgressBarFormats(click.Choice):

    formatters = dict(
        default=DEFAULT_FORMATTERS,
        plain=PLAIN_FORMATTERS,
        simple=SIMPLE_FORMATTERS
    )

    def __init__(self):
        super().__init__(self.formatters)

    def convert(self, value, param, ctx):
        result = super().convert(value, param, ctx)
        return self.formatters[result]


class TableStyles(click.Choice):

    name = "table_style"

    def __init__(self):
        styles = [s.name.lstrip("STYLE_").lower()
                  for s in beautifultable.Style]
        super().__init__(styles, case_sensitive=False)

    def convert(self, value, param, ctx):
        result = super().convert(value, param, ctx)
        return beautifultable.Style["STYLE_" + result.upper()]


class Axes(click.ParamType):

    name = "axes"

    def convert(self, value, param, ctx):
        pap = ctx.obj["icepap"]
        if value == "all":
            axes = pap.find_axes(only_alive=False)
        elif value == "alive":
            axes = pap.find_axes(only_alive=True)
        else:
            axes = []
            for axis in value.split(","):
                try:
                    axes.append(int(axis))
                except ValueError:
                    axes.append(axis.strip())
        return pap[axes]


def Racks(value):
    return [int(v) for v in value.split(",")]


def cli_move(group, positions, format=None, bottom_toolbar=True, title=True):
    bar_options = dict(formatters=format)
    if not bottom_toolbar:
        bar_options["bottom_toolbar"] = None
    if title is not True:
        bar_options["title"] = None if title is False else title
    _move(group, positions, bar_options=bar_options)


def cli_rmove(
        group,
        deltas,
        format=None,
        bottom_toolbar=True,
        title=True,
        multiple=False):
    bar_options = dict(formatters=format)
    if not bottom_toolbar:
        bar_options["bottom_toolbar"] = None
    if title is not True:
        bar_options["title"] = None if title is False else title
    if multiple:
        _rmove_multiple(group, deltas, bar_options=bar_options)
    else:
        _rmove(group, deltas, bar_options=bar_options)


opt_url = click.argument(
    "icepap", type=IcePAPController.from_url,
    #help="hardware url (ex: 'ipap.acme.org' or 'tcp://ipap13:5001')"
)

opt_pb_format = click.option(
    "--pb-format", type=ProgressBarFormats(),
    default="default", show_default=True, help="progress bar style"
)

opt_toolbar = click.option(
    "--bottom-toolbar/--no-bottom-toolbar", default=True, show_default=True,
    help="show/hide bottom toolbar"
)

opt_title = click.option(
    "--title/--no-title", default=True, show_default=True,
    help="show/hide title"
)

opt_table_style = click.option(
    "--table-style", type=TableStyles(), default="box_rounded",
    show_default=True, help="table style"
)

opt_axes = click.option(
    "--axes", "motors", type=Axes(), default="all", show_default=True,
    help="comma separated list of axes. Also supports 'all' and 'alive'"
)

opt_mandatory_axes = click.option(
    "--axes", "motors", type=Axes(), required=True, show_default=True,
    help="comma separated list of axes. Also supports 'all' and 'alive'"
)

opt_rack = click.option(
    "--rack", type=int, default=None, show_default=True,
    help="rack number. Default is None, meaning the whole system"
)

opt_racks = click.option(
    "--racks", type=Racks, required=True, show_default=True,
    help="comma separated list of racks. Also supports 'all' and 'alive'"
)


@click.group()
@opt_url
@click.pass_context
def cli(ctx, icepap):
    """
    High level command line interface for IcePAP
    """
    ctx.ensure_object(dict)
    ctx.obj["icepap"] = icepap


@cli.command()
@click.argument("pairs", nargs=-1, type=str, required=True)
@opt_pb_format
@opt_toolbar
@opt_title
@click.pass_context
def move(ctx, pairs, pb_format, bottom_toolbar, title):
    """
    Move specified axes in pairs <axis, position> to the specified absolute
    positions.
    """
    pap = ctx.obj["icepap"]
    motors = [pap[int(address)] for address in pairs[::2]]
    positions = [int(position) for position in pairs[1::2]]
    cli_move(Group(motors), positions, pb_format, bottom_toolbar, title)


@cli.command()
@click.argument("pairs", nargs=-1, type=str, required=True)
@opt_pb_format
@opt_toolbar
@opt_title
@click.option("-m", "--multiple", is_flag=True)
@click.pass_context
def rmove(ctx, pairs, pb_format, bottom_toolbar, title, multiple):
    """
    Move specified axes in pairs <axis, position> relative to their current
    positions.
    """
    pap = ctx.obj["icepap"]
    motors = [pap[int(address)] for address in pairs[::2]]
    deltas = [int(position) for position in pairs[1::2]]
    cli_rmove(
        Group(motors),
        deltas,
        pb_format,
        bottom_toolbar,
        title,
        multiple)


@cli.command()
@opt_mandatory_axes
def stop(motors):
    """Stops the given motors"""
    group = Group(motors)
    print_formatted_text(
        HTML("<orange>Stopping... </orange>"),
        end="",
        flush=True)
    group.start_stop()
    group.wait_stopped()
    print_formatted_text(HTML("[<green>DONE</green>]"))


@cli.command()
@opt_axes
@opt_table_style
def state(motors, table_style):
    """Prints a summary of each axis state in form of table"""
    group = Group(motors)
    click.echo(StateTable(group, style=table_style))


@cli.command()
@opt_axes
@opt_table_style
def status(motors, table_style):
    """
    Prints a summary of each axis status (position velotiy, acc. time, etc)
    in form of table
    """
    group = Group(motors)
    click.echo(StatusTable(group, style=table_style))


@cli.command()
@opt_axes
@opt_table_style
def pos(motors, table_style):
    """Prints a summary of each axis detailed position in form of table"""
    group = Group(motors)
    click.echo(PositionTable(group, style=table_style))


@cli.command()
@click.pass_context
def ver(ctx):
    """Prints a summary of icepap version"""
    pap = ctx.obj["icepap"]
    click.echo(pap.ver)


@cli.command()
@click.pass_context
def mode(ctx):
    """Prints the operation mode"""
    pap = ctx.obj["icepap"]
    click.echo(pap.mode)


@cli.command()
@opt_rack
@click.confirmation_option(
    prompt="Are you sure you want to reset the rack(s)?"
)
@click.pass_context
def reset(ctx, rack):
    """Resets the given rack. If no rack is given, resets the whole system"""
    pap = ctx.obj["icepap"]
    pap.reset(rack)


@cli.command()
@click.confirmation_option(
    prompt="Are you sure you want to reboot?"
)
@click.pass_context
def reboot(ctx):
    "Reboots the icepap"
    pap = ctx.obj["icepap"]
    pap.reboot()


@cli.command()
@opt_racks
@opt_table_style
@click.pass_context
def rinfo(ctx, racks, table_style):
    """Prints a summary of each rack information in form of table"""
    pap = ctx.obj["icepap"]
    rids = pap.get_rid(racks)
    temps = pap.get_rtemp(racks)
    table = Table(style=table_style)
    table.columns.header = ("Rack #", "RID", "Temp.")
    for row in zip(racks, rids, temps):
        table.rows.append(row)
    click.echo(table)


if __name__ == "__main__":
    cli()
