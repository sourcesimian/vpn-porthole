import sys
import os
from configobj import ConfigObj, get_extra_values, DuplicateError
from validate import Validator
from pkg_resources import resource_stream

from vpnporthole.ip import IPv4Subnet


class Settings(object):
    __proxy = None
    __sudo_password = None

    def __init__(self, profile, config=None, proxy=None):
        self.__profile_name = profile
        self.__confobj = self.__get_confobj(config)
        try:
            self.__profile = self.__confobj['session'][profile]
        except KeyError:
            sys.stderr.write('! Profile "%s" not found\n' % profile)
            exit(1)
        if proxy:
            self.__proxy = self.__confobj['proxy'][proxy]

    @property
    def profile(self):
        return self.__profile_name

    def proxy(self):
        if not self.__proxy:
            return None
        return self.__proxy['http_proxy']

    def username(self):
        return self.__extract(self.__profile['username'])

    def password(self):
        pwd = self.__profile['password']
        if not pwd:
            import getpass
            pwd = getpass.getpass('')
        return self.__extract(pwd)

    def sudo(self):
        try:
            pwd = self.__confobj['system']['sudo']
        except KeyError:
            pwd = ''
        if not pwd:
            if self.__sudo_password is not None:
                return self.__sudo_password
            import getpass
            pwd = getpass.getpass('Enter sudo password:')
            self.__sudo_password = pwd
        return self.__extract(pwd)

    def custom_system(self):
        for key in sorted(self.__profile['custom']['system'].keys()):
            yield self.__profile['custom']['system'][key]

    def custom_user(self):
        for key in sorted(self.__profile['custom']['user'].keys()):
            yield self.__profile['custom']['user'][key]

    def custom_openconnect(self):
        args = []
        for key in sorted(self.__profile['custom']['openconnect'].keys()):
            value = self.__profile['custom']['openconnect'][key]
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

    @classmethod
    def __default_settings_path(cls):
        return os.path.expanduser('~/.config/vpn-porthole/settings.conf')

    @classmethod
    def __default_settings_content(cls):
        return resource_stream("vpnporthole", "resources/settings.conf.example").read()

    @classmethod
    def list_profiles(cls, config):
        config = config or cls.__default_settings_path()
        confobj = cls.__get_confobj(config)
        return {p: v for p, v in confobj['session'].items()}

    @classmethod
    def __get_confobj(cls, config):
        if config is None:
            config = cls.__default_settings_path()
            if not os.path.isdir(os.path.dirname(config)):
                os.makedirs(os.path.dirname(config))
        if not os.path.isfile(config):
            with open(config, 'w+b') as fh:
                fh.write(cls.__default_settings_content())
            print("* Configure vpn-porthole in: %s" % config)
            exit(1)

        spec_lines = resource_stream("vpnporthole", "resources/settings.spec").readlines()

        try:
            confobj = ConfigObj(config, configspec=spec_lines, raise_errors=True)
        except DuplicateError as e:
            sys.stderr.write('Bad settings file: %s\n' % e)
            exit(3)

        if not cls.__validate_confobj(confobj):
            exit(3)
        return confobj

    @classmethod
    def __validate_confobj(cls, confobj):
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
            sys.stderr.write('Unknown keys in settings file:\n')
            for key in bad_keys:
                sys.stderr.write(' - /%s\n' % '/'.join(key))

        if bad_values:
            sys.stderr.write('Bad values in settings file:\n')
            for key in bad_values:
                value = confobj
                for k in key:
                    value = value[k]
                sys.stderr.write(' - /%s = %s\n' % ('/'.join(key), value))

        return not bad_keys and not bad_values
