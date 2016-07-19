#!/usr/bin/env python3
import sys

from vpnporthole.session import Session
from vpnporthole.settings import Settings
from vpnporthole.argparsetree import ArgParseTree


class Main(ArgParseTree):
    """

    """
    def args(self, parser):
        parser.add_argument("--settings", default=None, help='Alternative settings file')
        parser.add_argument("--proxy", default=None, help="Selected proxy profile")


class Action(ArgParseTree):
    def args(self, parser):
        parser.add_argument("session", help='Selected session in settings')

    def run(self, args):
        if args.session == 'all':
            profiles = Settings.list_profiles(args.settings)
            for name in sorted(profiles.keys()):
                self.settings = Settings(name, args.settings, args.proxy)
                image = Session(self.settings)
                self.go(image, args)
        else:
            self.settings = Settings(args.session, args.settings, args.proxy)
            image = Session(self.settings)
            return self.go(image, args)


class Build(Action):
    """\
    Build session

    Build the docker image for this session
    """
    def go(self, image, args):
        return image.build()


class Start(Action):
    """\
    Start session

    Start the docker container for this session, requires user to enter password none configured
    """
    def go(self, image, args):
        try:
            return image.start()
        except KeyboardInterrupt:
            return 1


class Stop(Action):
    """\
    Stop session

    Stop the docker container for this session
    """
    def go(self, image, args):
        return image.stop()


class Status(Action):
    """\
    Session status

    Determine if the docker container for this image is running
    """
    def go(self, image, args):
        if image.status():
            status = 'RUNNING'
        else:
            status = 'STOPPED'
        sys.stdout.write("%s %s %s@%s\n" % (status, self.settings.profile, self.settings.username(), self.settings.vpn()))
        return status == 'RUNNING'


class Shell(Action):
    """\
    Shell into active session

    Open shell in Docker container
    """
    def go(self, image, args):
        return image.shell()


class Info(Action):
    """\
    Docker container info
    """
    def go(self, image, args):
        return image.info()


class Rm(Action):
    """\
    Purge session

    Remove any running/stopped containers and images for this session
    """
    def go(self, image, args):
        return image.purge()


class Restart(Action):
    """\
    Restart session

    Restart Docker container for this session
    """
    def go(self, image, args):
        if image.status():
            image.stop()
            return image.start()
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

    def go(self, image, args):
        return image.add_route(args.subnet)


class DelRoute(RouteAction):
    """\
    Delete route from session
    """
    name = 'del-route'

    def go(self, image, args):
        return image.del_route(args.subnet)


class DomainAction(Action):
    def args(self, parser):
        super(DomainAction, self).args(parser)
        parser.add_argument('domain')


class AddDomain(DomainAction):
    """\
    Add DNS domain to session
    """
    name = 'add-domain'

    def go(self, image, args):
        return image.add_domain(args.domain)


class DelDomain(DomainAction):
    """\
    Delete DNS domain from session
    """
    name = 'del-domain'

    def go(self, image, args):
        return image.del_domain(args.domain)


class Docs(ArgParseTree):
    """\
    vpn-porthole documentation
    """
    def run(self, args):
        print("vpn-porthole documentation can be found at:")
        print("  https://github.com/sourcesimian/vpn-porthole/blob/master/README.md")
        return 0


def main():
    m = Main()
    Docs(m)
    Build(m)
    Start(m)
    Status(m)
    Stop(m)
    Restart(m)
    AddRoute(m)
    DelRoute(m)
    AddDomain(m)
    DelDomain(m)
    Rm(m)
    Info(m)
    Shell(m)

    try:
        return m.main()
    except KeyboardInterrupt:
        sys.stderr.write('^C\n')
        return 3


if __name__ == "__main__":
    exit(main())
