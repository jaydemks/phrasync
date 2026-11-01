"use strict";

// Encode the composited GPU canvas without an RGBA round trip to Python.
// Output is streamed with bounded queues; no full-video Blob is retained.
window.VFGPUEncoder = (() => {
  let encoder, writes, failure, endpoint, transport;
  function bounded(promise, label, ms = 15000) {
    let timer;
    return Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label} timed out`)), ms);
    })]).finally(() => clearTimeout(timer));
  }
  async function prepare(width, height, fps, bitrate, destination) {
    if (!window.VideoEncoder || !window.VideoFrame) return false;
    let config;
    for (const codec of ["avc1.640034", "avc1.640033", "avc1.640028", "avc1.420034"]) {
      const candidate = {codec, width, height, framerate: fps, bitrate,
        bitrateMode: "constant", hardwareAcceleration: "prefer-hardware",
        avc: {format: "annexb"}, latencyMode: "realtime"};
      try { if ((await bounded(VideoEncoder.isConfigSupported(candidate), "GPU codec probe")).supported) { config = candidate; break; } }
      catch (_) { /* Try another supported H.264 level before compatibility mode. */ }
    }
    if (!config) return false;
    endpoint = destination; writes = Promise.resolve(); failure = null;
    transport = new AbortController();
    encoder = new VideoEncoder({
      output(chunk) {
        const data = new Uint8Array(chunk.byteLength); chunk.copyTo(data);
        writes = writes.then(async () => {
          if (failure) return;
          const response = await bounded(fetch(endpoint, {method: "POST", body: data, signal: transport.signal}), "Encoded frame upload");
          if (!response.ok) throw new Error(`Encoded frame transport failed: ${response.status}`);
        }).catch(error => { failure ||= error; });
      },
      error(error) { failure ||= error; }
    });
    encoder.configure(config);
    return true;
  }
  async function batch(frames, fps, first, keyInterval) {
    for (let i = 0; i < frames.length; i++) {
      if (failure) throw failure;
      const [time, amplitude, bands] = frames[i];
      window.__vfExportFrequencyData = bands; window.__vfExportSpectrum = bands.slice(0, 64);
      await bounded(VFExport.renderFrame(time, amplitude), `Composition at ${time.toFixed(3)}s`, 45000);
      const frame = new VideoFrame(VFExport.canvas(), {
        timestamp: Math.round((first+i)*1000000/fps), duration: Math.round(1000000/fps)});
      try { encoder.encode(frame, {keyFrame: (first+i)%keyInterval === 0}); }
      finally { frame.close(); }
    }
    // A bounded batch flush also propagates delayed device failures promptly.
    await bounded(encoder.flush(), "GPU encoder flush"); await bounded(writes, "Encoded frame uploads");
    if (failure) throw failure;
  }
  async function finish() {
    try { await bounded(encoder.flush(), "GPU encoder finish"); await bounded(writes, "Encoded frame uploads"); if (failure) throw failure; }
    finally { if (encoder?.state !== "closed") encoder.close(); }
  }
  async function abort() {
    failure ||= new Error("GPU encoding stopped");
    transport?.abort();
    if (encoder && encoder.state !== "closed") encoder.close();
  }
  return {prepare, batch, finish, abort};
})();
