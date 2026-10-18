import hashlib
import json
import random
import re
from pathlib import Path, PureWindowsPath

REQUIRED={'clip_id','speaker_id','source_id','label','synthesis_method','device','channel',
          'sample_rate','duration','consent_status','consent_ref','path','origin','license','is_test_fixture'}


def safe_path(root,relative):
    if Path(relative).is_absolute() or PureWindowsPath(relative).drive or '\\' in relative:
        raise ValueError('Đường dẫn phải tương đối, dùng dấu /.')
    root=Path(root).resolve(); path=(root/relative).resolve()
    if not path.is_relative_to(root) or path==root:
        raise ValueError('Đường dẫn ra ngoài data root.')
    return path


def validate(row):
    if REQUIRED-row.keys():
        raise ValueError('Thiếu trường: '+','.join(sorted(REQUIRED-row.keys())))
    for key in ('clip_id','speaker_id','source_id'):
        if not isinstance(row[key],str) or not re.fullmatch(r'[A-Za-z0-9_-]+',row[key]):
            raise ValueError('ID chỉ gồm chữ ASCII, số, _ và -.')
    for key in ('device','channel','synthesis_method','license','consent_ref'):
        if not isinstance(row[key],str) or not row[key].strip():
            raise ValueError('Metadata trống: '+key)
    if row['label'] not in {'real','fake'} or row['origin'] not in {'private','benchmark','test_fixture'}:
        raise ValueError('label hoặc origin không hợp lệ.')
    if type(row['is_test_fixture']) is not bool:
        raise ValueError('is_test_fixture phải là boolean.')
    if row['consent_status'] not in {'granted','licensed'}:
        raise ValueError('Chưa có đồng ý/quyền sử dụng được ghi nhận.')
    if row['origin']=='private' and row['consent_status']!='granted':
        raise ValueError('Dữ liệu riêng cần consent granted.')
    if row['label']=='fake' and row['synthesis_method']=='none':
        raise ValueError('Mẫu fake cần phương pháp tổng hợp.')
    for field in ('related_speaker_ids','related_source_ids'):
        values=row.get(field,[])
        if not isinstance(values,list) or any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',v) for v in values):
            raise ValueError('Danh sách quan hệ không hợp lệ: '+field)
    if row.get('parent_clip_id') and not re.fullmatch(r'[A-Za-z0-9_-]+',row['parent_clip_id']):
        raise ValueError('parent_clip_id không hợp lệ.')
    if row['origin']=='benchmark' and any(not row.get(key) for key in ('dataset_name','dataset_version','license_url')):
        raise ValueError('Benchmark cần dataset_name, dataset_version, license_url.')
    if not isinstance(row['duration'],(int,float)) or not 0<row['duration']<86400:
        raise ValueError('duration không hợp lệ.')
    if not isinstance(row['sample_rate'],int) or not 8000<=row['sample_rate']<=192000:
        raise ValueError('sample_rate không hợp lệ.')
    safe_path(Path.cwd(),row['path'])


def read_manifest(path,allow_fixtures=False):
    rows=[json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not rows:
        raise ValueError('Manifest chưa có dữ liệu.')
    seen=set()
    for row in rows:
        validate(row)
        if row['clip_id'] in seen:
            raise ValueError('clip_id trùng.')
        seen.add(row['clip_id'])
        if not allow_fixtures and (row['is_test_fixture'] or row['origin']=='test_fixture'):
            raise ValueError('Manifest mẫu/kiểm thử không được dùng cho nghiên cứu thật.')
    return rows


def write_manifest(path,rows):
    Path(path).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')


def assign_splits(rows,seed):
    """Connected components across speaker OR source OR parent, including VC ties."""
    parent=list(range(len(rows)))
    def find(i):
        while i!=parent[i]:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    seen={}
    for i,row in enumerate(rows):
        keys=[('speaker',row['speaker_id']),('source',row['source_id']),('clip',row['clip_id'])]
        keys += [('speaker',s) for s in row.get('related_speaker_ids',[])]
        keys += [('source',s) for s in row.get('related_source_ids',[])]
        if row.get('parent_clip_id'):
            keys.append(('clip',row['parent_clip_id']))
        for key in keys:
            if key in seen:
                parent[find(i)]=find(seen[key])
            seen[key]=i
    groups={}
    for i in range(len(rows)):
        groups.setdefault(find(i),[]).append(i)
    groups=sorted(groups.values(),key=lambda group:min(rows[i]['clip_id'] for i in group))
    if len(groups)<3:
        raise ValueError('Cần ít nhất 3 nhóm speaker/source độc lập để chia ba tập.')
    random.Random(seed).shuffle(groups)
    n=len(groups); n_test=max(1,round(n*.15)); n_val=max(1,round(n*.15))
    result=[dict(r) for r in rows]
    for g,group in enumerate(groups):
        split='test' if g<n_test else 'validation' if g<n_test+n_val else 'train'
        for i in group:
            result[i]['split']=split
    audit_splits(result)
    return result


def audit_splits(rows):
    seen={}
    for row in rows:
        split=row.get('split')
        if split not in {'train','validation','test'}:
            raise ValueError('Thiếu split hợp lệ.')
        keys=[('speaker',row['speaker_id']),('source',row['source_id']),('clip',row['clip_id'])]
        keys += [('speaker',s) for s in row.get('related_speaker_ids',[])]
        keys += [('source',s) for s in row.get('related_source_ids',[])]
        for field in ('parent_clip_id','sha256','original_sha256'):
            if row.get(field):
                keys.append(('clip' if field=='parent_clip_id' else 'hash',row[field]))
        for key in keys:
            if key in seen and seen[key]!=split:
                raise ValueError('Rò rỉ speaker/source/parent/hash giữa các split.')
            seen[key]=split


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
