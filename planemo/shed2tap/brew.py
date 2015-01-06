#!/usr/bin/env python
from __future__ import print_function
import os
import re
import traceback
import string
import subprocess
import sys
import urlparse

import click

from bioblend import toolshed

from .shed import (
    BaseDependencies,
    BasePackage,
    Repo,
    dispatch_on_action,
)

TOOLSHED = "https://toolshed.g2.bx.psu.edu"
TOOLSHED_MAP = {
    "toolshed": "https://toolshed.g2.bx.psu.edu",
    "testtoolshed": "https://testtoolshed.g2.bx.psu.edu",
}
GIT_USER = "jmchilton"
if sys.platform == "darwin":
    DEFAULT_HOMEBREW_ROOT = "/usr/local"
else:
    DEFAULT_HOMEBREW_ROOT = os.path.join(os.path.expanduser("~"),
                                         ".linuxbrew")

UNNEEDED_SET_ENV = ("# Tool Shed set environment variable that is "
                    "picked implicitly.")


EXTENSION_ENVIRONMENT = """
def environment(actions)
    # Setup envirnoment variable modifications that will be used later by
    # platform-brew's env and vinstall commands.
    act_hash = {"actions" => actions}
    (prefix / "platform_environment.json").write act_hash.to_json
end
"""

EXTENSION_PYTHON = """
  def depend_python(python_recipe)
    ENV["PYTHONHOME"] = Formula[python_recipe].prefix
    ENV["PYTHONPATH"] = Formula[python_recipe].prefix
    ENV.prepend_path "PATH", prefix / "bin"
    ENV.prepend_path "PYTHONPATH", prefix
  end

  def easy_install(what)
    system "easy_install", "--install-dir", prefix, "--script-dir",
           "#{prefix}/bin", what
  end
"""

EXTENSION_R = """
"""

EXTENSION_RUBY = """
"""

EXTENSION_PERL = """

"""


@click.command()
@click.option('--tool_shed',
              default="toolshed",
              type=click.Choice(TOOLSHED_MAP.keys()),
              help='Tool shed to target.')
@click.option('--owner',
              default=None,
              help='Limit generation to specific owner.')
@click.option('--name_filter',
              default=None,
              help='Apply regex to name filters.')
@click.option('--git_user', default="jmchilton")
@click.option('--brew_directory', default=DEFAULT_HOMEBREW_ROOT)
def main(**kwds):
    user = kwds["git_user"]
    repo_name = "homebrew-%s" % kwds["tool_shed"]
    target = os.path.join(
        kwds["brew_directory"],
        "Library",
        "Taps",
        user,
        repo_name
    )
    tap = Tap("%s/%s" % (user, kwds["tool_shed"]))
    # shell("rm -rf %s" % target)
    shell("mkdir -p %s" % target)
    prefix = kwds["tool_shed"]
    tool_shed_url = TOOLSHED_MAP[prefix]
    dependencies_list = []
    repo_iter = repos(
        tool_shed_url,
        owner=kwds["owner"],
        name_filter=kwds["name_filter"]
    )
    for raw_repo in repo_iter:
        repo = Repo.from_api(prefix, raw_repo)
        dependencies_file = repo.get_file("tool_dependencies.xml")
        if not dependencies_file:
            message = "skipping repository %s, no tool_dependencies.xml"
            click.echo(message % repo)
            continue
        try:
            dependencies = Dependencies(dependencies_file, repo, tap)
        except Exception as e:
            template = "Failed to parse dependencies for repo %s, skipping. "
            template += "Error [%s]."
            print(template % (repo, e))
            continue
        dependencies_list.append(dependencies)

    for dependencies in dependencies_list:
        for package in dependencies.packages:
            try:
                (file_name, contents) = package.to_recipe()
                recipe_path = os.path.join(target, file_name)
                open(recipe_path, "w").write(contents)
            except Exception as e:
                traceback.print_exc()
                message = "Failed to convert package [%s], exception [%s]"
                print(message % (package, e))

    shell("git init %s" % target)
    git_target = "--work-tree %s --git-dir %s/.git" % (target, target)
    shell("git %s add %s/*" % (git_target, target))
    shell("git %s commit -m 'Initial Commit' " % (git_target))


class Dependencies(BaseDependencies):

    def __init__(self, dependencies_file, repo, tap):
        self.tap = tap
        super(Dependencies, self).__init__(
            dependencies_file, repo, package_factory=Package
        )


class Tap(object):

    def __init__(self, prefix):
        self.prefix = prefix


class BrewActionHandler(object):

    def __init__(self, package):
        self.package = package

    def handle_shell_command(self, action):
        command = action.command.strip()
        if "\n" in command:
            command = templatize_string(command)
            cmd_parts = [p.strip() for p in command.split("\n") if p]
            command = "\n".join(cmd_parts)
            return 'system <<-EOF\n%s\nEOF' % command
        else:
            shell_command = shell_string(action.command)
            return 'system %s' % shell_command

    def handle_move_file(self, action):
        statements = []
        named_destination = self.named_dir(action.destination)
        if named_destination:
            args = (named_destination, shell_string(action.source))
            statements.append('%s.install %s' % args)
        else:
            shell_dest = shell_string(action.destination)
            shell_source = shell_string(action.source)
            statements.append('system "mkdir", "-p", %s' % shell_dest)
            statements.append('mv %s, %s' % (shell_source, shell_dest))
        return statements

    def handle_move_directory_files(self, action):
        statements = []
        named_destination = self.named_dir(action.destination_directory)
        if named_destination:
            temp = '''%s.install Dir["%s/*"]'''
            statements.append(temp % (
                named_destination,
                shell_string(action.source_directory, quote_now=False))
            )
        else:
            shell_dest = shell_string(action.destination_directory)
            statements.append('''system "mkdir", "-p", %s''' % shell_dest)
            statements.append('''mv Dir["%s/*"], %s ''' % (
                shell_string(action.source_directory, quote_now=False),
                shell_string(action.destination_directory))
            )
        return statements

    def handle_set_environment(self, action):
        statements = []
        modify_environment = []
        for raw_variable in action.variables:
            variable = BrewSetVariable(raw_variable)
            if variable.explicit:
                modify_environment.append(variable)
            else:
                statements.append(UNNEEDED_SET_ENV)
        if modify_environment:
            list_str = '''['''
            for i, set_variable in enumerate(modify_environment):
                if i > 0:
                    list_str += ","
                list_str += set_variable.to_ruby_hash()
            list_str += ']'
            if self.package.has_multiple_set_environments():
                statements.append('environment_actions += %s' % list_str)
            else:
                statements.append('''environment(%s)''' % list_str)
            self.package.extensions_used.add('ENVIRONMENT')
        return statements

    def handle_chmod(self, action):
        statements = []
        for mod in action.mods:
            target = shell_string(mod["target"])
            chmod_command = 'system "chmod", "%s", %s'
            statements.append(chmod_command % (mod["mode"], target))
        return statements

    def handle_download_file(self, action):
        statements = []
        resource = url_to_resource(action.url)
        statements.append("resource('%s').stage do" % resource)
        move_comment = ("Tool Shed would download inside build directory"
                        " instead of its own - so move download.")
        statements.append('''    # %s''' % move_comment)
        if action.extract:
            statements.append('''    buildpath.install Dir["../*"]''')
        else:
            statements.append('''    buildpath.install Dir["*"]''')
        statements.append("end")
        return statements

    def handle_make_install(self, action):
        return '''system "make install"'''

    def handle_change_directory(self, action):
        return "cd '%s'" % action.directory

    def handle_make_directory(self, action):
        shell_dir = shell_string(action.directory)
        return 'system "mkdir", "-p", %s' % shell_dir

    def handle_setup_perl_environment(self, action):
        return self.unhandled_action(action)

    def handle_setup_ruby_environment(self, action):
        return self.unhandled_action(action)

    def handle_setup_python_environment(self, action):
        return self.unhandled_action(action)

    def handle_setup_r_environment(self, action):
        return self.unhandled_action(action)

    def handle_setup_virtualenv(self, action):
        return self.unhandled_action(action)

    def handle_set_environment_for_install(self, action):
        return "# Skipping set_environment_for_install command, handled by platform brew."

    def unhandled_action(self, action):
        template = 'onoe("Unhandled tool shed action %s encountered.")'
        message = template % action.action_type
        return [message]

    def named_dir(self, path):
        ruby_path = shell_string(path, quote_now=False)
        if ruby_path == "#{prefix}":
            return "prefix"
        elif ruby_path == "#{prefix}/bin":
            return "bin"
        else:
            return None


class BrewSetVariable(object):

    def __init__(self, raw_set_variable):
        self.action = raw_set_variable.action
        self.name = raw_set_variable.name
        self.raw_value = raw_set_variable.raw_value
        self.ruby_value = templatize_string(self.raw_value)

    @property
    def explicit(self):
        return not self.implicit

    @property
    def implicit(self):
        if self.name == "PATH" and self.ruby_value == "#{prefix}/bin":
            return True
        else:
            return False

    def to_ruby_hash(self):
        action = self.action
        variable = self.name
        value = self.ruby_value.replace("#{prefix}", "$KEG_ROOT")
        if action == "set_to":
            action = "set"
        elif action == "prepend_to":
            action = "prepend"
        else:
            action = "append"
        template = '''{'action'=> '%s', 'variable'=> '%s', 'value'=> '%s'}'''
        return template % (action, variable, value)


def shell_string(tool_shed_str, quote_now=True, templatize=True):
    if templatize:
        target_string = templatize_string(tool_shed_str)
    else:
        target_string = tool_shed_str.replace("#", "\\#")
    to_ruby = (target_string.replace('"', '\\"'))
    if quote_now:
        return '"%s"' % to_ruby
    else:
        return to_ruby


def templatize_string(tool_shed_str):
    tool_shed_str.replace("#", "\\#")
    env_var_dict = {}
    env_var_dict['INSTALL_DIR'] = '#{prefix}'
    env_var_dict['system_install'] = '#{prefix}'
    # If the Python interpreter is 64bit then we can safely assume
    # that the underlying system is also 64bit.
    env_var_dict['__is64bit__'] = '#{Hardware.Hardware.is_64_bit?}'
    return string.Template(tool_shed_str).safe_substitute(env_var_dict)


class Package(BasePackage):

    def __init__(self, *args, **kwds):
        super(Package, self).__init__(*args, **kwds)
        self.extensions_used = set()

    def to_recipe(self):
        name = self.get_recipe_name()
        formula_builder = FormulaBuilder()
        if self.has_explicit_set_environments():
            # Required for environment method.
            formula_builder.require('json')

        name = name.replace("__", "_")
        parts = [p[0].upper() + p[1:] for p in name.split("__")]
        temp = "|".join(parts)
        parts = [p[0].upper() + p[1:] for p in temp.split("_")]
        class_name = "".join(parts).replace("|", "_")
        formula_builder.set_class_name(class_name)
        repo = self.dependencies.repo
        url = "%s/%s/%s" % (repo.tool_shed_url, repo.owner, repo.name)
        line = "# Recipe auto-generate from repository %s" % url
        formula_builder.add_line(line)
        if self.readme:
            formula_builder.add_line("# Tool Shed Readme:")
            for line in self.readme.split("\n"):
                formula_builder.add_line("#    %s" % line)
        formula_builder.add_line("")
        formula_builder.add_line('option "without-architecture", "Build '
                                 'without allowing architecture information ('
                                 'to force source install when binaries are '
                                 'available)."')
        formula_builder.add_line("")
        self.pop_download_block(formula_builder)
        formula_builder.add_line("")
        self.pop_deps(formula_builder)
        self.pop_install_def(formula_builder)
        self.pop_extensions(formula_builder)
        formula_builder.finish_formula()
        return "%s.rb" % name, formula_builder.to_file()

    def get_recipe_name(self):
        repo = self.dependencies.repo
        base = repo.recipe_base_name()
        if self.dependencies.single_package():
            return base
        else:
            return base + self.package_el.attrib["name"]

    def pop_install_def(self, formula_builder):
        formula_builder.add_and_indent("def install")
        multiple_set_environments = self.has_multiple_set_environments()
        if multiple_set_environments:
            formula_builder.add_line("environment_actions = []")

        def handle_actions(actions):
            if not actions.actions:
                return

            first_action = actions.actions[0]
            for_pop = actions.actions
            if first_action.action_type in ["download_by_url", "download_file"]:
                for_pop = for_pop[1:]

            return self.populate_actions(formula_builder, for_pop)

        if self.actions_diff_only_by_download():
            handle_actions(self.all_actions[0])
        else:
            self.conditional_action_map(formula_builder, handle_actions)

        if multiple_set_environments:
            formula_builder.add_line('''environment(environment_actions)''')

        formula_builder.end()

    def pop_deps(self, formula_builder):
        def handle_actions(actions):
            return self.populate_actions_packages(
                formula_builder,
                actions.action_packages
            )

        self.populate_actions_packages(
            formula_builder,
            self.dependencies.dependencies
        )
        self.conditional_action_map(formula_builder, handle_actions)

    def pop_extensions(self, formula_builder):
        for extension in self.extensions_used:
            ext_def = globals()["EXTENSION_%s" % extension].split("\n")
            map(formula_builder.add_line, ext_def)

    def populate_actions_packages(self, formula_builder, packages):
        for package in packages:
            repo = package.repo
            prefix = self.dependencies.tap.prefix
            base = "%s/%s" % (prefix, repo.recipe_base_name())
            formula_builder.add_line('depends_on "%s"' % base)

    def populate_actions(self, formula_builder, actions):
        for action in actions:
            handler = BrewActionHandler(self)
            statements = dispatch_on_action(
                handler, action, handler.unhandled_action
            )
            if not isinstance(statements, list):
                statements = [statements]
            for line in statements:
                formula_builder.add_line(line)

    def actions_diff_only_by_download(self):
        all_actions = self.all_actions
        first_actions = all_actions[0].actions
        for actions in all_actions[1:]:
            if len(first_actions) != len(actions.actions):
                return False
            for i, action in enumerate(actions.actions):
                download_action = action.action_type in ["download_by_url",
                                                         "download_file"]
                first_action = first_actions[0].action_type == action.action_type
                if download_action and first_action:
                    continue
                else:
                    if not action.same_as(first_actions[i]):
                        return False
        return True

    def pop_download_block(self, formula_builder):
        def func(actions):
            self.pop_download(actions, formula_builder)

        self.conditional_action_map(formula_builder, func)

    def conditional_action_map(self, formula_builder, func):
        all_actions = self.all_actions
        if len(all_actions) == 1:
            func(all_actions[0])
        else:
            self._complex_conditional(formula_builder, func)

    def _complex_conditional(self, formula_builder, func):
        all_actions = self.all_actions
        for i, actions in enumerate(all_actions):
            if i > 0:
                formula_builder.unindent()
            conds = []
            if actions.os and actions.os == "linux":
                conds.append("OS.linux?")
            elif actions.os and actions.os == "darwin":
                conds.append("OS.mac?")
            if actions.architecture and actions.architecture == "x86_64":
                conds.append("Hardware.is_64_bit?")
            elif actions.architecture and actions.architecture == "i386":
                conds.append("Hardware.is_32_bit?")
            if conds and self.no_arch_option:
                conds.append('!build.without?("architecture")')
            conds_str = " and ".join(conds)
            if not conds_str:
                assert i == len(all_actions) - 1, actions
                formula_builder.add_and_indent("else")
                func(actions)
            else:
                cond_op = "%sif" % ("" if i == 0 else "els")
                line = "%s %s" % (cond_op, conds_str)
                formula_builder.add_and_indent(line)
                func(actions)
        formula_builder.end()

    def has_no_achitecture_install(self):
        all_actions = self.all_actions
        if len(all_actions) < 2:
            return False
        else:
            last_action = all_actions[-1]
            return (not last_action.architecture) and (not last_action.os)

    def has_explicit_set_environments(self):
        all_actions = self.all_actions
        for actions in all_actions:
            for action in actions.actions:
                if Package.explicit_variables(action):
                    return True
        return False

    def has_multiple_set_environments(self):
        all_actions = self.all_actions
        for actions in all_actions:
            count = 0
            for action in actions.actions:
                if Package.explicit_variables(action):
                    count += 1
            if count > 1:
                return True
        return False

    @staticmethod
    def explicit_variables(action):
        if action.action_type == "set_environment":
            return filter(lambda v: v.explicit,
                          map(BrewSetVariable, action.variables))
        else:
            return []

    def pop_download(self, actions, formula_builder):
        one_populated = False
        for action in actions.downloads():
            if one_populated:
                resource = url_to_resource(action.url)
                line = "resource '%s' do" % resource
                formula_builder.add_and_indent(line)
                self.pop_single_download(action, formula_builder)
                formula_builder.end()
            else:
                self.pop_single_download(action, formula_builder)
            one_populated = True
        if not one_populated:
            self.pop_single_download(None, formula_builder)

    def pop_single_download(self, action, formula_builder):
        if action is None:
            url = "http://ftpmirror.gnu.org/hello/hello-2.9.tar.gz"
            sha1 = "cb0470b0e8f4f7768338f5c5cfe1688c90fbbc74"
        else:
            url = action.url
            sha1 = self.fetch_sha1(url)
        download_line = '''url "%s"''' % url
        if action and action.action_type == "download_file" and not action.extract:
            download_line += ", :using => :nounzip"
        if action is None:
            formula_builder.add_line("# Each homebrew formula must have at "
                                     "least one download, tool shed doesn't "
                                     "require this so hacking in hello source"
                                     " download.")
        formula_builder.add_line(download_line)
        formula_builder.add_line('''sha1 "%s"''' % sha1)

    def fetch_sha1(self, url):
        return ''  # TODO

    def __repr__(self):
        actions = self.all_actions
        parts = (
            self.package_el.attrib["name"],
            self.package_el.attrib["version"],
            self.dependencies,
            actions
        )
        template = "Install[name=%s,version=%s,dependencies=%s,actions=%s]"
        return template % parts


def url_to_resource(url):
    path = urlparse.urlparse(url).path
    name = os.path.split(path)[1]
    base = name.rstrip("\.tar\.gz").rstrip("\.zip")
    return base


class RubyBuilder(object):

    def __init__(self):
        self.lines = []
        self.indent = 0

    def add_line(self, line):
        indent_spaces = "  " * self.indent
        self.lines.append("%s%s" % (indent_spaces, line))

    def add_and_indent(self, line):
        self.add_line(line)
        self.indent += 1

    def end(self):
        self.unindent()
        self.add_line("end")

    def unindent(self):
        self.indent -= 1

    def to_file(self):
        assert self.indent == 0, "\n".join(self.lines)
        return "\n".join(self.lines)

    def require(self, module):
        assert self.indent == 0
        self.add_line("require '%s'" % module)


class FormulaBuilder(RubyBuilder):

    def __init__(self):
        super(FormulaBuilder, self).__init__()
        self.require('formula')

    def set_class_name(self, name):
        self.add_line("")
        self.add_and_indent("class %s < Formula" % name)
        self.add_line('version "1.0"')

    def finish_formula(self):
        self.end()


def shell(cmds, **popen_kwds):
    click.echo(cmds)
    p = subprocess.Popen(cmds, shell=True, **popen_kwds)
    return p.wait()


def repos(tool_shed_url, name_filter=None, owner=None):
    ts = toolshed.ToolShedInstance(url=TOOLSHED)
    repos = ts.repositories.get_repositories()
    if owner:
        repos = [r for r in repos if r["owner"] == owner]
    if name_filter:
        pattern = re.compile(name_filter)
        repos = [r for r in repos if pattern.match(r["name"])]
    return repos


if __name__ == "__main__":
    main()
