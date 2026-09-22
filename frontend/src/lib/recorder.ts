/**
 * Microphone recorder that produces a 16 kHz mono 16-bit WAV blob.
 * Uses Web Audio instead of MediaRecorder so the format is identical in every browser.
 */
export class WavRecorder {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private chunks: Float32Array[] = [];
  private inputRate = 48000;
  private startedAt = 0;
  private cancelled = false;

  /** Analyser exposed for a level meter. */
  analyser: AnalyserNode | null = null;

  static isSupported() {
    return (
      typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia
    );
  }

  async start() {
    this.chunks = [];
    this.cancelled = false;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });
    if (this.cancelled) {
      stream.getTracks().forEach((t) => t.stop());
      throw new Error("Recording cancelled");
    }
    this.stream = stream;
    try {
      this.ctx = new AudioContext();
      if (this.ctx.state === "suspended") await this.ctx.resume();
      this.inputRate = this.ctx.sampleRate;
      this.source = this.ctx.createMediaStreamSource(this.stream);
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 512;
      this.processor = this.ctx.createScriptProcessor(4096, 1, 1);
      this.processor.onaudioprocess = (e) => {
        this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };
      this.source.connect(this.analyser);
      this.analyser.connect(this.processor);
      // The processor must be connected to fire; its output buffer stays silent.
      this.processor.connect(this.ctx.destination);
      if (this.cancelled) throw new Error("Recording cancelled");
      this.startedAt = performance.now();
    } catch (error) {
      this.cancel();
      throw error;
    }
  }

  /** Synchronous resource release, also safe while permission is pending. */
  cancel() {
    this.cancelled = true;
    this.processor?.disconnect();
    this.source?.disconnect();
    this.analyser?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    if (this.ctx && this.ctx.state !== "closed")
      void this.ctx.close().catch(() => {});
    this.ctx = null;
    this.stream = null;
    this.source = null;
    this.processor = null;
    this.analyser = null;
    this.chunks = [];
    this.startedAt = 0;
  }

  /** Seconds recorded so far. */
  elapsed() {
    return this.startedAt ? (performance.now() - this.startedAt) / 1000 : 0;
  }

  /** RMS level 0..1 for a meter. */
  level() {
    if (!this.analyser) return 0;
    const buf = new Uint8Array(this.analyser.fftSize);
    this.analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) {
      const x = (v - 128) / 128;
      sum += x * x;
    }
    return Math.min(1, Math.sqrt(sum / buf.length) * 3);
  }

  async stop(): Promise<Blob> {
    this.processor?.disconnect();
    this.analyser?.disconnect();
    this.source?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    const ctx = this.ctx;
    this.ctx = null;
    this.processor = null;
    this.analyser = null;
    this.source = null;
    this.stream = null;
    this.startedAt = 0;
    if (ctx) await ctx.close();

    const merged = mergeChunks(this.chunks);
    this.chunks = [];
    const pcm = downsample(merged, this.inputRate, 16000);
    return encodeWav(pcm, 16000);
  }
}

function mergeChunks(chunks: Float32Array[]): Float32Array {
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const out = new Float32Array(total);
  let off = 0;
  for (const c of chunks) {
    out.set(c, off);
    off += c.length;
  }
  return out;
}

function downsample(
  input: Float32Array,
  fromRate: number,
  toRate: number,
): Float32Array {
  if (fromRate === toRate) return input;
  const ratio = fromRate / toRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  let pos = 0;
  for (let i = 0; i < outLen; i++) {
    const next = Math.floor((i + 1) * ratio);
    let sum = 0;
    let n = 0;
    for (; pos < next && pos < input.length; pos++) {
      sum += input[pos];
      n++;
    }
    out[i] = n ? sum / n : 0;
  }
  return out;
}

function encodeWav(samples: Float32Array, rate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let off = 44;
  for (let i = 0; i < samples.length; i++, off += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}
