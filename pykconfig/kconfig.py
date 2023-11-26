import re


class Regex(object):
    COMMENT = re.compile(r'\t*#')
    NEWLINE = re.compile(r'\n')


class Base(object):
    PARSED_NOTHING = 0
    PARSED = 1
    PARSED_PARTIAL = 2
    color = {
        PARSED_NOTHING: '\033[31m',
        PARSED: '\033[32m',
        PARSED_PARTIAL: '\033[33m',
        'DEFAULT': '\033[39m',
    }
    keywords = [
        'comment',
        'newline',
    ]

    def __init__(self, base, name):
        self.base = base
        self.name = name
        self.files = []
        self.lines = []
        self.children = []

    def __str__(self):
        return f'{self.__class__.__name__}({self.name})'

    def open(self, filename):
        f = open(self.base + '/' + filename)
        self.files.append(f)
        self.lines.append(0)

    def close(self):
        self.files.pop(-1)
        self.lines.pop(-1)

    def readline(self):
        f = self.files[-1]

        while True:
            line = f.readline()
            if not line:
                return None

            self.lines[-1] += 1
            self.line = line
            return line

    def log(self, level):
        filename = self.files[-1].name.replace(f'{self.base}/', '')
        mark = '    parsed' if level == self.PARSED else 'not parsed'
        print(f'{filename:30} : {self.lines[-1]:6} : {self.name:40} : '
              f'{self.color[level]}{mark}{self.color["DEFAULT"]} : '
              f'{self.color[level]}{self.line}',
              end=self.color['DEFAULT'])

    def parse(self):
        while self.readline():
            parsed = False

            for keyword in self.keywords:
                regex = getattr(Regex, keyword.upper())
                match = regex.match(self.line)
                if not match:
                    continue

                getattr(self, f'parse_{keyword}')(match)
                parsed = True
                break

            if not parsed:
                self.log(self.PARSED_NOTHING)

    def parse_comment(self, match):
        self.log(self.PARSED)

    def parse_newline(self, match):
        self.log(self.PARSED)

    def parse_variable(self, string):
        for match in re.finditer(Regex.VARIABLE, string):
            value = self.kconfig.variables[match.group(1)]
            string = string.replace(match.group(0), value)

        return string

    def append_child(self, child):
        self.children.append(child)
        child.parse()
        self.lines[-1] = child.lines[-1]


class Kconfig(Base):
    def __init__(self, base=''):
        super().__init__(base, '')

        self.kconfig = self
        self.variables = {}

        self.fill_unknown_variables()
        self.open('Kconfig')
        self.parse()
        self.close()

    def fill_unknown_variables(self):
        self.variables.update({
            'ARCH': 'x86',
            'KERNELVERSION': '',
        })


class EntryBase(Base):
    def __init__(self, parent, name):
        super().__init__(parent.kconfig.base, name)

        self.kconfig = parent.kconfig
        self.parent = parent
        self.files = [parent.files[-1]]
        self.lines = [parent.lines[-1]]
        self.line = parent.line

    def __str__(self):
        return self.name
