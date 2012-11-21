ifndef version
VERSION_STRING=
else
VERSION_STRING=-$(version)
endif

all:
	# try something like
	# $ version=0.6 make package

package: 
	mkdir plugin.video.onlinetvrecorder_com
	cp -R LICENSE.TXT addon.xml icon.png otr.py resources  plugin.video.onlinetvrecorder_com/
	find plugin.video.onlinetvrecorder_com/ -name '*.pyc' -delete
	find plugin.video.onlinetvrecorder_com/ -name '*.pyo' -delete
	zip -r xbmc-otr$(VERSION_STRING).zip plugin.video.onlinetvrecorder_com/
	rm -rf plugin.video.onlinetvrecorder_com/
	
