import shutil

import beautifultable
import click


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