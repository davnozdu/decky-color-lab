// Focus identity from Gamescope; UI overlays do not replace the base app ID.
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <stdio.h>
#include <stdlib.h>
static unsigned long prop(Display*d,Window w,const char*name){Atom type;int fmt;unsigned long n,left;unsigned char*p=NULL;unsigned long v=0;if(XGetWindowProperty(d,w,XInternAtom(d,name,False),0,1,False,AnyPropertyType,&type,&fmt,&n,&left,&p)==Success&&n&&fmt==32)v=*(unsigned long*)p;if(p)XFree(p);return v;}
static int ignore_error(Display*d,XErrorEvent*e){(void)d;(void)e;return 0;}
int main(){XSetErrorHandler(ignore_error);Display*d=XOpenDisplay(":0");if(!d)return 2;unsigned long id=prop(d,DefaultRootWindow(d),"GAMESCOPE_FOCUSED_APP_GFX");printf("%lu\n",id);XCloseDisplay(d);if(id==0||id==769)return 0;d=XOpenDisplay(":1");if(d){Window w=prop(d,DefaultRootWindow(d),"_NET_ACTIVE_WINDOW");char*name=NULL;if(w&&XFetchName(d,w,&name)&&name){for(char*p=name;*p;p++)if((unsigned char)*p<32)*p=' ';puts(name);XFree(name);}XCloseDisplay(d);}return 0;}
