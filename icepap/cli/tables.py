import shutil

import beautifultable
import click

from ..utils import State

ERROR_COLOR = "bright_red"
OK_COLOR = "green"
WARNING_COLOR = "bright_yellow"


def bool_text(data, false="NO", true="YES"):
    return true if data else false


def bool_text_color(data, text_false="NO", text_true="YES",
                    color_false=ERROR_COLOR,
                    color_true=OK_COLOR):
    color = color_true if data else color_false
    text = bool_text(data, text_false, text_true)
    text = click.style(text, fg=color)
    return text


def bool_text_color_inv(data, text_false="NO", text_true="YES"):
    return bool_text_color(data, text_false, text_true, OK_COLOR,
                           ERROR_COLOR)


def stop_code_text_color(code, return_msg=False):
    if code == 0:
        color = OK_COLOR
    elif code in [1, 2, 3, 4, 5]:
        color = WARNING_COLOR
    else:
        color = ERROR_COLOR

    if return_msg:
        output = '{}: {}'.format(code, State.status_meaning['stopcode'][code])
    else:
        output = '{}'.format(code)
    return click.style(output, fg=color)


def mode_text_color(motor):
    mode = motor.mode
    if mode == 'OPER':
        color = OK_COLOR
    else:
        color = ERROR_COLOR
    return click.style(mode, fg=color)


def limits_text_color(state):
    if state.is_limit_negative() and state.is_limit_positive():
        text = 'BOTH'
        color = ERROR_COLOR
    elif state.is_limit_positive():
        text = 'Lim+'
        color = WARNING_COLOR
    elif state.is_limit_negative():
        text = 'Lim-'
        color = WARNING_COLOR
    else:
        text = 'NO'
        color = OK_COLOR
    return click.style(text, fg=color)


def disable_text_color(code, return_msg=False):
    if code == 0:
        color = OK_COLOR
    elif code == 7:
        color = WARNING_COLOR
    else:
        color = ERROR_COLOR
    if return_msg:
        output = '{}: {}'.format(code,
                                 State.status_meaning['disable'][code])
    else:
        output = '{}'.format(code)
    return click.style(output, fg=color)


 

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


def StatusTable(group, style=beautifultable.Style.STYLE_BOX_ROUNDED):
    table = Table(style=style)
    table.columns.header = (
        "Axis", "Name", "Alive", "Mode", "Ready", "Power", "Disab.",
        "StopC.", "Limits")
    args = (
        group.motors,
        group.names,
        group.get_states(),
    )
    stop_codes = set()
    disable_codes = set()
    for motor, name, state in zip(*args):
        if state.get_stop_code() != 0:
            stop_codes.add(state.get_stop_code())
        if state.get_disable_code() != 0:
            disable_codes.add(state.get_disable_code())
        row = (motor.axis, name,
               bool_text_color(state.is_alive()),
               mode_text_color(motor),
               bool_text_color(state.is_ready()),
               bool_text_color(state.is_poweron(), "OFF", "ON"),
               disable_text_color(state.get_disable_code()),
               stop_code_text_color(state.get_stop_code()),
               limits_text_color(state))
        table.rows.append(row)
    output = '{}\n\n'.format(table)
    if disable_codes is not None:
        output += 'Disable codes:\n'
        for disable_code in disable_codes:
            output += '  {}\n'.format(disable_text_color(disable_code, True))
    if stop_codes is not None:
        output += 'Stop codes:\n'
        for stop_code in stop_codes:
            output += '  {}\n'.format(stop_code_text_color(stop_code, True))
    return output


def StateTable(group, style=beautifultable.Style.STYLE_BOX_ROUNDED):
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


def EncoderTable(group, style=beautifultable.Style.STYLE_BOX_ROUNDED):
    ctrl, axes = group.controller, group.axes
    table = Table(style=style)
    header = "Axis", "AXIS", "MEASURE", "ENCIN", "INPOS", "ABSENC", "MOTOR"
    table.columns.header = header
    cols = [
        ctrl.get_enc(axes, register=register)
        for i, register in enumerate(header[1:])
    ]
    for row in zip(axes, *cols):
        table.rows.append(row)
    return table


def VersionTable(group, info=True,
                 style=beautifultable.Style.STYLE_BOX_ROUNDED):
    table = Table(style=style)
    master_ver = group.controller.fver

    if not info:
        header = 'Axis', 'VER'
        for motor in group.motors:
            diff = False
            motor_ver = motor.fver
            if master_ver != motor_ver:
                diff = True

            data = [motor.addr, motor_ver]
            if diff:
                color = ERROR_COLOR
            else:
                color = OK_COLOR
            row = [click.style(str(v), fg=color) for v in data]
            table.rows.append(row)
    else:
        print('Reading...')
        header = "Axis", "SYSTEM", "DRIVER", "DSP", "FPGA", "PCB", "IO"
        for motor in group.motors:
            axis_ver = motor.ver
            diff = False
            if master_ver != axis_ver.driver[0]:
                diff = True

            data = [motor.addr, axis_ver.system[0], axis_ver.driver[0],
                    axis_ver.driver_dsp[0], axis_ver.driver_fpga[0],
                    axis_ver.driver_pcb[0], axis_ver.driver_io[0]]

            if diff:
                color = ERROR_COLOR
            else:
                color = OK_COLOR
            row = [click.style(str(v), fg=color) for v in data]

            table.rows.append(row)

    table.columns.header = header

    return table
