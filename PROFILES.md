[[README](/README.md)]

# vpn-porthole
## Profiles
Profiles are used to describe the VPN session. The structure of a profile is described in the
[README](/README.md#configuration). They are stored in: `~/.config/vpn-porthole/profiles/<name>.conf`.

Building a vpn-porthole profile is dependent on the configuration of the VPN endpoint, some can
be easy others can take a bit of experimentation before you can satisfy the security requirements.
The following examples will hopefully help you in building your custom profile.


### Basic
A basic profile called "example" is installed by default. You will find it here:
[`~/.config/vpn-porthole/profiles/example.conf`](/resources/example.conf). It shows usage of
Dockerfile templating, start, up and stop hooks, subnets and domains. Which can be sufficient
to build a working vpn-porthole profile.

### Cisco Hostscan
If the VPN requires Cisco Hostscan, this makes setting up a VPN connection a bit more complicated.

Below are some profile fragments that should help when satisfying Cisco Hostscan. You will need
to install the additional requirements such as anti-virus, firewall, etc into your Docker image.
Usually some experimentation will be needed to get it working.  However, once all the details
are captured in a vpn-porthole profile it should just work the same as any profile.

```
        Dockerfile.tmpl = '''
            ...
            WORKDIR /home/user/

            ADD csd-install.sh /home/user/
            RUN /bin/bash ./csd-install.sh
            ADD csd-wrapper.sh /home/user/
            ADD csd-wrapper-exec.sh /home/user/
            RUN sudo chown user ./*.sh && chmod u+x ./*.sh
            ...
        '''
```

The follwing `csd-*.sh` files were derived from this helpful
[Gist: "Cisco Anyconnect CSD wrapper for OpenConnect"](https://gist.github.com/l0ki000/56845c00fd2a0e76d688).

```
        csd-install.sh.tmpl = '''
            set -v
            CSD_HOSTNAME={{vpn.addr}}

            [ -z "$CSD_HOSTNAME" ] && exit 1

            HOSTSCAN_DIR="$HOME/.cisco/hostscan"
            LIB_DIR="$HOSTSCAN_DIR/lib"
            BIN_DIR="$HOSTSCAN_DIR/bin"

            mkdir -p $BIN_DIR
            mkdir -p $LIB_DIR

            if [ "$(uname -m)" == "x86_64" ]; then
                ARCH="linux_x64"
            else
                ARCH="linux_i386"
            fi

            echo "Getting manifest .."
            wget --no-check-certificate -c "https://${CSD_HOSTNAME}/CACHE/sdesktop/hostscan/$ARCH/manifest" -O "$HOSTSCAN_DIR/manifest"
            cat $HOSTSCAN_DIR/manifest

            echo "Fetching latest files ..."
            FILES="$(cat $HOSTSCAN_DIR/manifest | sed -r 's/\(|\)//g' | awk '{ print $2":"$4; }')"
            for i in $FILES; do
                IFS=':' read FILE MD5SUM <<< "$i"

                if echo $FILE | grep --extended-regexp --quiet --invert-match ".so|tables.dat"; then
                    BASE_DIR=$BIN_DIR
                else
                    BASE_DIR=$LIB_DIR
                fi

                echo "Downloading \"$FILE\" to $BASE_DIR ..."
                echo "$MD5SUM $BASE_DIR/$FILE" >> $HOSTSCAN_DIR/md5.sum
                if ! wget --no-check-certificate -c "https://${CSD_HOSTNAME}/CACHE/sdesktop/hostscan/$ARCH/$FILE" -P $BASE_DIR; then
                    rm -f $BASE_DIR/$FILE
                    echo "... \"$FILE\" not found. Trying $FILE.gz ..."
                    if ! wget --no-check-certificate -c "https://${CSD_HOSTNAME}/CACHE/sdesktop/hostscan/$ARCH/$FILE.gz" -P $BASE_DIR; then
                        rm -f $BASE_DIR/$FILE.gz
                        echo "!!! Failed to fetch \"$FILE\"."
                    else
                        gunzip --verbose $BASE_DIR/$FILE.gz
                    fi
                fi
            done
            chmod u+x $BIN_DIR/*

            echo "Verifying MD5SUMs ..."
            if ! md5sum --quiet -c $HOSTSCAN_DIR/md5.sum; then
                cat $HOSTSCAN_DIR/md5.sum;
                find .cisco -type f -exec ls -l {} \;
                echo "!!! Failed to fetch manifest."
                exit 1
            fi

            sudo cp /bin/false /usr/bin/hal-get-property
            sudo cp /bin/false /usr/bin/drweb

            echo "Hostscan installed."
        '''
```

```
        csd-wrapper.sh = '''
            #!/bin/bash

            echo "$0""$@"
            env | grep CSD | sort | sed -e "s/^/ENV: /"

            [ -z "$CSD_HOSTNAME" ] && exit 1

            HOSTSCAN_DIR="$HOME/.cisco/hostscan"
            LIB_DIR="$HOSTSCAN_DIR/lib"
            BIN_DIR="$HOSTSCAN_DIR/bin"

            URL=
            TICKET=
            STUB=
            GROUP=
            CERTHASH=
            LANGSELEN=

            shift
            while [ "$1" ]; do
                if [ "$1" == "-ticket" ];   then shift; TICKET=$1; fi
                if [ "$1" == "-stub" ];     then shift; STUB=$1; fi
                if [ "$1" == "-group" ];    then shift; GROUP=$1; fi
                if [ "$1" == "-certhash" ]; then shift; CERTHASH=$1; fi
                if [ "$1" == "-url" ];      then shift; URL=$1; fi
                if [ "$1" == "-langselen" ];then shift; LANGSELEN=$1; fi
                shift
            done

            ARGS="-log all -ticket $TICKET -stub $STUB -group $GROUP -host $URL -certhash $CERTHASH"
            ARGS="$ARGS -token $CSD_TOKEN"

            echo "CMD: $BIN_DIR/cstub $ARGS"
            $BIN_DIR/cstub $ARGS
            RET=$?
            if [ "$RET" != "0" ] ; then
                echo "cstub FAIL: $RET, grepping logs for error|warning:"
                grep -e error -e warning $HOSTSCAN_DIR/log/* | sed -e "s/^/  /"
            else
                echo "cstub SUCCESS"
            fi
        '''
```

```
        csd-wrapper-exec.sh = '''
            #!/bin/bash
            ~/csd-wrapper.sh "$@" 2>&1 | sed -e "s/^/ [csd] /"
        '''
```
Openconnect provides the `--csd-*` arguments for integration with Cisco Hostscan, which changes
the `start` hook to look like:

```
[run]
    [[hooks]]
        start = '''
            #!/bin/bash
            set -e -v
            sudo openconnect {{vpn.addr}} --interface tun1\
             -v\
             --csd-user user\
             --csd-wrapper /home/user/csd-wrapper-exec.sh
        '''
```

### Cisco Hostscan Stubbed
Interestingly, if you happen to know exactly what to submit to the VPN entrypoint it is
possible to satisfy the check without needing to instal or run the Cisco Hostscan software. The
example fragments below may help you achieve this.

_CAUTION: in using this technique you will most likely contravene the usage policy for the VPN endpoint._

```
        Dockerfile.tmpl = '''
            ...
            WORKDIR /home/user/

            ADD csd-responder.sh /home/user/
            ADD csd-responder-exec.sh /home/user/
            RUN sudo chown user ./*.sh && chmod u+x ./*.sh
            ...
        '''
```

```
        csd-responder.sh = '''
            #!/bin/bash

            echo "$0""$@"
            env | grep CSD | sort | sed -e "s/^/ENV: /"

            # location is usually "Default"
            location=$(wget -O - -q "https://$CSD_HOSTNAME/CACHE/sdesktop/data.xml?reusebrowser=1" | grep 'location name=' | head -1 | sed -e 's/.*"\(.*\)".*/\1/')

            POST_DATA=$(mktemp)
            CURL_CMD=$(mktemp)

            agent="AnyConnect Linux"
            plat=linux-x86_64
            ver=4.2.03013

            cat > $POST_DATA <<-END
            endpoint.policy.location="Default";
            endpoint.enforce="success";
            endpoint.fw["IPTablesFW"]={};
            endpoint.fw["IPTablesFW"].exists="true";
            endpoint.fw["IPTablesFW"].enabled="ok";
            endpoint.as["ClamAS"]={};
            endpoint.as["ClamAS"].exists="true";
            endpoint.as["ClamAS"].activescan="ok";
            endpoint.av["ClamAV"]={};
            endpoint.av["ClamAV"].exists="true";
            endpoint.av["ClamAV"].activescan="ok";
            END

            cat > $CURL_CMD <<-END
            curl \\
              --insecure \\
              --user-agent "$agent $ver" \\
              --header "X-Transcend-Version: 1" \\
              --header "X-Aggregate-Auth: 1" \\
              --header "X-AnyConnect-Platform: $plat" \\
              --cookie "sdesktop=$CSD_TOKEN" \\
              --data-ascii $POST_DATA \\
              "https://$CSD_HOSTNAME/+CSCOE+/sdesktop/scan.xml?reusebrowser=1"
            END

            cat $CURL_CMD | sed -e "s/^/CURL: /"
            cat $POST_DATA | sed -e "s/^/POST: /"

            . $CURL_CMD

            echo "curl exited with $?"
        '''
```

```
        csd-responder-exec.sh = '''
            #!/bin/bash
            ~/csd-responder.sh "$@" 2>&1 | sed -e "s/^/ [csd] /"
        '''

```
Change the `start` hook to:

```
[run]
    [[hooks]]
        start = '''
            #!/bin/bash
            set -e -v
            sudo openconnect {{vpn.addr}} --interface tun1\
             -v\
             --csd-user user\
             --csd-wrapper /home/user/csd-responder-exec.sh
        '''
```
