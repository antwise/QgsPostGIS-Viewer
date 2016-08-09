UI_SOURCES=$(wildcard ui/*.ui)
UI_FILES=$(patsubst %.ui,%_ui.py,$(UI_SOURCES))

GEN_FILES = resources.py ${UI_FILES}

all: $(GEN_FILES)


$(UI_FILES): %_ui.py: %.ui
	pyuic4 -o $@ $<
	
resources.py: resources.qrc
	pyrcc4 -o resources.py resources.qrc


clean:
	rm -f $(GEN_FILES) *.pyc

package:
	cd .. && ln -sTf sql_layer rt_sql_layer && rm -f rt_sql_layer.zip && zip -r rt_sql_layer.zip rt_sql_layer -x \*.svn* -x \*.pyc -x \*~ -x \*entries\* -x \*.git\*
