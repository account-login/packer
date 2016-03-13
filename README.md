
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
usage:
    compress files
    --------------
    packer.py 1.txt 2.txt --to archive.7z
    packer.py dir/ --format=tar.gz                  # got dir.tar.gz
    packer.py 1.txt 2.txt --format gz               # got 1.txt.gz, 2.txt.gz
    cat file | packer.py - --format xz > file.xz    # read from stdin
    
    extract
    -------
    packer.py -x archive.tgz                        # extract to current dir
    packer.py -x archive.7z --to directory/         # extract to directory/
    packer.py -x archive.gz --to -     # write contents of archive.gz to stdout
    
    view
    ----
    packer.py --list archive.rar                    # list archive.rar
    packer.py --test --list archive.rar             # test archive.rar


```

Installation
============

Get some command-line tools that packer.py can work with.

`apt-get install p7zip-full rar zip unzip tar gzip bzip2 xz-utils lzma lzip lzop`

Install dependency

`pip install plumbum`

Copy packer.py to /usr/local/bin and create `upacker`, `packer` symlinks by executing

`make install`

Options
=======
```
options:
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


```

