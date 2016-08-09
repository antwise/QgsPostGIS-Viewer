@echo on

; rem find QGIS in directories
set qgis_dirs="C:\Program Files\QGIS Brighton"  "C:\Program Files (x86)\QGIS Brighton" "C:\OSGeo4W"
set OSGEO4W_ROOT=
for %%d in (%qgis_dirs%) do (
    if not defined OSGEO4W_ROOT (
	    if exist %%d  set OSGEO4W_ROOT=%%~d
	)
)
if not defined OSGEO4W_ROOT   echo "ERROR:cannot find QGIS!!!!"
echo Find QGIS in : %OSGEO4W_ROOT%


; rem calc current path 
set DIR_SCRIPT=%~d0%~p0

; rem set Environment
set PATH=%OSGEO4W_ROOT%\bin;%DIR_SCRIPT%;%PATH%
for %%f in ("%OSGEO4W_ROOT%\etc\ini\*.bat") do call "%%f"
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python
set PATH=%OSGEO4W_ROOT%\apps\qgis\bin;%PATH%


start /B pyuic4 -o ui/querydlg_ui.py ui/querydlg.ui
start /B pyrcc4 -o resources.py resources.qrc

