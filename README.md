[[CHANGELOG](/CHANGELOG.md)]

# vpn-porthole
Splice in connectivity to one or more VPNs without interrupting existing connections, or altering your default networking.

> This utility is intended for people who have a good understanding of networking, Docker and virtualisation.

## Usage
Typical usage would be: `$ vpnp build example` to create the docker image for your session, then `$ vpnp start example`.

Once you have authenticated, your routes and domains will be setup. You can also dynamically add and
remove routes and domains using `add/del-route` and `add/del-domain`.

And then to stop: `$ vpnp stop example`.

See:
```$ vpnp --help```
for more options

## Setup
You will need [Docker](https://docs.docker.com/engine/installation/) installed, note the [Supported Platforms](#supported-platforms) below.
```
pip3 install vpn-porthole
```
or if you wish to install the latest development version:
```
pip3 install https://github.com/sourcesimian/vpn-porthole/tarball/master#egg=vpn-porthole-dev --process-dependency-links
```

Then:
* Run `vpnp status all` to auto generate a default settings files.
* Edit `~/.config/vpn-porthole/settings.conf`
* Copy and modify: `~/.config/vpn-porthole/sessions/example.conf` to setup your sessions.
* See [Configuration](#configuration) below for more details.

## Supported Platforms
So far vpn-porthole has been developed and tested on OSX and Ubuntu.

### OSX
At present vpn-porthole only works with **Docker Toolbox** using **VirtualBox**.
Support for **Docker for Mac** will follow when the necessary routing is possible.

**Docker Toolbox** can be installed with homebrew using:
`brew install Caskroom/cask/docker-toolbox`

#### DNS Resolution
vpn-porthole makes use of the build in multi-domain DNS support by writing resolver settings to
 `/etc/resolver/`, e.g.:

```
$ sudo cat /etc/resolver/test.org
nameserver 172.17.0.1  # vpnp_user_example
```

### Ubuntu
#### DNS Resolution
To use DNS multi-domain support your machine will need to be configured to use NetworkManager.
Vpn-porthole writes domain DNS resolver setting to `/etc/NetworkManager/dnsmasq.d/`, e.g.:

```
$ sudo cat /etc/NetworkManager/dnsmasq.d/test.org
server=/test.org/172.17.0.1  # vpnp_user_example
```

## Configuration
### Settings
System settings are in: `~/.config/vpn-porthole/settings.conf`.

```
[system]
    # sudo: (optional) vpn-porthole needs to make use of sudo privileges to setup and tear down
    # subnets and DNS domains. Can be configured with `SHELL:` as for password in a session.
    sudo =

[docker]
    # docker.machine: (optional) [OSX] Can be configured to connect to a specific docker
    # machine. If left blank, the DOCKER_* settings will be fetch from the environment.
    # Note: vpn-porthole only works with Docker Toolbox and VirtualBox on OSX.
    machine = default
```

### Sessions
Sessions are described in: `~/.config/vpn-porthole/sessions/<name>.conf`.

#### Basic
Here is an full example of a basic session config:

```
# vpn: the endpoint at which the VPN is contacted
vpn = vpn.example.com

# username: Directly add VPN username here, or use the SHELL feature as for the password
username = joe

# password: (optional) You can directly add your password here,
# but that is not good security. If you leave it blank then you will be
# prompted when needed. You can also configure your password to be
# retrieved with a shell command. I like to store my passwords in a keyring:
#   OSX: https://joshtronic.com/2014/02/17/using-keyring-access-on-the-osx-commandline/
#   Ubuntu: http://manpages.ubuntu.com/manpages/wily/man1/secret-tool.1.html
password = SHELL:~/path/to/password/script

# subnets: Add the IP address ranges that you wish to route into the VPN session
[[[subnets]]]
    10.11.0.0/28 = True
    10.12.13.0/24 = True

# domains: Add the DNS domains for which you wish to forward DNS lookups into the
[[[domains]]]
    example.org = True

# build: Describe how to build your Docker image.
# User defined `options` can also be added to the Tempita context (e.g. `{{option.proxy}}`).
[[[build]]]
    [[[options]]]
        proxy = proxy.example.com:80

    # files: must include at least a mention of a Dockerfile. Other user files can
    # be added to the Docker build context either by path (e.g.: foo.sh) or content
    # (e.g.: bar.sh). Files names that end in `.tmpl` will be rendered with Tempita
    # and provided without the `.tmpl` extension.
    [[[[files]]]]
        Dockerfile.tmpl = '''
            FROM debian

            RUN echo 'Acquire::http::proxy "http://{{option.proxy}}";' > /etc/apt/apt.conf

            RUN apt-get update &&\
             apt-get install -y sudo openvpn openconnect iptables dnsmasq &&\
             apt-get autoremove -y &&\
             apt-get clean -y

            RUN echo -e "\\ninterface=eth0\\nuser=root\\n" >> /etc/dnsmasq.conf

            RUN groupadd --gid {{local.user.gid}} {{local.user.group}} || true &&\
              useradd -ms /bin/bash {{local.user.name}} --uid {{local.user.uid}} --gid {{local.user.gid}}
            RUN echo "{{local.user.name}} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/90-{{local.user.name}}

            {{vpnp.hooks}}

            USER {{local.user.name}}
        '''

        # And example of a user defined file added to the build context by path
        foo.sh = ~/.config/vpn-porthole/example/install.sh

        # And example of a user defined file added to the build context by content
        bar.sh = '''
            #!/bin/bash

            wget ...

            /usr/bin/expect <<EOF
            spawn ./install.sh
            expect {
             " Do you wish to continue (y/n)?"
            }
            send "y\r"
            EOF
        '''

# run: Define the run time behaviour of the docker container.
[run]
    # options: are included in the `docker run` command line.
    [[options]]
        1 = --volume /tmp:/tmp

    # hooks: Are scripts that vpn-porthole runs to control the container. They are
    # rendered with Tempita and written to /vpnp/ in the image.
    # It is important to include `{{vpnp.hooks}}` somewhere in the Dockerfile above so
    # that the hooks get installed.
    [[hooks]]
        # /vpnp/start: is called with `docker run`
        start = '''
            #!/bin/bash
            set -e -v
            sudo openconnect {{vpn.addr}} --interface tun1
        '''

        # /vpnp/up: is called with `docker exec` once `/vpnp/start` has established a connection
        up = '''
            #!/bin/bash
            set -e -v
            sudo iptables -t nat -A POSTROUTING -o tun1 -j MASQUERADE
            sudo /etc/init.d/dnsmasq start
        '''

        # /vpnp/stop: is called with `docker exec` before the container is torn down
        stop = '''
            #!/bin/bash
            sudo pkill openconnect
        '''
```
