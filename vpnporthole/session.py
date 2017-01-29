import os
from pkg_resources import resource_stream
from docker import Client as DockerClient

from vpnporthole.ip import IPv4Subnet
from vpnporthole.system import TmpDir, SystemCalls


Dockerfile_tmpl = resource_stream("vpnporthole", "resources/Dockerfile.tmpl").read().decode("utf-8")


class Session(object):
    __dnsmasq_port = 53
    __ip = None

    def __init__(self, settings):
        self.__settings = settings
        self.__sc = SystemCalls(self._tag(), self.__settings)
        self.__dc = DockerClient.from_env(environment=self.__sc.get_docker_env())

    def _local_user(self):
        return os.environ['USER']

    def _tag(self):
        return "vpnp_%s_%s" % (self._local_user(), self.__settings.session)

    def _prefix(self):
        return self._tag() + '_'

    def _ctx(self):
        ctx = {
            'gid': os.getgid(),
            'group': 'user',
            'uid': os.getuid(),
            'user': 'user',
        }
        return ctx

    def build(self):

        ctx = self._ctx()
        tag = self._tag()

        http_proxy = self.__settings.proxy()

        if http_proxy:
            ctx['proxy'] = "RUN echo 'Acquire::http::proxy \"%(http_proxy)s\";' > /etc/apt/apt.conf" % \
                           {'http_proxy': http_proxy}
        else:
            ctx['proxy'] = '# No proxy'

        ctx['vpn'] = self.__settings.vpn()

        ctx['optional_system'] = ''

        if self.__settings.socks5_port:
            from textwrap import dedent
            install_ssh_client = dedent(
                """\
                RUN apt-get update &&\
                 apt-get install -y openssh-client &&\
                 apt-get autoremove -y &&\
                 apt-get clean -y
                """
            )
            ctx['optional_system'] += install_ssh_client

        ctx['custom_system'] = '\n'.join(self.__settings.custom_system())
        ctx['custom_user'] = '\n'.join(self.__settings.custom_user())

        with TmpDir() as tmp:
            for filename, content in self.__settings.custom_files().items():
                userfile = os.path.join(tmp.path, filename)
                if filename.endswith('.tmpl'):
                    content = content % ctx
                    userfile = userfile[:-5]
                with open(userfile, 'wt') as fh:
                    fh.write(content)
                os.utime(userfile, (0, 0))

            Dockerfile = os.path.join(tmp.path, 'Dockerfile')
            with open(Dockerfile, 'w') as fh:
                fh.write(Dockerfile_tmpl % ctx)
            os.utime(Dockerfile, (0, 0))

            stream = self.__dc.build(tmp.path, tag=tag)
            import json
            for buf in stream:
                block = json.loads(buf.decode('utf-8'))
                if 'stream' in block:
                    self.__sc.stdout.write(block['stream'])
                if 'error' in block:
                    self.__sc.stdout.write(block['error'] + '\n')
                    exit(3)
            image = block['stream'].split()[2]
            return image

    def start(self):

        if self.status():
            self.__sc.stderr.write("Already running\n")
            return 3

        if not self._images():
            self.build()

        self.__ip = None
        self.__sc.container_ip(None)

        image = self._tag()

        args = ['/usr/bin/sudo', 'openconnect', self.__settings.vpn(), '--interface', 'tun1']

        args.extend(self.__settings.custom_openconnect())

        pe = self.__sc.docker_run_expect(image, args)
        try:
            old_pwd = None
            while True:
                i = pe.expect(['Username:', 'Password:', 'Established', 'Login failed.'])
                if i < 0:
                    pe.wait()
                    return pe.exitstatus
                if i == 0:
                    pe.sendline(self.__settings.username())
                if i == 1:
                    pwd = self.__settings.password()
                    if old_pwd == pwd:  # Prevent lockout
                        self.__sc.stderr.write(" <password was same as previous attempt> \n")
                        pe.send(chr(3))
                        pe.wait()
                        return 3
                    old_pwd = pwd
                    pe.sendline('%s' % pwd)
                if i == 2:
                    break
                if i == 3:
                    pass
        except (Exception, KeyboardInterrupt) as e:
            pe.send(chr(3))
            pe.wait()
            self.__sc.stderr.write('%s\n' % e)
            raise

        ip = self._ip()
        self.__sc.container_ip(ip)

        args = ['/usr/bin/sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', 'tun1', '-j', 'MASQUERADE']
        self.__sc.docker_exec(self.__dc, self._container()['Id'], args)

        args = ['/usr/bin/sudo', '/etc/init.d/dnsmasq', 'start']
        self.__sc.docker_exec(self.__dc, self._container()['Id'], args)

        if self.__settings.socks5_port:
            args = ['/usr/bin/ssh', '-f', '-N', '-D',
                    '0.0.0.0:%s' % self.__settings.socks5_port, 'localhost']
            self.__sc.docker_exec(self.__dc, self._container()['Id'], args)

        print("- Container IP: %s" % ip)

        self.__sc.connect()

        for subnet in self.__settings.subnets():
            self.__sc.add_route(subnet)

        for domain in self.__settings.domains():
            self.__sc.add_domain(domain)

        self.info()

    def add_route(self, subnet):
        subnet = IPv4Subnet(subnet)
        ip = self._ip()
        if ip is None:
            return 1
        self.__sc.container_ip(ip)
        self.__sc.add_route(subnet)

    def del_route(self, subnet):
        subnet = IPv4Subnet(subnet)
        ip = self._ip()
        self.__sc.container_ip(ip)
        for sn in self.__sc.list_routes():
            if sn in subnet:
                self.__sc.del_route(sn)

    def add_domain(self, domain):
        ip = self._ip()
        self.__sc.container_ip(ip)
        if ip is None:
            return 1
        self.__sc.add_domain(domain)

    def del_domain(self, domain):
        ip = self._ip()
        if ip is None:
            return 1
        domains = self.__sc.list_domains()
        if domain in domains:
            self.__sc.del_domain(domain)

    def status(self):
        if self._container():
            return True
        return False

    def _images(self):
        tag = self._tag()
        all_images = self.__dc.images()

        return [i for i in all_images if any([True for t in i['RepoTags'] if t.startswith(tag)])]

    def _containers(self):
        tag = self._tag()
        all_containers = self.__dc.containers(all=True)
        return [c for c in all_containers
                if c['Image'] == tag]

    def _container(self):
        running = [c for c in self._containers()
                   if c['State'] == 'running']
        if not running:
            return None
        if len(running) > 1:
            print('WARNING: there is more than one container: %s' % running)
        return running[0]

    def _ip(self):
        if self.__ip:
            return self.__ip
        container = self._container()
        if container:
            info = self.__dc.inspect_container(container)
            if info:
                self.__ip = info['NetworkSettings']['IPAddress']
                return self.__ip

    def stop(self):
        ip = self._ip()
        self.__ip = None
        self.__sc.container_ip(ip)
        self.__sc.del_all_domains()
        self.__sc.del_all_routes(self.__settings.subnets())
        self.__sc.disconnect()
        self.__sc.container_ip(None)

        running = [c['Id'] for c in self._containers() if c['State'] == 'running']
        for id in running:
            self.__dc.stop(id)

        not_running = [c['Id'] for c in self._containers() if c['State'] != 'running']
        for id in not_running:
            self.__dc.remove_container(id)

    def purge(self):
        self.stop()
        for image in self._images():
            self.__dc.remove_image(image, force=True)

    def shell(self):
        container = self._container()
        if not container:
            return

        self.__sc.docker_shell(container['Id'])

    def info(self):
        for image in self._images():
            print('Image: %s\t%s\t%.1f MB' % (image['RepoTags'][0],
                                              image['Id'][7:19],
                                              image['Size'] / 1024 / 1024,))
        ip = self._ip()
        if ip is None:
            return 0
        self.__sc.container_ip(ip)
        container = self._container()
        print('Container: %s\t%s\t%s' % (container['Image'],
                                         container['State'],
                                         container['Id'][7:19],))
        if container:
            print('IP: %s' % ip)
            subnets = self.__sc.list_routes()
            for subnet in subnets:
                print('Route: %s' % subnet)
            domains = self.__sc.list_domains()
            for domain in domains:
                print('Domain: %s' % domain)
