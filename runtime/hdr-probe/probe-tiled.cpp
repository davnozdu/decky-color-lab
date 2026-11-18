#include <onnxruntime_cxx_api.h>
#include <chrono>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
#include <array>
#include <cmath>
static void readfile(const std::filesystem::path&p,std::vector<float>&x){std::ifstream f(p,std::ios::binary);f.read((char*)x.data(),x.size()*4);if(f.gcount()!=long(x.size()*4))throw std::runtime_error("Bad input: "+p.string());}
int main(int argc,char**argv){try{
 if(argc!=7)throw std::runtime_error("Usage: hdr-probe-tiled POINTWISE IMAGE OUTPUT CACHE CONFIG COUNT");
 int count=std::stoi(argv[6]);bool cpu=getenv("COLOR_CPU");Ort::Env env(ORT_LOGGING_LEVEL_WARNING,"hdr_tiled");
 Ort::SessionOptions options,co;for(auto*p:{&options,&co}){p->SetIntraOpNumThreads(1);p->SetInterOpNumThreads(1);}
 if(count){options.EnableProfiling("hdr-tile-profile");co.EnableProfiling("hdr-condition-profile");}
 if(!cpu){if(!getenv("COLOR_ALLOW_CPU"))options.AddConfigEntry("session.disable_cpu_ep_fallback","1");options.AppendExecutionProvider_VitisAI({{"config_file",argv[5]},{"cache_dir",argv[4]},{"cache_key","hdr-agcm-pointwise-tile64-v4"},{"enable_cache_file_io_in_mem","1"}});}
 auto root=std::filesystem::path(argv[1]).parent_path();Ort::Session classifier(env,(root/"hdr-condition.onnx").c_str(),co),pointwise(env,argv[1],options);
 const size_t n=33*33*33,tile=4096;std::vector<float>pixels(3*256*256),all_grid(3*n),grid(3*tile),output(3*n);std::array<float,6>features{};
 readfile(argv[2],pixels);readfile(root/"grid-unpadded.bin",all_grid);
 auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);int64_t is[]={1,3,256,256},gs[]={1,3,64,64},fs[]={1,6};
 auto image=Ort::Value::CreateTensor<float>(memory,pixels.data(),pixels.size(),is,4);
 std::vector<Ort::Value>inputs;inputs.push_back(Ort::Value::CreateTensor<float>(memory,grid.data(),grid.size(),gs,4));inputs.push_back(Ort::Value::CreateTensor<float>(memory,features.data(),features.size(),fs,2));
 const char*ci[]={"image"},*couts[]={"features"},*pi[]={"grid","features"},*po[]={"hdr_lut"};
 auto run=[&](){
  auto condition=classifier.Run(Ort::RunOptions{nullptr},ci,&image,1,couts,1);memcpy(features.data(),condition[0].GetTensorData<float>(),24);
  for(size_t start=0;start<n;start+=tile){size_t size=std::min(tile,n-start);
   for(size_t ch=0;ch<3;ch++){memcpy(grid.data()+ch*tile,all_grid.data()+ch*n+start,size*4);if(size<tile)std::fill(grid.begin()+ch*tile+size,grid.begin()+(ch+1)*tile,0);}
   auto result=pointwise.Run(Ort::RunOptions{nullptr},pi,inputs.data(),2,po,1);auto*v=result[0].GetTensorData<float>();for(size_t ch=0;ch<3;ch++)memcpy(output.data()+ch*n+start,v+ch*tile,size*4);
  }
  for(float v:output)if(!std::isfinite(v))throw std::runtime_error("Non-finite output");
 };
 auto save=[&](){std::ofstream f(argv[3],std::ios::binary);f.write((char*)output.data(),output.size()*4);if(!f)throw std::runtime_error("Output write failed");};
 for(int i=0;i<3;i++)run();
 if(!count){std::cout<<"HDR_READY"<<std::endl;while(std::cin.read((char*)pixels.data(),pixels.size()*4)){auto t=std::chrono::steady_clock::now();auto c=std::clock();run();double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count(),cm=1000.*(std::clock()-c)/CLOCKS_PER_SEC;save();std::cout<<"HDR_RESULT "<<ms<<' '<<cm<<std::endl;}return 0;}
 auto t=std::chrono::steady_clock::now();auto c=std::clock();for(int i=0;i<count;i++)run();double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count()/count,cm=1000.*(std::clock()-c)/CLOCKS_PER_SEC/count;save();
 std::cout<<"device="<<(cpu?"CPU":"NPU-pointwise+CPU-condition")<<" inference_ms="<<ms<<" process_cpu_ms="<<cm<<std::endl;Ort::AllocatorWithDefaultOptions a;std::cout<<"profile="<<pointwise.EndProfilingAllocated(a).get()<<" condition_profile="<<classifier.EndProfilingAllocated(a).get()<<std::endl;
}catch(const std::exception&e){std::cerr<<"FAILED: "<<e.what()<<std::endl;return 1;}}
