
[system]
    sudo = string(default='')

[docker]
    machine = string(default='')

[proxy]
    [[__many__]]
        http_proxy = string(default='')
