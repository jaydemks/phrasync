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
  const flakes = new THREE.Points(
    weatherGeometry(THREE, 560),
    new THREE.PointsMaterial({ color: 0xe9f5ff, size: 0.24, transparent: true, opacity: 0.82, depthWrite: false })
  );
  rain.frustumCulled = flakes.frustumCulled = false;
  rain.visible = flakes.visible = false;
  group.add(rain, flakes);

  const canvas = document.createElement("canvas");
  canvas.width = 32; canvas.height = 512;
  const skyTexture = new THREE.CanvasTexture(canvas);
  skyTexture.colorSpace = THREE.SRGBColorSpace;

  return {
    group, rain, flakes, canvas, skyTexture, theme,
    rainSeed: seededValues(620 * 3, 0x7135),
    flakeSeed: seededValues(560 * 3, 0x51f0),
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

function updateRain(environment, camera, t, storm) {
  const position = environment.rain.geometry.attributes.position;
  const seed = environment.rainSeed;
  const speed = storm ? 34 : 24;
  for (let index = 0; index < seed.length / 3; index += 1) {
    const x = camera.x + (seed[index * 3] - 0.5) * 72;
    const y = 0.4 + wrap(seed[index * 3 + 1] * 24 - t * speed, 24);
    const z = camera.z - 3 - seed[index * 3 + 2] * 105;
    const offset = index * 6;
    position.array[offset] = x; position.array[offset + 1] = y; position.array[offset + 2] = z;
    position.array[offset + 3] = x - (storm ? 0.65 : 0.24);
    position.array[offset + 4] = y - (storm ? 2.6 : 1.5);
    position.array[offset + 5] = z + 0.18;
  }
  position.needsUpdate = true;
}

function updateFlakes(environment, camera, t, leaves) {
  const position = environment.flakes.geometry.attributes.position;
  const seed = environment.flakeSeed;
  for (let index = 0; index < seed.length / 3; index += 1) {
    const phase = seed[index * 3] * Math.PI * 2;
    const x = camera.x + (seed[index * 3] - 0.5) * 62
      + Math.sin(t * (leaves ? 1.8 : 0.65) + phase) * (leaves ? 4 : 1.2);
    const y = 0.3 + wrap(seed[index * 3 + 1] * 22 - t * (leaves ? 2.5 : 1.4), 22);
    const z = camera.z - 3 - seed[index * 3 + 2] * 95;
    position.setXYZ(index, x, y, z);
  }
  position.needsUpdate = true;
}

export function updateEnvironment(THREE, environment, context) {
  const { scene, sky, ground, camera, ambient, key, rim, travelLight, t, state } = context;
  if (!environment || !sky) return;
  const palette = blendedPalette(THREE, state);
  paintSky(environment, palette);
  if (sky.children[0].material.map !== environment.skyTexture) {
    sky.children[0].material.map?.dispose();
    sky.children[0].material.map = environment.skyTexture;
  }
  const nightWeight = state.daytime === "night" ? 1 : state.daytime === "dawn" ? 0.35 : 0;
  sky.children[1].material.opacity = nightWeight;
  sky.children[2].visible = sky.children[3].visible = state.daytime !== "day";

  const weather = state.weather || "clear";
  const storm = weather === "storm";
  const rain = weather === "rain" || storm;
  const flakes = weather === "snow" || weather === "leaves";
  environment.rain.visible = rain;
  environment.flakes.visible = flakes;
  if (rain) updateRain(environment, camera, t, storm);
  if (flakes) {
    const leaves = weather === "leaves";
    environment.flakes.material.color.set(leaves ? 0xe07032 : 0xe9f5ff);
    environment.flakes.material.size = leaves ? 0.34 : 0.24;
    updateFlakes(environment, camera, t, leaves);
  }

  const fogRange = { clear: [30, 260], rain: [18, 170], snow: [16, 150], fog: [7, 78], storm: [9, 105], leaves: [22, 205] }[weather];
  scene.fog.color.copy(palette.fog);
  scene.fog.near = fogRange[0]; scene.fog.far = fogRange[1];
  scene.background.copy(palette.fog);
  ground.material.color.copy(palette.ground);
  scene.traverse(object => {
    if (object.material?.userData?.environmentRole === "foliage") {
      object.material.color.copy(palette.foliage);
    }
  });

  const flashWave = storm ? Math.max(0, Math.sin(t * 2.73 + 1.4) - 0.965) / 0.035 : 0;
  const flash = Math.pow(Math.min(1, flashWave), 3);
  ambient.color.copy(palette.horizon); ambient.intensity = palette.ambient + flash * 1.8;
  key.color.copy(palette.key); key.intensity = 0.9 + palette.ambient * 0.45 + flash * 3;
  rim.intensity = 0.35 + nightWeight * 0.65 + flash * 2;
  travelLight.intensity += flash * 44;
}
