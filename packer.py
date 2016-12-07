#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Introduction
============

`packer.py` is a wrapper around popular file archiving/compressing tools (tar, zip, rar, gzip, ...).
The purpose of this script is to provide unified command-line interface to existing tools,
so you don't need to read boring manpages when you forget the command-line option of tar, 7z, zip, and etc.
There is a similar project `atool` that achieves the same purpose.

`packer.py` currently supports 7z, rar, zip, tar, tar.*, gzip, bzip2, xz, lzma, lzip, lzop formats.
`packer.py` uses `file` command to identify archive, then the appropriate tool was used to handle
 that archive.
If the type of a archive can't be identified, 7z was used to handle that archive.

packer.py requires python3.4+, plumbum

Usage
=====
```
{usage}
```

Installation
============

Get some command-line tools that packer.py can work with.

`apt-get install p7zip-full rar zip unzip tar gzip bzip2 xz-utils lzma lzip lzop`

Install dependency

`pip install plumbum`

Copy packer.py to /usr/local/bin and create `packer` symlinks by executing

`make install`

Options
=======
```
{options}
```
'''

# TODO: add, convert
# TODO: --best option
# TODO: --override option
# TODO: --comment option
# TODO: cpio, dar, ar, arj, ace, arc, rpm, deb, cab, rzip, lrzip, alzip, lha
# TODO: atool
# TODO: bash completion

import sys, os, argparse, shlex
from io import StringIO
from plumbum import local, CommandNotFound


def print_usage(app, file=sys.stdout):
    s_compress = """
    compress files
    --------------
    {app} 1.txt 2.txt --to archive.7z
    {app} dir/ --format=tar.gz                  # got dir.tar.gz
    {app} 1.txt 2.txt --format gz               # got 1.txt.gz, 2.txt.gz
    cat file | {app} - --format xz > file.xz    # read from stdin
    """
    s_extract = """
    extract
    -------
    {app} -x archive.tgz                        # extract to current dir
    {app} -x archive.7z --to directory/         # extract to directory/
    {app} -x archive.gz --to -     # write contents of archive.gz to stdout
    """
    s_view = """
    view
    ----
    {app} --list archive.rar                    # list archive.rar
    {app} --test --list archive.rar             # test archive.rar
"""
    s = 'usage:' + s_compress + s_extract + s_view
    print(s.format(app=app), file=file)

def print_options_help(app, file=sys.stdout):
    print("""options:
  -h, --help
                        show this help message and exit
  -v, --verbosity
                        increase output verbosity
  -x ARCHIVE, --extract ARCHIVE
                        extract ARCHIVE
  --to OUTPUT
                        output to OUTPUT (file or dir)
  --list ARCHIVE, -l ARCHIVE
                        list files in ARCHIVE
  --test, -t
                        test ARCHIVE, must be used with --list
  --password PASSWORD, --passwd PASSWORD, -p PASSWORD
                        specify password for archive
  --extra-opt EXTRA_OPT
                        extra options passed to the packer
  --packer {lzma,bzip2,unzip,zip,tar,lzop,7zr,lzip,xz,unrar,rar,gzip,winrar,7z}
                        specify packer
  --format FORMAT, -f FORMAT
                        specify archive format
  --dry-run, --simulate
                        do not run the command
""", file=file)

def print_help(app, file=sys.stdout):
    print_usage(app, file=file)
    print_options_help(app, file=file)

def fill_doc_string():
    # complete __doc__ string
    usage = StringIO()
    print_usage(app='packer.py', file=usage)
    usage = usage.getvalue()

    options = StringIO()
    print_options_help(app='packer.py', file=options)
    options = options.getvalue()

    global __doc__ # @ReservedAssignment
    __doc__ = __doc__.format(usage=usage, options=options) # @ReservedAssignment

fill_doc_string()

class ParseError(Exception):
    pass

class SilentArgumentParser(argparse.ArgumentParser):
    '''
    ArgumentParser that do not exit on parsing failure.
    '''
    def __init__(self, *args, **kwds):
        super(SilentArgumentParser, self).__init__(formatter_class=argparse.RawDescriptionHelpFormatter, *args, **kwds)
    def error(self, message):
        raise ParseError('not match')
    def user_error(self, msg):
        print(msg, file=sys.stderr)
        self.print_usage()

# cmds: zip, unzip, rar, unrar, 7z, 7za, 7zr, tar, ar, gzip, xz, bzip2, lzma, lzip, lzop, compress
# uses: zip, rar, unrar, 7z, tar, gzip, xz, bzip2

filter_type = {'gz', 'bz2', 'xz', 'lzma', 'Z', 'lz', 'lzo'}
suf2filter = {
    'gz'  : 'gzip',
    'bz2' : 'bzip2',
    'xz'  : 'xz',
    'lzma': 'lzma',
    'Z'   : 'compress',
    'lz'  : 'lzip',
    'lzo' : 'lzop',
}

def get_format_by_filename(filename):
    if '.' not in filename:
        return None
    ext = filename.split('.')[-2:]
    if len(ext) == 2:
        if ext[0].lower() == 'tar':
            return format_normalize('.'.join(ext))
    return format_normalize(ext[-1])

def format_normalize(fmt):
    if fmt in {'taZ', 'tar.Z'}:
        return 'tar.Z'
    if fmt.upper() == 'Z':
        return 'Z'

    lfmt = fmt.lower()
    norm = {
        'tgz'  : 'tar.gz',
        'taz'  : 'tar.gz',
        'tz2'  : 'tar.bz2',
        'tbz'  : 'tar.bz2',
        'tbz2' : 'tar.bz2',
        'tlz'  : 'tar.lzma',
        'gzip' : 'gz',
        'bzip2': 'bz2',
        'lzip' : 'lz',
        'lzop' : 'lzo',
    }
    if lfmt in norm:
        return norm[lfmt]
    else:
        return lfmt

def run_cmd(cmd, verbose=False):
    if verbose:
        print('running: '+str(cmd), file=sys.stderr)
    from plumbum import FG, ProcessExecutionError
    try:
        cmd & FG
        return 0
    except ProcessExecutionError as e:
        return e.retcode

def run_cmd_dry(cmd, verbose=False):
    print(str(cmd))
    return 0


## begin pack*
def pack_tar(args):
    tar = local['tar']

    tar_opt = ['cf', '-']
    if args.extra_opt is not None:
        tar_opt += shlex.split(args.extra_opt)
    if args.verbosity:
        tar_opt.append('-v')
    tar_opt.append('--')
    tar_opt += args.inputs

    if args.format == 'tar':
        cmd = tar[tar_opt] > args.archive
    else:
        _, suf = args.format.split('.')
        compressor = local[suf2filter[suf]]
        compressor_opt = []
        if args.verbosity:
            compressor_opt.append('-v')
        cmd = (tar[tar_opt] | compressor[compressor_opt]) > args.archive

    return run_cmd(cmd, args.verbosity)

def pack_filter(args):
    opt = []
    if args.verbosity:
        opt.append('-v')
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)

    if args.packer is None:
        compressor = local[suf2filter[args.format]]
    else:
        compressor = local[args.packer]

    retcode_final = 0
    for x in args.inputs:
        if len(args.inputs) == 1:
            outfile = args.archive
        else:   # multiple inputs
            if x == '-':
                outfile = '-'
            else:
                outfile = x+'.'+args.format

        cmd = compressor[opt]
        if x != '-':
            cmd = cmd < x
        if outfile != '-':
            cmd = cmd > outfile
        retcode = run_cmd(cmd, args.verbosity)
        if retcode != 0:
            retcode_final = retcode
    return retcode_final

def pack_7z_common(args, cmd_bin):
    sevenz = local[cmd_bin]
    opt = ['a', args.archive, '-t'+format_normalize(args.format)]
    if args.password is not None:
        opt.append('-p'+args.password)
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    opt.append('--')
    opt += args.inputs

    cmd = sevenz[opt]
    return run_cmd(cmd, args.verbosity)

def pack_7z(args):
    return pack_7z_common(args, '7z')

def pack_7zr(args):
    return pack_7z_common(args, '7zr')

def pack_rar(args):
    rar = local['rar']
    opt = ['a', args.archive]
    opt.append('-r')    # rar is not recursive by default
    if args.password is not None:
        opt.append('-p'+args.password)
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    opt.append('--')
    opt += args.inputs

    cmd = rar[opt]
    return run_cmd(cmd, args.verbosity)

def pack_winrar(args):
    rar = local['winrar']
    opt = ['a', args.archive, '-af'+args.format]
    opt.append('-r')    # rar is not recursive by default
    if args.password is not None:
        opt.append('-p'+args.password)
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    opt.append('--')
    opt += args.inputs

    cmd = rar[opt]
    return run_cmd(cmd, args.verbosity)

def pack_zip(args):
    zip_cmd = local['zip']
    opt = ['-r', args.archive]
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    if args.password is not None:
        opt.append('-P'+args.password)
    if args.verbosity:
        opt.append('-v')
    opt.append('--')
    opt += args.inputs

    cmd = zip_cmd[opt]
    return run_cmd(cmd, args.verbosity)

format2packer = {
    '7z'     : (pack_7z, pack_7zr),
    'rar'    : (pack_rar, pack_winrar),
    'zip'    : (pack_zip, pack_7z, pack_winrar),
    'unknown': (pack_7z, pack_winrar),
}

def pack(args):
    fmt = args.format = format_normalize(args.format)
    # tar, tar.*
    if fmt in {'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.lzma', 'tar.Z', 'tar.lz', 'tar.lzo'}:
        return pack_tar(args)
    # filter_type = {'gz', 'bz2', 'xz', 'lzma', 'Z', 'lz', 'lzo'}
    elif fmt in filter_type:
        return pack_filter(args)
    elif fmt in {'7z', 'rar', 'zip'}:
        if args.packer is None:
            for packer in format2packer[fmt]:
                try:
                    return packer(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception(str(format2packer[fmt])+' not found')
        else:
            packer = getattr(sys.modules[__name__], 'pack_'+args.packer)
            return packer(args)
    else:
        raise Exception('unhandled format')
## end pack*


def identify(filename):
    # BUG: tar.lzo, tar.lzma
    # TODO: stdin?
    file_cmd = local['file']
    opt = ['-zb', '--', filename]
    cmd = file_cmd[opt]
    result = cmd()

    outer = {
        'gzip compressed data' : 'gz',
        'bzip2 compressed data': 'bz2',
        'XZ compressed data'   : 'xz',
        'compress\'d data'     : 'Z',
        'lzip compressed data' : 'lz',
        #'LZMA compressed data' : 'lzma',
        #'lzop compressed data' : 'lzo',
    }
    for x in outer:
        if x in result:
            if 'tar archive' in result:
                return 'tar.'+outer[x]
            else:
                return outer[x]
    else:
        if 'LZMA compressed data' in result:
            try:
                lzma = local['lzma']
            except CommandNotFound:
                return 'lzma'
            else:
                cmd = (lzma['-d'] < filename) | file_cmd['-']
                res2 = cmd()
                if 'tar archive' in res2:
                    return 'tar.lzma'
                else:
                    return 'lzma'
        elif 'lzop compressed data' in result:
            try:
                lzop = local['lzop']
            except CommandNotFound:
                return 'lzo'
            else:
                cmd = (lzop['-d'] < filename) | file_cmd['-']
                res2 = cmd()
                if 'tar archive' in res2:
                    return 'tar.lzo'
                else:
                    return 'lzo'

        sig = {
            'RAR archive data'    : 'rar',
            'RAR self-extracting' : 'rar',
            'Zip archive data'    : 'zip',
            'ZIP self-extracting' : 'zip',
            'tar archive'         : 'tar',
            '7-zip archive data'  : '7z',
        }
        for x in sig:
            if x in result:
                return sig[x]
        else:
            return 'unknown'


## begin unpack*
def ensure_output_dir(directory):
    if directory is None:
        directory = '.'
    os.makedirs(directory, exist_ok=True)
    return directory

def ensure_output_dir_dry(directory):
    return directory

def unpack_tar(args):
    args.output = ensure_output_dir(args.output)
    tar = local['tar']
    tar_opt = ['xf', args.archive, '-C', args.output]
    # tar bug
    if args.format == 'tar.lzma':
        tar_opt.append('--lzma')
    if args.extra_opt is not None:
        tar_opt += shlex.split(args.extra_opt)
    if args.verbosity:
        tar_opt.append('-v')

    cmd = tar[tar_opt]
    return run_cmd(cmd, args.verbosity)

def unpack_filter(args):
    if args.packer is None:
        args.packer = suf2filter[args.format] if args.format != 'Z' else 'gzip'
    filter_cmd = local[args.packer]
    opt = ['-d']
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)

    cmd = filter_cmd[opt]
    if args.archive != '-':
        cmd = cmd < args.archive
    if args.output != '-':
        cmd = cmd > args.output
    return run_cmd(cmd, args.verbosity)

def unpack_7z_rar_common(args, cmd_bin, rar):
    sevenz = local[cmd_bin]
    opt = ['x', args.archive]
    if args.format is not None and not rar:
        opt.append('-t'+format_normalize(args.format))
    if args.password is not None:
        opt.append('-p'+args.password)
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    if args.output is not None:
        args.output = ensure_output_dir(args.output)
        if rar:
            opt.append(args.output)
        else:
            opt.append('-o'+args.output)

    cmd = sevenz[opt]
    return run_cmd(cmd, args.verbosity)

def unpack_7z(args):
    return unpack_7z_rar_common(args, '7z', False)

def unpack_7zr(args):
    return unpack_7z_rar_common(args, '7zr', False)

def unpack_rar(args):
    return unpack_7z_rar_common(args, 'rar', True)

def unpack_unrar(args):
    return unpack_7z_rar_common(args, 'unrar', True)

def unpack_winrar(args):
    return unpack_7z_rar_common(args, 'winrar', True)

def unpack_unzip(args):
    unzip_cmd = local['unzip']
    args.output = ensure_output_dir(args.output)
    opt = ['-d', args.output]
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    if args.password is not None:
        opt.append('-P'+args.password)
    opt += ['--', args.archive]

    cmd = unzip_cmd[opt]
    return run_cmd(cmd, args.verbosity)

format2unpacker = {
    '7z' : (unpack_7z, unpack_7zr, unpack_winrar),
    'rar': (unpack_unrar, unpack_rar, unpack_winrar, unpack_7z),
    'zip': (unpack_unzip, unpack_7z, unpack_winrar),
}

def unpack(args):
    fmt = args.format
    if fmt is None:
        fmt = identify(args.archive)
        if fmt != 'unknown':
            args.format = fmt

    fmt = format_normalize(fmt)
    if args.packer is None:
        # tar, tar.*
        if fmt in {'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.lzma', 'tar.Z', 'tar.lz', 'tar.lzo'}:
            return unpack_tar(args)
        # filter_type = {'gz', 'bz2', 'xz', 'lzma', 'Z', 'lz', 'lzo'}
        elif fmt in filter_type:
            if args.output is None:
                if args.archive.endswith('.'+fmt):
                    args.output = args.archive[:-len('.'+fmt)]
                else:
                    raise Exception('you must specify --to option')
            return unpack_filter(args)
        elif fmt in {'7z', 'rar', 'zip'}:
            for unpacker in format2unpacker[fmt]:
                try:
                    return unpacker(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception(str(format2unpacker[fmt])+' not found')
        elif fmt == 'unknown':
            for unpacker in (unpack_7z, unpack_rar, unpack_winrar):
                try:
                    return unpacker(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception('unknown format, 7z or rar or winrar not found')
        else:
            raise Exception('unhandled format '+str(args.format))
    else:
        if args.packer == 'zip':
            args.packer = 'unzip'
        unpacker = getattr(sys.modules[__name__], 'unpack_'+args.packer)
        return unpacker(args)
## end unpack*

## begin view*
def view_tar(args):
    tar = local['tar']
    tar_opt = ['tf', args.archive]
    # tar bug
    if args.format == 'tar.lzma':
        tar_opt.append('--lzma')
    if args.extra_opt is not None:
        tar_opt += shlex.split(args.extra_opt)
    if args.verbosity:
        tar_opt.append('-v')

    cmd = tar[tar_opt]
    return run_cmd(cmd, args.verbosity)

def view_gz(args):
    gz_cmd = local['gzip']
    opt = ['--list']
    if args.verbosity:
        opt.append('-v')
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)

    cmd = gz_cmd[opt]
    if args.archive != '-':
        cmd = cmd < args.archive
    ret =  run_cmd(cmd, args.verbosity)
    if args.test:
        opt.remove('--list')
        opt.append('--test')
        cmd = gz_cmd[opt]
        if args.archive != '-':
            cmd = cmd < args.archive
        ret2 = run_cmd(cmd, args.verbosity)
        ret = ret or ret2

    return ret

def view_7z_common(args, cmd_bin):
    sevenz = local[cmd_bin]
    if args.test:
        opt = ['t', args.archive]
    else:
        opt = ['l', args.archive]
        if args.verbosity > 1:
            opt.append('-slt')

    if args.format is not None:
        opt.append('-t'+format_normalize(args.format))
    if args.password is not None:
        opt.append('-p'+args.password)
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)

    cmd = sevenz[opt]
    return run_cmd(cmd, args.verbosity)

def view_7z(args):
    return view_7z_common(args, '7z')

def view_7zr(args):
    return view_7z_common(args, '7zr')

def view_rar_common(args, cmd_bin):
    rar = local[cmd_bin]
    if args.test:
        opt = ['t', args.archive]
    else:
        if args.verbosity > 2:
            opt = ['vta', args.archive]
        elif args.verbosity > 1:
            opt = ['vt', args.archive]
        elif args.verbosity > 0:
            opt = ['v', args.archive]
        else:
            opt = ['lb', args.archive]

    if args.password is not None:
        opt.append('-p'+args.password)
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)

    cmd = rar[opt]
    return run_cmd(cmd, args.verbosity)

# winrar do not support listing

def view_rar(args):
    return view_rar_common(args, 'rar')

def view_unrar(args):
    return view_rar_common(args, 'unrar')

def view_unzip(args):
    unzip = local['unzip']
    if args.test:
        opt = ['-t']
    else:
        opt = ['-Z']
        if args.verbosity > 1:
            opt.append('-v')
        elif args.verbosity > 0:
            opt.append('-s')
        else:
            opt.append('-1')
    opt.append('--')
    opt.append(args.archive)

    cmd = unzip[opt]
    return run_cmd(cmd, args.verbosity)

format2viewer = {
    '7z' : (view_7z, view_7zr),
    'rar': (view_unrar, view_rar, view_7z),
    'zip': (view_unzip, view_7z),
}

def view(args):
    fmt = args.format
    if fmt is None:
        fmt = identify(args.archive)
        if fmt != 'unknown':
            args.format = fmt

    fmt = format_normalize(fmt)
    if args.packer is None:
        # tar, tar.*
        if fmt in {'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.lzma', 'tar.Z', 'tar.lz', 'tar.lzo'}:
            return view_tar(args)
        elif fmt == 'gz':
            return view_gz(args)
        # filter_type = {'gz', 'bz2', 'xz', 'lzma', 'Z', 'lz', 'lzo'}
        elif fmt in filter_type:
            raise Exception("'%s' do not support listing" % fmt)
        elif fmt in {'7z', 'rar', 'zip'}:
            for viewer in format2viewer[fmt]:
                try:
                    return viewer(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception(str(format2viewer[fmt])+' not found')
        elif fmt == 'unknown':
            for viewer in (view_7z,):
                try:
                    return viewer(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception('unknown format, 7z or rar or winrar not found')
        else:
            raise Exception('unhandled format '+str(args.format))
    else:
        if args.packer == 'zip':
            args.packer = 'unzip'
        viewer = getattr(sys.modules[__name__], 'view_'+args.packer)
        return viewer(args)
# end view*

def dry_run_patch():
    global run_cmd, ensure_output_dir
    run_cmd = run_cmd_dry
    ensure_output_dir = ensure_output_dir_dry


def main():
    argv = sys.argv.copy()
    app = argv[0].rsplit(os.path.sep, maxsplit=1)[-1]
    argv_body = argv[1:]


    # packer file1 [file2]... [--to output] [--format tgz]
    parser1 = SilentArgumentParser(prog=app, add_help=False, description='compress files.\n'
                               'examples:\n'
                               '    packer 1.txt 2.txt --to archive.7z\n'
                               '    packer dir/ --format=tar.gz                   # got dir.tar.gz\n'
                               '    packer 1.txt 2.txt --format gz                # got 1.txt.gz, 2.txt.gz\n'
                               '    cat file | packer - --format xz > file.xz     # read from stdin\n'
                               '\n')
    parser1.add_argument('inputs', nargs='+')
    parser1.add_argument('--to', metavar='ARCHIVE', dest='archive')

    # packer -x archive --to dir/
    parser2 = SilentArgumentParser(prog=app, add_help=False, description='decompress archive.\n'
                               'examples:\n'
                               '    packer -x archive.tgz\n'
                               '    packer -x archive.7z --to directory/\n'
                               '    packer -x archive.gz --to -    # write contents of archive.gz to stdout\n'
                               '\n')
    parser2.add_argument('-x', '--extract', metavar='ARCHIVE', required=True, dest='archive')
    parser2.add_argument('--to', metavar='OUTPUT', required=False, dest='output')

    # packer [--test] --list archive
    parser3 = SilentArgumentParser(prog=app, add_help=False, description='list archive contents, test archive')
    parser3.add_argument('--test', '-t', action='store_true')
    parser3.add_argument('--list', '-l', metavar='ARCHIVE', required=True, dest='archive')

    # add common options
    for parser in (parser1, parser2, parser3):
        parser.add_argument("-v", "--verbosity", action="count", default=0,
                            help="increase output verbosity")
        parser.add_argument('--password', '--passwd', '-p', help='specify password for archive')
        parser.add_argument('--extra-opt', help='extra options passed to the packer')
        parser.add_argument('--packer',
                            choices={'rar', 'winrar', 'unrar', '7z', '7zr', 'zip', 'unzip', 'tar',
                                     'gzip', 'bzip2', 'xz', 'lzma', 'lzip', 'lzop'},
                            help='specify packer')
        parser.add_argument('--format', '-f', help='specify archive format')
        # --dry-run option was not handled here, it is handled in help_tester below
        parser.add_argument('--dry-run', '--simulate', help='do not run the command', dest='dry_run',
                            action='store_true')

    # print help and exit if -h in options
    help_tester = SilentArgumentParser(add_help=False)
    help_tester.add_argument('-h', '--help', help='show all help', dest='help', nargs='?', const='cmd')
    # --dry-run option was handled here
    help_tester.add_argument('--dry-run', '--simulate', help='do not run the command', dest='dry_run',
                             action='store_true')
    args, unknown = help_tester.parse_known_args(argv_body) # @UnusedVariable
    if args.help == 'cmd':
        print_help(app)
        return 0
    elif args.help == 'markdown':
        print(__doc__)
        return 0

    if args.dry_run:
        dry_run_patch()

    # packer file1 [file2]... [--to output] [--format tgz]
    try:
        args = parser1.parse_args(argv_body)
    except ParseError:
        # try next parser
        pass
    else:
        # run
        # do furer check on options
        if args.format is None and args.archive is None:
            parser1.user_error('you must specify --to or --format')
            return 1

        if args.format is None:
            # guess format by archive name
            args.format = get_format_by_filename(args.archive)
            if args.format is None:
                parser1.user_error('could not determine archive type, '
                               'add --format option or use proper extension in --to')
                return 1
        else:
            if args.format in filter_type:
                if args.archive is not None:
                    if len(args.inputs) > 1:
                        parser1.user_error('too many INPUTS')
                        return 1

        if args.archive is None:
            if len(args.inputs) == 1:
                # guess archive name by input file name
                if args.inputs[0] == '-':
                    args.archive = '-'
                else:
                    args.archive = os.path.normpath(args.inputs[0]) + '.' + args.format
            else:
                if args.format not in filter_type:
                    # guess archive name by cwd
                    cwd = os.getcwd()
                    cwd = os.path.abspath(cwd)  # is this necessary?
                    archive = cwd.split(os.sep)[-1]
                    if archive == '':
                        # we are at root directory
                        parser1.user_error('could not determine archive name, you must specify --to')
                        return 1
                    archive += '.'+args.format
                    args.archive = archive

        args.format = format_normalize(args.format)
        return pack(args)

    # packer -x archive --to dir/
    try:
        args = parser2.parse_args(argv_body)
    except ParseError:
        # try next parser
        pass
    else:
        # run
        return unpack(args)

    # packer [--test] --list archive
    try:
        args = parser3.parse_args(argv_body)
    except ParseError:
        pass
    else:
        return view(args)

    # all parsers fail to parse, print usage and exit
    print_usage(app)
    print('Run `{} --help=markdown` to see full documentation.'.format(app))
    return 1

if __name__ == '__main__':
    sys.exit(main())
