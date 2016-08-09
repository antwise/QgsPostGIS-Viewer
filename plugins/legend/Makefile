
GEN_FILES = resources.py

all: $(GEN_FILES)
	
resources.py: resources.qrc
	pyrcc4 -o resources.py resources.qrc

clean:
	rm -f $(GEN_FILES) *.pyc

package:
	cd .. && ln -sTf legend legend && rm -f legend.zip && zip -r legend.zip legend -x \*.svn* -x \*.git* -x \*.pyc -x \*~ -x \*entries\* -x \*.git\*
