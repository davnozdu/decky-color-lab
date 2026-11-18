// Read the focused XWayland application's backing image through MIT-SHM.
// Emits only a 256x256 RGB thumbnail on stdout. Does not invoke screenshot APIs.
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <X11/extensions/XShm.h>
#include <X11/extensions/Xcomposite.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <stdio.h>
#include <stdlib.h>
static int failed;
static int xerror(Display*d,XErrorEvent*e){char s[160];XGetErrorText(d,e->error_code,s,sizeof(s));fprintf(stderr,"X capture: %s\n",s);failed=1;return 0;}
int main(int argc,char**argv){
 Display*d=XOpenDisplay(argc>1?argv[1]:":1");if(!d)return 2;
 XSetErrorHandler(xerror);Window w=0,root=DefaultRootWindow(d);Atom type;int format;unsigned long n,left;unsigned char*p=NULL;
 if(XGetWindowProperty(d,root,XInternAtom(d,"_NET_ACTIVE_WINDOW",False),0,1,False,XA_WINDOW,&type,&format,&n,&left,&p)==Success&&n)w=*(Window*)p;
 if(p)XFree(p);
 if(!w)return 3;
 XWindowAttributes a;if(!XGetWindowAttributes(d,w,&a)||a.width<32||a.height<32)return 4;
 Drawable target=w;
 if(argc>2){target=XCompositeNameWindowPixmap(d,w);XSync(d,False);if(failed)return 9;}
 XShmSegmentInfo si={0};si.shmid=-1;
 XImage*im=XShmCreateImage(d,a.visual,a.depth,ZPixmap,NULL,&si,a.width,a.height);if(!im)return 5;
 si.shmid=shmget(IPC_PRIVATE,(size_t)im->bytes_per_line*im->height,IPC_CREAT|0600);if(si.shmid<0)return 6;
 si.shmaddr=shmat(si.shmid,0,0);si.readOnly=False;im->data=si.shmaddr;
 if(si.shmaddr==(void*)-1){shmctl(si.shmid,IPC_RMID,0);return 7;}
 XShmAttach(d,&si);XSync(d,False);shmctl(si.shmid,IPC_RMID,0);
 int ok=!failed&&XShmGetImage(d,target,im,0,0,AllPlanes);XSync(d,False);
 unsigned char out[256*256*3];
 if(ok&&!failed){
  unsigned long masks[3]={im->red_mask,im->green_mask,im->blue_mask};int shifts[3]={0};
  for(int c=0;c<3;c++){while(masks[c]&&!(masks[c]&1)){masks[c]>>=1;shifts[c]++;}}
  for(int y=0;y<256;y++)for(int x=0;x<256;x++){
   unsigned long v=XGetPixel(im,(2*x+1)*im->width/512,(2*y+1)*im->height/512);
   for(int c=0;c<3;c++)out[(y*256+x)*3+c]=(unsigned char)(((v>>shifts[c])&masks[c])*255/(masks[c]?masks[c]:1));
  }
  if(fwrite(out,1,sizeof(out),stdout)!=sizeof(out))ok=0;
 }
 XShmDetach(d,&si);XSync(d,False);im->data=NULL;XDestroyImage(im);shmdt(si.shmaddr);XCloseDisplay(d);return ok&&!failed?0:8;
}
