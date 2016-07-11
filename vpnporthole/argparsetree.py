#!/usr/bin/env python
import sys
from argparse import ArgumentParser


class ArgParseTree(object):
    """
    Facilitates building a CLI argument parser with sub commands and options.

    Example:
        $ script [--fish] foo <bar>
        $ script [--fish] spam [--eggs <EGGS>]

    >>> from argparsetree import ArgParseTree
    ...
    >>> class Main(ArgParseTree):
    ...     def args(self, parser):
    ...         parser.add_argument("--fish", default=False, action='store_true')
    ...
    >>> class Foo(ArgParseTree):
    ...     def args(self, parser):
    ...         parser.add_argument("bar")
    ...
    ...     def run(self, args):
    ...         print("FOO: %s (%s)" % (args.bar, args.fish))
    ...         return 3
    ...
    >>> class Spam(ArgParseTree):
    ...     name = 'ham'
    ...     def args(self, parser):
    ...         parser.add_argument("--eggs", default=None)
    ...
    ...     def run(self, args):
    ...         print("SPAM: %s (%s)" % (args.eggs, args.fish))
    ...         return 4
    ...
    >>> m = Main()
    >>> Foo(m)  # doctest: +ELLIPSIS
    <...>
    >>> Spam(m)  # doctest: +ELLIPSIS
    <...>
    >>> m.main([])
    usage: argparsetree.py [-h] [--fish] {foo,ham} ...
    <BLANKLINE>
    positional arguments:
      {foo,ham}
        foo
        ham
    <BLANKLINE>
    optional arguments:
      -h, --help  show this help message and exit
      --fish
    >>> m.main(['foo', "BAR"])
    FOO: BAR (False)
    3
    >>> m.main(['--fish', 'ham', '--eggs', "green"])
    SPAM: green (True)
    4
    """
    usage = None
    name = None
    _parent = None
    _children = None
    _parser = None
    _subparser = None

    def __init__(self, parent=None, **kwargs):
        self.__kwargs = kwargs
        if parent:
            self._parent = parent
            parent._children = parent._children or []
            parent._children.append(self)

    def _setup_args(self):
        if self._parent is None:
            self._parser = ArgumentParser(usage=self.usage)
        else:
            name = self.name or self.__class__.__name__.lower()
            help = None
            description = None
            if self.__doc__:
                from textwrap import dedent
                doc = dedent(self.__doc__.rstrip()).splitlines()
                help = doc[0]
                description = '\n'.join(doc[2:])

            self._parser = self._parent._subparser.add_parser(name=name,
                                                              help=help,
                                                              description=description)

        try:
            self.args(self._parser)
        except AttributeError:
            pass

        if self._children:
            self._subparser = self._parser.add_subparsers()
            for child in self._children:
                child._setup_args()
        else:
            try:
                self._parser.set_defaults(_run=self.run)
            except AttributeError:
                pass

    def main(self, argv=None):
        self._setup_args()

        if argv is None:
            argv = sys.argv[1:]

        args = self._parser.parse_args(argv)
        if '_run' in args:
            return args._run(args)
        self._parser.print_help()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
