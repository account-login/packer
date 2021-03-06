install: packer.py
	install packer.py /usr/local/bin/packer.py
	ln -sf packer.py /usr/local/bin/packer

link: packer.py
	ln -sf "$(realpath packer.py)" /usr/local/bin/packer

doc: packer.py
	./packer.py --help=markdown >README.md

uninstall:
	rm -rf /usr/local/bin/packer.py
	rm -rf /usr/local/bin/packer
	rm -rf /usr/local/bin/unpacker
