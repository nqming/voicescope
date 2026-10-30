'use strict';
const $ = id => document.getElementById(id);
let selected = null, audioURL = null, currentReport = null, ready = false, busy = false;
let selectionVersion = 0, maxBytes = 20 * 1024 * 1024, maxDuration = 120;
let recorder = null, recordStream = null, recordTimer = null, recording = false;
function message(text, error = false) { $('input-status').textContent = text; $('input-status').classList.toggle('error', error); }
function buttons() { $('analyze').disabled = !selected || !ready || busy || recording; $('record').disabled = busy; }
function clearResult() { currentReport = null; $('result').hidden = true; $('empty-result').hidden = false; }
function drawWave(samples) {
  const canvas = $('waveform'), context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height); context.strokeStyle = '#1b9ba5'; context.lineWidth = 1;
  context.beginPath(); const step = Math.max(1, Math.floor(samples.length / canvas.width));
  for (let x = 0; x < canvas.width; x++) {
    let lo = 0, hi = 0;
    for (let j = x * step; j < Math.min((x + 1) * step, samples.length); j++) { lo = Math.min(lo, samples[j]); hi = Math.max(hi, samples[j]); }
    context.moveTo(x, 75 + lo * 70); context.lineTo(x, 75 + hi * 70);
  }
  context.stroke(); $('waveform-empty').hidden = true;
}
function clearFile() {
  selectionVersion++; selected = null; clearResult();
  if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
  $('player').removeAttribute('src'); $('player').load(); $('file').value = ''; $('file-detail').hidden = true;
  $('duration').textContent = '—'; $('waveform').getContext('2d').clearRect(0, 0, 900, 150); $('waveform-empty').hidden = false;
  message('Chọn audio để kiểm tra thông tin tệp.'); buttons();
}
async function selectFile(file) {
  if (!file || busy || recording) return;
  clearFile(); const version = selectionVersion;
  if (!/\.(wav|flac)$/i.test(file.name)) return message('Chỉ hỗ trợ WAV hoặc FLAC. Hãy chuyển đổi MP3/M4A trước.', true);
  if (!file.size || file.size > maxBytes) return message(`Tệp phải lớn hơn 0 và không quá ${(maxBytes / 1048576).toFixed(0)} MB.`, true);
  selected = file; audioURL = URL.createObjectURL(file); $('player').src = audioURL;
  $('file-name').textContent = file.name; $('file-meta').textContent = `${(file.size / 1048576).toFixed(2)} MB · đang đọc thời lượng…`; $('file-detail').hidden = false;
  let context;
  try {
    context = new AudioContext(); const decoded = await context.decodeAudioData(await file.arrayBuffer());
    if (version !== selectionVersion) return;
    if (decoded.duration > maxDuration || decoded.duration < .25) { clearFile(); return message(`Audio cần dài từ 0,25 đến ${maxDuration} giây.`, true); }
    $('file-meta').textContent = `${decoded.duration.toFixed(2)} giây · ${decoded.sampleRate} Hz · ${decoded.numberOfChannels} kênh · ${(file.size / 1048576).toFixed(2)} MB`;
    $('duration').textContent = `${decoded.duration.toFixed(2)} s`; drawWave(decoded.getChannelData(0));
    message(ready ? 'Audio đã chọn. Sẵn sàng gửi đến API của hệ thống.' : 'Audio đã chọn. Chưa cấu hình mô hình để phân tích.');
  } catch {
    if (version !== selectionVersion) return;
    $('file-meta').textContent = `${(file.size / 1048576).toFixed(2)} MB · trình duyệt không đọc được thời lượng`;
    message('Trình duyệt chưa giải mã được tệp; API sẽ kiểm tra định dạng và thời lượng.', true);
  } finally { if (context) await context.close(); buttons(); }
}
let healthRetryTimer;
async function health(attempt = 0) {
  clearTimeout(healthRetryTimer);
  try {
    const response = await fetch('/health'); if (!response.ok) throw new Error('health'); const data = await response.json();
    ready = data.model_ready === true; maxBytes = data.max_upload_bytes; maxDuration = data.max_duration_seconds;
    $('limits').textContent = `WAV, FLAC · tối đa ${(maxBytes / 1048576).toFixed(0)} MB · ${maxDuration} giây`;
    $('model-status').textContent = data.message;
    $('model-help').textContent = ready ? `${data.model || 'Detector'} đã nạp. Sẵn sàng phân tích âm thanh.` : 'Bạn vẫn có thể chọn tệp và nghe thử. Phân tích sẽ mở khi mô hình sẵn sàng.';
    if (ready) { $('empty-result').querySelector('h3').textContent = 'Chưa có audio để phân tích'; $('empty-result').querySelector('p').textContent = 'Chọn tệp rồi bấm phân tích để nhận kết quả từ máy chủ.'; $('empty-result').querySelector('.pill').textContent = 'Mô hình đã cấu hình'; }
    else if (data.status === 'load_error') $('model-help').textContent += ' · Không nạp được checkpoint, hãy kiểm tra cấu hình máy chủ.';
  } catch {
    ready = false;
    $('model-status').textContent = 'Đang chờ máy chủ phản hồi';
    $('model-help').textContent = 'Máy chủ có thể đang khởi động. Bạn vẫn có thể chọn tệp và nghe thử.';
    if (attempt < 5) healthRetryTimer = setTimeout(() => health(attempt + 1), [2000, 5000, 10000, 20000, 30000][attempt]);
    else $('model-help').textContent = 'Chưa kết nối được máy chủ. Hãy tải lại trang để thử lại.';
  }
  buttons();
}
function renderReport(report) {
  if (!Number.isFinite(report.fake_score) || report.fake_score < 0 || report.fake_score > 1 || !['real', 'fake'].includes(report.label)) throw new Error('API trả kết quả không hợp lệ.');
  currentReport = report; $('empty-result').hidden = true; $('result').hidden = false;
  $('result-label').textContent = report.label === 'fake' ? 'Mô hình phân loại: Giả (Fake)' : 'Mô hình phân loại: Thật (Real)';
  $('score').textContent = `${(report.fake_score * 100).toFixed(1)} / 100`; $('score-bar').style.width = `${report.fake_score * 100}%`;
  $('result-duration').textContent = `${report.duration_seconds.toFixed(2)} s`;
  $('latency').textContent = `${report.timing_ms.server_compute.toFixed(1)} ms`;
  $('result-notice').textContent = report.notice;
}
$('analyze').addEventListener('click', async () => {
  if (!selected || !ready || busy) return;
  busy = true; buttons(); clearResult(); $('progress').hidden = false; $('progress').removeAttribute('value'); message('Đang tải audio và phân tích tại máy chủ…');
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 180000);
  try {
    const response = await fetch('/inference', {method: 'POST', headers: {'Content-Type': /\.flac$/i.test(selected.name) ? 'audio/flac' : 'audio/wav'}, body: selected, signal: controller.signal});
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || 'Máy chủ không thể phân tích.');
    renderReport(result); message('Phân tích hoàn tất. Kết quả được trả từ API.');
  } catch (error) { message(error.name === 'AbortError' ? 'Hết thời gian chờ. Máy chủ có thể vẫn đang xử lý; hãy thử lại sau.' : error.message, true); }
  finally { clearTimeout(timeout); busy = false; $('progress').hidden = true; buttons(); }
});
$('file').addEventListener('change', event => selectFile(event.target.files[0]));
$('dropzone').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('file').click(); } });
for (const name of ['dragenter', 'dragover']) $('dropzone').addEventListener(name, e => { e.preventDefault(); $('dropzone').classList.add('dragging'); });
for (const name of ['dragleave', 'drop']) $('dropzone').addEventListener(name, e => { e.preventDefault(); $('dropzone').classList.remove('dragging'); });
$('dropzone').addEventListener('drop', e => selectFile(e.dataTransfer.files[0]));
for (const id of ['reset', 'remove']) $(id).addEventListener('click', () => { if (!busy && !recording) clearFile(); });
for (const mode of ['upload', 'record']) $(`${mode}-tab`).addEventListener('click', () => {
  for (const other of ['upload', 'record']) { $(`${other}-panel`).hidden = mode !== other; $(`${other}-tab`).classList.toggle('active', mode === other); }
});
function wavFile(buffer) {
  const mono = new Float32Array(buffer.length);
  for (let c = 0; c < buffer.numberOfChannels; c++) { const channel = buffer.getChannelData(c); for (let i = 0; i < mono.length; i++) mono[i] += channel[i] / buffer.numberOfChannels; }
  const bytes = new ArrayBuffer(44 + mono.length * 2), view = new DataView(bytes);
  const str = (pos, text) => { for (let i = 0; i < text.length; i++) view.setUint8(pos + i, text.charCodeAt(i)); };
  str(0, 'RIFF'); view.setUint32(4, 36 + mono.length * 2, true); str(8, 'WAVE'); str(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, buffer.sampleRate, true); view.setUint32(28, buffer.sampleRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true); str(36, 'data'); view.setUint32(40, mono.length * 2, true);
  for (let i = 0; i < mono.length; i++) { const value = Math.max(-1, Math.min(1, mono[i])); view.setInt16(44 + i * 2, value * (value < 0 ? 32768 : 32767), true); }
  return new File([bytes], 'ghi-am-cuc-bo.wav', {type: 'audio/wav'});
}
function stopRecording() { if (recorder && recorder.state !== 'inactive') recorder.stop(); clearTimeout(recordTimer); if (recordStream) recordStream.getTracks().forEach(track => track.stop()); }
$('record').addEventListener('click', async () => {
  if (recording) { stopRecording(); return; }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { $('record-status').textContent = 'Ghi âm cần trình duyệt hỗ trợ và localhost/HTTPS.'; return; }
  $('record').disabled = true;
  try {
    recordStream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: false, noiseSuppression: false, autoGainControl: false}});
    recorder = new MediaRecorder(recordStream); const chunks = []; let bytes = 0;
    recorder.ondataavailable = e => { bytes += e.data.size; chunks.push(e.data); if (bytes > maxBytes) stopRecording(); };
    recorder.onstop = async () => {
      clearTimeout(recordTimer); recordStream.getTracks().forEach(track => track.stop());
      let context;
      try { context = new AudioContext(); const buffer = await context.decodeAudioData(await new Blob(chunks, {type: recorder.mimeType}).arrayBuffer()); recording = false; await selectFile(wavFile(buffer)); $('record-status').textContent = 'Đã dừng. Bản ghi chưa được gửi đi.'; }
      catch { $('record-status').textContent = 'Không chuyển được bản ghi sang WAV; hãy chọn tệp WAV/FLAC.'; }
      finally { recording = false; recorder = null; $('record').textContent = '● Bắt đầu ghi âm'; if (context) await context.close(); buttons(); }
    };
    recording = true; clearResult(); recorder.start(250); recordTimer = setTimeout(stopRecording, maxDuration * 1000);
    $('record').textContent = '■ Dừng ghi âm'; $('record-status').textContent = `Đang ghi âm · tự dừng sau ${maxDuration} giây. Có thể thiết bị vẫn áp dụng xử lý âm thanh.`;
  } catch { if (recordStream) recordStream.getTracks().forEach(track => track.stop()); $('record-status').textContent = 'Không có quyền hoặc không tìm thấy microphone.'; }
  finally { buttons(); }
});
$('download').addEventListener('click', () => { if (!currentReport) return; const url = URL.createObjectURL(new Blob([JSON.stringify(currentReport, null, 2)], {type: 'application/json'})); const link = document.createElement('a'); link.href = url; link.download = 'voicescope-report.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
window.addEventListener('beforeunload', () => { stopRecording(); if (audioURL) URL.revokeObjectURL(audioURL); });
health();
