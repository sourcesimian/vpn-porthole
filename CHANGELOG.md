# vpn-porthole - CHANGELOG

## [Unreleased] - CCYY-MM-DD
### Changed
- Session config file format to allow templatable free form Dockerfile definition
- Dependency: "docker-py" replaced with "docker".

### Added
- Hook scripts
- Dependency: "Tempita"
- Shell commands output to stdout it they fail

### Removed
- Proxy support, this can now be done in the session config
