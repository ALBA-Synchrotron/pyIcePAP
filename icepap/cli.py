import shutil
import threading
import collections

import click
import beautifultable
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts.progress_bar import ProgressBar
from prompt_toolkit.shortcuts.progress_bar.formatters import (
    Formatter, Label, Text, Percentage, Progress, Bar, TimeLeft
)

from .group import Group
from .controller import IcePAPController
from .tools import (
    ensure_power,
    interrupt_myself,
    is_moving,
    calc_deltas,
    gen_move,
    gen_rmove,
    gen_motion,
    gen_rate_limiter)

# -----------------------------------------------------------------------------
# Progress bar stuff


class Position(Formatter):

    moving = "<moving>{}</moving>"
    stopped = "<stopped>{}</stopped>"
    pos_format = ">{width}g"

    def format(self, progress_bar, progress, width):
        state = progress.state
        template = self.moving if state.is_moving() else self.stopped
        fmt = "{{:{}}}".format(self.pos_format.format(width=width)).format
        pos = fmt(progress.position)
        return HTML(template).format(pos)

    def get_width(self, progress_bar):
        fmt = "{{:{}}}".format(self.pos_format.format(width='')).format
        lengths = [len(fmt(c.initial_position)) for c in progress_bar.counters]
        lengths += [len(fmt(c.final_position)) for c in progress_bar.counters]
        # +2 to account for - sign and space
        return D.exact(max(lengths) + 2)


class InitialPosition(Formatter):

    pos_format = ">{width}g"

    def format(self, progress_bar, progress, width):
        fmt = "{{:{}}}".format(self.pos_format.format(width=width)).format
        return fmt(progress.initial_position)

    def get_width(self, progress_bar):
        fmt = "{{:{}}}".format(self.pos_format.format(width='')).format
        lengths = (len(fmt(c.initial_position)) for c in progress_bar.counters)
        return D.exact(max(lengths))


class TargetPosition(Formatter):

    pos_format = ">{width}g"

    def format(self, progress_bar, progress, width):
        fmt = "{{:{}}}".format(self.pos_format.format(width=width)).format
        return fmt(progress.final_position)

    def get_width(self, progress_bar):
        fmt = "{{:{}}}".format(self.pos_format.format(width='')).format
        lengths = (len(fmt(c.final_position)) for c in progress_bar.counters)
        return D.exact(max(lengths))


DEFAULT_FORMATTERS = [
    Label(),
    Text(" ["),
    InitialPosition(),
    Text(" => "),
    TargetPosition(),
    Text("] "),
    Position(),
    Text(" "),
    Percentage(),
    Text(" "),
    Bar(sym_a="=", sym_b=">", sym_c=" "),
    Text(" "),
    Progress(),
    Text(" "),
    Text("eta [", style="class:time-left"),
    TimeLeft(),
    Text("]", style="class:time-left"),
    Text(" "),
]

PLAIN_FORMATTERS = [
    Label(),
    Text(" ["),
    InitialPosition(),
    Text(" => "),
    TargetPosition(),
    Text("] "),
    Position(),
    Text(" "),
    Percentage(),
]

SIMPLE_FORMATTERS = [
    Label(),
    Text(": "),
    Position(),
]

DEFAULT_STYLE = Style.from_dict({
        "moving": "DeepSkyBlue bold",
        "stopped": "bold",
        "time-left": "DarkKhaki",
        "preparing": "DarkKhaki",
        "ctrlc": "orange",
        "error": "red",
        "done": "green",
})

DEFAULT_TOOLBAR = HTML(" Press [<b>x</b>] or [<b>Ctrl-C</b>] Stop.")


def create_default_key_bindings():
    kb = KeyBindings()

    @kb.add("x")
    def _(event):
        interrupt_myself()

    return kb


Motion = collections.namedtuple(
    "Motion",
    "group start_states start_positions initial_positions final_positions")


class MotionHandler:

    def __init__(self, on_ok=None, on_error=None, always=None):
        self.on_ok = on_ok or (lambda: None)
        self.on_error = on_error or (lambda err: None)
        self.always = always or (lambda: None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_value is None:
            self.on_ok()
        else:
            self.on_error(exc_value)
        self.always()


def MotionProgressBar(motion, bar_options=None):

    def prepare_counter(counter):
        def update(state, position):
            counter.state = state
            counter.position = position
            counter.items_completed = abs(position - counter.initial_position)

        def reset(initial, final):
            counter.total = abs(final - initial)
            counter.initial_position = initial
            counter.final_position = final

        counter.update = update
        counter.reset = reset

    def update(states, positions):
        for counter, state, pos in zip(prog_bar.counters, states, positions):
            counter.update(state, pos)
        prog_bar.invalidate()

    def reset(motion):
        args = (
            prog_bar.counters,
            motion.initial_positions,
            motion.final_positions)
        for counter, initial, final in zip(*args):
            counter.reset(initial, final)
        prog_bar.invalidate()

    bar_options = bar_options or {}
    bar_options.setdefault("title", HTML("<moving>Preparing...</moving>"))
    bar_options.setdefault("formatters", DEFAULT_FORMATTERS)
    bar_options.setdefault("style", DEFAULT_STYLE)
    bar_options.setdefault("key_bindings", create_default_key_bindings())
    bar_options.setdefault("bottom_toolbar", DEFAULT_TOOLBAR)
    prog_bar = ProgressBar(**bar_options)
    prog_bar.update = update
    prog_bar.reset = reset
    names = motion.group.names
    for name, state, start, initial, final in zip(names, *motion[1:]):
        counter = prog_bar(label=name, total=abs(final - initial))
        prepare_counter(counter)
        counter.reset(initial, final)
        counter.update(state, start)
    return prog_bar


def _move(group, final_positions, refresh_period=0.1, bar_options=None):
    start_states = group.get_states()
    start_positions = group.get_pos()
    motion = Motion(
        group, start_states, start_positions, start_positions, final_positions
    )

    def motion_loop(gen):
        for states, positions in gen_rate_limiter(gen, refresh_period):
            prog_bar.update(states, positions)

    def on_ok():
        nonlocal title
        title = HTML("<done>Finished!</done>")

    def on_error(error):
        nonlocal title
        group.start_stop()
        kb = isinstance(error, KeyboardInterrupt)
        if kb:
            msg = "<ctrlc>Stopping... </ctrlc>"
        else:
            msg = "<error>Motion error: {!r}<error>. ".format(error)
            msg += "Waiting for motors to stop..."
        title = HTML(msg)
        motion_loop(gen_motion(group))
        title = HTML(msg + "[<done>DONE</done>]")

    def always_end_with():
        prog_bar.update(group.get_states(), group.get_pos())

    title = HTML("<preparing>Preparing...</preparing>")
    bar_options = bar_options or {}
    bar_options.setdefault("title", lambda: title)
    prog_bar = MotionProgressBar(motion, bar_options=bar_options)
    power = ensure_power(group)
    handler = MotionHandler(on_ok, on_error, always_end_with)
    with prog_bar, power, handler:
        title = HTML("<moving>Moving...</moving>")
        motion_loop(gen_move(group, final_positions))


def _rmove(group, deltas, refresh_period=0.1, bar_options=None):
    start_states = group.get_states()
    start_positions = group.get_pos()
    final_positions = [p + d for p, d in zip(start_positions, deltas)]
    motion = Motion(
        group, start_states, start_positions, start_positions, final_positions
    )

    def motion_loop(gen):
        for states, positions in gen_rate_limiter(gen, refresh_period):
            prog_bar.update(states, positions)

    def on_ok():
        nonlocal title
        title = HTML("<done>Finished!</done>")

    def on_error(error):
        nonlocal title
        group.start_stop()
        kb = isinstance(error, KeyboardInterrupt)
        if kb:
            msg = "<ctrlc>Stopping... </ctrlc>"
        else:
            msg = "<error>Motion error: {!r}<error>. ".format(error)
            msg += "Waiting for motors to stop..."
        title = HTML(msg)
        motion_loop(gen_motion(group))
        title = HTML(msg + "[<done>DONE</done>]")

    def always_end_with():
        prog_bar.update(group.get_states(), group.get_pos())

    title = HTML("<preparing>Preparing...</preparing>")
    bar_options = bar_options or {}
    bar_options.setdefault("title", lambda: title)
    prog_bar = MotionProgressBar(motion, bar_options=bar_options)
    power = ensure_power(group)
    handler = MotionHandler(on_ok, on_error, always_end_with)
    with prog_bar, power, handler:
        title = HTML("<moving>Moving...</moving>")
        motion_loop(gen_rmove(group, deltas))


def _rmove_multiple(group, deltas, refresh_period=0.1, bar_options=None):
    start_states = group.get_states()
    start_positions = group.get_pos()
    final_positions = [p + d for p, d in zip(start_positions, deltas)]
    dir_deltas = deltas
    rev_deltas = [-delta for delta in deltas]
    motion = Motion(
        group, start_states, start_positions, start_positions, final_positions
    )

    def motion_loop(gen):
        for states, positions in gen_rate_limiter(gen, refresh_period):
            prog_bar.update(states, positions)

    def on_ok():
        nonlocal title
        title = HTML("<done>Finished!</done>")

    def on_error(error):
        nonlocal title
        group.start_stop()
        kb = isinstance(error, KeyboardInterrupt)
        if kb:
            msg = "<ctrlc>Stopping... </ctrlc>"
        else:
            msg = "<error>Motion error: {!r}</error>. ".format(error)
            msg += "Waiting for motors to stop..."
        title = HTML(msg)
        motion_loop(gen_motion(group))
        title = HTML(msg + "[<done>DONE</done>]")

    def always_end_with():
        prog_bar.update(group.get_states(), group.get_pos())

    title = HTML("<preparing>Preparing...</preparing>")
    bar_options = bar_options or {}
    evt = threading.Event()
    keys = create_default_key_bindings()
    action = None

    @keys.add('right')
    def _(event):
        nonlocal action
        action = "right"
        evt.set()

    @keys.add('left')
    def _(event):
        nonlocal action
        action = "left"
        evt.set()
    bar_options["key_bindings"] = keys
    bar_options["bottom_toolbar"] = HTML(
        " Press [<b>x</b>] or [<b>Ctrl-C</b>] Stop | "
        '[<a bg="deepskyblue">left arrow</a>] Move left | '
        '[<a bg="deepskyblue">right arrow</a>] Move right.')
    bar_options.setdefault("title", lambda: title)
    prog_bar = MotionProgressBar(motion, bar_options=bar_options)
    power = ensure_power(group)
    handler = MotionHandler(on_ok, on_error, always_end_with)
    with prog_bar, power, handler:
        while True:
            evt.wait()
            evt.clear()
            if action == "stop":
                break
            curr_deltas = dir_deltas if action == "right" else rev_deltas
            start_pos = group.get_pos()
            final_pos = [p + d for p, d in zip(start_pos, curr_deltas)]
            motion = Motion(
                group, start_states, start_pos, start_pos, final_pos
            )
            prog_bar.reset(motion)
            action = None
            title = HTML("<moving>Moving...</moving>")
            motion_loop(gen_rmove(group, curr_deltas))
            title = HTML("<done>Finished!</done>")

# -----------------------------------------------------------------------------
# Tables


def bool_text(data, false="NO", true="YES"):
    return true if data else false


def bool_text_color(data, text_false="NO", text_true="YES",
                    color_false="bright_red",
                    color_true="green"):
    color = color_true if data else color_false
    text = bool_text(data, text_false, text_true)
    text = click.style(text, fg=color)
    return text


def bool_text_color_inv(data, text_false="NO", text_true="YES"):
    return bool_text_color(data, text_false, text_true,
                           "green",
                           "bright_red")


def Table(**kwargs):
    style = kwargs.pop("style", beautifultable.Style.STYLE_BOX_ROUNDED)
    kwargs.setdefault("default_padding", 1)
    kwargs.setdefault("maxwidth", shutil.get_terminal_size().columns - 1)
    kwargs.setdefault(
        "default_alignment",
        beautifultable.Alignment.ALIGN_RIGHT)
    table = beautifultable.BeautifulTable(**kwargs)
    table.set_style(style)
    return table


def StateTable(group, style=beautifultable.Style.STYLE_BOX_ROUNDED):
    table = Table(style=style)
    table.columns.header = (
        "Axis", "Name", "Pos.", "Ready", "Alive", "Pres.", "Enab.",
        "Power", "5V", "Lim-", "Lim+", "Warn")
    args = (
        group.motors,
        group.names,
        group.get_states(),
        group.get_fpos()
    )
    for motor, name, state, pos in zip(*args):
        row = (motor.axis, name, pos,
               bool_text_color(state.is_ready()),
               bool_text_color(state.is_alive()),
               bool_text_color(state.is_present()),
               bool_text_color(not state.is_disabled()),
               bool_text_color(state.is_poweron(), "OFF", "ON"),
               bool_text_color(state.is_5vpower()),
               bool_text_color_inv(state.is_limit_negative(), "OFF", "ON"),
               bool_text_color_inv(state.is_limit_positive(), "OFF", "ON"),
               bool_text_color_inv(state.is_warning()))
        table.rows.append(row)
    return table


def StatusTable(group, style=beautifultable.Style.STYLE_BOX_ROUNDED):
    table = Table(style=style)
    table.columns.header = ('Axis', 'Name', 'Pos.', 'Ready', 'Vel.', 'Acc. T.')
    args = (group.motors, group.names, group.get_states(), group.get_fpos(),
            group.get_acctime(), group.get_velocity())
    for motor, name, state, pos, acctime, velocity in zip(*args):
        row = (motor.axis, name, pos,
               bool_text_color(state.is_ready()), velocity, acctime)
        table.rows.append(row)
    return table


def PositionTable(group, style=beautifultable.Style.STYLE_BOX_ROUNDED):
    ctrl, axes = group.controller, group.axes
    table = Table(style=style)
    header = "Axis", "AXIS", "MEASURE", "ENCIN", "INPOS", "ABSENC", "MOTOR"
    table.columns.header = header
    cols = [
        ctrl.get_pos(axes, register=register)
        for i, register in enumerate(header[1:])
    ]
    for row in zip(axes, *cols):
        table.rows.append(row)
    return table


# ------------------------------------------------------------------------------
# Command line interface


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


opt_url = click.option(
    "-u", "--url", "icepap", type=IcePAPController.from_url, required=True,
    help="hardware url (ex: 'ipap.acme.org' or 'tcp://ipap13:5001')"
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
