import click
import beautifultable


from .progress_bar import DEFAULT_FORMATTERS, PLAIN_FORMATTERS, \
    SIMPLE_FORMATTERS, _move, _rmove, _rmove_multiple
from .tables import Table, StateTable, StatusTable, PositionTable, \
    VersionTable, EncoderTable
from ..group import Group
from ..controller import IcePAPController
from .utils import get_axes


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


class Racks(click.ParamType):
    name = 'racks'

    def convert(self, value, param, ctx):
        ipap = ctx.obj["icepap"]
        if value == 'all':
            racks = ipap.find_racks()
        else:
            racks = [int(v) for v in value.split(",")]
        return racks
    

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


opt_mandatory_rack = click.option(
    "--rack", type=int, default=None, show_default=True,
    help="rack number. Default is None, meaning the whole system"
)

opt_mandatory_racks = click.option(
    "--racks", type=Racks(), required=True, show_default=True,
    help="comma separated list of racks. Also supports 'all'"
)

opt_racks = click.option(
    "--racks", "racks", type=Racks(), default="all", show_default=True,
    help="comma separated list of racks. Also supports 'all'"
)


@click.group(invoke_without_command=True)
@click.pass_context
@click.argument("icepap", type=IcePAPController.from_url)
@click.option("--axes", "axes_str", type=str, default="alive",
              show_default=True,
              help="comma separated list of axes. Also supports 'all' and "
                   "'alive'")
@click.option("--table-style", type=TableStyles(), default="compact",
              show_default=True, help="table style")
@click.option("--pb-format", type=ProgressBarFormats(), default="default",
              show_default=True, help="progress bar style")
@click.option("--title/--no-title", default=True, show_default=True,
              help="show/hide title")
@click.option("--bottom-toolbar/--no-bottom-toolbar", default=True,
              show_default=True, help="show/hide bottom toolbar")
def cli(ctx, icepap, axes_str, table_style, pb_format, title, bottom_toolbar):
    """
    High level Command Line Interface for IcePAP

    Connects to the given ICEPAP (a url in format [tcp://]<host/ip>[:<port=5000])
    (ex: 'ice1', 'tcp://ice1' and 'tcp://ice1:5000' all mean the same)

    Runs without command will open the Console Application
    (ex: icpapctl <url>)
    """
    ctx.ensure_object(dict)
    ctx.obj["icepap"] = icepap
    ctx.obj["axes_str"] = axes_str
    ctx.obj['axes'] = get_axes(icepap, axes_str)
    alive_axes = get_axes(icepap, 'alive')
    all_axes = get_axes(icepap, 'all')
    not_alive_axes = list(set(all_axes) - set(alive_axes))
    if axes_str == 'all':
        click.echo('Warning: There are not alive axes: {}'.format(
            ', '.join(not_alive_axes)))
    ctx.obj['table_style'] = table_style
    ctx.obj['pb_format'] = pb_format
    ctx.obj['title'] = title
    ctx.obj['bottom_toolbar'] = bottom_toolbar
    if ctx.invoked_subcommand is None:
        from .repl import run
        run(ctx)


@cli.command()
@click.pass_context
@click.argument("pairs", nargs=-1, type=str, required=True)
def mv(ctx, pairs):
    """
    Move specified axes in pairs <axis, position> to the specified absolute
    positions. If the motor is off, the command will turn ON and at the end
    will turn OFF again
    """
    ipap = ctx.obj["icepap"]
    pb_format = ctx.obj['pb_format']
    title = ctx.obj['title']
    bottom_toolbar = ctx.obj['bottom_toolbar']
    motors = [ipap[int(address)] for address in pairs[::2]]
    positions = [int(position) for position in pairs[1::2]]
    cli_move(Group(motors), positions, pb_format, bottom_toolbar, title)


@cli.command()
@click.pass_context
@click.argument("pairs", nargs=-1, type=str, required=True)
@click.option("-m", "--multiple", is_flag=True)
def mvr(ctx, pairs, multiple):
    """
    Move specified axes in pairs <axis, position> relative to their current
    positions.If the motor is off, the command will turn ON and at the end
    will turn OFF again
    """
    ipap = ctx.obj["icepap"]
    pb_format = ctx.obj['pb_format']
    bottom_toolbar = ctx.obj['bottom_toolbar']
    title = ctx.obj['title']
    motors = [ipap[int(address)] for address in pairs[::2]]
    deltas = [int(position) for position in pairs[1::2]]
    cli_rmove(
        Group(motors),
        deltas,
        pb_format,
        bottom_toolbar,
        title,
        multiple)


@cli.command()
@click.pass_context
def state(ctx):
    """Prints a summary of each axis state in form of table"""
    motors = ctx.obj['axes']
    table_style = ctx.obj['table_style']
    group = Group(motors)
    click.echo(StateTable(group, style=table_style))


@cli.command()
@click.pass_context
def status(ctx):
    """
    Prints a summary of each axis status (position velotiy, acc. time, etc)
    in form of table
    """
    motors = ctx.obj['axes']
    table_style = ctx.obj['table_style']
    group = Group(motors)
    click.echo(StatusTable(group, style=table_style))


@cli.command()
@click.pass_context
@click.option('--enc', is_flag=True, default=False,
              help='Get encoders registers')
def wa(ctx, enc):
    """Prints a summary of each axis detailed position in form of table"""
    motors = ctx.obj['axes']
    table_style = ctx.obj['table_style']
    group = Group(motors)
    if not enc:
        click.echo('Unit: Axis Steps')
        click.echo(PositionTable(group, style=table_style))
    else:
        click.echo('Unit: Encoder Steps')
        click.echo(EncoderTable(group, style=table_style))


@cli.command()
@click.pass_context
@click.option('-v', 'verbose', is_flag=True, default=False,
              help='Get all info')
@click.option('--saved', is_flag=True, default=False, help='Get saved info')
@click.option('--axes', is_flag=True, default=False, help='Get axes version')
def version(ctx, verbose, saved, axes):
    """Prints a summary of icepap version"""
    ipap = ctx.obj["icepap"]
    if axes and saved:
        click.echo('Only one option is valid --axes or --saved', color='red')
        return
    if axes:
        motors = ctx.obj['axes']
        table_style = ctx.obj['table_style']
        group = Group(motors)
        click.echo(VersionTable(group, verbose, style=table_style))
        return

    if not saved:
        click.echo(ipap.ver)
    else:
        click.echo(ipap.ver_saved)


@cli.command()
@click.pass_context
@opt_mandatory_rack
@click.confirmation_option(
    prompt="Are you sure you want to reset the rack(s)?"
)
def reset(ctx, rack):
    """Resets the given rack. If no rack is given, resets the whole system"""
    ipap = ctx.obj["icepap"]
    ipap.reset(rack)


@cli.command()
@click.pass_context
@click.confirmation_option(
    prompt="Are you sure you want to reboot?"
)
def reboot(ctx):
    """Reboots the icepap"""
    ipap = ctx.obj["icepap"]
    ipap.reboot()


@cli.command()
@click.pass_context
@opt_racks
def rackinfo(ctx, racks):
    """Prints a summary of each rack information in form of table"""
    ipap = ctx.obj["icepap"]
    rids = ipap.get_rid(racks)
    temps = ipap.get_rtemp(racks)
    table_style = ctx.obj['table_style']
    table = Table(style=table_style)
    table.columns.header = ("Rack #", "RID", "Temp.")
    for row in zip(racks, rids, temps):
        table.rows.append(row)
    click.echo(table)


@cli.command()
@click.pass_context
@click.argument("cmd", nargs=-1, type=str, required=True)
def send(ctx, cmd):
    """Send raw command to the icepap"""
    ipap = ctx.obj['icepap']
    cmd = ' '.join(cmd)
    output = ipap.send_cmd(cmd)
    if output is not None:
        # Allow name with spaces:
        if not ipap.multiline_answer:
            click.echo(' '.join(output))
        else:
            for line in output:
                click.echo(line)
    else:
        click.echo('Done')


@cli.command()
@click.pass_context
@click.argument("cmd", nargs=-1, type=str, required=True)
def sendall(ctx, cmd):
    """
    Send raw command to selected axes with option --axes. The ':' character
    will be removed from the command
    """
    axes = ctx.obj['axes']
    cmd = ' '.join(cmd)
    if ':' in cmd:
        cmd = cmd.split(':')[1]
    for axis in axes:
        try:
            output = axis.send_cmd(cmd)
            if output is not None:
                click.echo('Axis {} anwser:'.format(axis.axis))
                for line in output:
                    click.echo('  {}'.format(line))
                click.echo('-'*40)
        except Exception as e:
            click.echo('Error sending command to {}'.format(axis.axis),
                       color='red')
            click.echo(e, color='red')
            click.echo('-' * 20)


if __name__ == "__main__":
    cli()
