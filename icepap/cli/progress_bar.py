import collections
import threading

from prompt_toolkit import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import D
from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit.shortcuts.progress_bar import Formatter, Label, Text, \
    Percentage, Bar, Progress, TimeLeft
from prompt_toolkit.styles import Style

from ..group import gen_motion, ensure_power, gen_move, gen_rmove
from ..utils import interrupt_myself, gen_rate_limiter


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