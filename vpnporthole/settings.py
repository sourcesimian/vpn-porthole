import sys
import os
from configobj import ConfigObj, get_extra_values, DuplicateError
from validate import Validator
from pkg_resources import resource_stream

from vpnporthole.ip import IPv4Subnet


class Settings(object):
    __proxy = None
    __sudo_password = None

    def __init__(self, session, proxy=None):
        self.__session_name = session
        self.__settings = self.__get_settings()
        try:
            self.__session = self.__settings['session'][session]
        except KeyError:
            sys.stderr.write('! Session "%s" not found\n' % session)
            exit(1)
        if proxy:
            self.__proxy = self.__settings['proxy'][proxy]

    @property
    def session(self):
        return self.__session_name

    @property
    def docker_machine(self):
        machine = self.__session['docker']['machine']
        if machine:
            return machine
        machine = self.__settings['docker']['machine']
        if machine:
            return machine
        return None

    @property
    def socks5_port(self):
        return self.__session['socks5']['port']

    def proxy(self):
        if not self.__proxy:
            return None
        return self.__proxy['http_proxy']

    def username(self):
        usr = self.__extract(self.__session['username'])
        if not usr:
            # TODO: add prompting for username
            pass
        return usr

    def password(self):
        pwd = self.__session['password']
        if not pwd:
            import getpass
            pwd = getpass.getpass('')
        return self.__extract(pwd)

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

    def custom_files(self):
        from textwrap import dedent
        ret = {}
        for k, v in self.__session['dockerfile']['files'].iteritems():
            if v.startswith((' ', '\n', '\t', '\\')):
                ret[k] = dedent(v[v.find('\n') + 1:]).rstrip(' ')
            else:
                with open(os.path.expanduser(v), 'rt') as fh:
                    ret[k] = fh.read()
        return ret

    def custom_system(self):
        for key in sorted(self.__session['dockerfile']['system'].keys()):
            yield self.__session['dockerfile']['system'][key]

    def custom_user(self):
        for key in sorted(self.__session['dockerfile']['user'].keys()):
            yield self.__session['dockerfile']['user'][key]

    def custom_openconnect(self):
        args = []
        for key in sorted(self.__session['openconnect'].keys()):
            value = self.__session['openconnect'][key]
            args.extend(value.split(' ', 1))
        return args

    def __extract(self, value):
        if value and value.startswith('SHELL:'):
            import subprocess
            value = subprocess.check_output(value[6:], shell=True).decode('utf-8').rstrip()
        return value

    def vpn(self):
        return self.__session['vpn']

    def subnets(self):
        return [IPv4Subnet(k)
                for k, v in self.__session['subnets'].items()
                if v is True]

    def domains(self):
        return [k
                for k, v in self.__session['domains'].items()
                if v is True]

    @classmethod
    def __default_settings_root(cls):
        return os.path.expanduser('~/.config/vpn-porthole')

    @classmethod
    def list_sessions(cls):
        settings = cls.__get_settings()
        return {p: v for p, v in settings['session'].items()}

    @classmethod
    def __ensure_config_setup(cls):
        root = cls.__default_settings_root()
        if not os.path.exists(root):
            os.makedirs(root)

        settings = os.path.join(root, 'settings.conf')
        if not os.path.exists(settings):
            with open(settings, 'w+b') as fh:
                content = resource_stream("vpnporthole", "resources/settings.conf.example").read()
                fh.write(content)
            print("* Wrote: %s" % settings)

        root = os.path.join(root, 'sessions')
        if not os.path.exists(root):
            os.makedirs(root)

            session = os.path.join(root, 'example.conf')
            if not os.path.exists(session):
                with open(session, 'w+b') as fh:
                    content = resource_stream("vpnporthole", "resources/session.conf.example").read()
                    fh.write(content)
                print("* Wrote: %s" % session)

    @classmethod
    def __get_settings(cls):
        cls.__ensure_config_setup()
        config_root = cls.__default_settings_root()

        settings_file = os.path.join(config_root, 'settings.conf')
        sessions_glob = os.path.join(config_root, 'sessions', '*.conf')

        settings_spec_lines = resource_stream("vpnporthole", "resources/settings.spec").readlines()
        session_spec_lines = resource_stream("vpnporthole", "resources/session.spec").readlines()

        settings = cls.__load_configobj(settings_file, settings_spec_lines)
        if not settings:
            exit(3)

        settings['session'] = {}

        from glob import glob
        session_to_file_map = {}
        for session_file in glob(sessions_glob):
            sessions = cls.__load_configobj(session_file, session_spec_lines)
            if not settings:
                exit(3)

            for name, session in sessions['session'].iteritems():
                if name in settings['session']:
                    sys.stderr.write('! Duplicate session "%s" in: "%s" and "%s"\n' %
                                     (name, session_file, session_to_file_map[name]))
                    exit(3)
                session_to_file_map[name] = session_file
                settings['session'][name] = session

        return settings

    @classmethod
    def __load_configobj(cls, config_file, spec_lines):
        try:
            confobj = ConfigObj(config_file, configspec=spec_lines, raise_errors=True)
        except DuplicateError as e:
            sys.stderr.write('! Bad config file "%s": %s\n' % (config_file, e))
            return None

        bad_values = []
        bad_keys = []
        result = confobj.validate(Validator())
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
                for k in key:
                    value = value[k]
                sys.stderr.write('  - /%s = %s\n' % ('/'.join(key), value))

        if bad_keys or bad_values:
            return None
        return confobj
