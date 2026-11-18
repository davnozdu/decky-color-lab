// Minimal Gamescope base-plane screenshot client. Protocol license retained in XML.
#include <wayland-client.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "gamescope-control-client.h"
static struct gamescope_control* control;
static int complete;
static void feature(void*d,struct gamescope_control*c,uint32_t a,uint32_t b,uint32_t f){(void)d;(void)c;(void)a;(void)b;(void)f;}
static void display(void*d,struct gamescope_control*c,const char*a,const char*b,const char*n,uint32_t f,struct wl_array*r){(void)d;(void)c;(void)a;(void)b;(void)n;(void)f;(void)r;}
static void shot(void*d,struct gamescope_control*c,const char*p){(void)d;(void)c;(void)p;complete=1;}
static void stats(void*d,struct gamescope_control*c,uint32_t a,uint32_t l,uint32_t h){(void)d;(void)c;(void)a;(void)l;(void)h;}
static const struct gamescope_control_listener listener={feature,display,shot,stats};
static void global(void*d,struct wl_registry*r,uint32_t n,const char*i,uint32_t v){(void)d;if(!strcmp(i,"gamescope_control")&&v>=3){control=wl_registry_bind(r,n,&gamescope_control_interface,v<7?v:7);gamescope_control_add_listener(control,&listener,NULL);}}
static void removed(void*d,struct wl_registry*r,uint32_t n){(void)d;(void)r;(void)n;}
static const struct wl_registry_listener registry_listener={global,removed};
int main(int argc,char**argv){
 if(argc!=2||argv[1][0]!='/')return 1;
 struct wl_display*d=wl_display_connect("gamescope-0");if(!d)return 2;
 struct wl_registry*r=wl_display_get_registry(d);wl_registry_add_listener(r,&registry_listener,NULL);
 if(wl_display_roundtrip(d)<0||!control)return 3;
 gamescope_control_take_screenshot(control,argv[1],GAMESCOPE_CONTROL_SCREENSHOT_TYPE_BASE_PLANE_ONLY,0);wl_display_flush(d);
 for(int n=0;n<20&&!complete;n++){struct pollfd fd={wl_display_get_fd(d),POLLIN,0};int s=poll(&fd,1,500);if(s<0)break;if(s>0&&wl_display_dispatch(d)<0)break;}
 gamescope_control_destroy(control);wl_registry_destroy(r);wl_display_disconnect(d);
 if(!complete){fprintf(stderr,"Gamescope screenshot timed out\n");return 4;}return 0;
}
