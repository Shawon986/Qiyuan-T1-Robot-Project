#!/usr/bin/env bash
# T1 SDK setup — part 2 (run as regular user)
set -o pipefail

echo "==> pip install --user nanobind numpy opencv-python"
python3 -m pip install --user nanobind numpy opencv-python

echo "==> verify imports"
python3 -c 'import nanobind, numpy, cv2; print("nanobind", nanobind.__version__, "| numpy", numpy.__version__, "| cv2", cv2.__version__)'

echo "==> clone pinned T1 SDK"
mkdir -p "$HOME/t1_workspaces"
cd "$HOME/t1_workspaces"
if [ ! -d primebot_sdk/.git ]; then
  git clone https://gitcode.com/primebot/t1-sdk.git primebot_sdk
fi
cd primebot_sdk
git checkout fe2e186c867391ec78b301accdc91f0260ad0ff3
echo "HEAD=$(git rev-parse HEAD)"
echo "==> repo size and top-level"
du -sh .
ls
echo "==> user setup done"
