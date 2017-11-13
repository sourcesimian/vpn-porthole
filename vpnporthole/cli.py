#!/usr/bin/env python3
import sys

from vpnporthole.session import Session
from vpnporthole.settings import Settings
from vpnporthole.argparsetree import ArgParseTree


class Main(ArgParseTree):
    """

    """
    def args(self, parser):
        pass


class Action(ArgParseTree):
    settings = None

    def args(self, parser):
        parser.add_argument("profile", help='Profile name or "all"')

    def run(self, args):
        if args.profile == 'all':
            profile_names = Settings.list_profile_names()
            for profile_name in sorted(profile_names):
                self.settings = Settings(profile_name)
                session = Session(self.settings)
                self.go(session, args)
        else:
            self.settings = Settings(args.profile)
            session = Session(self.settings)
            return self.go(session, args)

    def go(self, session, args):
        raise NotImplementedError()


class Build(Action):
    """\
    Build profile

    Build the docker image for this profile
    """
    def go(self, session, args):
        if session.build():
            return 0
        return 1


class Start(Action):
    """\
    Start profile

    Start the docker container for this profile, requires user to enter password none configured
    """
    def go(self, session, args):
        try:
            if session.start():
                return 0
            return 1
        except KeyboardInterrupt:
            return 1


class Stop(Action):
    """\
    Stop profile

    Stop the docker container for this profile
    """
    def go(self, session, args):
        if session.stop():
            return 0
        return 1


class Status(Action):
    """\
    Profile status

    Determine if the docker container for this image is running
    """
    def go(self, session, args):
        if session.status():
            status = 'RUNNING'
            exitcode = 0
        else:
            status = 'STOPPED'
            exitcode = 1
        sys.stdout.write("%s %s %s@%s\n" % (status, self.settings.profile_name,
                                            self.settings.username(), self.settings.vpn()))
        return exitcode


class Health(Action):
    """\
    Profile health

    Run the user defined "health" hook inside the container
    """
    def go(self, session, args):
        exitcode = session.health()
        if exitcode == 0:
            status = 'OK'
        else:
            status = 'BAD'
        sys.stdout.write("%s %s %s@%s\n" % (status, self.settings.profile_name,
                                            self.settings.username(), self.settings.vpn()))
        return exitcode


class Refresh(Action):
    """\
    Profile refresh

    Run the user defined "refresh" hook inside the container
    """
    def go(self, session, args):
        exitcode = session.refresh()
        return exitcode


class Shell(Action):
    """\
    Shell into active profile

    Open shell in Docker container
    """
    def go(self, session, args):
        if session.shell():
            return 0
        return 1


class Info(Action):
    """\
    Docker container info for profile
    """
    def go(self, session, args):
        if session.info():
            return 0
        return 1


class Rm(Action):
    """\
    Stop the profile, and remove the docker container

    Remove any running/stopped containers and images for this profile
    """
    def go(self, session, args):
        if session.purge():
            return 0
        return 1


class Restart(Action):
    """\
    Restart profile

    Restart Docker container for this profile
    """
    def go(self, session, args):
        if session.status():
            if not session.stop():
                sys.stderr.write("Failed to stop!\n")
                return 1
            if session.start():
                return 0
            sys.stderr.write("Failed to start!\n")
            return 1
        sys.stderr.write("Not running!\n")
        return 1


class RouteAction(Action):
    def args(self, parser):
        super(RouteAction, self).args(parser)
        parser.add_argument('subnet', help="IPv4 subnet to route into active profile, e.g.: 10.1.2.0/24")


class AddRoute(RouteAction):
    """\
    Add route to active profile
    """
    name = 'add-route'

    def go(self, session, args):
        if session.add_route(args.subnet):
            return 0
        return 1


class DelRoute(RouteAction):
    """\
    Remove route to active profile
    """
    name = 'del-route'

    def go(self, session, args):
        if session.del_route(args.subnet):
            return 0
        return 1


class DomainAction(Action):
    def args(self, parser):
        super(DomainAction, self).args(parser)
        parser.add_argument('domain', help="DNS sub-domain to delegate into the  active profile, e.g.: example.com")


class AddDomain(DomainAction):
    """\
    Add DNS domain to active profile
    """
    name = 'add-domain'

    def go(self, session, args):
        if session.add_domain(args.domain):
            return 0
        return 1


class DelDomain(DomainAction):
    """\
    Remove DNS domain to active profile
    """
    name = 'del-domain'

    def go(self, session, args):
        if session.del_domain(args.domain):
            return 0
        return 1


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
    Health(m)
    Refresh(m)
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
