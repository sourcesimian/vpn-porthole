vpn = string()

username = string(default='')
password = string(default='')

[subnets]
    ___many___ = boolean()

[domains]
    ___many___ = boolean()

[docker]
    machine = string(default='')

[build]
    [[options]]
        ___many___ = string()

    [[files]]
        ___many___ = string()

[run]
    [[options]]
        ___many___ = string()

    [[hooks]]
        start = string()
        up = string(default=' #!/bin/bash')
        health = string(default=' #!/bin/bash')
        refresh = string(default=' #!/bin/bash')
        stop = string(default=' #!/bin/bash')
