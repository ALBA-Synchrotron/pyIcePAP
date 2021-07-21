import shlex
import socket

import click.exceptions
import click._bashcomplete
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer as BaseCompleter, Completion
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import run_in_terminal

from icepap import version as sw_version


def human_host(host):
    if host in {"", "0", "0.0.0.0"}:
        return socket.gethostname()
    return host


class Toolbar:
    def __init__(self, icepap):
        self.icepap = icepap
        comm = icepap._comm
        self.host = human_host(comm.host)
        self.addr = "{}:{}".format(self.host, comm.port)
        self.ver = icepap.fver
        self.mode = icepap.mode

    def __call__(self):
        msg = "icepapctl {} | <b>{}</b> - {} - {} | " \
          "<b>[F5]</b>: State <b>[F6]</b>: Status | <b>[Ctrl-D]</b>: Quit".format(
            sw_version, self.addr, self.ver, self.mode)
        return HTML(msg)


class Completer(BaseCompleter):

    def __init__(self, ctx):
        self.ctx = ctx
        self.icepap = ctx.obj["icepap"]
        self.host = self.icepap._comm.host

    def get_completions(self, document, complete_event=None):
        # Code analogous to click._bashcomplete.do_complete

        try:
            args = shlex.split(document.text_before_cursor)
        except ValueError:
            # Invalid command, perhaps caused by missing closing quotation.
            return

        cursor_within_command = (
            document.text_before_cursor.rstrip() == document.text_before_cursor
        )

        if args and cursor_within_command:
            # We've entered some text and no space, give completions for the
            # current word.
            incomplete = args.pop()
        else:
            # We've not entered anything, either at all or for the current
            # command, so give all relevant completions for this context.
            incomplete = ""

        # icepapctl specific: assumes a CLI: icepapctl [OPTS] ICEPAP COMMAND [ARGS]...
        if args:
            args.insert(0, self.host)

        ctx = click._bashcomplete.resolve_ctx(self.ctx.command, "", args)
        if ctx is None:
            return

        if args:
            choices = [Completion(
                "--help", -len(incomplete), display_meta="displays help")]
        else:
            choices = [Completion(
                "exit", -len(incomplete), display_meta="Quits application")]

        for param in ctx.command.params:
            if isinstance(param, click.Option):
                for options in (param.opts, param.secondary_opts):
                    for o in options:
                        choices.append(Completion(
                            str(o), -len(incomplete), display_meta=param.help))
            elif isinstance(param, click.Argument):
                if isinstance(param.type, click.Choice):
                    for choice in param.type.choices:
                        choices.append(Completion(
                            str(choice), -len(incomplete)))

        if isinstance(ctx.command, click.MultiCommand):
            for name in ctx.command.list_commands(ctx):
                command = ctx.command.get_command(ctx, name)
                choices.append(
                    Completion(
                        str(name),
                        -len(incomplete),
                        display_meta=command.get_short_help_str(),
                    )
                )

        for item in choices:
            if item.text.startswith(incomplete):
                yield item


def Prompt(context):
    icepap = context.obj["icepap"]

    kb = KeyBindings()

    def state():
        command("state --table-style=compact", context)
        print()

    def status():
        command("status --table-style=compact", context)
        print()

    @kb.add("f5")
    def _(event):
        run_in_terminal(state)

    @kb.add("f6")
    def _(event):
        run_in_terminal(status)

    @kb.add('c-space')
    def _(event):
        " Initialize autocompletion, or select the next completion. "
        buff = event.app.current_buffer
        if buff.complete_state:
            buff.complete_next()
        else:
            buff.start_completion(select_first=False)

    return PromptSession(
        completer=Completer(context),
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
        bottom_toolbar=Toolbar(icepap),
        key_bindings=kb,
        enable_history_search=True,
        complete_while_typing=False,
        message="> ",
    )


def command(text, context):
    args = shlex.split(text)
    group = context.command
    name = args[0]
    try:
        if name not in group.commands:
            context.fail("No such command {!r}".format(name))
        cmd = group.commands[name]
        args = args[1:]
        cmd.main(args, standalone_mode=False,
                 parent=context, default_map=context.params)
    except (click.exceptions.Exit, click.exceptions.Abort):
        pass
    except click.exceptions.ClickException as error:
        error.show()
    except Exception as error:
        print("Unexpected error: {!r}".format(error))


def step_raw(prompt, context):
    while True:
        text = prompt.prompt('raw mode> ')
        # empty text would create a sub-repl.
        # Avoid it by returning to the prompt
        if not text:
            continue
        elif text == "exit":
           return
        text = 'raw {}'.format(text)
        command(text, context)


def step(prompt, context):
   while True:
        text = prompt.prompt('> ')
        # empty text would create a sub-repl.
        # Avoid it by returning to the prompt
        if not text:
            continue
        elif text == "exit":
            raise EOFError
        elif text == "raw":
            return step_raw(prompt, context)
        return command(text, context)


def run(context):
    prompt = Prompt(context)
    while True:
        try:
            step(prompt, context)
        except EOFError:
            # Ctrl-D
            break
