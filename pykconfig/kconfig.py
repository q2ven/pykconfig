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


class Kconfig(Base):
    def __init__(self, base=''):
        super().__init__(base, '')

        self.open('Kconfig')
        self.parse()
        self.close()
