import platform

from vpnporthole.system.path import TmpDir


if platform.system() == 'Darwin':
    from vpnporthole.system.darwin import SystemCalls
elif platform.system() == 'Linux':
    from vpnporthole.system.linux import SystemCalls
else:
    raise NotImplementedError(platform.system())


__all__ = ['TmpDir', 'SystemCalls']
