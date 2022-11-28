# ilert-nagios

iLert Integration Plugin for Nagios, Icinga, and Check_MK.

For setup instructions, refer to our integration guides below.

> Note: use Python >= 3.7 (in case Python 2 is needed, use scripts in `/python2`)

## Integration Guides

- [iLert Nagios Integration](https://docs.ilert.com/integrations/nagios/)
- [iLert checkmk Integration](https://docs.ilert.com/integrations/check-mk/)

### Local environment

#### Nagios

```sh
docker-compose up -d
```

#### CheckMk

```sh
docker-compose -f ./docker-compose-checkmk.yaml up -d
```
