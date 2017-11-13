import os
from docker.client import from_env
from pkg_resources import resource_stream

from vpnporthole.ip import IPv4Subnet
from vpnporthole.system import TmpDir, SystemCalls


class Session(object):
    __dnsmasq_port = 53
    __ip = None

    def __init__(self, settings):
        self.__settings = settings
        self.__sc = SystemCalls(self._name(), self.__settings)
        self.__dc = from_env(environment=self.__sc.get_docker_env()).api

    def _local_user(self):
        return os.environ['USER']

    def _name(self):
        return "vpnp/%s_%s" % (self.__settings.profile_name, self.__settings.ctx.local.user.name,)

    def build(self):
        name = self._name()

        with TmpDir() as tmp:
            hook_dir = os.path.join(tmp.path, 'vpnp')
            os.makedirs(hook_dir)
            hook_files = self.__settings.run_hook_files()
            hook_files['exec'] = resource_stream("vpnporthole", "resources/exec").read().decode('utf-8')

            for hook, content in hook_files.items():
                hook_file = os.path.join(hook_dir, hook)
                with open(hook_file, 'wt') as fh:
                    fh.write(content)
                os.utime(hook_file, (0, 0))

            for filename, content in self.__settings.build_files().items():
                user_file = os.path.join(tmp.path, filename)
                with open(user_file, 'wt') as fh:
                    fh.write(content)
                os.utime(user_file, (0, 0))

            stream = self.__dc.build(tmp.path, tag=name)
            import json
            for buf in stream:
                block = json.loads(buf.decode('utf-8'))
                if 'stream' in block:
                    self.__sc.stdout.write(block['stream'])
                if 'error' in block:
                    self.__sc.stdout.write(block['error'] + '\n')
                    exit(3)
            # image = block['stream'].split()[2]
            print("Name: %s" % name)
            return True

    def start(self):
        if self.run():
            return self.local_up()
        return False

    def run(self):
        if self.status():
            self.__sc.stderr.write("Already running\n")
            return False

        if not self._images():
            self.build()

        self.__ip = None
        self.__sc.container_ip(None)

        self._container_hook('start')

        self._container()
        if not self.__ip:
            self.__sc.stderr.write("Failed to start\n")
            return False

        self._container_hook('up')
        self.__sc.on_connect()
        return True

    def local_up(self):
        self._container()
        for subnet in self.__settings.subnets():
            self.__sc.add_route(subnet)

        for domain in self.__settings.domains():
            self.__sc.add_domain(domain)
        return True

    def add_route(self, subnet):
        subnet = IPv4Subnet(subnet)
        self._container()
        self.__sc.add_route(subnet)
        return True

    def del_route(self, subnet):
        subnet = IPv4Subnet(subnet)
        self._container()
        for sn in self.__sc.list_routes():
            if sn in subnet:
                self.__sc.del_route(sn)
        return True

    def add_domain(self, domain):
        self._container()
        self.__sc.add_domain(domain)
        return True

    def del_domain(self, domain):
        self._container()
        domains = self.__sc.list_domains()
        if domain in domains:
            self.__sc.del_domain(domain)
        return True

    def status(self):
        if self._container():
            return True
        return False

    def stop(self):
        self.local_down()
        self._container_hook('stop')
        self.__sc.container_ip(None)

        running = [c['Id'] for c in self._containers() if c['State'] == 'running']
        for id in running:
            try:
                self.__dc.stop(id)
            except Exception as e:
                self.__sc.stderr.write("Error stopping: %s\n%s" % (id, e))

        not_running = [c['Id'] for c in self._containers() if c['State'] != 'running']
        for id in not_running:
            self.__dc.remove_container(id)
        return True

    def local_down(self):
        self._container()
        self.__sc.del_all_domains()
        self.__sc.del_all_routes(self.__settings.subnets())
        self.__sc.on_disconnect()
        return True

    def purge(self):
        self.stop()
        for image in self._images():
            self.__dc.remove_image(image, force=True)
        return True

    def shell(self):
        container = self._container()
        if not container:
            return False

        self.__sc.docker_shell(container['Id'])
        return True

    def info(self):
        for image in self._images():
            print('Image: %s\t%s\t%.1f MB' % (image['RepoTags'][0],
                                              image['Id'][7:19],
                                              image['Size'] / 1024 / 1024,))
        container = self._container()
        if self.__ip is None:
            return True
        print('Container: %s\t%s\t%s' % (container['Image'],
                                         container['State'],
                                         container['Id'][7:19],))
        if container:
            print('IP: %s' % self.__ip)
            subnets = self.__sc.list_routes()
            for subnet in subnets:
                print('Route: %s' % subnet)
            domains = self.__sc.list_domains()
            for domain in domains:
                print('Domain: %s' % domain)
        return True

    def _images(self):
        tag = self._name()
        all_images = self.__dc.images()

        filtered_images = []
        for image in all_images:
            tags = image['RepoTags']
            if tags:
                if any([True for t in tags if t.startswith(tag)]):
                    filtered_images.append(image)

        return filtered_images

    def _containers(self):
        name = self._name()
        all_containers = self.__dc.containers(all=True)
        return [c for c in all_containers
                if c['Image'] == name]

    def _container(self):
        running = [c for c in self._containers()
                   if c['State'] == 'running']
        if not running:
            self.__ip = None
            return None
        if len(running) > 1:
            print('WARNING: there is more than one container: %s' % running)

        container = running[0]
        info = self.__dc.inspect_container(container)
        if info:
            self.__ip = info['NetworkSettings']['IPAddress']
        else:
            self.__ip = None
        self.__sc.container_ip(self.__ip)

        return container

    def _container_hook(self, hook):

        if hook == 'start':
            args = ['/vpnp/start']
            name = self._name()

            pe = self.__sc.docker_run_expect(name, args)
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
            return 0
        else:
            container = self._container()
            if container:
                return self.__sc.docker_exec(self.__dc, container['Id'], ['/vpnp/%s' % hook])

    def health(self):
        if self._container():
            return self._container_hook('health')
        return 127  # "command not found"

    def refresh(self):
        if self._container():
            return self._container_hook('refresh')
        return 127  # "command not found"
