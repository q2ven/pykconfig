import re


class Regex(object):
    CHOICE = re.compile(r'choice')
    COMMENT = re.compile(r'\t*#')
    CONFIG = re.compile(r'config ([0-9A-Z_]+)')
    DEFAULT = re.compile(r'(?:\t|\s+)(default|def_bool|def_tristate) (.+)')
    DEPEND = re.compile(r'(?:\t|\s+)depends on (.+)')
    ENDCHOICE = re.compile(r'endchoice')
    ENDIF = re.compile(r'endif')
    ENDMENU = re.compile(r'endmenu')
    HELP = re.compile(r'(?:\t|\s+)help')
    IF = re.compile(r'if (.+)')
    IMPLY = re.compile(r'(?:\t|\s+)imply (.+)')
    MAINMENU = re.compile('mainmenu "(.+?)"')
    MENU = re.compile(r'menu "(.+)"')
    MENUCONFIG = re.compile(r'menuconfig ([0-9A-Z_]+)')
    NEWLINE = re.compile(r'\n')
    PROMPT = re.compile(r'(?:\t|\s+)prompt "(.+)"')
    RANGE = re.compile(r'(?:\t|\s+)range (.+)')
    SELECT = re.compile(r'(?:\t|\s+)select (.+)')
    SOURCE = re.compile(r'\s*source[\t\s]"(.+?)"')
    TRISTATE = re.compile(r'(?:\t|\s+)tristate(?: (.+))?')
    TYPE = re.compile(r'(?:\t|\s+)(bool|hex|int|string)')
    VARIABLE = re.compile(r'\$\(([A-Z_]+)\)')


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
    keywords_bailout = []

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

    def undoline(self):
        pos = self.files[-1].tell()
        pos -= len(self.line)
        self.files[-1].seek(pos)
        self.lines[-1] -= 1

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

            for keyword in self.keywords_bailout:
                regex = getattr(Regex, keyword.upper())
                if regex.match(self.line):
                    func = getattr(self, f'parse_{keyword}', None)
                    if func:
                        func()
                    else:
                        self.undoline()

                    return

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
    keywords = {
        'comment': Regex.COMMENT,
        'mainmenu': Regex.MAINMENU,
        'newline': Regex.NEWLINE,
    }

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
            'SRCARCH': 'x86',
        })

    def parse_mainmenu(self, match):
        name = self.parse_variable(match.group(1))
        self.append_child(Menu(self, name, True))


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


class MultipleEntryBase(EntryBase):
    keywords = [
        'choice',
        'comment',
        'config',
        'if',
        'menu',
        'menuconfig',
        'newline',
        'source',
    ]
    keywords_bailout = [
        'endchoice',
        'endif',
        'endmenu',
    ]

    def __init__(self, parent, name):
        super().__init__(parent, name)

    def parse_choice(self, match):
        self.append_child(Choice(self, ''))

    def parse_config(self, match):
        self.append_child(Config(self, match.group(1)))

    def parse_endchoice(self):
        if not isinstance(self, Choice):
            raise

        self.parent.lines[-1] = self.lines[-1]
        self.log(self.PARSED)

    def parse_endif(self):
        if not isinstance(self, If):
            raise

        self.parent.lines[-1] = self.lines[-1]
        self.log(self.PARSED)

    def parse_endmenu(self):
        if not isinstance(self, Menu) or self.is_main:
            raise

        self.parent.lines[-1] = self.lines[-1]
        self.log(self.PARSED)

    def parse_if(self, match):
        self.append_child(If(self, match.group(1)))

    def parse_menu(self, match):
        name = self.parse_variable(match.group(1))
        self.append_child(Menu(self, name))

    def parse_menuconfig(self, match):
        self.append_child(MenuConfig(self, match.group(1)))

    def parse_source(self, match):
        filename = self.parse_variable(match.group(1))

        self.log(self.PARSED)
        self.open(filename)
        self.parse()
        self.close()


class Menu(MultipleEntryBase):
    def __init__(self, parent, name, is_main=False):
        super().__init__(parent, name)

        self.is_main = is_main

        self.log(self.PARSED)


class If(MultipleEntryBase):
    def __init__(self, parent, name):
        super().__init__(parent, name)

        self.log(self.PARSED)


class Choice(MultipleEntryBase):
    keywords = [
        'choice',
        'config',
        'comment',
        'default',
        'depend',
        'help',
        'menu',
        'newline',
        'prompt',
        'source',
    ]
    keywords_bailout = [
        'endchoice',
        'endmenu',
    ]

    def __init__(self, parent, name):
        super().__init__(parent, name)

        self.logs = [(self.PARSED, self.line)]
        self.flush = False

        def parse_misc(match):
            self.log(self.PARSED)

        for keyword in self.keywords:
            func = getattr(self, f'parse_{keyword}', None)
            if not func:
                setattr(self, f'parse_{keyword}', parse_misc)

    def log(self, level):
        self.logs.append((level, self.line))

        if not self.flush:
            return

        self.lines[-1] -= len(self.logs)

        for level, line in self.logs:
            self.line = line
            self.lines[-1] += 1
            super().log(level)

        self.logs = []

    def parse_help(self, match):
        self.log(self.PARSED)

        while self.readline():
            if Regex.CONFIG.match(self.line):
                self.undoline()
                return

            self.log(self.PARSED)

    def parse_prompt(self, match):
        self.name = match.group(1)
        self.flush = True
        self.log(self.PARSED)


class Config(EntryBase):
    keywords = [
        'comment',
        'default',
        'depend',
        'help',
        'imply',
        'newline',
        'prompt',
        'range',
        'select',
        'tristate',
        'type',
    ]
    keywords_bailout = [
        'choice',
        'config',
        'endchoice',
        'endif',
        'endmenu',
        'if',
        'menu',
        'menuconfig',
        'source',
    ]

    def __init__(self, parent, name):
        super().__init__(parent, name)

        self.log(self.PARSED)

        def parse_misc(match):
            self.log(self.PARSED)

            while self.line.endswith('\\\n'):
                self.readline()
                self.log(self.PARSED)

        for keyword in self.keywords:
            func = getattr(self, f'parse_{keyword}', None)
            if not func:
                setattr(self, f'parse_{keyword}', parse_misc)

    def parse_help(self, match):
        self.log(self.PARSED)

        while self.readline():
            for keyword in self.keywords_bailout:
                regex = getattr(Regex, keyword.upper())
                if regex.match(self.line):
                    self.undoline()
                    return

            self.log(self.PARSED)


class MenuConfig(Config):
    pass


if __name__ == "__main__":
    Kconfig("/home/kuniyu/kernel/linux")
