
UI_FILES = querydlg.py
GEN_FILES = resources.py

all: $(GEN_FILES) $(UI_FILES)

querydlg.py: ui/querydlg.ui
	pyuic4 -o ui/querydlg.py ui/querydlg.ui
	
resources.py: resources.qrc
	pyrcc4 -o resources.py resources.qrc


clean:
	rm -f $(GEN_FILES) *.pyc

package:
	cd .. && ln -sTf last_pgadmin_query last_pgadmin_query && rm -f last_pgadmin_query.zip && zip -r last_pgadmin_query.zip last_pgadmin_query -x \*.svn* -x \*.pyc -x \*~ -x \*entries\* -x \*.git\*
