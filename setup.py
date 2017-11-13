from setuptools import setup

setup(
    name="vpn-porthole",
    version="0.0.7",
    download_url="https://github.com/sourcesimian/vpn-porthole/tarball/v0.0.7",
    url='https://github.com/sourcesimian/vpn-porthole',
    description="Splice VPN access into your default network space",
    author="Source Simian",
    author_email='sourcesimian@users.noreply.github.com',
    license='MIT',
    packages=['vpnporthole', 'vpnporthole.system'],
    entry_points={
        "console_scripts": [
            "vpnp=vpnporthole.cli:main",
        ]
    },
    install_requires=[
        'ConfigObj>=4.7.0',
        'pexpect',
        'docker==2.0.2',
        'Tempita==0.5.2',
    ],
    package_data={
        'vpnporthole': ['resources/*'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
    ],
    platforms=[]
)
