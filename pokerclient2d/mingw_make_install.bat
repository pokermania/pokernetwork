@echo %PYTHONROOT%\Lib\site-packages\_pokerinterface2_4.dll
%MINGWROOT%\bin\gcc.exe -o %PYTHONROOT%\Lib\site-packages\_pokerinterface2_4.dll blind.c buy_in.c cashier.c chat.c check_warning.c chooser.c credits.c dispatcher.c gui.c hand_history.c lobby.c login.c menu.c message_box.c muck.c outfits.c python.c sit_actions.c tournaments.c util.c yesno_message.c -DPYTHON_VERSION=\"2_4\" -DVERSION_NAME(a)=a##2_4 -I%PYTHONROOT%\include -I%GTKROOT%\include\libglade-2.0 -I%GTKROOT%\include\gtk-2.0 -I%GTKROOT%\include\libxml2 -I%GTKROOT%\lib\gtk-2.0\include -I%GTKROOT%\include\atk-1.0 -I%GTKROOT%\include\cairo -I%GTKROOT%\include\pango-1.0 -I%GTKROOT%\include\glib-2.0 -I%GTKROOT%\lib\glib-2.0\include -I%GTKROOT%\include\libxml2 -I%GTKROOT%\include -shared -L%PYTHONROOT%\libs -lpython24 -L%GTKROOT%\lib -lglib-2.0 -lgtk-win32-2.0 -lglade-2.0 -lgobject-2.0 -lintl -liconv -lgdk-win32-2.0 -lgdk_pixbuf-2.0 -lxml2
@echo %PYTHONROOT%\Lib\site-packages\pokerclient2d\*.py
mkdir %PYTHONROOT%\Lib\site-packages\pokerclient2d
copy __init__.py  %PYTHONROOT%\Lib\site-packages\pokerclient2d
copy poker2d.py %PYTHONROOT%\Lib\site-packages\pokerclient2d
copy pokeranimation2d.py %PYTHONROOT%\Lib\site-packages\pokerclient2d
copy pokerdisplay2d.py %PYTHONROOT%\Lib\site-packages\pokerclient2d
copy pokerinterface2d.py %PYTHONROOT%\Lib\site-packages\pokerclient2d
copy gamewindow.py %PYTHONROOT%\Lib\site-packages\pokerclient2d
