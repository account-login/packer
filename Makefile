install: packer.py
	install packer.py /usr/local/bin/packer.py
	ln -sf packer.py /usr/local/bin/packer

link: packer.py
	ln -sf "$(realpath packer.py)" /usr/local/bin/packer

uninstall:
	rm -rf /usr/local/bin/packer.py
	rm -rf /usr/local/bin/packer

