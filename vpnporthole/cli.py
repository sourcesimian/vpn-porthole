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
        parser.add_argument("profile", help='Selected profile in the settings "all" can be used')

    def run(self, args):
        if args.profile == 'all':
            profiles = Settings.list_profiles(args.settings)
            for name in sorted(profiles.keys()):
                self.settings = Settings(name, args.settings, args.proxy)
                image = Session(self.settings)
                self.go(image, args)
        else:
            self.settings = Settings(args.profile, args.settings, args.proxy)
            image = Session(self.settings)
            return self.go(image, args)


class Build(Action):
    """\
    Build profile

    Build the docker image for this profile
    """
    def go(self, image, args):
        return image.build()


class Start(Action):
    """\
    Start profile

    Start the docker container for this profile, requires user to enter password none configured
    """
    def go(self, image, args):
        try:
            return image.start()
        except KeyboardInterrupt:
            return 1


class Stop(Action):
    """\
    Stop profile

    Stop the docker container for this profile
    """
    def go(self, image, args):
        return image.stop()


class Status(Action):
    """\
    Purge profile

    Determine if the docker container fo this image is running
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
    Purge profile

    Remove any running/stopped containers and images for this profile
    """
    def go(self, image, args):
        return image.purge()


class Restart(Action):
    """\
    Purge profile

    Remove any running/stopped containers and images for this profile
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
        parser.add_argument('subnet')


class AddRoute(RouteAction):
    """\
    Add a route
    """
    name = 'add-route'

    def go(self, image, args):
        return image.add_route(args.subnet)


class DelRoute(RouteAction):
    """\
    Delete a route
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
    Add a domain
    """
    name = 'add-domain'

    def go(self, image, args):
        return image.add_domain(args.domain)


class DelDomain(DomainAction):
    """\
    Delete a domain
    """
    name = 'del-domain'

    def go(self, image, args):
        return image.del_domain(args.domain)


def main():
    m = Main()
    Build(m)
    Start(m)
    Status(m)
    Stop(m)
    Restart(m)
    Info(m)
    Shell(m)
    Rm(m)
    AddRoute(m)
    DelRoute(m)
    AddDomain(m)
    DelDomain(m)

    try:
        return m.main()
    except KeyboardInterrupt:
        sys.stderr.write('^C\n')
        return 3


if __name__ == "__main__":
    exit(main())
