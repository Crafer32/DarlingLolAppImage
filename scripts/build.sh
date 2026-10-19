#!/bin/sh
# Builds the darling-lol AppImage from scratch in a rootless podman container.
#   scripts/build.sh            full build (sources ~5 GB, build ~1-2 h)
#   STEP=appimage scripts/build.sh   only re-assemble the AppImage
# Needs: podman, ~60 GB free, network. The container uses Ubuntu 24.04 (glibc 2.39) + LLVM 23,
# so the result runs on any x86-64 distro with glibc >= 2.39.
set -eu
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK=${WORK:-$REPO/work}
DARLING_LOL_REF=${DARLING_LOL_REF:-bcb3245}
JOBS=${JOBS:-$(nproc)}
IMAGE=darling-lol-appimage-build:noble
mkdir -p "$WORK" "$REPO/release"
podman image exists $IMAGE || podman build -t $IMAGE "$REPO/container"
run() { podman run --rm --cap-add SYS_ADMIN --security-opt seccomp=unconfined --security-opt label=disable \
	-v "$WORK:/build" -v "$REPO:/repo:ro" -w /build/darling-lol \
	-v "$WORK/usr-local:/usr/local" $IMAGE sh -euc "$1"; }
mkdir -p "$WORK/usr-local"

if [ "${STEP:-all}" = all ]; then
	[ -d "$WORK/darling-lol" ] || git clone https://github.com/lucannez64/darling-lol.git "$WORK/darling-lol"
	git -C "$WORK/darling-lol" checkout -q "$DARLING_LOL_REF"
	git -C "$WORK/darling-lol" apply "$REPO/patches/darling-lol-tools-appimage.patch"
	run 'git lfs install --skip-repo >/dev/null; python3 scripts/configure.py --guest-user lol --prefix /build/prefix && python3 scripts/prepare.py'
	run 'sh /repo/scripts/build-ffmpeg.sh'
	patch -d "$WORK/darling-lol/build/darling-src" -p1 < "$REPO/patches/darling-rootless.patch"
	patch -d "$WORK/darling-lol/build/darling-src" -p1 < "$REPO/patches/darling-window-drag.patch"
	run "cmake -S build/darling-src -B build/darling-src/build -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE= -DTARGET_i386=OFF \
		-DCMAKE_INSTALL_PREFIX=/usr/local -DENABLE_METAL=ON -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
		-DCMAKE_C_FLAGS='-O3 -march=x86-64-v2 -mtune=generic -pipe' -DCMAKE_CXX_FLAGS='-O3 -march=x86-64-v2 -mtune=generic -pipe' \
		&& cmake --build build/darling-src/build --parallel $JOBS && cmake --install build/darling-src/build \
		&& python3 -m venv build/venv && build/venv/bin/pip install -q -r requirements.txt \
		&& DPREFIX=/build/prefix sh scripts/install-runtime.sh"
fi

# MAJOR.MINOR: bump MINOR for each release, MAJOR for big changes (1.0, 1.1, ... 2.0)
VERSION=${VERSION:-$(cat "$REPO/VERSION")}
run "VERSION=$VERSION sh /repo/scripts/build-appdir.sh"
[ -x "$WORK/appimagetool" ] || curl -sL -o "$WORK/appimagetool" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
[ -f "$WORK/runtime-x86_64" ] || curl -sL -o "$WORK/runtime-x86_64" https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64
chmod +x "$WORK/appimagetool"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$WORK/appimagetool" --runtime-file "$WORK/runtime-x86_64" --comp zstd \
	"$WORK/AppDir" "$REPO/release/DarlingLol-$VERSION-x86_64.AppImage"
echo "Done: release/DarlingLol-$VERSION-x86_64.AppImage"
