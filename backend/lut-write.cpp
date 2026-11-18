// Build Gamescope SDR LUT without a per-entry Python loop.
#include <array>
#include <cstdint>
#include <vector>
#include <fstream>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <stdexcept>
static std::vector<float> read(const char*p,size_t n){std::vector<float>x(n);std::ifstream f(p,std::ios::binary);f.read((char*)x.data(),n*4);if(f.gcount()!=long(n*4))throw std::runtime_error("LUT asset size");for(float v:x)if(!std::isfinite(v))throw std::runtime_error("LUT non-finite");return x;}
static float smoothstep(float low,float high,float value){float t=std::clamp((value-low)/(high-low),0.f,1.f);return t*t*(3.f-2.f*t);}
using RGB=std::array<float,3>;
static float luminance(const RGB&v){return .2126f*v[0]+.7152f*v[1]+.0722f*v[2];}
static size_t index_of(size_t r,size_t g,size_t b){return r+33*g+1089*b;}
// A gray input traverses diagonal LUT cells. The three one-high and three
// two-high corners have equal interpolation weights within each group.
// Matching their channel sums makes the entire gray ramp neutral, including
// values between lattice nodes. Ordered group means also prevent gray reversals.
static void balance_group(std::vector<RGB>&table,const std::array<size_t,3>&ids,float target){
 for(size_t ch=0;ch<3;ch++){
  float low=-1,high=1;
  for(int iteration=0;iteration<24;iteration++){
   float shift=(low+high)*.5f,sum=0;
   for(size_t id:ids)sum+=std::clamp(table[id][ch]+shift,0.f,1.f);
   if(sum<3*target)low=shift;else high=shift;
  }
  for(size_t id:ids)table[id][ch]=std::clamp(table[id][ch]+(low+high)*.5f,0.f,1.f);
 }
}
static void protect_neutrals(std::vector<RGB>&table){
 std::array<float,33>gray{};
 for(size_t k=1;k<32;k++)gray[k]=std::max(gray[k-1],luminance(table[index_of(k,k,k)]));
 gray[32]=1;
 for(size_t k=0;k<33;k++)table[index_of(k,k,k)].fill(gray[k]);
 for(size_t k=0;k<32;k++){
  std::array<size_t,3>one={index_of(k+1,k,k),index_of(k,k+1,k),index_of(k,k,k+1)};
  std::array<size_t,3>two={index_of(k+1,k+1,k),index_of(k+1,k,k+1),index_of(k,k+1,k+1)};
  RGB sum_one{},sum_two{};
  for(size_t ch=0;ch<3;ch++)for(size_t j=0;j<3;j++){sum_one[ch]+=table[one[j]][ch];sum_two[ch]+=table[two[j]][ch];}
  float first=std::clamp(luminance(sum_one)/3,gray[k],gray[k+1]);
  float second=std::clamp(luminance(sum_two)/3,first,gray[k+1]);
  balance_group(table,one,first);balance_group(table,two,second);
 }
}
int main(int argc,char**argv){try{
 if(argc!=10)throw std::runtime_error("Usage: lut-write BASIS HDR-or-dash W0 W1 W2 STRENGTH BLACK CONTRAST OUTPUT");
 const size_t n=33*33*33;bool hdr=argv[2][0]!='-';auto basis=read(hdr?argv[2]:argv[1],hdr?3*n:9*n);
 float weight[3]={std::stof(argv[3]),std::stof(argv[4]),std::stof(argv[5])};float s=std::clamp(std::stof(argv[6])/100,0.f,1.f),black=std::clamp(std::stof(argv[7])/100,0.f,.3f),c=std::stof(argv[8]);
 for(float value:{s,black,c})if(!std::isfinite(value))throw std::runtime_error("Non-finite look parameter");
 if(!hdr)for(float value:weight)if(!std::isfinite(value))throw std::runtime_error("Non-finite adaptive weight");
 // Photo-trained adaptive LUTs can lift black with unequal RGB offsets. In
 // shadows use the same monotone tone curve for each channel, so neutral
 // surfaces stay neutral. Fade back to the original look in the midtones.
 // HDRTVNet's separately tone-mapped output bypasses this correction.
 std::array<float,33> shadow_tone{};
 if(!hdr){
  for(size_t k=1;k<33;k++){
   size_t index=k*(1089+33+1);float neutral[3];
   for(size_t ch=0;ch<3;ch++)neutral[ch]=std::clamp(weight[0]*basis[ch*n+index]+weight[1]*basis[(3+ch)*n+index]+weight[2]*basis[(6+ch)*n+index],0.f,1.f);
   float t=float(k)/32,luma=.2126f*neutral[0]+.7152f*neutral[1]+.0722f*neutral[2];
   float tone=t+smoothstep(.04f,.12f,t)*(luma-t);
   shadow_tone[k]=std::max(shadow_tone[k-1],tone);
  }
 }
 FILE*f=fopen(argv[9],"w");
 if(!f)throw std::runtime_error("LUT open");
 setvbuf(f,nullptr,_IOFBF,65536);fprintf(f,"TITLE \"Decky Color Lab SDR\"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n");
 std::vector<RGB>table(n);
 for(size_t i=0;i<n;i++){
  float identity[3]={float(i%33)/32,float(i/33%33)/32,float(i/1089)/32},rgb[3];
  float shadow=hdr?0.f:1-smoothstep(.125f,.25f,std::max({identity[0],identity[1],identity[2]}));
  size_t channel_index[3]={i%33,i/33%33,i/1089};
  for(int ch=0;ch<3;ch++){float v=hdr?basis[ch*n+i]:weight[0]*basis[ch*n+i]+weight[1]*basis[(3+ch)*n+i]+weight[2]*basis[(6+ch)*n+i];if(shadow>0)v=v*(1-shadow)+shadow_tone[channel_index[ch]]*shadow;rgb[ch]=std::clamp(identity[ch]*(1-s)+v*s,0.f,1.f);}
  float y=.2126f*rgb[0]+.7152f*rgb[1]+.0722f*rgb[2],mapped=(y+c*(y-.5f)*y*(1-y))*(1-black*(1-y)*(1-y));float ratio=y>1e-7f?mapped/y:1;
  for(int ch=0;ch<3;ch++)table[i][ch]=std::clamp(rgb[ch]*ratio,0.f,1.f);
 }
 if(!hdr&&s>0)protect_neutrals(table);
 std::vector<char> text(n*30);char*cursor=text.data();
 for(size_t i=0;i<n;i++){
  for(int ch=0;ch<3;ch++){
   double v=table[i][ch];uint32_t q=uint32_t(v*10000000.+.5);
   cursor[0]=q>=10000000?'1':'0';cursor[1]='.';
   for(int digit=8;digit>=2;digit--){cursor[digit]='0'+q%10;q/=10;}
   cursor[9]=ch==2?'\n':' ';cursor+=10;
  }
 }
 if(fwrite(text.data(),1,text.size(),f)!=text.size())throw std::runtime_error("LUT write");
 if(fclose(f))throw std::runtime_error("LUT write");
 return 0;
}catch(const std::exception&e){fprintf(stderr,"%s\n",e.what());return 1;}}
