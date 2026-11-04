#!/usr/bin/env python3
"""Minimal synchronous harness example; not a sandbox or policy enforcement engine."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def hook(root,name,env):
    return subprocess.run([sys.executable,str(root/'hooks'/name/'hook.py')],env=env).returncode

def main():
    root=Path(os.environ['REVIEW_SYSTEM']).resolve()
    repo=Path(os.environ['TARGET_REPO']).resolve()
    state_env=os.environ.get('REVIEW_STATE_DIR')
    if state_env:
        state=Path(state_env).resolve(strict=False)
    else:
        # Create unique REVIEW_STATE_DIR path, not the directory itself.
        # Restrict TMPDIR to outside the repository.
        temp_root=Path(tempfile.gettempdir()).resolve()
        if temp_root==repo or repo in temp_root.parents:
            print('Unsafe temporary directory',file=sys.stderr);return 12
        state=temp_root/('codex-review-'+__import__('uuid').uuid4().hex)
    env={**os.environ,'REVIEW_STATE_DIR':str(state),'TARGET_REPO':str(repo)}
    initial=hook(root,'init-review',env)
    if initial:return initial
    maven_rc=None
    pre=hook(root,'before-validation',env)
    try:
        if pre==0:
            wrapper=repo/'mvnw'
            command=[str(wrapper) if wrapper.is_file() and os.access(wrapper,os.X_OK) else 'mvn','-s',env['MAVEN_SETTINGS'],'test']
            try:
                maven_rc=subprocess.run(command,cwd=repo,env=env).returncode
            except OSError as e:
                print('Maven launch failed:',type(e).__name__,file=sys.stderr)
                maven_rc=127
        elif pre==3:
            print('Maven unavailable: continue static review',file=sys.stderr)
        else:
            print('Pre-validation integrity or configuration check failed',file=sys.stderr)
    finally:
        # MUST run even if Maven returns nonzero, fails to spawn, or is interrupted.
        post=hook(root,'after-validation',env)
        final=hook(root,'verify-working-tree',env)
    if post:return post
    if final:return final
    if pre not in (0,3):return pre
    if maven_rc not in (None,0):return maven_rc
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except KeyError as e:
        print('Missing required env:',str(e),file=sys.stderr);sys.exit(2)
