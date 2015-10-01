install: packer.py
	install packer.py /usr/local/bin/packer.py
	ln -sf packer.py /usr/local/bin/packer
	ln -sf packer.py /usr/local/bin/unpacker

link: packer.py
	ln -sf "$(realpath packer.py)" /usr/local/bin/packer
	ln -sf "$(realpath packer.py)" /usr/local/bin/unpacker

uninstall:
	rm -rf /usr/local/bin/packer.py
	rm -rf /usr/local/bin/packer
	rm -rf /usr/local/bin/unpacker

