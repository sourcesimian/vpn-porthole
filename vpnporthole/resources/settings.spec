
[session]
    [[__many__]]
        vpn = string()

        username = string()
        password = string(default='')

        sudo = string(default='')

        [[[subnets]]]
            ___many___ = boolean()

        [[[domains]]]
            ___many___ = boolean()

        [[[custom]]]
            [[[[openconnect]]]]
                ___many___ = string()
            [[[[system]]]]
                ___many___ = string()
            [[[[user]]]]
                ___many___ = string()

[proxy]
    [[__many__]]
        http_proxy = string(default='')
