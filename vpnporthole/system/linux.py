import glob
import os
import tempfile

from vpnporthole.ip import IPv4Subnet
from vpnporthole.system.base import SystemCallsBase


class SystemCalls(SystemCallsBase):

    def add_route(self, subnet):
        self._shell(['sudo', 'ip', 'route', 'add', str(subnet), 'via', self._ip])

    def del_route(self, subnet):
        self._shell(['sudo', 'ip', 'route', 'del', str(subnet)])

    def list_routes(self):
        subnets = []
        if self._ip:
            lines = self._shell(['sudo', 'ip', 'route', 'show', 'via', self._ip])
            for line in lines:
                subnets.append(IPv4Subnet(line.split()[0]))
        return subnets

    def add_domain(self, domain):
        with tempfile.NamedTemporaryFile() as temp:
            temp.file.write(bytes('server=/%s/%s  # %s\n' % (domain, self._ip, self._tag), 'utf-8'))
            temp.file.flush()
            self._shell(['sudo', 'cp', temp.name, '/etc/NetworkManager/dnsmasq.d/%s' % domain])
            temp.close()

        # /etc/NetworkManager/dnsmasq.d/foo
        # server=/domain.intra/192.168.30.1

        # sudo service network-manager restart

        # echo "nameserver $container_ip  # $name" | sudo tee -a /etc/resolvconf/resolv.conf.d/head >/dev/null
        # sudo sudo resolvconf -u
        pass

        # With dnsmasq:
        # /etc/resolv.conf:
        #
        # nameserver 127.0.0.1
        # nameserver 208.67.222.222
        # nameserver 208.67.220.220

        # /etc/dnsmasq.conf:
        #
        # server=/freenode.net/8.8.8.8
        # server=/freenode.net/8.8.4.4

    def del_domain(self, domain):
        self._shell(['sudo', 'rm', '/etc/NetworkManager/dnsmasq.d/%s' % domain])

        # if grep "$name" /etc/resolvconf/resolv.conf.d/head >/dev/null; then
        #     sudo sed -i "/  # $name/d" /etc/resolvconf/resolv.conf.d/head
        #     sudo sudo resolvconf -u
        # fi
        pass

    def list_domains(self):
        domains = []
        all_files = glob.glob('/etc/NetworkManager/dnsmasq.d/*')
        if all_files:
            for line in self._shell(['sudo', 'grep', '-l', self._tag] + all_files):
                domains.append(os.path.basename(line.strip()))
        return domains
