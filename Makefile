install: packer.py
	install packer.py /usr/local/bin/packer.py
	ln -s packer.py /usr/local/bin/packer

link: packer.py
	ln -s "$(realpath packer.py)" /usr/local/bin/packer

uninstall:
	rm -rf /usr/local/bin/packer.py
	rm -rf /usr/local/bin/packer

