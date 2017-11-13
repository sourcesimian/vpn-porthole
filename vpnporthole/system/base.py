import os
import sys
import re
import subprocess

from pexpect import spawn as pe_spawn, TIMEOUT, EOF


class SystemCallsBase(object):
    _ip = None
    __docker_bin = None
    __sudo_cache = None
    __sudo_prompt = 'SUDO PASSWORD: '

    def __init__(self, tag, settings):
        self._tag = tag
        self._settings = settings
        self.__cb_sudo = self._settings.sudo

    def container_ip(self, ip):
        self._ip = ip

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def add_route(self, subnet):
        pass

    def del_route(self, subnet):
        pass

    def list_routes(self):
        return []

    def del_all_routes(self, other_subnets):
        subnets = set(self.list_routes())
        subnets.update(other_subnets)
        for subnet in subnets:
            self.del_route(subnet)

    def add_domain(self, domain):
        pass

    def del_domain(self, domain):
        pass

    def list_domains(self):
        return []

    def del_all_domains(self):
        domains = self.list_domains()
        for domain in domains:
            self.del_domain(domain)

    @property
    def docker_bin(self):
        if self.__docker_bin:
            return self.__docker_bin
        self.__docker_bin = subprocess.check_output('which docker', shell=True).decode('utf-8').rstrip()
        return self.__docker_bin

    def docker_shell(self, container_id):
        args = [self.docker_bin, 'exec', '-it', container_id, '/bin/bash']
        p = self._popen(args, env=self.get_docker_env())
        p.wait()

    def docker_run_expect(self, image, args):

        all_args = [self.docker_bin, 'run', '-it', '--rm', '--privileged']
        all_args.extend([os.path.expanduser(os.path.expandvars(o)) for o in self._settings.run_options()])
        all_args.extend([image])
        all_args.extend(args)

        self.__print_cmd(all_args)
        return Pexpect(self.__args_to_string(all_args), env=self.get_docker_env())

    def __sudo(self):
        if self.__sudo_cache is None:
            out = subprocess.check_output('which sudo', shell=True)
            exe = out.decode('utf-8').strip()
            self.__sudo_cache = [exe, '-S', '-p', self.__sudo_prompt]
        return self.__sudo_cache

    def _shell(self, args):
        self.__print_cmd(args)
        if args[0] == 'sudo':
            args = self.__sudo() + args[1:]

        pe = Pexpect(self.__args_to_string(args), ignores=(self.__sudo_prompt,), stdout=False)

        pe.timeout = 10

        asked_sudo = False
        while True:
            i = pe.expect([self.__sudo_prompt, TIMEOUT, EOF])
            if i == 0:
                if asked_sudo:
                    pe.send(chr(3))
                    pe.wait()
                    sys.stderr.write('Sudo password was wrong\n')
                    exit(3)
                asked_sudo = True
                pe.sendline(self.__cb_sudo())
                continue
            break
        while len(pe.logfile.lines) and not pe.logfile.lines[0].strip():
            pe.logfile.lines = pe.logfile.lines[1:]
        pe.close()
        return pe.exitstatus, pe.logfile.lines

    def _shell_check(self, args):
        exitstatus, lines = self._shell(args)
        if exitstatus != 0:
            sys.stderr.write("Error running: %s\n" % ' '.join(args))
            for line in lines:
                sys.stderr.write("%s\n" % line)
        return exitstatus, lines

    def _popen(self, args, *vargs, **kwargs):
        self.__print_cmd(args)
        try:
            return subprocess.Popen(args, *vargs, **kwargs)
        except IOError as e:
            sys.stderr.write('Error running: %s\n%s\n' % (' '.join(args), e))
            raise

    def docker_exec(self, docker_client, container_id, args):
        if not self._ip:
            return None
        full_args = ['/vpnp/exec']
        full_args.extend(args)
        self.__print_cmd(full_args, 'exec')
        exe = docker_client.exec_create(container_id, full_args)
        errcode = re.compile('/vpnp/exec:EXITCODE=(?P<code>\d+)\n', re.MULTILINE)
        for buf in docker_client.exec_start(exe['Id'], stream=True):
            line = buf.decode('utf-8')
            m = errcode.search(line)
            line = errcode.sub(lambda a: '', line)
            if m:
                return int(m.group('code'))
            sys.stdout.write(line)
        return None

    @property
    def stdout(self):
        return sys.stdout

    @property
    def stderr(self):
        return sys.stderr

    def __print_cmd(self, args, scope=None):
        if scope:
            line = ' >(%s)$ ' % scope
        else:
            line = ' >$ '
        line += self.__args_to_string(args)
        sys.stdout.write(line + '\n')

    def __args_to_string(self, args):
        def q(s):
            if not isinstance(s, str):
                s = str(s)
            if '"' in s:
                s = s.replace('"', '\\"')
            if '"' in s or ' ' in s:
                s = '"%s"' % s
                return s
            return s

        return ' '.join([q(s) for s in args])

    def get_docker_env(self):
        return None


class Pexpect(pe_spawn):
    class Out(object):
        lines = None
        ignore = 0
        _stdout = True

        def __init__(self, ignores, stdout):
            self.__ignores = ignores
            self.lines = []
            self._stdout = stdout

        def write(self, b):
            try:
                st = b.decode("utf-8", "replace")
            except UnicodeDecodeError as e:
                print("! except: UnicodeDecodeError: %s" % e)
                st = '\r\n'

            for line in st.splitlines(True):
                ignore = line.startswith(self.__ignores)
                if ignore:
                    self.ignore += 1
                elif self.ignore > 0:
                    self.ignore -= 1
                    return
                if not ignore:
                    self.lines.append(line)
                if self._stdout:
                    sys.stdout.write('%s' % line)

        def flush(self):
            sys.stdout.flush()

    def __init__(self, cmd, ignores=('Password', 'Username'), stdout=True, env=None):
        super(Pexpect, self).__init__(cmd, env=env)
        self.logfile = self.Out(ignores, stdout)

    def expect(self, pattern, **kwargs):
        pattern.insert(0, EOF)
        pattern.insert(1, TIMEOUT)

        if 'timeout' not in kwargs:
            kwargs['timeout'] = 99  # Don't wait forever
        i = super(Pexpect, self).expect(pattern, **kwargs)

        return i - 2
