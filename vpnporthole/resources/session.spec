
[session]
    [[__many__]]
        vpn = string()

        username = string()
        password = string(default='')

        [[[subnets]]]
            ___many___ = boolean()

        [[[domains]]]
            ___many___ = boolean()

        [[[socks5]]]
            port = integer(default=0)

        [[[docker]]]
            machine = string(default='')

        [[[dockerfile]]]
            [[[[system]]]]
                ___many___ = string()
            [[[[user]]]]
                ___many___ = string()
            [[[[files]]]]
                ___many___ = string()

        [[[openconnect]]]
            ___many___ = string()
