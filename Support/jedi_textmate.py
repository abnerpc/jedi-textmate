import os, sys, subprocess
import plistlib
from xml.parsers.expat import ExpatError

support_path = os.environ["TM_BUNDLE_SUPPORT"]

parso_path = os.path.join(support_path, "parso")
sys.path.insert(0, parso_path)

jedi_path = os.path.join(support_path, "jedi")
sys.path.insert(0, jedi_path)

import jedi


def get_env(var_name):
    return os.environ.get(var_name)


def read_file(file_path):
    try:
        with open(file_path, "r") as _file:
            return _file.read()
    except FileNotFoundError:
        return ""


def get_project_path():
    return get_env("TM_PROJECT_DIRECTORY")


def get_selection():
    selected_line, selected_column = get_env("TM_SELECTION").split(":")
    return int(selected_line), int(selected_column)


def get_pyenv_path():
    project_path = get_project_path()
    version_file_path = f"{project_path}/.python-version"
    file_content = read_file(version_file_path)
    if file_content:
        venv_name = file_content.strip()
        return f"{os.environ['HOME']}/.pyenv/versions/{venv_name}"


def get_environment():
    if pyenv_path := get_pyenv_path():
        return jedi.create_environment(pyenv_path, safe=False)

    paths = [os.environ["TM_PROJECT_DIRECTORY"]]
    envs.extend(jedi.find_virtualenvs(paths=paths))
    envs = list(jedi.find_system_environments())
    if envs:
        return envs[0]
    else:
        # TODO: show warning
        pass


_current_project_cache = None, None


def get_project():
    global _current_project_cache
    project_path = get_project_path()
    environment_path = get_pyenv_path()
    cache_key = f"{project_path}-{environment_path}"
    if cache_key == _current_project_cache[0]:
        return _current_project_cache[1]
    
    project = jedi.Project(project_path, environment_path=environment_path)
    _current_project_cache = cache_key, project
    return project
    

def get_script():
    file_path = get_env("TM_FILEPATH")
    source = read_file(file_path)
    return jedi.Script(source, path=file_path, project=get_project())


def to_string(data):
    return plistlib.dumps(data)


def from_string(string):
    pretty_list = get_env('TM_PROPERTY_LIST_BUNDLE_SUPPORT') + '/bin/pretty_plist'
    try:
        return plistlib.loads(string)
    except ExpatError:
        # string must have contained a TM format plist, which cannot be
        # parsed. Try converting it using pretty_list
        proc = subprocess.Popen([pretty_list, '-a'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE
                                )

        string, _ = proc.communicate(string)
        return plistlib.loads(string)


def _call_dialog(command, *args):
    dialog = get_env("DIALOG")
    popen_args = [dialog, command]
    popen_args.extend(args)
    result = subprocess.check_output(popen_args)
    return from_string(result) if result else {}


def popup_dialog(suggestions, already_typed="", static_prefix="", extra_chars="",
            case_insensitive=False, return_choice=False):
    """ Popup an autocomplete menu.
    suggestions is a list strings or 2-tuples to display. A string, if matched
    will be inserted as-is. If the first element of a 2-tuple is matched, the
    second element will be inserted.
    """

   # --returnChoice
    def item(val):
        if isinstance(val, tuple):
            return {'display': val[0], 'insert': val[1]}
        return {'display': val}

    d = [item(s) for s in suggestions]
    p = to_string(d)
    return _call_dialog('popup', '--suggestions', p,
                 '--alreadyTyped', already_typed,
                 '--staticPrefix', static_prefix,
                 '--additionalWordCharacters', extra_chars,
                 '--returnChoice' if return_choice else ''
                 '--caseInsensitive' if case_insensitive else '')


def goto_definition():
    script = get_script()
    if not script:
        return

    selection = get_selection()    
    names = script.goto(*selection, follow_imports=True)
    if not names:
        return

    definition = names[0]
    path = definition.module_path
    line = str(definition.line or 1)
    column = str(definition.column)
    
    url = f"txmt://open/?url=file://{path}&line={line}&column={column}"
    subprocess.call(["open", url])


def show_completions():
    script = get_script()
    if not script:
        return

    selection = get_selection()
    completions = [s.name for s in script.complete(*selection)]
    current_word = get_env("TM_CURRENT_WORD")
    typed = current_word.lstrip(".") if current_word else ""
    if len(completions) == 1:
        # There is only one completion. Insert it.
        sys.stdout.write(completions[0][len(typed):])
    elif completions is not []:
        # Python identifiers can contain _, so completions may contain it
        popup_dialog(completions, already_typed=typed, extra_chars="_")

    # mate = get_env("TM_MATE")
    # subprocess.call([mate, path, "-l", f"{line}:{column}", "-u", _uuid])

    # script = get_script()
#     if script is None:
#         return
#     try:
#         definitions = script.goto_definitions()
#     except jedi.NotFoundError:
#         exit_codes.exit_show_tool_tip('No definition found')
#     if definitions:
#         definition = definitions[0]
#         path = definition.module_path
#         if definition.in_builtin_module:
#             exit_codes.exit_show_tool_tip('Cannot jump to builtin module')
#         line = str(definition.line or 1)
#         column = str(definition.column)
#         #mate = env['TM_SUPPORT_PATH'] + b"/bin/mate"
#         url = b"txmt://open/?url=file://{path}&line={line}&column={column}".format(
#             path=path, line=line, column=column)
#         subprocess.call(['open', url])
#
    
# environ({'COMMAND_MODE': 'unix2003', 'DIALOG': '/Applications/TextMate.app/Contents/PlugIns/Dialog2.tmplugin/Contents/Resources/tm_dialog2', 'DIALOG_1': '/Applications/TextMate.app/Contents/PlugIns/Dialog.tmplugin/Contents/Resources/tm_dialog', 'DIALOG_1_PORT_NAME': 'com.macromates.dialog_1.60710', 'DIALOG_PORT_NAME': 'com.macromates.dialog.60710', 'HOME': '/Users/abnerpc', 'LANG': 'en_US.UTF-8', 'LC_CTYPE': 'en_US.UTF-8', 'LOGNAME': 'abnerpc', 'MATEFLAGS': '--no-recent', 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/Users/abnerpc/Library/Application Support/TextMate/Managed/Bundles/Bundle Support.tmbundle/Support/shared/bin', 'SHELL': '/bin/zsh', 'SHLVL': '1', 'SSH_AUTH_SOCK': '/private/tmp/com.apple.launchd.ndr8M6RSnH/Listeners', 'TMPDIR': '/var/folders/zf/m4bnp1l158q7frj1s23t6wkc0000gn/T/', 'TM_APP_IDENTIFIER': 'com.macromates.TextMate', 'TM_APP_PATH': '/Applications/TextMate.app', 'TM_BUNDLE_ITEM_NAME': 'Go To Definition', 'TM_BUNDLE_ITEM_UUID': '8A165E8D-14D6-476D-BB47-E2260389D1E5', 'TM_BUNDLE_SUPPORT': '/Users/abnerpc/Library/Application Support/TextMate/Bundles/python_jedi.tmbundle/Support', 'TM_COLUMN_NUMBER': '40', 'TM_COMMENT_START': '# ', 'TM_CURRENT_LINE': 'from scheduler.metrics import SchedulerMetric', 'TM_CURRENT_THEME_PATH': '/Users/abnerpc/Library/Application Support/TextMate/Managed/Bundles/Themes.tmbundle/Themes/Twilight.tmTheme', 'TM_CURRENT_WORD': 'SchedulerMetric', 'TM_DIRECTORY': '/Users/abnerpc/Dev/projects/loadsmart/scheduler-i9n/scheduler/events', 'TM_DISPLAYNAME': 'handlers.py', 'TM_DOCUMENT_UUID': 'D9234D10-A08C-4474-9C0C-EA0EABE571DE', 'TM_FILENAME': 'handlers.py', 'TM_FILEPATH': '/Users/abnerpc/Dev/projects/loadsmart/scheduler-i9n/scheduler/events/handlers.py', 'TM_FULLNAME': 'Abner Campanha', 'TM_LINE_INDEX': '39', 'TM_LINE_NUMBER': '10', 'TM_LINE_TERMINATOR': ':', 'TM_LINK_FORMAT': '(this language is not supported, see … for more info)', 'TM_MATE': '/Applications/TextMate.app/Contents/MacOS/mate', 'TM_PID': '60710', 'TM_PROJECT_DIRECTORY': '/Users/abnerpc/Dev/projects/loadsmart/scheduler-i9n', 'TM_PROJECT_UUID': '1D511076-2999-4BE4-86EA-65F83DCF5792', 'TM_PROPERTIES_PATH': '/Applications/TextMate.app/Contents/Resources/Default.tmProperties', 'TM_QUERY': '/Applications/TextMate.app/Contents/MacOS/tm_query', 'TM_RST2HTML': '/Users/abnerpc/.pyenv/versions/3.9.9/bin/rst2html.py', 'TM_SCM_COMMIT_WINDOW': '/Applications/TextMate.app/Contents/MacOS/CommitWindowTool', 'TM_SCM_NAME': 'git', 'TM_SCOPE': 'source.python meta.identifier.python attr.os-version.12.6.0 attr.project.make attr.rev-path.py.handlers.events.scheduler.scheduler-i9n.loadsmart.projects.Dev.abnerpc.Users attr.scm.branch.test-shipment-booked-sqs-4 attr.scm.git attr.scm.status.clean', 'TM_SCOPE_LEFT': 'source.python meta.identifier.python attr.os-version.12.6.0 attr.project.make attr.rev-path.py.handlers.events.scheduler.scheduler-i9n.loadsmart.projects.Dev.abnerpc.Users attr.scm.branch.test-shipment-booked-sqs-4 attr.scm.git attr.scm.status.clean', 'TM_SELECTED_FILE': '/Users/abnerpc/Dev/projects/loadsmart/scheduler-i9n/scheduler/events/handlers.py', 'TM_SELECTED_FILES': '/Users/abnerpc/Dev/projects/loadsmart/scheduler-i9n/scheduler/events/handlers.py', 'TM_SELECTION': '10:40', 'TM_SOFT_TABS': 'YES', 'TM_SUPPORT_PATH': '/Users/abnerpc/Library/Application Support/TextMate/Managed/Bundles/Bundle Support.tmbundle/Support/shared', 'TM_TAB_SIZE': '4', 'TM_THEME_PATH': '/Users/abnerpc/Library/Application Support/TextMate/Managed/Bundles/Themes.tmbundle/Support/web-themes', 'USER': 'abnerpc', '__CF_USER_TEXT_ENCODING': '0x1F5:0x0:0x0', 'SDKROOT': '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk', 'CPATH': '/usr/local/include', 'LIBRARY_PATH': '/usr/local/lib'})
