/* Dedicated vertical worlds. Up is inhabited sky architecture; down is geology.
 * All meshes have fixed capacities, all placements are functions of time/seed.
 */
const wrap = (v, n) => ((v % n) + n) % n;
const rand = (i, seed) => {
  let n = Math.imul(i + seed, 1597334677); n = Math.imul(n ^ (n >>> 16), 2246822519);
  return ((n ^ (n >>> 13)) >>> 0) / 4294967296;
};

function roofGeometry(T) {
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute([
    -1,0,-1, 1,0,-1, 0,.9,-1, -1,0,1, 1,0,1, 0,.9,1
  ],3));
  g.setIndex([0,2,1,3,4,5,0,3,5,0,5,2,2,5,4,2,4,1,0,1,4,0,4,3]);
  g.computeVertexNormals(); return g;
}

export function cloudTexture(T) {
  const canvas = document.createElement('canvas'); canvas.width = 256; canvas.height = 128;
  const ctx = canvas.getContext('2d');
  for (let i = 0; i < 28; i++) {
    const x = 30 + rand(i, 22) * 196, y = 48 + rand(i + 90, 22) * 36;
    const r = 18 + rand(i + 40, 22) * 25;
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
    gradient.addColorStop(0, 'rgba(255,255,255,.28)'); gradient.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gradient; ctx.fillRect(x-r,y-r,r*2,r*2);
  }
  return new T.CanvasTexture(canvas);
}

export function rockSurface(T) {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=256;
  const ctx=canvas.getContext('2d');ctx.fillStyle='#c2c0b7';ctx.fillRect(0,0,256,256);
  for(let i=0;i<1000;i++){
    const x=rand(i,84)*256,y=rand(i+1400,84)*256;
    ctx.fillStyle=i%3?'rgba(68,75,73,.07)':'rgba(255,249,224,.09)';
    ctx.beginPath();ctx.ellipse(x,y,2+rand(i+20,84)*19,1+rand(i+40,84)*5,0,0,Math.PI*2);ctx.fill();
  }
  ctx.strokeStyle='rgba(62,66,61,.25)';ctx.lineWidth=.7;
  for(let y=0;y<256;y+=11){ctx.beginPath();for(let x=0;x<=256;x+=4){
    const yy=y+Math.sin(x*.037+y)*3+Math.sin(x*.12)*1.4;
    if(x===0)ctx.moveTo(x,yy);else ctx.lineTo(x,yy);
  }ctx.stroke();}
  const texture=new T.CanvasTexture(canvas);texture.wrapS=texture.wrapT=T.RepeatWrapping;
  texture.colorSpace=T.SRGBColorSpace;return texture;
}

export function createExpeditions(T) {
  const group = new T.Group(), sky = new T.Group(), cave = new T.Group();
  group.add(sky,cave);
  const batches = {}, box = new T.BoxGeometry(1,1,1);
  const mat = (color, extra={}) => new T.MeshStandardMaterial({ color, roughness:.9, ...extra });
  const rockMap=rockSurface(T);
  const rock=(color)=>mat(color,{map:rockMap,bumpMap:rockMap,bumpScale:.2,flatShading:true});
  const add = (name, parent, geo, material, count) => {
    const mesh = new T.InstancedMesh(geo,material,count); mesh.frustumCulled=false;
    mesh.instanceMatrix.setUsage(T.DynamicDrawUsage); parent.add(mesh); batches[name]=mesh;
    return mesh;
  };
  const islandGeo = new T.CylinderGeometry(1,.13,1,11,4);
  const vertices = islandGeo.attributes.position;
  for(let i=0;i<vertices.count;i++) {
    const x=vertices.getX(i),y=vertices.getY(i),z=vertices.getZ(i);
    const wobble=1+.11*Math.sin(x*9+z*5)+.08*Math.sin(z*13-y*10);
    vertices.setXYZ(i,x*wobble,y,z*wobble);
  }
  islandGeo.computeVertexNormals();
  add('islands',sky,islandGeo,rock(0x9a8e77),14);
  add('meadows',sky,new T.CylinderGeometry(1,.96,.13,16),mat(0x718852),14);
  add('houses',sky,box,mat(0xd6c1a0),42);
  add('roofs',sky,roofGeometry(T),mat(0x78574b,{flatShading:true}),42);
  add('windows',sky,box,mat(0xffdf9e,{emissive:0xffc477,emissiveIntensity:.55}),336);
  add('timbers',sky,box,mat(0x524a3e),336);
  add('bridges',sky,box,mat(0x9a8160),70);
  add('sails',sky,box,mat(0xe6d9bb),56);
  add('millTowers',sky,new T.CylinderGeometry(.52,.8,1,8),mat(0xc4b79d),14);
  add('millCaps',sky,new T.ConeGeometry(.95,1.1,8),mat(0x786250),14);
  add('ivy',sky,new T.ConeGeometry(.35,1,5),mat(0x557749),140);
  add('falls',sky,new T.PlaneGeometry(1,1),mat(0x99dce1,{emissive:0x497c87,emissiveIntensity:.45,
    transparent:true,opacity:.4,side:T.DoubleSide,depthWrite:false}),28);
  const cloudMap=cloudTexture(T);
  add('mist',sky,new T.PlaneGeometry(1,1),new T.MeshBasicMaterial({color:0xe3e9e2,map:cloudMap,
    transparent:true,opacity:.75,depthWrite:false}),34);
  const rootPath = new T.CatmullRomCurve3([
    new T.Vector3(0,-1,0),new T.Vector3(.24,-.35,.16),new T.Vector3(-.15,.25,-.12),new T.Vector3(.3,1,0)
  ]);
  add('roots',cave,new T.TubeGeometry(rootPath,14,.065,6,false),mat(0x433a35),112);
  const ribGeo=new T.TorusGeometry(1,.23,8,32,Math.PI*1.4);
  const rv=ribGeo.attributes.position;
  for(let i=0;i<rv.count;i++){
    const x=rv.getX(i),y=rv.getY(i),z=rv.getZ(i),f=1+.08*Math.sin(x*12+y*6)+.04*Math.cos(y*16);
    rv.setXYZ(i,x*f,y*f,z*(1+.3*Math.cos(x*19)));
  }
  ribGeo.computeVertexNormals();
  add('ribs',cave,ribGeo,rock(0x66777d),28);
  const strataGeo=new T.BoxGeometry(1,1,1,3,5,2),sp=strataGeo.attributes.position;
  for(let i=0;i<sp.count;i++){
    const x=sp.getX(i),y=sp.getY(i),z=sp.getZ(i);
    sp.setXYZ(i,x*(1+.18*Math.sin(y*22+z*8)),y+.05*Math.sin(x*11+z*7),z*(1+.17*Math.cos(y*24)));
  }
  strataGeo.computeVertexNormals();
  add('strata',cave,strataGeo,rock(0x607178),70);
  add('teeth',cave,new T.ConeGeometry(1,2,7,3),rock(0x6f7778),84);
  add('crystals',cave,new T.ConeGeometry(1,2,5),mat(0x66d4de,{emissive:0x31848d,emissiveIntensity:.9,
    metalness:.35,roughness:.28}),210);
  add('veins',cave,new T.TorusGeometry(1,.009,4,32,Math.PI*.4),mat(0x387e78,{emissive:0x387e78,emissiveIntensity:.3}),28);
  return {group,sky,cave,batches,dummy:new T.Object3D()};
}

export function updateExpeditions(T, world, {t,travel,cameraZ,direction,seed=1337,artStyle='cinematic'}) {
  const up=direction==='up'||direction==='ascend';
  const down=direction==='down'||direction==='dive';
  world.group.visible=up||down; world.sky.visible=up; world.cave.visible=down;
  if(!world.group.visible)return;
  const {batches:b,dummy:d}=world;
  const put=(name,i,x,y,z,sx,sy,sz,rx=0,ry=0,rz=0)=>{
    d.position.set(x,y,z);d.scale.set(sx,sy,sz);d.rotation.set(rx,ry,rz);d.updateMatrix();b[name].setMatrixAt(i,d.matrix);
  };
  if(up){
    for(let i=0;i<14;i++){
      const r=n=>rand(i*37+n,seed), side=r(1)<.46?-1:1;
      const z=cameraZ-32-r(2)*110, x=side*(15+r(3)*49), y=wrap(r(4)*170-travel+85,170)-85;
      const s=.95+r(5)*1, rad=5.5*s;
      put('islands',i,x,y-5*s,z,rad,10*s,rad,0,r(6),.05*Math.sin(i));
      put('meadows',i,x,y,z,rad,1,rad);
      for(let j=0;j<3;j++){
        const n=i*3+j, hx=x+(j-1)*3.8*s, hz=z+(j===1?-1.4:1)*s, h=(2.5+j*.65)*s;
        put('houses',n,hx,y+h/2,hz,2.8*s,h,2.4*s);
        put('roofs',n,hx,y+h,hz,1.7*s,1.4*s,1.6*s);
        for(let k=0;k<8;k++){
          const row=Math.floor(k/4),wx=hx+((k%4)-1.5)*.57*s,wy=y+(row*.85+.7)*s;
          put('windows',n*8+k,wx,wy,hz+1.215*s,.27*s,.39*s,.05);
          put('timbers',n*8+k,hx+((k%4)-1.5)*.85*s,y+h*(row?.78:.27),hz+1.24*s,
            row?2.8*s:.085*s,row?.1*s:h,.08*s);
        }
      }
      // Scaffold bridge cantilevers and paired guard rails make inhabited scale.
      for(let k=0;k<5;k++){
        const rail=k>0, bx=x+side*(rad+(rail?2:2.5))*s;
        put('bridges',i*5+k,bx,y+(rail?.6:0)+(k===4?-1.4:0),z+(k%2?.7:-.7),
          k===4?.14:6*s,k===4?3*s:.12,k===0?1.9:.12,0,0,k===4?side*.6:0);
      }
      const mx=x+rad*.64,my=y+7*s,mz=z+1.8*s;
      put('millTowers',i,mx,y+3.5*s,mz-.35,s,7*s,s);
      put('millCaps',i,mx,my+.4*s,mz-.35,s,s,s);
      for(let k=0;k<4;k++){
        const a=t*.22+i+k*Math.PI/2;
        put('sails',i*4+k,mx+Math.sin(a)*1.1*s,my+Math.cos(a)*1.1*s,mz,.42*s,2.35*s,.09,0,0,-a);
      }
      for(let k=0;k<10;k++){
        const a=k*.628+i;
        put('ivy',i*10+k,x+Math.cos(a)*rad*.92,y-(1+r(k+10)*3)*s,z+Math.sin(a)*rad*.92,
          s,(2+r(k+11)*4)*s,s,0,0,Math.sin(t*.5+i+k)*.045);
      }
      for(let k=0;k<2;k++)put('falls',i*2+k,x+side*(rad-.3+k*.4),y-8*s,z+1,
        .35+.15*Math.sin(i+k),15*s,1);
    }
    for(let i=0;i<34;i++)put('mist',i,(rand(i+200,seed)-.5)*200,
      wrap(rand(i+300,seed)*160-travel*.72+80,160)-80,cameraZ-25-rand(i+500,seed)*160,55,17,1);
    b.roofs.material.color.set(artStyle==='psychedelic'?0x7357a5:artStyle==='storybook'?0x99715b:0x78574b);
  } else {
    for(let i=0;i<28;i++){
      const r=n=>rand(i*23+n,seed),z=cameraZ-30-r(1)*125;
      const y=wrap(r(2)*180+travel+90,180)-90,side=r(3)<.5?-1:1,x=side*(20+r(4)*45);
      put('ribs',i,x,y,z,10+r(5)*13,8+r(6)*12,5,0,.3*side,r(7)*6);
      put('veins',i,x,y,z+1,10+r(5)*13,8+r(6)*12,5,0,.3*side,r(7)*6);
      for(let j=0;j<4;j++)put('roots',i*4+j,x+(j-1.5)*3,y,z+3,7,10+r(j+10)*10,7,0,0,side*.35+Math.sin(i)*.3);
      for(let j=0;j<3;j++)put('teeth',i*3+j,x+(j-1)*3,y+8,z+4,1+r(j+13),3+r(j+15)*4,1.4,0,0,Math.PI);
    }
    for(let i=0;i<70;i++){
      const r=n=>rand(i*19+n,seed),side=r(1)<.5?-1:1;
      const x=side*(23+r(2)*35),y=wrap(r(3)*180+travel+90,180)-90,z=cameraZ-32-r(4)*105;
      put('strata',i,x,y,z,13+r(5)*12,5+r(6)*9,12,0,r(7)*.6,side*.16);
      for(let j=0;j<3;j++)put('crystals',i*3+j,x+(j-1)*1.6,y+3,z+3,.5+r(j+8),2+r(j+9)*4,.7,
        .1,0,(j-1)*.3);
    }
    const psycho=artStyle==='psychedelic',book=artStyle==='storybook';
    b.strata.material.color.set(book?0x889285:psycho?0x574468:0x607178);
    b.ribs.material.color.set(book?0x929481:psycho?0x684d7b:0x66777d);
    b.crystals.material.color.set(psycho?0xe892fa:book?0xb4ce9b:0x66d4de);
    b.crystals.material.emissive.set(psycho?0x853aa6:book?0x667e3f:0x31848d);
  }
  for(const mesh of Object.values(b))mesh.instanceMatrix.needsUpdate=true;
}
