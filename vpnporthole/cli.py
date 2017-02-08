#!/usr/bin/env python3
import sys

from vpnporthole.session import Session
from vpnporthole.settings import Settings
from vpnporthole.argparsetree import ArgParseTree


class Main(ArgParseTree):
    """

    """
    def args(self, parser):
        parser.add_argument("--proxy", default=None, help="Selected proxy profile")


class Action(ArgParseTree):
    settings = None

    def args(self, parser):
        parser.add_argument("session", help='Session name or "all"')

    def run(self, args):
        if args.session == 'all':
            sessions = Settings.list_sessions()
            for name in sorted(sessions.keys()):
                self.settings = Settings(name, args.proxy)
                session = Session(self.settings)
                self.go(session, args)
        else:
            self.settings = Settings(args.session, args.proxy)
            session = Session(self.settings)
            return self.go(session, args)

    def go(self, session, args):
        raise NotImplementedError()


class Build(Action):
    """\
    Build session

    Build the docker image for this session
    """
    def go(self, session, args):
        return session.build()


class Start(Action):
    """\
    Start session

    Start the docker container for this session, requires user to enter password none configured
    """
    def go(self, session, args):
        try:
            return session.start()
        except KeyboardInterrupt:
            return 1


class Stop(Action):
    """\
    Stop session

    Stop the docker container for this session
    """
    def go(self, session, args):
        return session.stop()


class Status(Action):
    """\
    Session status

    Determine if the docker container for this image is running
    """
    def go(self, session, args):
        if session.status():
            status = 'RUNNING'
        else:
            status = 'STOPPED'
        sys.stdout.write("%s %s %s@%s\n" % (status, self.settings.session,
                                            self.settings.username(), self.settings.vpn()))
        return status == 'RUNNING'


class Shell(Action):
    """\
    Shell into active session

    Open shell in Docker container
    """
    def go(self, session, args):
        return session.shell()


class Info(Action):
    """\
    Docker container info for session
    """
    def go(self, session, args):
        return session.info()


class Rm(Action):
    """\
    Stop the session, and remove the docker container

    Remove any running/stopped containers and images for this session
    """
    def go(self, session, args):
        return session.purge()


class Restart(Action):
    """\
    Restart session

    Restart Docker container for this session
    """
    def go(self, session, args):
        if session.status():
            session.stop()
            return session.start()
        sys.stderr.write("Not running!\n")
        return 1


class RouteAction(Action):
    def args(self, parser):
        super(RouteAction, self).args(parser)
        parser.add_argument('subnet', help="IPv4 subnet to route into session, e.g.: 10.1.2.0/24")


class AddRoute(RouteAction):
    """\
    Add route to session
    """
    name = 'add-route'

    def go(self, session, args):
        return session.add_route(args.subnet)


class DelRoute(RouteAction):
    """\
    Delete route from session
    """
    name = 'del-route'

    def go(self, session, args):
        return session.del_route(args.subnet)


class DomainAction(Action):
    def args(self, parser):
        super(DomainAction, self).args(parser)
        parser.add_argument('domain', help="DNS sub-domain to delegate into the session, e.g.: example.com")


class AddDomain(DomainAction):
    """\
    Add DNS domain to session
    """
    name = 'add-domain'

    def go(self, session, args):
        return session.add_domain(args.domain)


class DelDomain(DomainAction):
    """\
    Delete DNS domain from session
    """
    name = 'del-domain'

    def go(self, session, args):
        return session.del_domain(args.domain)


class Docs(ArgParseTree):
    """\
    vpn-porthole documentation
    """
    def run(self, args):
        import pkg_resources
        try:
            tag = 'v' + pkg_resources.get_distribution('vpn-porthole').version
        except pkg_resources.DistributionNotFound:
            tag = 'master'

        print("vpn-porthole documentation can be found at:")
        print("  https://github.com/sourcesimian/vpn-porthole/blob/%s/README.md" % tag)
        return 0


def main():
    m = Main()
    Build(m)
    Start(m)
    Status(m)
    Stop(m)
    Restart(m)
    AddRoute(m)
    DelRoute(m)
    AddDomain(m)
    DelDomain(m)
    Info(m)
    Shell(m)
    Rm(m)
    Docs(m)

    try:
        return m.main()
    except KeyboardInterrupt:
        sys.stderr.write('^C\n')
        return 3


if __name__ == "__main__":
    exit(main())
