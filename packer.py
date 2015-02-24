#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# apt-get install p7zip-full rar zip unzip tar gzip bzip2 xz-utils lzma lzip lzop

# TODO: --best option
# TODO: unpacker.py

from __future__ import print_function, unicode_literals

import argparse
import shlex
import sys
from plumbum import local, CommandNotFound

class ParseError(Exception):
    pass

class SilentArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwds):
        super().__init__(formatter_class=argparse.RawDescriptionHelpFormatter, *args, **kwds)
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
        
    compressor = local[suf2filter[args.format]]
    
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
            'Zip archive data'    : 'zip',
            'tar archive'         : 'tar',
            '7-zip archive data'  : '7z',
        }
        for x in sig:
            if x in result:
                return sig[x]
        else:
            return 'unknown'


## begin unpack*
def unpack_tar(args):
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
    opt = ['-d', args.output]
    if args.extra_opt is not None:
        opt += shlex.split(args.extra_opt)
    if args.password is not None:
        opt.append('-P'+args.password)
    opt += ['--', args.archive]
    
    cmd = unzip_cmd[opt]
    return run_cmd(cmd, args.verbosity)

format2unpacker = {
    '7z' : (unpack_7z, unpack_7zr, unpack_rar, unpack_winrar),
    'rar': (unpack_unrar, unpack_rar, unpack_winrar, unpack_7z),
    'zip': (unpack_unzip, unpack_7z, unpack_rar),
}

def unpack(args):
    fmt = args.format
    if fmt is None:
        fmt = identify(args.archive)
        if fmt != 'unknown':
            args.format = fmt

    fmt = format_normalize(fmt)
    # tar, tar.*
    if fmt in {'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.lzma', 'tar.Z', 'tar.lz', 'tar.lzo'}:
        if args.output is None:
            args.output = '.'
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
        if args.output is None:
            args.output = '.'
        if args.packer is None:
            for unpacker in format2unpacker[fmt]:
                try:
                    return unpacker(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception(str(format2unpacker[fmt])+' not found')
        else:
            if args.packer == 'zip':
                args.packer = 'unzip'
            unpacker = getattr(sys.modules[__name__], 'unpack_'+args.packer)
            return unpacker(args)
    elif fmt == 'unknown':
        if args.output is None:
            args.output = '.'
        if args.packer is None:
            for unpacker in (unpack_7z, unpack_rar, unpack_winrar):
                try:
                    return unpacker(args)
                except CommandNotFound:
                    continue
            else:
                raise Exception('unknown format, 7z or rar or winrar not found')
        else:
            unpacker = getattr(sys.modules[__name__], 'unpack_'+args.packer)
            return unpacker(args)
    else:
        raise Exception('unhandled format '+str(args.format))
## end unpack*

def view(args):
    pass

def main():
    # packer file1 [file2]... [--to output] [--format tgz]
    ps1 = SilentArgumentParser(description='compress files.\n'
                               'examples:\n'
                               '    packer 1.txt 2.txt --to archive.7z\n'
                               '    packer 1.txt 2.txt --to archive.tar.gz --format=tar.gz\n'
                               '    packer 1.txt 2.txt --format gz                # got 1.txt.gz, 2.txt.gz\n'
                               '    cat file | packer - --format xz > file.xz     # read from stdin\n'
                               '\n')
    ps1.add_argument('inputs', nargs='+')
    ps1.add_argument('--to', metavar='ARCHIVE', dest='archive')

#     # packer --add|-a archive [--format tgz] --with files...
#     ps2 = SilentArgumentParser()
#     ps2.add_argument('--add', '-a', metavar='ARCHIVE', required=True, dest='archive')
#     ps2.add_argument('--with', nargs='+', metavar='INPUT', required=True, dest='inputs')
    
    # packer -x archive --to dir/
    ps3 = SilentArgumentParser(description='decompress archive.\n'
                               'examples:\n'
                               '    packer -x archive.tgz\n'
                               '    packer -x archive.7z --to directory/\n'
                               '    packer -x archive.gz --to -    # write contents of archive.gz to stdout\n'
                               '\n')
    ps3.add_argument('-x', '--extract', metavar='ARCHIVE', required=True, dest='archive')
    ps3.add_argument('--to', metavar='OUTPUT', required=False, dest='output')
    
    # packer [--test] archive
    ps4 = SilentArgumentParser(description='list archive contents, test archive.')
    ps4.add_argument('--test', '-t', action='store_true')
    ps4.add_argument('archive')
    
    # add common options
    for parser in (ps1, ps3, ps4):
        parser.add_argument("-v", "--verbosity", action="count", default=0,
                            help="increase output verbosity")
        parser.add_argument('--password', '--passwd', '-p', help='specify password for archive')
        parser.add_argument('--extra-opt', help='extra options passed to the packer')
        parser.add_argument('--packer', choices={'rar', 'winrar', '7z', 'zip', 'tar', 'gzip', 'bzip2', 'xz'},
                            help='specify packer')
        parser.add_argument('--format', '-f', help='specify archive format')
    
    # print help and exit if -h in options
    help_tester = SilentArgumentParser(add_help=False)
    help_tester.add_argument('-h', '--help', help='show all help', dest='help', action='store_true')
    args, unknown = help_tester.parse_known_args()
    if args.help:
        for parser in (ps1, ps3, ps4):
            parser.print_help()
            print()
            print()
        return 0
    
    # packer file1 [file2]... [--to output] [--format tgz]
    try:
        args = ps1.parse_args()
    except ParseError:
        # try next parser
        pass
    else:
        # run
        # do furer check on options
        if args.format is None and args.archive is None:
            ps1.user_error('you must specify --to or --format')
            return 1
        
        if args.format is None:
            # guess format by archive name
            args.format = get_format_by_filename(args.archive)
            if args.format is None:
                ps1.user_error('could not determine archive type, '
                               'add --format option or use proper extension in --to')
                return 1
        else:
            if args.format in filter_type:
                if args.archive is not None:
                    if len(args.inputs) > 1:
                        ps1.user_error('too many INPUTS')
        
        if args.archive is None:
            if len(args.inputs) == 1:
                # guess archive name by input file name
                if args.inputs[0] == '-':
                    args.archive = '-'
                else:
                    args.archive = args.inputs[0] + '.' + args.format
            else:
                if args.format not in filter_type:
                    # guess archive name by cwd
                    import os
                    cwd = os.getcwd()
                    cwd = os.path.abspath(cwd)  # is this necessary?
                    archive = cwd.split(os.sep)[-1]
                    if archive == '':
                        # we are at root directory
                        ps1.user_error('could not determine archive name, you must specify --to')
                        return 1
                    archive += '.'+args.format
                    args.archive = archive

        args.format = format_normalize(args.format)
        return pack(args)
    
    # packer -x archive --to dir/
    try:
        args = ps3.parse_args()
    except ParseError:
        # try next parser
        pass
    else:
        # run
        return unpack(args)
    
    # packer [--test] archive
    # todo:
    
    # all parsers fail to parse, print usage and exit
    for parser in (ps1, ps3, ps4):
        parser.print_usage()
    return 1
    

if __name__ == '__main__':
    sys.exit(main())
