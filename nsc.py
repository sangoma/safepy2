from safe import api
import requests


class Structure(object):
    def __init__(self, api):
        self._api = api
        self._data = api.retrieve()

        for field in self.__fields__:
            attr, cls = field[0], field[1]
            key = field[2] if len(field) > 2 else attr
            setattr(self, attr, cls(self._data[key]))

    def __eq__(self, other):
        return self._data == other._data


class Collection(object):
    def __init__(self, api):
        self.api = api

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        for key in self.keys():
            yield self[key]

    def __getitem__(self, name):
        return self.__cls__(self.api[name])

    def keys(self):
        return self.api.list()

    def create(self, name):
        pass


class NotFound(Exception):
    pass


class Profile(Structure):
    __fields__ = [('ip', str, 'sip-ip'),
                  ('port', int, 'sip-port')]

    @property
    def running(self):
        return bool(self._api.status())
        
    def start(self):
        if self.running:
            return
        
        try:
            self._api.start()
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                raise RuntimeError("Failed to start profile")

    def stop(self):
        if not self.running:
            return

        try:
            self._api.stop()
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                raise RuntimeError("Failed to stop profile")

    @property
    def name(self):
        return self._api.ident

    @property
    def addr(self):
        return (self.ip, self.port)


class Profiles(Collection):
    __cls__ = Profile


class Trunk(Structure):
    __fields__ = [('profile', str, 'sip_profile')]

    @property
    def name(self):
        return self._api.ident

    def __repr__(self):
        return 'Trunk({} bound to {})'.format(self.name, self.profile)


class Trunks(Collection):
    __cls__ = Trunk


class Version(Structure):
    __fields__ = [('major', int, 'major_version'),
                  ('minor', int, 'minor_version'),
                  ('patch', int, 'patch_version'),
                  ('build', int, 'build_version'),
                  ('release', str, 'release_version')]

    def __str__(self):
        return self._data['product_version']


class Address(Structure):
    __fields__ = [('address', str),
                  ('interface', str),
                  ('prefix', int),
                  ('interface', str)]

    @property
    def proto(self):
        value = self._data['proto']
        if value == 'static-4':
            return 'inet'
        elif value == 'static-6':
            return 'inet6'
        raise RuntimeError("Unexpected proto field {}".format(value))

    def __repr__(self):
        return 'Address({}/{} on {})'.format(self.address, self.prefix, self.interface)


class Addresses(Collection):
    __cls__ = Address


class Network(object):
    def __init__(self, api):
        self._api = api
        self._data = api.configuration.retrieve()

    @property
    def dns(self):
        def dns_iter():
            for key in ('dns/1', 'dns/2', 'dns/3', 'dns/4'):
                entry = self._data[key]
                if not entry:
                    return
                yield str(entry)
        return list(dns_iter())

    @property
    def hostname(self):
        return str(self._data['global/hostname'])

    @property
    def ips(self):
        return Addresses(self._api.ip)


class NSC(object):
    def __init__(self, host='localhost'):
        self.host = host
        self.api = api(host)

    @property
    def running(self):
        status = self.api.nsc.service.status()['status_text']
        if status == 'RUNNING':
            return True
        elif status == 'STOPPED':
            return False
        raise RuntimeError("Unexpected status {}".format(status))
    
    def start(self):
        self.api.nsc.service.start()

    def stop(self):
        self.api.nsc.service.stop()

    @property
    def version(self):
        return Version(self.api.nsc.version)

    @property
    def profiles(self):
        return Profiles(self.api.sip.profile)

    @property
    def trunks(self):
        return Trunks(self.api.sip.trunk)

    @property
    def network(self):
        return Network(self.api.network)
