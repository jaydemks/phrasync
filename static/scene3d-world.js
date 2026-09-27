/* Site-specific streets and gardens. Planting lives between landmark lots. */
import { cloudTexture, rockSurface } from '/static/scene3d-expeditions.js';
const wrap=(v,n)=>((v%n)+n)%n;
const random=(i,s=1337)=>{let n=Math.imul(i+s,1597334677);n=Math.imul(n^(n>>>16),2246822519);return((n^(n>>>13))>>>0)/4294967296;};
export function sceneryPoint(x,y,z,travel,direction,cameraZ){
  if(direction==='left'||direction==='right'){const sign=direction==='left'?-1:1;return[sign*(wrap(z+travel+132,264)-132),y,cameraZ-85-sign*x];}
  if(['up','down','ascend','dive'].includes(direction))return[x*1.7,(direction==='up'||direction==='ascend'?1:-1)*(wrap(-z-travel+70,140)-70),cameraZ-26-Math.abs(x)*1.5];
  return[x,y,cameraZ-wrap(-z-travel+12,264)+12];
}
function paving(T,kit){
  const canvas=document.createElement('canvas');canvas.width=canvas.height=256;const c=canvas.getContext('2d');
  const palette={japan:['#aca99d','#777c73'],italy:['#c6b397','#aa9478'],china:['#a7a99d','#757b76'],usa:['#444950','#343a40']}[kit]||['#aaa99a','#75786d'];
  c.fillStyle=palette[0];c.fillRect(0,0,256,256);
  if(kit!=='usa'){c.strokeStyle=palette[1];c.lineWidth=1.4;const h=kit==='italy'?32:64;
    for(let y=0;y<256;y+=h){c.beginPath();c.moveTo(0,y);c.lineTo(256,y);c.stroke();
      for(let x=(y/h%2)*32;x<256;x+=64){c.beginPath();c.moveTo(x,y);c.lineTo(x,y+h);c.stroke();}}}
  for(let i=0;i<1800;i++){c.fillStyle=i%2?'rgba(0,0,0,.025)':'rgba(255,255,255,.04)';c.fillRect(random(i)*256,random(i+1900)*256,1,1);}
  const tex=new T.CanvasTexture(canvas);tex.wrapS=tex.wrapT=T.RepeatWrapping;tex.repeat.set(28,55);tex.colorSpace=T.SRGBColorSpace;return tex;
}
function pitchedRoof(T,curved){
  const profile=curved?[[-1,.10],[-.88,0],[-.6,.22],[0,.7],[.6,.22],[.88,0],[1,.1]]:[[-1,0],[0,.7],[1,0]];
  const vertices=[],indices=[];
  for(const z of [-1,1])for(const [x,y]of profile)vertices.push(x,y,z);
  const n=profile.length;for(let i=0;i<n-1;i++)indices.push(i,n+i,i+1,i+1,n+i,n+i+1);
  indices.push(0,n-1,n, n-1,n*2-1,n);
  const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(vertices,3));g.setIndex(indices);g.computeVertexNormals();return g;
}
export function createWorld(T,theme){
  const kit=theme.kit||({torii:'japan',arch:'italy',moonGate:'china',billboard:'usa'}[theme.builders?.[0]])||'japan';
  const group=new T.Group(),batches={},dummy=new T.Object3D();
  const mat=(color,extra={})=>new T.MeshStandardMaterial({color,roughness:.9,...extra});
  const add=(name,geo,material,count)=>{const m=new T.InstancedMesh(geo,material,count);m.frustumCulled=false;m.instanceMatrix.setUsage(T.DynamicDrawUsage);group.add(m);batches[name]=m;return m;};
  const box=new T.BoxGeometry(1,1,1),rockTexture=rockSurface(T),paperTexture=rockSurface(T);
  const surfaceMap=paving(T,kit),surface=new T.Mesh(new T.PlaneGeometry(180,540),mat(0xffffff,{map:surfaceMap,metalness:0}));
  surface.rotation.x=-Math.PI/2;surface.position.y=.035;group.add(surface);
  const waterMat=mat(0x467f87,{roughness:.3,metalness:.25,emissive:0x173b40,emissiveIntensity:.25}),clock={value:0};
  waterMat.onBeforeCompile=shader=>{shader.uniforms.contextClock=clock;shader.fragmentShader='uniform float contextClock;\n'+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
      float wave=sin(vViewPosition.z*3.1+sin(vViewPosition.x*1.8)+contextClock*.6)*sin(vViewPosition.x*2.4+vViewPosition.z*.4);
      diffuseColor.rgb+=vec3(.06,.10,.11)*pow(max(0.0,wave),8.0);`);};
  const river=new T.Mesh(new T.PlaneGeometry(6,540),waterMat);river.rotation.x=-Math.PI/2;river.position.y=.05;group.add(river);
  add('curbs',box,mat(0xb7b7aa),44);add('beds',box,mat(0x626f42),22);
  add('cliffs',new T.IcosahedronGeometry(1,1),mat(0x94958c,{map:rockTexture}),66);
  add('bamboo',new T.CylinderGeometry(.07,.09,1,6),mat(0x6c824a),154);
  add('leaves',new T.ConeGeometry(.13,1,3),mat(0x849757,{side:T.DoubleSide}),308);
  add('cypress',new T.ConeGeometry(1,1,9),mat(0x354e37),22);
  add('benchwood',box,mat(0x917350),66);add('benchlegs',box,mat(0x444a43),88);
  add('facades',box,mat(0xffffff),22);
  add('windows',box,mat(kit==='usa'?0xa9cee0:kit==='japan'?0xeee7d0:kit==='china'?0x48392e:0x3a5048,
    {emissive:kit==='usa'?0x507b95:kit==='japan'?0x9e937a:0x172627,emissiveIntensity:kit==='usa'?.3:.12}),1056);
  add('walls',box,mat(kit==='japan'?0xaaa997:0xb7b5a4),22);
  add('eaves',pitchedRoof(T,kit==='china'),mat(kit==='italy'?0xa45d3e:kit==='japan'?0x363f39:0x505b60,{side:T.DoubleSide}),44);
  add('frames',box,mat(kit==='japan'?0x514235:kit==='china'?0x8a4637:0x526b55),2112);
  add('balconies',box,mat(0xd9c6a1),176);
  add('railings',box,mat(0x4d5147),528);
  const arch=new T.Shape();arch.moveTo(-.8,0);arch.lineTo(-.8,1.5);arch.absarc(0,1.5,.8,Math.PI,0,true);arch.lineTo(.8,0);arch.closePath();
  add('arcades',new T.ShapeGeometry(arch),mat(0x403f36,{side:T.DoubleSide}),176);
  add('archtrim',new T.TorusGeometry(.84,.07,5,18,Math.PI),mat(0xe0cbab),176);
  add('cornices',box,mat(kit==='usa'?0x83939a:0xe0cfad),66);add('awnings',box,mat(0x9b6651),44);
  add('markings',box,new T.MeshBasicMaterial({color:0xd4c692}),66);
  const cloudMap=cloudTexture(T);add('clouds',new T.PlaneGeometry(1,1),new T.MeshBasicMaterial({map:cloudMap,color:0xe9e6df,transparent:true,opacity:.55,depthWrite:false}),16);
  add('portals',new T.TorusGeometry(1,.03,6,40),mat(theme.cool,{emissive:theme.cool,emissiveIntensity:.7}),14);
  group.userData.ownedTextures=[rockTexture,paperTexture,surfaceMap,cloudMap];
  return{group,batches,dummy,kit,surface,river,paperTexture,clock,style:''};
}
export function updateWorld(T,w,{t,travel,direction,cameraZ,seed=1337,artStyle='cinematic',secondaryMotion='none',motionAmount=.35}){
  const {batches:b,dummy:d,kit}=w,lateral=direction==='left'||direction==='right',amount=Math.max(0,Math.min(1,Number(motionAmount)||0));
  w.group.position.set(secondaryMotion==='sway'?Math.sin(t*.19)*amount*5:0,secondaryMotion==='rise'?Math.sin(t*.14)*amount*4:0,0);
  w.group.rotation.z=secondaryMotion==='orbit'?Math.sin(t*.12)*amount*.12:0;
  w.clock.value=t;w.surface.position.z=cameraZ-100;
  w.surface.material.map.offset.set(lateral?travel/180*28:0,lateral?0:travel/540*55);
  w.river.visible=kit==='china';w.river.position.set(0,.05,cameraZ-(lateral?85:100));w.river.rotation.set(-Math.PI/2,0,lateral?Math.PI/2:0);
  for(const m of Object.values(b))m.visible=false;
  const yaw=new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),lateral?(direction==='left'?-1:1)*Math.PI/2:0);
  const put=(name,i,x,y,z,sx,sy,sz,rx=0,ry=0,rz=0)=>{const p=sceneryPoint(x,y,z,travel,direction,cameraZ);
    d.position.set(...p);d.scale.set(sx,sy,sz);d.rotation.set(rx,ry,rz);d.quaternion.premultiply(yaw);d.updateMatrix();b[name].setMatrixAt(i,d.matrix);b[name].visible=true;};
  for(let i=0;i<22;i++){
    const side=i%2?1:-1,row=Math.floor(i/2),z=-row*24-12;
    if(kit==='japan'||kit==='china'){
      const bedX=side*(kit==='japan'?7.5:8.5);put('beds',i,bedX,.14,z,3.2,.28,6);
      for(let j=0;j<3;j++)put('cliffs',i*3+j,bedX+(j-1)*.7,.25,z+(j-1)*1.1,.42,.3,.6,0,j);
      for(let j=0;j<7;j++){const h=3+random(i*7+j,seed)*2,px=side*24+(j%3-1)*.4,pz=z+Math.floor(j/3)*.5;
        put('bamboo',i*7+j,px,h/2,pz,1,h,1,0,0,Math.sin(t*.35+i)*.016);
        for(let k=0;k<2;k++)put('leaves',(i*7+j)*2+k,px+(k?-.3:.3),h*.78,pz,1,1.7,1,0,0,k?.8:-.8);}
      put('curbs',i*2,side*(kit==='china'?3.3:5.3),.1,-row*24,.35,.2,24);
      put('curbs',i*2+1,side*(kit==='china'?4:9.7),.1,-row*24,.22,.2,24);
    }
    if(kit==='italy'){
      put('cypress',i,side*24,3.7,z,1.2,7.4,1.2);
      for(let j=0;j<3;j++)put('benchwood',i*3+j,side*7,.85+j*.18,z,2.9,.1,.18);
      for(let j=0;j<4;j++)put('benchlegs',i*4+j,side*7+(j%2?1.1:-1.1),.4,z+(j<2?.3:-.3),.12,.8,.12);
    }
    {
      const garden=kit==='japan'||kit==='china';
      const x=side*(kit==='usa'?23:garden?37:32),bz=-row*24,h=kit==='usa'?9+random(i,seed)*16:garden?4.2+random(i,seed)*1.5:7+random(i,seed)*5;
      put('facades',i,x,h/2,bz,12,h,14);
      const palettes=kit==='usa'?[0x647782,0x7a6b64,0x687170,0x79838d]:kit==='china'?[0xe1ded0,0xd5d2c4]:kit==='japan'?[0xb7a887,0xc2b18f]:[0xd4ad78,0xd0a08b,0xc2b88b,0xe0bd8e];
      b.facades.setColorAt(i,new T.Color(palettes[i%palettes.length]));
      const rows=kit==='usa'?6:2,windowCount=rows*4*2;
      b.windows.count=22*windowCount;
      for(let j=0;j<rows*4;j++){const floor=Math.floor(j/4),col=j%4,wy=garden?(floor+.55)*h/2:(floor+1.35)*h/3,wz=bz+(col-1.5)*2.7;
        for(let face=0;face<2;face++){
          const wx=x+(face?1:-1)*6.02,n=i*windowCount+j*2+face;
          const yy=kit==='usa'?(floor+.65)*h/6:wy,wh=garden?h*.34:kit==='usa'?.65+h*.025:1.45;
          put('windows',n,wx,yy,wz,.045,wh,garden?1.9:1.25);
          if(garden)for(let k=0;k<6;k++){
            const vertical=k<3;
            put('frames',n*6+k,wx+(face?1:-1)*.03,yy+(vertical?0:(k-4)*wh*.35),wz+(vertical?(k-1)*.7:0),
              .075,vertical?wh+.12:.06,vertical?.055:2.05);
          }
          if(kit==='italy')for(let k=0;k<2;k++)put('frames',n*2+k,wx+(face?1:-1)*.045,yy,wz+(k?1:-1)*.87,.09,1.55,.43);
        }
      }
      b.frames.count=garden?22*windowCount*6:kit==='italy'?22*windowCount*2:0;
      for(let j=0;j<3;j++)put('cornices',i*3+j,x,h*(j===0?1:j===1?.1:.52),bz,12.35,.23,14.3);
      for(let j=0;j<2;j++)put('awnings',i*2+j,x-side*6.5,2.5,bz+(j?3:-3),1.1,.2,4.5);
      if(garden){
        put('walls',i,side*29,.85,-row*24, .5,1.7,24);
        const roofs=kit==='china'?2:1;b.eaves.count=22*roofs;
        for(let j=0;j<roofs;j++)put('eaves',i*roofs+j,x,h+j*.8,bz,6.9-j*.5,1.4,7.7-j*.3);
      }
      if(kit==='italy'){
        b.eaves.count=22;put('eaves',i,x,h,bz,6.6,1.4,7.5);
        for(let face=0;face<2;face++)for(let col=0;col<4;col++){
          const sign=face?1:-1,n=i*8+face*4+col,wz=bz+(col-1.5)*2.7,wx=x+sign*6.06;
          put('arcades',n,wx,0,wz,1,1,1,0,sign*Math.PI/2);
          put('archtrim',n,wx+sign*.025,1.5,wz,1,1,1,0,sign*Math.PI/2);
          put('balconies',n,x+sign*6.4,h*.38,wz,.8,.16,2.2);
          for(let k=0;k<3;k++)put('railings',n*3+k,x+sign*6.76,h*.38+.2+k*.2,wz,.045,.045,2.15);
        }
      }
      if(kit==='usa'){put('curbs',i*2,side*8,.12,-row*24,.3,.24,24);put('curbs',i*2+1,side*12,.06,-row*24,7,.12,24);}
    }
  }
  if(kit==='usa')for(let i=0;i<66;i++)put('markings',i,i%2?.18:-.18,.06,-Math.floor(i/2)*8,.07,.012,3);
  for(let i=0;i<16;i++)put('clouds',i,(random(i+80,seed)-.5)*240,40+random(i+90,seed)*30,-i*16,48,16,1);
  if(artStyle==='psychedelic')for(let i=0;i<14;i++)put('portals',i,0,6,-i*19,12,12,12,0,0,t*.03+i*.1);
  for(const m of Object.values(b))if(m.visible)m.instanceMatrix.needsUpdate=true;
  if(b.facades.instanceColor)b.facades.instanceColor.needsUpdate=true;
}
