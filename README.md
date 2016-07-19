# vpn-porthole
Splice VPN access into your default network space. Without interrupting existing connections, or
altering your default networking.

## Installation
You will need [Docker](https://docs.docker.com/engine/installation/) installed.
```
pip3 install vpn-porthole
```

## Setup
* Run `vpnp` to auto generate a default settings file.
* Edit `~/.config/vpn-porthole/settings.conf`
* See [settings.conf.example](/vpnporthole/resources/settings.conf.example) for more details

## Usage
As a prerequisite you need to have your Docker env setup in your shell.

Typical usage would be:
```$ vpnp build sample```

to create the docker image for your profile, then
```$ vpnp start sample```

once you have authenticated, your routes and domains will be setup. You can also dynamically add and
remove routes and domains using `add/del-route` and `add/del-domain`.

And then to stop
```$ vpnp start sample```


See:
```$ vpnp --help```
for more options

## DNS Resolution
### Ubuntu
To use DNS multi-domain support your machine will need to be configured to use NetworkManager.
Vpn-porthole writes domain DNS resolver setting to `/etc/NetworkManager/dnsmasq.d`, e.g.:

```
$ sudo cat /etc/NetworkManager/dnsmasq.d/test.org
server=/test.org/172.17.0.1  # vpnp_user_example
```
