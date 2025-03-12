import shlex
import socket

import click.exceptions

from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer as BaseCompleter, Completion
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import run_in_terminal

from icepap import version as sw_version

from .utils import get_axes
from .. import version

# Handle backwards compatibility between Click 7.0 and 8.0
try:
    import click.shell_completion
    HAS_C8 = True
except ImportError:
    import click._bashcomplete
    HAS_C8 = False


def human_host(host):
    if host in {"", "0", "0.0.0.0"}:
        return socket.gethostname()
    return host


def get_addr_ver(icepap):

    if icepap.port != 5000:
        addr = "{}:{}".format(icepap.host, icepap.port)
    else:
        addr = icepap.host

    try:
        ver = icepap.fver
    except Exception:
        ver = 'ERROR: Can not read master version'

    return addr, ver


class Toolbar:
    def __init__(self, icepap):
        self.icepap = icepap
        self.addr, self.ver = get_addr_ver(icepap)

    def __call__(self):
        msg = "icepapctl {} | {} - {}| " \
              "<b>[F5]</b>: State <b>[F6]</b>: Status | " \
              "<b>[Ctrl-D]</b>: Quit".format(sw_version, self.addr,
                                             self.ver)
        return HTML(msg)


class Completer(BaseCompleter):

    def __init__(self, ctx):
        self.ctx = ctx
        self.icepap = ctx.obj["icepap"]

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

        # icepapctl specific:
        # assumes a CLI: icepapctl [OPTS] ICEPAP COMMAND [ARGS]...
        if args:
            args.insert(0, self.icepap.host)

        if HAS_C8:
            ctx = click.shell_completion._resolve_context(self.ctx.command,
                                                          {}, "",
                                                          args)
        else:
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
        command("state", context)
        print()

    def status():
        command("status", context)
        print()

    @kb.add("f5")
    def _(event):
        run_in_terminal(state)

    @kb.add("f6")
    def _(event):
        run_in_terminal(status)

    @kb.add('c-space')
    def _(event):
        """ Initialize autocompletion, or select the next completion. """
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
            name = 'send'
        else:
            args = args[1:]

        # From click documentation:
        # https://click.palletsprojects.com/en/8.1.x/arguments/
        # Option-Like Arguments:
        # To recognize negative values Click does what any POSIX style
        # command line script does, and that is to accept the string -- as a
        # separator for options and arguments. After the -- marker, all
        # further parameters are accepted as arguments.
        #
        # This is valid for send, mv, mvr
        if name in ['send', 'mv', 'mvr']:
            args.insert(0, '--')
            if name == 'mvr' and '-m' in args:
                args.pop(args.index('-m'))
                args.insert(0, '-m')

        cmd = group.commands[name]
        cmd.main(args, standalone_mode=False,
                 parent=context, default_map=context.params)
    except (click.exceptions.Exit, click.exceptions.Abort):
        pass
    except click.exceptions.ClickException as error:
        error.show()
    except Exception as error:
        print("Unexpected error: {!r}".format(error))


def print_help(text, ctx):
    args = shlex.split(text)
    if len(args) == 1:
        print('The console allows raw command (Icepap commands) \n'
              'without using the "send" command e.g:\n\n'
              '   "1:?vstatus" is equivalent to "send 1:?vstatus"\n\n')
        print('Console Commands:')
        print('  axes        Get/Set default axes used.')
        print('  help <cmd>  Get CLI command help\n\n')
        print('CLI Commands:')
        print(ctx.get_help().split('Commands:')[1])
    else:
        cmd = args[1]
        cmd_help = ctx.command.commands[cmd].get_help(ctx)
        for line in cmd_help.split('\n'):
            if line.startswith('Usage:'):
                continue
            if line.startswith('Options:'):
                break
            print(line)


def step(prompt, context):
    while True:
        text = prompt.prompt('> ')
        # empty text would create a sub-repl.
        # Avoid it by returning to the prompt
        if not text:
            continue
        elif text == "exit":
            raise EOFError
        elif text.startswith("help"):
            print_help(text, context)
            return
        elif text.startswith('axes'):
            new_axes = text.split('axes')[1]
            if not new_axes:
                print(context.obj['axes_str'])
                return
            else:
                context.obj['axes_str'] = new_axes
                context.obj['axes'] = get_axes(context.obj['icepap'],
                                               new_axes)
                print('New axes: {}'.format(new_axes))
                return

        return command(text, context)


def run(context):
    prompt = Prompt(context)
    icepap = context.obj["icepap"]
    print('Icepap Console Application {}'.format(version))
    addr, ver = get_addr_ver(icepap)
    if 'ERROR' in str(ver):
        ver = '\033[93m{}\033[0m'.format(ver)
    print('Connected to: {} - {}'.format(addr, ver))
    print('Type "help" for more information.')
    while True:
        try:
            step(prompt, context)
        except EOFError:
            # Ctrl-D
            break
