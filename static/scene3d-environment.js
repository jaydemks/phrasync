/* Deterministic weather, daytime and season treatment for Odyssey 3D. */

const DAYLIGHT = {
  dawn: { top: 0x17152f, horizon: 0xf28775, fog: 0x6b4053, ambient: 0.62, key: 0xffb080 },
  day: { top: 0x397fc2, horizon: 0xb9dcf2, fog: 0x79a7c4, ambient: 1.05, key: 0xfff1cf },
  sunset: { top: 0x211338, horizon: 0xf05a68, fog: 0x693044, ambient: 0.58, key: 0xff765f },
  night: { top: 0x030611, horizon: 0x161329, fog: 0x100d21, ambient: 0.32, key: 0x779cff }
};

const SEASONS = {
  spring: { foliage: 0xd85f91, ground: 0x17221d, tint: 0xffd7e8 },
  summer: { foliage: 0x1f633c, ground: 0x101713, tint: 0xd8ffe7 },
  autumn: { foliage: 0xb44720, ground: 0x21130d, tint: 0xffb15d },
  winter: { foliage: 0xb8c9d5, ground: 0x26313b, tint: 0xd9efff }
};

const smooth = value => value * value * (3 - 2 * value);
const wrap = (value, span) => ((value % span) + span) % span;

function seededValues(count, seed) {
  let state = seed >>> 0;
  const values = new Float32Array(count);
  for (let index = 0; index < count; index += 1) {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    values[index] = state / 4294967296;
  }
  return values;
}

function weatherGeometry(THREE, count, lines = false) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(
    new Float32Array(count * (lines ? 6 : 3)), 3
  ));
  return geometry;
}

export function createEnvironment(THREE, theme) {
  const group = new THREE.Group();
  const rain = new THREE.LineSegments(
    weatherGeometry(THREE, 620, true),
    new THREE.LineBasicMaterial({ color: 0xa9d8ff, transparent: true, opacity: 0.48, depthWrite: false })
  );
  const flakeCanvas=document.createElement("canvas");flakeCanvas.width=flakeCanvas.height=32;
  const flakeCtx=flakeCanvas.getContext("2d"),fade=flakeCtx.createRadialGradient(16,16,1,16,16,16);
  fade.addColorStop(0,"white");fade.addColorStop(.35,"rgba(255,255,255,.9)");fade.addColorStop(1,"rgba(255,255,255,0)");
  flakeCtx.fillStyle=fade;flakeCtx.fillRect(0,0,32,32);
  const flakeTexture=new THREE.CanvasTexture(flakeCanvas);
  const flakes = new THREE.Points(
    weatherGeometry(THREE, 560),
    new THREE.PointsMaterial({ color: 0xe9f5ff, size: 0.24, map:flakeTexture, alphaTest:.02, transparent: true, opacity: 0.82, depthWrite: false })
  );
  const leaves=new THREE.Points(weatherGeometry(THREE,320),new THREE.PointsMaterial({color:0xe07032,size:.34,map:flakeTexture,alphaTest:.02,transparent:true,opacity:.85,depthWrite:false}));
  leaves.frustumCulled=false;leaves.visible=false;
  rain.frustumCulled = flakes.frustumCulled = false;
  rain.visible = flakes.visible = false;
  group.add(rain, flakes, leaves);
  group.userData.ownedTextures=[flakeTexture];
  const fogGeometry=new THREE.BufferGeometry();fogGeometry.setAttribute("position",new THREE.Float32BufferAttribute([-1,-1,0,3,-1,0,-1,3,0],3));
  const fogUniforms={amount:{value:0},flash:{value:0},time:{value:0},tint:{value:new THREE.Color(0xd5dfeb)}};
  const fog=new THREE.Mesh(fogGeometry,new THREE.ShaderMaterial({uniforms:fogUniforms,transparent:true,depthTest:false,depthWrite:false,toneMapped:false,
    vertexShader:`varying vec2 uvFog;void main(){uvFog=position.xy*.5+.5;gl_Position=vec4(position.xy,0.,1.);}`,
    fragmentShader:`varying vec2 uvFog;uniform float amount,flash,time;uniform vec3 tint;
      void main(){float drift=.88+.12*sin(uvFog.x*9.+time*.19+sin(uvFog.y*7.-time*.11));
      float haze=amount*mix(.35,1.,smoothstep(0.,.72,uvFog.y))*drift;
      gl_FragColor=vec4(mix(tint,vec3(1.),flash),clamp(max(haze,flash),0.,.85));
      #include <colorspace_fragment>
      }` }));
  fog.frustumCulled=false;fog.renderOrder=-9000;fog.visible=false;group.add(fog);

  const canvas = document.createElement("canvas");
  canvas.width = 32; canvas.height = 512;
  const skyTexture = new THREE.CanvasTexture(canvas);
  skyTexture.colorSpace = THREE.SRGBColorSpace;
  group.userData.ownedTextures.push(skyTexture);

  return {
    group, rain, flakes, leaves, fog, fogUniforms, canvas, skyTexture, theme,
    velocity:new THREE.Vector3(),
    rainSeed: seededValues(620 * 3, 0x7135),
    flakeSeed: seededValues(560 * 3, 0x51f0),
    leafSeed: seededValues(320 * 3, 0x6eaf),
    signature: ""
  };
}

function blendedPalette(THREE, state) {
  const dayA = DAYLIGHT[state.daytime] || DAYLIGHT.sunset;
  const dayB = DAYLIGHT[state.nextDaytime] || dayA;
  const seasonA = SEASONS[state.season] || SEASONS.summer;
  const seasonB = SEASONS[state.nextSeason] || seasonA;
  const dayMix = smooth(state.dayMix || 0);
  const seasonMix = smooth(state.seasonMix || 0);
  const blend = (a, b, amount) => new THREE.Color(a).lerp(new THREE.Color(b), amount);
  const tint = blend(seasonA.tint, seasonB.tint, seasonMix);
  return {
    top: blend(dayA.top, dayB.top, dayMix).lerp(tint, 0.05),
    horizon: blend(dayA.horizon, dayB.horizon, dayMix).lerp(tint, 0.08),
    fog: blend(dayA.fog, dayB.fog, dayMix),
    key: blend(dayA.key, dayB.key, dayMix),
    ambient: dayA.ambient + (dayB.ambient - dayA.ambient) * dayMix,
    foliage: blend(seasonA.foliage, seasonB.foliage, seasonMix),
    ground: blend(seasonA.ground, seasonB.ground, seasonMix)
  };
}

function paintSky(environment, palette) {
  const ctx = environment.canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, environment.canvas.height);
  gradient.addColorStop(0, `#${palette.top.getHexString()}`);
  gradient.addColorStop(0.67, `#${palette.horizon.getHexString()}`);
  gradient.addColorStop(1, `#${palette.fog.getHexString()}`);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, environment.canvas.width, environment.canvas.height);
  environment.skyTexture.needsUpdate = true;
}

function updateRain(environment, camera, t, storm, wind=0, surfaceY=null) {
  const position = environment.rain.geometry.attributes.position;
  const seed = environment.rainSeed;
  const speed = storm ? 34 : 24;
  const velocity=environment.velocity.set(wind*12,-speed,0);
  const origin=camera.position||camera;
  for (let index = 0; index < seed.length / 3; index += 1) {
    // Rebase world-space particles near the camera, without attaching them to
    // its translation or rotation. Wrapping occurs only at volume boundaries.
    const x = wrap(seed[index * 3]*96+t*velocity.x-origin.x+48,96)-48;
    const y = surfaceY===null ? wrap(seed[index * 3+1]*64+t*velocity.y-origin.y+32,64)-32
      : surfaceY+wrap(seed[index * 3+1]*64+t*velocity.y,64)-origin.y;
    const z = wrap(seed[index * 3+2]*128-origin.z+64,128)-64;
    const offset = index * 6;
    position.array[offset] = x; position.array[offset + 1] = y; position.array[offset + 2] = z;
    position.array[offset + 3] = x+velocity.x*.065;
    position.array[offset + 4] = surfaceY===null ? y+velocity.y*.065 : Math.max(surfaceY-origin.y,y+velocity.y*.065);
    position.array[offset + 5] = z+velocity.z*.065;
  }
  position.needsUpdate = true;
}

function updateFlakes(environment, camera, t, leaves, wind=0, surfaceY=null) {
  const target=leaves?environment.leaves:environment.flakes;
  const position = target.geometry.attributes.position;
  const seed = leaves?environment.leafSeed:environment.flakeSeed;
  const velocity=environment.velocity.set(wind*4,leaves?-2.5:-1.4,0);
  const origin=camera.position||camera;
  for (let index = 0; index < seed.length / 3; index += 1) {
    const phase = seed[index * 3] * Math.PI * 2;
    const x = wrap(seed[index * 3]*96+t*velocity.x-origin.x+48,96)-48
      + Math.sin(t * (leaves ? 1.8 : 0.65) + phase) * (leaves ? 4 : 1.2);
    const y = surfaceY===null ? wrap(seed[index * 3+1]*64+t*velocity.y-origin.y+32,64)-32
      : surfaceY+wrap(seed[index * 3+1]*64+t*velocity.y,64)-origin.y;
    const z = wrap(seed[index * 3+2]*128-origin.z+64,128)-64;
    position.setXYZ(index, x, y, z);
  }
  position.needsUpdate = true;
}

export function updateWeather(THREE, environment, {camera,t,state={},screenFog=true,surfaceY=null}) {
  if(!environment)return {};
  const levels=state.levels || {[state.weather||"clear"]:1};
  const level=key=>Math.max(0,Math.min(1.5,Number(levels[key])||0));
  const storm=level('storm'),rain=Math.max(level('rain'),storm),snow=level('snow'),leaves=level('leaves');
  const speed=Math.max(0,Math.min(2,state.speed??1)),wind=Math.max(-1,Math.min(1,state.wind||0));
  environment.group.position.copy(camera.position||camera);
  environment.group.quaternion.identity();
  for(const [object,amount,count,multiplier]of [[environment.rain,rain,620,2],[environment.flakes,snow,560,1],[environment.leaves,leaves,320,1]]){
    object.visible=amount>0;object.geometry.setDrawRange(0,Math.floor(count*Math.min(1,amount))*multiplier);
    object.material.opacity=Math.min(.95,(object===environment.rain ? .48 : .82)*amount);
  }
  if(rain>0)updateRain(environment,camera,t*speed,storm>0,wind,surfaceY);
  if(snow>0)updateFlakes(environment,camera,t*speed,false,wind,surfaceY);
  if(leaves>0)updateFlakes(environment,camera,t*speed,true,wind,surfaceY);
  const flash=state.lightning!==false&&speed>0?Math.pow(Math.max(0,Math.sin(t*2.73+1.4)-.965)/.035,3)*storm*.6:0;
  environment.fogUniforms.amount.value=screenFog?Math.min(.8,level('fog')*.68+storm*.1+rain*.025+snow*.025):0;
  environment.fogUniforms.flash.value=screenFog?Math.min(.7,flash):0;
  environment.fogUniforms.time.value=t*speed;
  environment.fog.visible=environment.fogUniforms.amount.value>0||environment.fogUniforms.flash.value>0;
  return {rain,snow,leaves,storm,fog:level('fog')};
}

export function updateEnvironment(THREE, environment, context) {
  const { scene, sky, ground, camera, ambient, key, rim, travelLight, t, state } = context;
  const levels=updateWeather(THREE,environment,{camera,t,state,screenFog:!sky});
  if (!environment || !sky) return;
  const palette = blendedPalette(THREE, state);
  const signature = [state.daytime, state.nextDaytime, state.season, state.nextSeason,
    Math.round((state.dayMix || 0) * 120), Math.round((state.seasonMix || 0) * 120)].join(':');
  if (signature !== environment.signature) {
    paintSky(environment, palette);
    environment.signature = signature;
    if (!environment.foliageMaterials) {
      const materials = new Set();
      scene.traverse(object => {
        if (object.material?.userData?.environmentRole === 'foliage') materials.add(object.material);
      });
      environment.foliageMaterials = [...materials];
    }
    for (const material of environment.foliageMaterials) material.color.copy(palette.foliage);
  }
  if (sky.children[0].material.map !== environment.skyTexture) {
    sky.children[0].material.map?.dispose();
    sky.children[0].material.map = environment.skyTexture;
  }
  const nightWeight = state.daytime === "night" ? 1 : state.daytime === "dawn" ? 0.35 : 0;
  sky.children[1].material.opacity = nightWeight;
  sky.children[2].visible = sky.children[3].visible = state.daytime !== "day";

  const weather = state.weather || "clear";
  const storm = levels.storm>0;

  const fogRange = { clear: [30, 260], rain: [18, 170], snow: [16, 150], fog: [7, 78], storm: [9, 105], leaves: [22, 205] }[weather] || [30, 260];
  scene.fog.color.copy(palette.fog);
  scene.fog.near=30;scene.fog.far=260;
  for(const [kind,amount]of Object.entries(levels)){
    const range={rain:[18,170],snow:[16,150],fog:[7,78],storm:[9,105],leaves:[22,205]}[kind];
    if(range){scene.fog.near=Math.min(scene.fog.near,30+(range[0]-30)*Math.min(1,amount));scene.fog.far=Math.min(scene.fog.far,260+(range[1]-260)*Math.min(1,amount));}
  }
  scene.background.copy(palette.fog);
  ground.material.color.copy(palette.ground);

  const flashWave = storm && state.lightning!==false ? Math.max(0, Math.sin(t * 2.73 + 1.4) - 0.965) / 0.035*Math.min(1,levels.storm) : 0;
  const flash = Math.pow(Math.min(1, flashWave), 3);
  ambient.color.copy(palette.horizon); ambient.intensity = palette.ambient + flash * 1.8;
  key.color.copy(palette.key); key.intensity = 0.9 + palette.ambient * 0.45 + flash * 3;
  rim.intensity = 0.35 + nightWeight * 0.65 + flash * 2;
  travelLight.intensity += flash * 44;
}
