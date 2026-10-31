const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let Processor;const messages=[];
const context={AudioWorkletProcessor:class{constructor(){this.port={postMessage:m=>messages.push(m),onmessage:null};}},registerProcessor:(name,type)=>Processor=type,Float32Array};
vm.runInNewContext(fs.readFileSync('web/pcm-recorder.js','utf8'),context);
const recorder=new Processor(),samples=Float32Array.from({length:5003},(_,i)=>Math.sin(i*.05)*.6);
for(let i=0;i<samples.length;i+=128){const a=samples.slice(i,i+128),b=Float32Array.from(a,x=>x*.5);assert.equal(recorder.process([[a,b]]),true);}
recorder.port.onmessage({data:'stop'});const blocks=messages.filter(x=>x.samples).map(x=>x.samples);assert.equal(blocks.reduce((n,x)=>n+x.length,0),samples.length);assert.equal(messages.at(-1).stopped,true);
const mono=Float32Array.from(blocks.flatMap(x=>Array.from(x)));for(let i=0;i<samples.length;i++)assert.ok(Math.abs(mono[i]-samples[i]*.75)<1e-6);
const code=fs.readFileSync('web/app.js','utf8');const wav=code.slice(code.indexOf('function wavFile('),code.indexOf('let captureContext'));
const target={Float32Array,ArrayBuffer,DataView,Math,File};vm.runInNewContext(wav,target);
(async()=>{const file=target.wavFile({length:mono.length,sampleRate:48000,numberOfChannels:1,getChannelData:()=>mono});const bytes=Buffer.from(await file.arrayBuffer());assert.equal(bytes.readUInt32LE(24),48000);assert.equal(bytes.readUInt32LE(40),samples.length*2);for(let i=0;i<mono.length;i++){const actual=bytes.readInt16LE(44+i*2)/32768;assert.ok(Math.abs(actual-mono[i])<2/32768);}console.log('PASS: raw PCM stereo downmix, block order, final partial block, stop and WAV encoding (5003 samples)');})();
