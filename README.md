# vpn-porthole
Splice VPN access into your default network space. No more hijacking all your networking.

## Installation
```
pip3 install vpn-porthole
```

## Setup
* Run `vpnp` to auto generate a default settings file.
* Edit `~/.config/vpn-porthole/settings.conf`
* See [settings.conf.example](/vpnporthole/resources/settings.conf.example) for more details

## Usage
As a prerequisite you need to have your docker env setup in your shell.

Typical usage would be:
```$ vpnp build sample```

to create the docker image for your profile, then
```$ vpnp start sample```

once you have authenticated, your routes and domains will be setup. You can then dynamically add and
remove routes and domains using `add/del-route` and `add/del-domain`.

And then to stop
```$ vpnp start sample```


See:
```$ vpnp --help```
for more options