import sys
import os
from configobj import ConfigObj, get_extra_values, DuplicateError
from validate import Validator
from pkg_resources import resource_stream

from vpnporthole.ip import IPv4Subnet


class Settings(object):
    __sudo_password = None
    __ctx = None

    def __init__(self, profile_name):
        self.__profile_name = profile_name
        self.__ensure_config_setup()
        self.__settings = self.__get_settings()
        self.__profile = self.__get_profile(profile_name)
        if not self.__settings or not self.__profile:
            exit(3)

    @property
    def profile_name(self):
        return self.__profile_name

    @property
    def docker_machine(self):
        machine = self.__profile['docker']['machine']
        if machine:
            return machine
        machine = self.__settings['docker']['machine']
        if machine:
            return machine
        return None

    def username(self):
        usr = self.__extract(self.__profile['username'])
        if not usr:
            usr = input("")
        return usr

    def password(self):
        pwd = self.__extract(self.__profile['password'])
        if not pwd:
            import getpass
            pwd = getpass.getpass('')
        return pwd

    def sudo(self):
        try:
            pwd = self.__settings['system']['sudo']
        except KeyError:
            pwd = ''
        if not pwd:
            if self.__sudo_password is not None:
                return self.__sudo_password
            import getpass
            pwd = getpass.getpass('Enter sudo password:')
            Settings.__sudo_password = pwd
        return self.__extract(pwd)

    def build_files(self):
        ret = {}
        for filename, content in self.__profile['build']['files'].iteritems():
            if content:
                content = self.__file_content(content)
                if filename.endswith('.tmpl'):
                    content = self.__render_template(content)
                    filename = filename[:-5]
                ret[filename] = content
        return ret

    def run_hook_files(self):
        ret = {}
        for filename, content in self.__profile['run']['hooks'].iteritems():
            if content:
                content = self.__file_content(content)
                content = self.__render_template(content)
                ret[filename] = content
        return ret

    def __file_content(self, value):
        from textwrap import dedent
        if value.startswith((' ', '\n', '\t', '\\')):
            return dedent(value[value.find('\n') + 1:]).rstrip(' ')
        else:
            try:
                with open(os.path.expanduser(value), 'rt') as fh:
                    return fh.read()
            except FileNotFoundError:
                raise FileNotFoundError('"%s"' % value)

    def __render_template(self, content):
        from tempita import Template
        template = Template(content)

        result = template.substitute(**{k: self.ctx[k] for k in self.ctx})
        return result

    def build_options(self):
        ret = {}
        for k, v in self.__profile['build']['options'].iteritems():
            if v:
                ret[k] = self.__extract(v)
        return ret

    def run_options(self):
        args = []
        for key in sorted(self.__profile['run']['options'].keys()):
            value = self.__profile['run']['options'][key]
            args.extend(value.split(' ', 1))
        return args

    def __extract(self, value):
        if value and value.startswith('SHELL:'):
            import subprocess
            value = subprocess.check_output(value[6:], shell=True).decode('utf-8').rstrip()
        return value

    def vpn(self):
        return self.__profile['vpn']

    def subnets(self):
        return [IPv4Subnet(k)
                for k, v in self.__profile['subnets'].items()
                if v is True]

    def domains(self):
        return [k
                for k, v in self.__profile['domains'].items()
                if v is True]

    @property
    def ctx(self):
        if not self.__ctx:
            import pwd
            import grp

            class dotdict(dict):
                __getattr__ = dict.get
                __setattr__ = dict.__setitem__

            gid = os.getgid()
            uid = os.getuid()

            user = dotdict()
            user.gid = gid
            user.group = grp.getgrgid(gid).gr_name
            user.uid = uid
            user.name = pwd.getpwuid(uid).pw_name

            local = dotdict()
            local.user = user

            vpn = dotdict()
            vpn.addr = self.vpn()

            option = dotdict()
            for k, v in self.build_options().items():
                option[k] = v

            vpnp = dotdict()
            from textwrap import dedent
            vpnp.hooks = dedent('''
                    ADD vpnp/ /vpnp/
                    RUN sudo chmod +x /vpnp/*
            ''')

            ctx = dotdict()
            ctx.local = local
            ctx.vpn = vpn
            ctx.vpnp = vpnp
            ctx.option = option

            self.__ctx = ctx

        return self.__ctx

    @classmethod
    def __default_settings_root(cls):
        return os.path.expanduser('~/.config/vpn-porthole')

    @classmethod
    def __ensure_config_setup(cls):
        root = cls.__default_settings_root()
        if not os.path.exists(root):
            os.makedirs(root)

        settings_file = os.path.join(root, 'settings.conf')
        if not os.path.exists(settings_file):
            with open(settings_file, 'w+b') as fh:
                content = resource_stream("vpnporthole", "resources/settings.conf").read()
                fh.write(content)
            print("* Wrote: %s" % settings_file)

        root = os.path.join(root, 'profiles')
        if not os.path.exists(root):
            os.makedirs(root)

            profile_file = os.path.join(root, 'example.conf')
            if not os.path.exists(profile_file):
                with open(profile_file, 'w+b') as fh:
                    content = resource_stream("vpnporthole", "resources/example.conf").read()
                    fh.write(content)
                print("* Wrote: %s" % profile_file)

    @classmethod
    def __get_settings(cls):
        config_root = cls.__default_settings_root()

        settings_file = os.path.join(config_root, 'settings.conf')
        settings_spec_lines = resource_stream("vpnporthole", "resources/settings.spec").readlines()

        settings = cls.__load_configobj(settings_file, settings_spec_lines)
        if not settings:
            exit(3)
        return settings

    @classmethod
    def __get_profile(cls, name):
        config_root = cls.__default_settings_root()

        if name in ('all',):
            sys.stderr.write('! Invalid profile name "%s"\n' % name)
            exit(1)

        session_file = os.path.join(config_root, 'profiles', '%s.conf' % name)
        session_spec_lines = resource_stream("vpnporthole", "resources/profile.spec").readlines()

        profile = cls.__load_configobj(session_file, session_spec_lines)

        return profile

    @classmethod
    def list_profile_names(cls):
        names = []

        config_root = cls.__default_settings_root()
        sessions_glob = os.path.join(config_root, 'profiles', '*.conf')

        from glob import glob
        for session_file in glob(sessions_glob):
            name = os.path.splitext(os.path.basename(session_file))[0]
            names.append(name)
        return names

    @classmethod
    def __load_configobj(cls, config_file, spec_lines):
        try:
            confobj = ConfigObj(config_file, configspec=spec_lines, raise_errors=True,
                                interpolation=False)
        except DuplicateError as e:
            sys.stderr.write('! Bad config file "%s": %s\n' % (config_file, e))
            return None
        except Exception as e:
            sys.stderr.write('! Bad config file "%s": %s\n' % (config_file, e))
            return None

        bad_values = []
        bad_keys = []
        result = confobj.validate(Validator())
        if result is False:
            sys.stderr.write('! Unable to validate config file "%s":\n' % config_file)
            return None
        if result is not True:
            def walk(node, dir):
                for key, item in node.items():
                    path = dir + [key]
                    if isinstance(item, dict):
                        walk(item, path)
                    else:
                        if item is False:
                            bad_values.append(path)
            walk(result, [])
        extra = get_extra_values(confobj)
        if extra:
            for path, key in extra:
                bad_keys.append(list(path) + [key])

        if bad_keys:
            sys.stderr.write('! Unknown keys in config file "%s":\n' % config_file)
            for key in bad_keys:
                sys.stderr.write('  - /%s\n' % '/'.join(key))

        if bad_values:
            sys.stderr.write('! Bad values in settings file "%s":\n' % config_file)
            for key in bad_values:
                value = confobj
                try:
                    for k in key:
                        value = value[k]
                except KeyError:
                    value = '<missing>'
                sys.stderr.write('  - /%s = %s\n' % ('/'.join(key), value))

        if bad_keys or bad_values:
            return None
        return confobj
