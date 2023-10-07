import os, sys, subprocess
import plistlib
from xml.parsers.expat import ExpatError

support_path = os.environ["TM_BUNDLE_SUPPORT"]
parso_path = os.path.join(support_path, "parso")
jedi_path = os.path.join(support_path, "jedi")
sys.path[:0] = [parso_path, jedi_path]

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
    line = get_env("TM_LINE_NUMBER")
    column = get_env("TM_COLUMN_NUMBER")
    return int(line), int(column)


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
    source = sys.stdin.read()
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
    if not selection:
        return

    names = script.goto(*selection, follow_imports=True)
    if not names:
        return

    definition = names[0]
    path = definition.module_path
    line = str(definition.line or 1)

    os.system(f"{os.environ['TM_MATE']} '{path}' -l{line}")


def show_completions():
    script = get_script()
    if not script:
        return

    selection = get_selection()
    selection = selection[0], selection[-1]-1
    if not selection:
        return

    completions = [s.name for s in script.complete(*selection)]
    current_word = get_env("TM_CURRENT_WORD")
    typed = current_word.lstrip(".") if current_word else ""
    if len(completions) == 1:
        # There is only one completion. Insert it.
        sys.stdout.write(completions[0][len(typed):])
    elif completions is not []:
        # Python identifiers can contain _, so completions may contain it
        popup_dialog(completions, already_typed=typed, extra_chars="_")