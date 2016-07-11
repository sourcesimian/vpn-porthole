import os
import subprocess
import tempfile
import glob

from vpnporthole.ip import IPv4Subnet
from vpnporthole.system.base import SystemCallsBase


class SystemCalls(SystemCallsBase):
    __host_ip_cache = None

    def connect(self):
        self.__host_ssh(['sudo', '/usr/local/sbin/iptables',
                         '-t', 'nat',
                         '-A', 'POSTROUTING',
                         '-o', 'docker0',
                         '-j', 'MASQUERADE'])

        self.__host_ssh(['sudo', '/usr/local/sbin/iptables',
                         '-A', 'FORWARD',
                         '-i', 'eth1',
                         '-j', 'ACCEPT'])

        self._shell(['sudo', 'route', '-n', 'add', '%s/32' % self._ip, self.__host_ip()])

    def disconnect(self):
        if self._ip:
            self._shell(['sudo', 'route', '-n', 'delete', '%s/32' % self._ip, self.__host_ip()])

    def add_route(self, subnet):
        self.__host_ssh(['sudo', 'ip', 'route', 'add', str(subnet), 'via', self._ip])

        self._shell(['sudo', 'route', '-n', 'add', str(subnet), self.__host_ip()])

    def del_route(self, subnet):
        self._shell(['sudo', 'route', '-n', 'delete', str(subnet)])

        self.__host_ssh(['sudo', 'ip', 'route', 'del', str(subnet)])

    def list_routes(self):
        subnets = []
        if not self._ip:
            return []
        for line in self.__host_ssh(['sudo', 'ip', 'route', 'show', 'via', self._ip]):
            subnets.append(IPv4Subnet(line.split()[0]))
        return subnets

    def add_domain(self, domain):
        with tempfile.NamedTemporaryFile() as temp:
            temp.file.write(bytes('nameserver %s  # %s\n' % (self._ip, self._tag), 'utf-8'))
            temp.file.flush()
            self._shell(['sudo', 'cp', temp.name, '/etc/resolver/%s' % domain])
            temp.close()

    def del_domain(self, domain):
        self._shell(['sudo', 'rm', '/etc/resolver/%s' % domain])

    def list_domains(self):
        domains = []
        all_files = glob.glob('/etc/resolver/*')
        if all_files:
            for line in self._shell(['sudo', 'grep', '-l', self._tag] + all_files):
                domains.append(os.path.basename(line.strip()))
        return domains

    def __host_ssh(self, args):
        machine = os.environ['DOCKER_MACHINE_NAME']

        base = ['docker-machine', 'ssh', machine]
        base.extend(args)
        return self._shell(base)

    def __host_ip(self):
        if self.__host_ip_cache:
            return self.__host_ip_cache
        machine = os.environ['DOCKER_MACHINE_NAME']

        args = ['docker-machine', 'ip', machine]
        p = self._popen(args, stdout=subprocess.PIPE)
        line = ''
        for line in p.stdout:
            pass
        p.wait()

        self.__host_ip_cache = line.decode('utf-8').strip()
        return self.__host_ip_cache
