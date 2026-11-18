// Native Gamescope PipeWire consumer. One mapped buffer -> RGB thumbnail on stdout.
// No screenshot request, notification, PNG encoder, or image file.
#include <pipewire/pipewire.h>
#include <spa/param/video/format-utils.h>
#include <spa/pod/builder.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
struct app {struct pw_main_loop*loop;struct pw_context*ctx;struct pw_core*core;struct pw_registry*registry;struct pw_stream*stream;struct spa_hook rh,ch,sh;struct spa_video_info_raw video;uint32_t node;uint64_t app_id;const char*cache_path;int sync,ok,small,server,pending,have;struct spa_source*timer;unsigned char last[256*256*3];};
static void send_cached(struct app*a){uint32_t size=a->have?sizeof(a->last):0;fwrite(&size,1,4,stdout);if(size)fwrite(a->last,1,size,stdout);fflush(stdout);a->pending=0;if(a->stream)pw_stream_set_active(a->stream,false);}
static void request(void*data,int fd,uint32_t mask){struct app*a=data;char cmd[32];if((mask&SPA_IO_HUP)||read(fd,cmd,sizeof(cmd))<=0){pw_main_loop_quit(a->loop);return;}a->pending=1;if(a->stream)pw_stream_set_active(a->stream,true);struct timespec ts=a->have?(struct timespec){.tv_nsec=150000000}:(struct timespec){.tv_sec=4};pw_loop_update_timer(pw_main_loop_get_loop(a->loop),a->timer,&ts,NULL,false);}
static void param(void*data,uint32_t id,const struct spa_pod*p){struct app*a=data;if(p&&id==SPA_PARAM_Format)spa_format_video_raw_parse(p,&a->video);}
static void process(void*data){
 struct app*a=data;struct pw_buffer*b=pw_stream_dequeue_buffer(a->stream);if(!b)return;
 struct spa_data*d=&b->buffer->datas[0];int w=a->video.size.width,h=a->video.size.height;
 if((!a->server||a->pending)&&d->data&&d->chunk&&d->chunk->size&&!(d->chunk->flags&SPA_CHUNK_FLAG_CORRUPTED)&&w>0&&h>0&&(a->small?(w<=256&&h<=256):(w>=1920&&h>=1080))){
  int stride=d->chunk->stride>0?d->chunk->stride:w*4;unsigned char out[256*256*3];const unsigned char*p=(const unsigned char*)d->data+d->chunk->offset;
  if((size_t)(h-1)*stride+(size_t)w*4<=d->maxsize-d->chunk->offset){
   for(int y=0;y<256;y++)for(int x=0;x<256;x++){
    const unsigned char*v=p+((2*y+1)*h/512)*stride+((2*x+1)*w/512)*4;
    out[(y*256+x)*3]=v[2];out[(y*256+x)*3+1]=v[1];out[(y*256+x)*3+2]=v[0];
   }
   if(a->server){memcpy(a->last,out,sizeof(out));a->have=1;a->ok=1;if(a->cache_path){FILE*f=fopen(a->cache_path,"wb");if(f){fwrite(out,1,sizeof(out),f);fclose(f);}}}else a->ok=fwrite(out,1,sizeof(out),stdout)==sizeof(out);fprintf(stderr,"PW_CAPTURE %d %d\n",w,h);
  }
 }
 pw_stream_queue_buffer(a->stream,b);if(a->ok){if(a->server){send_cached(a);a->ok=0;}else pw_main_loop_quit(a->loop);}
}
static void state(void*data,enum pw_stream_state old,enum pw_stream_state now,const char*error){(void)old;if(now==PW_STREAM_STATE_ERROR){struct app*a=data;fprintf(stderr,"PipeWire capture: %s\n",error?error:"stream error");pw_main_loop_quit(a->loop);}}
static const struct pw_stream_events se={PW_VERSION_STREAM_EVENTS,.state_changed=state,.param_changed=param,.process=process};
static void global(void*data,uint32_t id,uint32_t permissions,const char*type,uint32_t version,const struct spa_dict*props){(void)permissions;(void)version;struct app*a=data;if(strcmp(type,PW_TYPE_INTERFACE_Node))return;const char*name=props?spa_dict_lookup(props,PW_KEY_NODE_NAME):NULL;if(name&&!strcmp(name,"gamescope"))a->node=id;}
static const struct pw_registry_events re={PW_VERSION_REGISTRY_EVENTS,.global=global};
static void done(void*data,uint32_t id,int seq){struct app*a=data;if(id!=PW_ID_CORE||seq!=a->sync||a->stream)return;if(a->node==PW_ID_ANY){fprintf(stderr,"Gamescope PipeWire source unavailable; restart Gamescope session to restore it\n");pw_main_loop_quit(a->loop);return;}
 a->stream=pw_stream_new(a->core,"Decky Color Lab capture",pw_properties_new(PW_KEY_MEDIA_TYPE,"Video",PW_KEY_MEDIA_CATEGORY,"Capture",PW_KEY_MEDIA_ROLE,"Production",NULL));pw_stream_add_listener(a->stream,&a->sh,&se,a);
 uint8_t buf[2048];struct spa_pod_builder b=SPA_POD_BUILDER_INIT(buf,sizeof(buf));struct spa_rectangle def=SPA_RECTANGLE(1920,1080),min=SPA_RECTANGLE(1,1),max=SPA_RECTANGLE(8192,8192),small=SPA_RECTANGLE(256,256);struct spa_fraction rate=SPA_FRACTION(0,1);
 // Accept native dimensions and variable rate; requested_size asks Gamescope to scale.
 const struct spa_pod*p=spa_pod_builder_add_object(&b,SPA_TYPE_OBJECT_Format,SPA_PARAM_EnumFormat,
  SPA_FORMAT_mediaType,SPA_POD_Id(SPA_MEDIA_TYPE_video),SPA_FORMAT_mediaSubtype,SPA_POD_Id(SPA_MEDIA_SUBTYPE_raw),
  SPA_FORMAT_VIDEO_format,SPA_POD_Id(SPA_VIDEO_FORMAT_BGRx),SPA_FORMAT_VIDEO_size,SPA_POD_CHOICE_RANGE_Rectangle(&def,&min,&max),
  SPA_FORMAT_VIDEO_framerate,SPA_POD_Fraction(&rate),0x70000,SPA_POD_Rectangle(a->small?&small:&def),0x70001,SPA_POD_Long((int64_t)a->app_id));
 int result=pw_stream_connect(a->stream,PW_DIRECTION_INPUT,a->node,PW_STREAM_FLAG_AUTOCONNECT|PW_STREAM_FLAG_MAP_BUFFERS|(a->server?PW_STREAM_FLAG_INACTIVE:0),&p,1);if(result<0){fprintf(stderr,"PipeWire connect: %d\n",result);pw_main_loop_quit(a->loop);}else if(a->server){puts("PW_READY");fflush(stdout);}
}
static void error(void*data,uint32_t id,int seq,int res,const char*msg){(void)id;(void)seq;struct app*a=data;fprintf(stderr,"PipeWire error %d: %s\n",res,msg);pw_main_loop_quit(a->loop);}
static const struct pw_core_events ce={PW_VERSION_CORE_EVENTS,.done=done,.error=error};
static void timeout(void*data,uint64_t n){(void)n;struct app*a=data;if(a->server){if(a->pending)send_cached(a);}else pw_main_loop_quit(a->loop);}
int main(int argc,char**argv){pw_init(NULL,NULL);struct app a={.node=PW_ID_ANY,.app_id=argc>2?strtoull(argv[2],NULL,10):0,.server=argc>1&&!strcmp(argv[1],"serve"),.small=!(argc>1&&!strcmp(argv[1],"native"))};if(argc>3){a.cache_path=argv[3];FILE*f=fopen(a.cache_path,"rb");if(f){a.have=fread(a.last,1,sizeof(a.last),f)==sizeof(a.last);fclose(f);}}a.loop=pw_main_loop_new(NULL);a.ctx=pw_context_new(pw_main_loop_get_loop(a.loop),NULL,0);a.core=pw_context_connect(a.ctx,NULL,0);if(!a.core)return 2;pw_core_add_listener(a.core,&a.ch,&ce,&a);a.registry=pw_core_get_registry(a.core,PW_VERSION_REGISTRY,0);pw_registry_add_listener(a.registry,&a.rh,&re,&a);a.sync=pw_core_sync(a.core,PW_ID_CORE,0);
 struct spa_source*t=pw_loop_add_timer(pw_main_loop_get_loop(a.loop),timeout,&a);a.timer=t;struct timespec ts={.tv_sec=4};if(a.server)pw_loop_add_io(pw_main_loop_get_loop(a.loop),STDIN_FILENO,SPA_IO_IN|SPA_IO_HUP,false,request,&a);else pw_loop_update_timer(pw_main_loop_get_loop(a.loop),t,&ts,NULL,false);pw_main_loop_run(a.loop);
 if(a.stream)pw_stream_destroy(a.stream);
 pw_loop_destroy_source(pw_main_loop_get_loop(a.loop),t);pw_proxy_destroy((struct pw_proxy*)a.registry);pw_core_disconnect(a.core);pw_context_destroy(a.ctx);pw_main_loop_destroy(a.loop);return a.ok?0:3;
}
