# vpn-porthole
Access one or more VPNs without interrupting existing connections, or altering your default networking.

<aside class="notice">
This utility is intended for people who have a a good understanding of networking.
</aside>

## Installation
You will need [Docker](https://docs.docker.com/engine/installation/) installed.
```
pip3 install vpn-porthole
```
or if you wish to install the latest development version:
```
pip3 install https://github.com/sourcesimian/vpn-porthole/tarball/master#egg=vpn-porthole-dev --process-dependency-links
```

## Setup
* Run `vpnp status all` to auto generate a default settings files.
* Edit `~/.config/vpn-porthole/settings.conf`
* See [settings.conf.example](/vpnporthole/resources/settings.conf.example) for more details
* Copy: `~/.config/vpn-porthole/sessions/example.conf` to setup your sessions.
* See [session.conf.example](/vpnporthole/resources/session.conf.example) for more details

## Usage
Typical usage would be:
```$ vpnp build example```

to create the docker image for your session, then
```$ vpnp start example```

once you have authenticated, your routes and domains will be setup. You can also dynamically add and
remove routes and domains using `add/del-route` and `add/del-domain`.

And then to stop
```$ vpnp stop example```

See:
```$ vpnp --help```
for more options

## DNS Resolution
### OSX
Vpn-porthole makes use of the build in multi-domain DNS support by writing resolver settings to
 `/etc/resolver/`, e.g.:

```
$ sudo cat /etc/resolver/test.org
nameserver 172.17.0.1  # vpnp_user_example
```

### Ubuntu
To use DNS multi-domain support your machine will need to be configured to use NetworkManager.
Vpn-porthole writes domain DNS resolver setting to `/etc/NetworkManager/dnsmasq.d/`, e.g.:

```
$ sudo cat /etc/NetworkManager/dnsmasq.d/test.org
server=/test.org/172.17.0.1  # vpnp_user_example
```
