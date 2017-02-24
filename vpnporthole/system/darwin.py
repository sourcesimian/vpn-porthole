import os
import sys
import subprocess
import tempfile
import glob
import re

from vpnporthole.ip import IPv4Subnet
from vpnporthole.system.base import SystemCallsBase


class SystemCalls(SystemCallsBase):
    __host_ip_cache = None

    def __init__(self, *args, **kwargs):
        super(SystemCalls, self).__init__(*args, **kwargs)
        self.__docker_env = self.__get_docker_env()

    def on_connect(self):
        self.__host_ssh_check(['sudo', '/usr/local/sbin/iptables',
                               '-t', 'nat',
                               '-A', 'POSTROUTING',
                               '-o', 'docker0',
                               '-j', 'MASQUERADE'])

        self.__host_ssh_check(['sudo', '/usr/local/sbin/iptables',
                               '-A', 'FORWARD',
                               '-i', 'eth1',
                               '-j', 'ACCEPT'])

        if self._ip:
            self._shell(['sudo', 'route', '-n', 'add', '%s/32' % self._ip, self.__host_ip()])

    def on_disconnect(self):
        if self._ip:
            self._shell(['sudo', 'route', '-n', 'delete', '%s/32' % self._ip, self.__host_ip()])

    def add_route(self, subnet):
        if self._ip:
            self.__host_ssh_check(['sudo', 'ip', 'route', 'add', str(subnet), 'via', self._ip])

        self._shell_check(['sudo', 'route', '-n', 'add', str(subnet), self.__host_ip()])

    def del_route(self, subnet):
        self._shell(['sudo', 'route', '-n', 'delete', str(subnet)])

        self.__host_ssh(['sudo', 'ip', 'route', 'del', str(subnet)])

    def list_routes(self):
        subnets = []
        if not self._ip:
            return []
        _, lines = self.__host_ssh(['ip', 'route', 'show', 'via', self._ip])
        for line in lines:
            subnets.append(IPv4Subnet(line.split()[0]))
        return subnets

    def add_domain(self, domain):
        if not self._ip:
            return
        with tempfile.NamedTemporaryFile() as temp:
            temp.file.write(bytes('nameserver %s  # %s\n' % (self._ip, self._tag), 'utf-8'))
            os.chmod(temp.name, 0o644)
            temp.file.flush()
            self._shell_check(['sudo', 'cp', temp.name, '/etc/resolver/%s' % domain])
            temp.close()

    def del_domain(self, domain):
        self._shell(['sudo', 'rm', '/etc/resolver/%s' % domain])

    def list_domains(self):
        domains = []
        all_files = glob.glob('/etc/resolver/*')
        if all_files:
            for line in self._shell(['grep', '-l', self._tag] + all_files)[1]:
                domains.append(os.path.basename(line.strip()))
        return domains

    def __host_ssh(self, args):
        base = ['docker-machine', 'ssh', self.__docker_env['DOCKER_MACHINE_NAME']]
        base.extend(args)
        return self._shell(base)

    def __host_ssh_check(self, args):
        base = ['docker-machine', 'ssh', self.__docker_env['DOCKER_MACHINE_NAME']]
        base.extend(args)
        return self._shell_check(base)

    def __host_ip(self):
        if self.__host_ip_cache:
            return self.__host_ip_cache

        args = ['docker-machine', 'ip', self.__docker_env['DOCKER_MACHINE_NAME']]
        p = self._popen(args, stdout=subprocess.PIPE)
        line = ''
        for line in p.stdout:
            pass
        p.wait()

        self.__host_ip_cache = line.decode('utf-8').strip()
        return self.__host_ip_cache

    def get_docker_env(self):
        return self.__docker_env

    def __get_docker_env(self):
        machine = self._settings.docker_machine

        environ = {}
        vars = ('DOCKER_TLS_VERIFY', 'DOCKER_HOST', 'DOCKER_CERT_PATH', 'DOCKER_MACHINE_NAME')

        if not machine:
            for var in vars:
                try:
                    environ[var] = os.environ[var]
                except KeyError as e:
                    sys.stderr.write('! %s not found in environment\n' % e)
                    exit(3)
        else:
            env_patten = re.compile('export (?P<name>.*)="(?P<value>.*)"')
            try:
                stdout = subprocess.check_output(['docker-machine', 'env', machine])
            except subprocess.CalledProcessError:
                sys.stderr.write('! Failed to get env for docker-machine "%s"\n' % (machine,))
                stdout = subprocess.check_output(['docker-machine', 'ls'])
                sys.stderr.write(stdout.decode())
                exit(3)
            for line in stdout.decode().split('\n'):
                m = env_patten.match(line)
                if m:
                    environ[m.group('name')] = m.group('value')
            for var in vars:
                if var not in environ:
                    sys.stderr.write(
                        '! Expected "%s" in env for docker-machine "%s"\n' % (var, machine))
                    exit(3)

        return environ
