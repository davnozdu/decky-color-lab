"""PQ/BT.2020 global neural LUT -> SDR BT.709/Gamma22 preview.
This is a custom luminance-preserving filmic preview, not an HDR display mode.
"""
import numpy as np
def to_sdr(pq):
 pq=np.asarray(pq,dtype=np.float64).reshape(3,-1)
 v=np.clip(pq,0,1)**(1/(2523/32))
 linear=10000*(np.maximum(v-3424/4096,0)/np.maximum(2413/128-2392/128*v,1e-12))**(1/(2610/16384))
 matrix=np.array([[1.660491,-.587641,-.072850],[-.124550,1.132900,-.008350],[-.018151,-.100579,1.118730]])
 rgb=np.maximum(matrix@linear,0)
 y=np.array([.2126,.7152,.0722])@rgb
 z=y/203
 def film(x):return x*(2.51*x+.03)/(x*(2.43*x+.59)+.14)
 mapped=np.clip(film(z)/film(1000/203),0,1)
 rgb=rgb*(mapped/np.maximum(y,1e-10))[None]
 return np.ascontiguousarray(np.clip(rgb,0,1)**(1/2.2),dtype=np.float32)
