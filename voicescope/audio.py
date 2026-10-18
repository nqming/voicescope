"""Deterministic PCM decoding, polyphase resampling and HTK log-Mel power."""
from math import gcd
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def decode(source, cfg):
    try:
        with sf.SoundFile(source) as f:
            if f.format not in {'WAV', 'WAVEX', 'FLAC'}:
                raise ValueError('Chỉ hỗ trợ WAV/FLAC; hãy chuyển đổi tệp trước.')
            duration = len(f) / f.samplerate
            if not cfg.min_duration <= duration <= cfg.max_duration:
                raise ValueError('Thời lượng audio ngoài giới hạn cấu hình.')
            if not 8000 <= f.samplerate <= 192000 or not 1 <= f.channels <= 8:
                raise ValueError('Sample rate hoặc số kênh ngoài giới hạn.')
            if len(f)*f.channels > cfg.max_decoded_samples:
                raise ValueError('Audio giải nén vượt giới hạn bộ nhớ; chuyển sang mono 16 kHz trước.')
            y = f.read(dtype='float32', always_2d=True)
            sr = f.samplerate
    except (sf.LibsndfileError, RuntimeError) as exc:
        raise ValueError('Không giải mã được audio WAV/FLAC.') from exc
    if not np.isfinite(y).all():
        raise ValueError('Audio chứa NaN/Inf.')
    # Check channels before downmix: opposite clipped channels must not cancel.
    if np.mean(np.abs(y) >= .999) > .01:
        raise ValueError('Audio clipping trên 1% mẫu.')
    y = y.mean(axis=1)
    if sr != cfg.sample_rate:
        divisor = gcd(sr,cfg.sample_rate)
        y = resample_poly(y,cfg.sample_rate//divisor,sr//divisor).astype(np.float32)
    if np.max(np.abs(y)) > 1.0:
        raise ValueError('Resampling gây peak vượt biên PCM; kiểm tra mức âm nguồn.')
    if cfg.peak_normalize and np.max(np.abs(y)) > 1e-8:
        y = y * (.95 / np.max(np.abs(y)))
    return np.asarray(y,dtype=np.float32), cfg.sample_rate


def quality(y):
    return {'peak':float(np.max(np.abs(y))),
            'rms_dbfs':float(20*np.log10(max(float(np.sqrt(np.mean(y*y))),1e-12))),
            'clipping_fraction':float(np.mean(np.abs(y)>=.999))}


def windows(y,sr,seconds):
    size = int(sr*seconds)
    for start in range(0,len(y),size):
        end=min(start+size,len(y))
        yield start/sr,end/sr,y[start:end]


def speech_regions(y,cfg):
    """Energy gate, NOT a learned speech detector. Keep original offsets."""
    frame=cfg.hop_length
    active=[]
    for start in range(0,len(y),frame):
        rms=np.sqrt(np.mean(y[start:start+frame]**2))
        active.append(20*np.log10(max(float(rms),1e-12)) >= cfg.vad_db)
    # Bridge <= 200 ms gaps and add 100 ms context without concatenating time.
    ids=np.flatnonzero(active)
    if not len(ids):
        return []
    groups=np.split(ids,np.where(np.diff(ids)>int(.2*cfg.sample_rate/frame)+1)[0]+1)
    spans=[]
    for group in groups:
        a=max(0,int(group[0]*frame-.1*cfg.sample_rate))
        b=min(len(y),int((group[-1]+1)*frame+.1*cfg.sample_rate))
        if spans and a<=spans[-1][1]:
            spans[-1]=(spans[-1][0],b)
        else:
            spans.append((a,b))
    return [(a,b) for a,b in spans if (b-a)/cfg.sample_rate>=cfg.min_duration]


def log_mel(y,cfg):
    """Left-aligned 25 ms frames, zero-pad FFT, centers at (i*hop+win/2)/sr."""
    y=np.asarray(y,dtype=np.float32)
    if len(y)<cfg.win_length:
        y=np.pad(y,(0,cfg.win_length-len(y)))
    count=1+int(np.ceil((len(y)-cfg.win_length)/cfg.hop_length))
    y=np.pad(y,(0,(count-1)*cfg.hop_length+cfg.win_length-len(y)))
    frames=np.lib.stride_tricks.sliding_window_view(y,cfg.win_length)[::cfg.hop_length]
    # Periodic Hann, fixed scaling; no per-file min/max fit.
    hann=np.hanning(cfg.win_length+1)[:-1]
    power=np.abs(np.fft.rfft(frames*hann,n=cfg.n_fft))**2 / np.sum(hann**2)
    mel_max=2595*np.log10(1+(cfg.sample_rate/2)/700)
    hz=700*(10**(np.linspace(0,mel_max,cfg.n_mels+2)/2595)-1)
    bins=np.fft.rfftfreq(cfg.n_fft,1/cfg.sample_rate)
    bank=np.maximum(0,np.minimum((bins[None,:]-hz[:-2,None])/(hz[1:-1]-hz[:-2])[:,None],
                                (hz[2:,None]-bins[None,:])/(hz[2:]-hz[1:-1])[:,None]))
    mel=bank @ power.T
    db=10*np.log10(np.maximum(mel,1e-10))
    # Fixed [-80,20] dB scale; recorded in checkpoint preprocessing config.
    image=np.clip((db+80)/100,0,1).astype(np.float32)
    times=(np.arange(count)*cfg.hop_length+cfg.win_length/2)/cfg.sample_rate
    return image,times


def speech_windows(y,cfg):
    """Shared selection for data preparation and serving, absolute time retained."""
    for a,b in speech_regions(y,cfg):
        for start,end,part in windows(y[a:b],cfg.sample_rate,cfg.window_seconds):
            if len(part)/cfg.sample_rate>=cfg.min_duration:
                yield a/cfg.sample_rate+start,a/cfg.sample_rate+end,part
