# vpn-porthole - CHANGELOG

## [0.0.6] - 2017-02-28
### Changed
- Profile file format to allow templatable free form Dockerfile definition.
- Dependency: "docker-py" replaced with "docker".
- Folder: `~/.config/vpnp-porthole/sessions` to `~/.config/vpnp-porthole/profiles`

### Added
- Hook scripts.
- Dependency: "Tempita".
- Shell commands output to stdout it they fail.

### Removed
- Proxy support, this can now be done in the profile config.
