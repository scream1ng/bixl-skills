#!/usr/bin/env python3
"""Orthographic CAD renders from exact STEP solids, without generated geometry."""
import argparse,json
from pathlib import Path
import cadquery as cq
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

def unit(v):
    v=np.array(v,dtype=float)
    if np.linalg.norm(v)<1e-9:raise ValueError('Zero camera vector')
    return v/np.linalg.norm(v)

def render(solids,view,out):
    camera=unit(view['camera']);up=unit(view.get('up',[0,0,1]));right=unit(np.cross(up,camera));up=unit(np.cross(camera,right))
    polygons=[];projected=[];light=unit(camera+.6*up-.4*right)
    for index in view['solids']:
        verts,tris=solids[index].tessellate(view.get('tolerance',.06),.15)
        v=np.array([p.toTuple() for p in verts]);pts=np.stack([v@right,-v@up,v@camera],axis=1);projected.extend(pts[:,:2])
        for tri in tris:
            tri=np.array(tri);xyz=v[tri];n=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);length=np.linalg.norm(n)
            if length<1e-12:continue
            n=n/length
            if np.dot(n,camera)<-1e-7:continue
            shade=.53+.47*max(0,float(np.dot(n,light)))
            base=np.array(view.get('color',[168,180,186]));rgb=tuple(np.clip(base*shade,0,255).astype(int))+(255,)
            polygons.append((pts[tri,2].mean(),pts[tri,:2],rgb))
    projected=np.array(projected);lo=projected.min(axis=0);hi=projected.max(axis=0)
    width,height=view.get('size',[640,640]);supersample=2;padding=20
    factor=min((width-2*padding)/(hi[0]-lo[0]),(height-2*padding)/(hi[1]-lo[1]))
    offset=np.array([width,height])/2-(lo+hi)/2*factor
    im=Image.new('RGBA',(width*supersample,height*supersample),(255,255,255,0));d=ImageDraw.Draw(im)
    for depth,poly,color in sorted(polygons,key=lambda p:p[0]):
        p=(poly*factor+offset)*supersample;d.polygon([tuple(x) for x in p],fill=color)
    # A thin silhouette clarifies sheet edges without drawing mesh triangles.
    alpha=im.getchannel('A');border=alpha.filter(ImageFilter.MaxFilter(3));edge=Image.new('RGBA',im.size,(38,45,49,255));edge.putalpha(border);edge.alpha_composite(im)
    edge.resize((width,height),Image.Resampling.LANCZOS).save(out,optimize=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('step');p.add_argument('config');p.add_argument('--out',required=True);a=p.parse_args()
    solids=cq.importers.importStep(a.step).solids().vals();config=json.loads(Path(a.config).read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    for key,view in config['views'].items():
        if not view['solids'] or any(i<0 or i>=len(solids) for i in view['solids']):raise ValueError('Invalid STEP solid selection '+key)
        target=out/(key+'.png');render(solids,view,target);print(target)
if __name__=='__main__':main()
