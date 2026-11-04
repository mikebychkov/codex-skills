"""Review integrity core. Pure Python stdlib; writes only to external review state."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

USAGE=2; MAVEN_UNAVAILABLE=3; BAD_REPO=4; CHANGED=10; NO_BASELINE=11; UNSAFE_STATE=12

class HookError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code=code

def git(repo, *args):
    p=subprocess.run(['git','--no-optional-locks','-C',str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
    if p.returncode: raise HookError('Git state inspection failed',BAD_REPO)
    return p.stdout

def paths(require_state=True):
    raw=os.environ.get('TARGET_REPO')
    if not raw: raise HookError('TARGET_REPO is required',USAGE)
    repo=Path(raw).resolve(strict=True) if Path(raw).exists() else None
    if repo is None or not repo.is_dir(): raise HookError('Invalid TARGET_REPO',BAD_REPO)
    if git(repo,'rev-parse','--is-inside-work-tree').strip()!=b'true':raise HookError('Not a Git worktree',BAD_REPO)
    # Always work at the Git root to avoid misleading relative snapshots.
    top=Path(os.fsdecode(git(repo,'rev-parse','--show-toplevel').strip())).resolve()
    if repo!=top: raise HookError('TARGET_REPO must be the worktree root',BAD_REPO)
    rawstate=os.environ.get('REVIEW_STATE_DIR')
    if not rawstate: raise HookError('REVIEW_STATE_DIR must be a unique absolute directory supplied by the harness',UNSAFE_STATE)
    state=Path(rawstate)
    if not state.is_absolute(): raise HookError('REVIEW_STATE_DIR must be absolute',UNSAFE_STATE)
    # resolve(strict=False) follows already-existing symlink ancestors before any creation.
    state=state.resolve(strict=False)
    # Linked worktrees use external Git metadata. Reject state inside any
    # protected root before making directories, including symlinked ancestors.
    git_dir=Path(os.fsdecode(git(repo,'rev-parse','--absolute-git-dir').strip())).resolve()
    common_dir=Path(os.fsdecode(git(repo,'rev-parse','--path-format=absolute','--git-common-dir').strip())).resolve()
    if any(state==parent or parent in state.parents for parent in (repo,git_dir,common_dir)):
        raise HookError('State directory overlaps source or Git metadata',UNSAFE_STATE)
    if require_state and not state.is_dir():raise HookError('Baseline state directory unavailable',NO_BASELINE)
    return repo,state

def sha(b):return hashlib.sha256(b).hexdigest()

def state_snapshot(repo):
    # Includes staged/unstaged content and tracking/index shape; does not print secrets.
    result={
       'status':sha(git(repo,'status','--porcelain=v1','-z','--untracked-files=no')),
       'worktree_diff':sha(git(repo,'diff','--no-ext-diff','--binary')),
       'index_diff':sha(git(repo,'diff','--cached','--no-ext-diff','--binary')),
       'index_entries':sha(git(repo,'ls-files','--stage','-z')),
       'head':sha(git(repo,'rev-parse','HEAD')),
       'head_symbolic':sha(git(repo,'symbolic-ref','-q','HEAD') if is_branch(repo) else b'DETACHED'),
       'refs':sha(git(repo,'for-each-ref','--format=%(refname) %(objectname) %(symref)')),
    }
    # Shared repository config lives in the common Git directory for linked
    # worktrees. config.worktree is additional when worktreeConfig is enabled.
    git_dir=Path(os.fsdecode(git(repo,'rev-parse','--absolute-git-dir').strip())).resolve()
    common_dir=Path(os.fsdecode(git(repo,'rev-parse','--path-format=absolute','--git-common-dir').strip())).resolve()
    for label, cfg in (('git_common_config',common_dir/'config'),
                       ('git_worktree_config',git_dir/'config.worktree')):
        result[label]=sha(cfg.read_bytes() if cfg.is_file() else b'')
    return result

def is_branch(repo):
    return subprocess.run(['git','--no-optional-locks','-C',str(repo),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0

def baseline(state):
    f=state/'baseline.json'
    if not f.is_file():raise HookError('Baseline unavailable',NO_BASELINE)
    try:return json.loads(f.read_text())
    except (ValueError,OSError):raise HookError('Baseline unreadable',NO_BASELINE)

def atomic_create(path, data):
    # exclusive file creation; never overwrite a baseline after initialization
    with path.open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2,sort_keys=True)
        f.write('\n')

def init_review():
    repo,state=paths(require_state=False)
    if state.exists():
        # Caller must create a fresh unique path; never overwrite an existing run.
        raise HookError('Review state directory already exists; use unique REVIEW_STATE_DIR',UNSAFE_STATE)
    # Parents may exist; both state and its resolved path have already passed checks.
    state.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.chmod(state,0o700)
    try: atomic_create(state/'baseline.json',{'repository':str(repo),'snapshot':state_snapshot(repo)})
    except Exception:
        # Never auto-delete state; caller can inspect failed initialization.
        raise
    print('init-review: baseline recorded independently of Maven')
    return 0

def check_settings():
    path=os.environ.get('MAVEN_SETTINGS')
    if not path or not Path(path).is_file() or not os.access(path,os.R_OK):
        raise HookError('Maven validation was not executed because MAVEN_SETTINGS was not configured or was unavailable to the review environment.',MAVEN_UNAVAILABLE)

def before_validation():
    repo,state=paths()
    base=baseline(state)
    if base.get('repository')!=str(repo):raise HookError('Baseline belongs to another repository',NO_BASELINE)
    verify_state(repo,base,'before-validation')
    check_settings()
    print('before-validation: Maven prerequisites satisfied')
    return 0

def verify_state(repo,base,phase):
    now=state_snapshot(repo)
    expected=base['snapshot']
    modified=sorted(k for k in expected if expected.get(k)!=now.get(k))
    if modified:
        raise HookError(f'{phase}: Git state CHANGED (categories: {", ".join(modified)}). No automatic revert.',CHANGED)
    print(f'{phase}: tracked content and checked Git state UNCHANGED')

def after_validation():
    repo,state=paths();base=baseline(state)
    if base.get('repository')!=str(repo):raise HookError('Baseline belongs to another repository',NO_BASELINE)
    verify_state(repo,base,'after-validation')
    return 0

def verify_working_tree():
    repo,state=paths();base=baseline(state)
    if base.get('repository')!=str(repo):raise HookError('Baseline belongs to another repository',NO_BASELINE)
    verify_state(repo,base,'Working-tree status')
    return 0

def run(action):
    try:return {'init-review':init_review,'before-validation':before_validation,'after-validation':after_validation,'verify-working-tree':verify_working_tree}[action]()
    except HookError as e:
        print(str(e),file=sys.stderr);return e.code
    except (OSError,ValueError,KeyError) as e:
        print(f'{action}: verification unavailable ({type(e).__name__})',file=sys.stderr);return NO_BASELINE
