#include <onnxruntime_cxx_api.h>
#include <chrono>
#include <cmath>
#include <ctime>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

int main(int argc,char** argv) {
  try {
    if(argc!=7) throw std::runtime_error("Usage: color-probe MODEL INPUT OUTPUT CACHE CONFIG COUNT");
    int count=std::stoi(argv[6]); if(count<0) throw std::runtime_error("Bad count");
    Ort::Env env(ORT_LOGGING_LEVEL_INFO,"color_probe");
    Ort::SessionOptions options; options.SetIntraOpNumThreads(1);options.SetInterOpNumThreads(1);
    bool cpu=std::getenv("COLOR_CPU")!=nullptr;
    bool allow_cpu=std::getenv("COLOR_ALLOW_CPU")!=nullptr;
    if(std::getenv("COLOR_VERBOSE")) options.SetLogSeverityLevel(0);
    if(count>0) options.EnableProfiling("color-profile");
    if(!cpu) {
      if(!allow_cpu) options.AddConfigEntry("session.disable_cpu_ep_fallback","1");
      options.AppendExecutionProvider_VitisAI({{"config_file",argv[5]},{"cache_dir",argv[4]},
        {"cache_key","adaptive-lut-unpaired-explicit-norm-v1"},{"enable_cache_file_io_in_mem","1"}});
    }
    Ort::Session session(env,argv[1],options);
    std::vector<float> pixels(3*256*256);
    std::ifstream input(argv[2],std::ios::binary);
    input.read(reinterpret_cast<char*>(pixels.data()),pixels.size()*4);
    if(input.gcount()!=static_cast<std::streamsize>(pixels.size()*4)) throw std::runtime_error("Bad input file");
    auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    int64_t shape[]={1,3,256,256};
    auto image=Ort::Value::CreateTensor<float>(memory,pixels.data(),pixels.size(),shape,4);
    const char* ins[]={"image"};const char* outs[]={"weights"};
    auto run=[&](){return session.Run(Ort::RunOptions{nullptr},ins,&image,1,outs,1);};
    auto result=run(); for(int i=0;i<2;++i) result=run();
    if(result[0].GetTensorTypeAndShapeInfo().GetElementCount()!=3) throw std::runtime_error("Bad output shape");
    if(count==0) {
      std::cout<<"COLOR_READY"<<std::endl;
      while(std::cin.read(reinterpret_cast<char*>(pixels.data()),pixels.size()*sizeof(float))) {
        auto t=std::chrono::steady_clock::now();auto c=std::clock();result=run();
        double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count();
        double cpu_ms=1000.*(std::clock()-c)/CLOCKS_PER_SEC;
        auto* v=result[0].GetTensorData<float>();
        for(int i=0;i<3;++i) if(!std::isfinite(v[i])) throw std::runtime_error("Non-finite coefficient");
        std::cout<<"COLOR_RESULT "<<v[0]<<' '<<v[1]<<' '<<v[2]<<' '<<ms<<' '<<cpu_ms<<std::endl;
      }
      return 0;
    }
    auto start=std::chrono::steady_clock::now();auto cpu_start=std::clock();
    for(int i=0;i<count;++i) result=run();
    double wall=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()/count;
    double cpu_ms=1000.*(std::clock()-cpu_start)/CLOCKS_PER_SEC/count;
    auto* weights=result[0].GetTensorData<float>();
    std::ofstream output(argv[3],std::ios::binary);output.write(reinterpret_cast<const char*>(weights),3*4);
    std::cout<<"device="<<(cpu?"CPU":allow_cpu?"VitisAI-hybrid-diagnostic":"VitisAI-strict")<<" inference_ms="<<wall<<" process_cpu_ms="<<cpu_ms<<" weights=";
    for(int i=0;i<3;++i) {if(!std::isfinite(weights[i]))throw std::runtime_error("Non-finite coefficient");std::cout<<weights[i]<<' ';}
    std::cout<<std::endl;
    Ort::AllocatorWithDefaultOptions allocator;auto profile=session.EndProfilingAllocated(allocator);
    std::cout<<"profile="<<profile.get()<<std::endl;
  } catch(const std::exception& error){std::cerr<<"FAILED: "<<error.what()<<std::endl;return 1;}
}
