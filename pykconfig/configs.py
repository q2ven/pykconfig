import re
from collections import OrderedDict


class Configs(object):
    regex = re.compile(r'^CONFIG_(.*?)=(.*?)\n')

    def __init__(self, filename=""):
        self.configs = OrderedDict()

        self.filename = filename
        self.parse()

    def __len__(self):
        return len(self.configs)

    def __iter__(self):
        return iter(self.configs)

    def __contains__(self, key):
        return key in self.configs

    def __getitem__(self, key):
        return self.configs[key]

    def __setitem__(self, key, value):
        self.configs[key] = value

    def __and__(self, other):
        result = self.__class__()

        for key in self:
            if key in other and self[key] == other[key]:
                result[key] = self[key]

        return result

    def __str__(self):
        config_list = []

        for key in self:
            config_list.append(f'CONFIG_{key}={self[key]}')

        return '\n'.join(config_list)

    def parse(self):
        if not self.filename:
            return self

        with open(self.filename, 'r') as f:
            for config in f.readlines():
                match = self.regex.match(config)

                if not match:
                    continue

                self.configs[match.group(1)] = match.group(2)

        return self
