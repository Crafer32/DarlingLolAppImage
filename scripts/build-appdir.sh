#!/bin/sh
# Runs INSIDE the build container (see scripts/build.sh). Assembles /build/AppDir.
set -eu
V=${VERSION:?}
A=/build/AppDir
P=/build/darling-lol
rm -rf $A; mkdir -p $A/usr/bin $A/usr/lib/darling-lol $A/usr/share/darling-lol
# Darling (sin setuid: el modo rootless se activa solo)
install -m755 /usr/local/bin/darling /usr/local/bin/darlingserver /usr/local/bin/darling-coredump $A/usr/bin/
mkdir -p $A/usr/libexec; cp -a /usr/local/libexec/darling $A/usr/libexec/
find $A/usr/libexec/darling -perm -4000 -exec chmod u-s {} + 2>/dev/null || true
# Darling's userland ships man pages and vim; nothing in the game path uses them (~80 MB)
rm -rf $A/usr/libexec/darling/usr/share/man $A/usr/libexec/darling/usr/share/vim
# Librerías del host de ABI variable, empaquetadas junto a mldr
B=$A/usr/libexec/darling/usr/lib/host-bundle; mkdir -p $B
LIBS="libjpeg.so.8 libgif.so.7 libtiff.so.6 libfuse.so.2"
# ffmpeg 6.1 built with decoders/demuxers only and no external libraries (scripts/build-ffmpeg.sh):
# same sonames Darling expects, ~15 MB instead of ~160 MB of distro codecs
FFMPEG=${FFMPEG:-/build/ffmpeg-min/lib}
# Minimal libLLVM for Iridium (scripts/build-llvm-min.sh): no backends, no z3/libxml2/ICU
LLVM=$(readlink -f /build/llvm-min/lib/libLLVM.so.23.1)
EXCL='/(libc|libm|libdl|libpthread|librt|ld-linux-x86-64|libresolv|libutil|libgcc_s|libstdc\+\+|libGL|libEGL|libGLX|libGLdispatch|libgbm|libdrm|libvulkan|libX11|libX11-xcb|libXext|libXau|libXdmcp|libXfixes|libXrender|libxcb[^/]*|libwayland[^/]*|libasound|libpulse[^/]*|libdbus-1|libsystemd|libudev|libfontconfig|libfreetype|libexpat|libz|libbsd|libmd|libcap|libgpg-error|libgcrypt|liblzma|libzstd|libbz2|libcrypto|libssl|libselinux|libpcre2-8|libglib-2.0|libgobject-2.0|libgio-2.0|libgmodule-2.0|libblkid|libmount|liblz4)\.so'
{ for l in $LIBS; do p=$(ldconfig -p | grep -m1 -P "^\s$l " | sed 's/.*=> //'); echo $p; ldd $p | awk '{print $3}'; done
  echo $LLVM; ldd $LLVM | awk '{print $3}'; } | grep / | sort -u | grep -v -E "$EXCL" | while read f; do cp -L "$f" $B/; done
ln -sf $(basename $LLVM) $B/libLLVM-23.so
for l in libavcodec.so.60 libavformat.so.60 libavutil.so.58 libswresample.so.4; do cp -L "$FFMPEG/$l" $B/; done
for f in $B/*.so*; do [ -L "$f" ] || patchelf --set-rpath '$ORIGIN' "$f"; done
patchelf --set-rpath '$ORIGIN/../../lib/host-bundle' $A/usr/libexec/darling/usr/libexec/darling/mldr
# Transporte X11 SHM de darling-lol
install -m755 $P/build/libdarling-xshm.so $A/usr/lib/darling-lol/
# Iridium lleva la ruta absoluta del LLVM de Ubuntu: dejar solo el nombre (lo resuelve el RUNPATH de mldr)
python3 /repo/scripts/fix-llvm-path.py $(grep -rl -a /usr/lib/llvm-23/lib/libLLVM-23.so /build/prefix/Users/lol $A/usr/libexec/darling 2>/dev/null) || true
# Runtime por usuario (overlays) + system_profiler
tar -C /build/prefix/Users/lol -czf $A/usr/share/darling-lol/guest-runtime.tar.gz RuntimeFrameworks RuntimeLibraries libDarlingXShm.dylib
install -m755 /build/prefix/usr/sbin/system_profiler $A/usr/share/darling-lol/system_profiler
# Proyecto (scripts y plantillas; se renderiza en el PC del usuario)
mkdir -p $A/usr/share/darling-lol/project
cp -a $P/scripts $P/tools $P/upstream $P/requirements.txt $P/LICENSE $P/NOTICE.md $A/usr/share/darling-lol/project/
rm -rf $A/usr/share/darling-lol/project/scripts/__pycache__
cp /repo/appdir/fonts.conf $A/usr/share/darling-lol/
echo "$V" > $A/usr/share/darling-lol/VERSION
# Lanzador + escritorio
install -m755 /repo/appdir/AppRun $A/AppRun
cp $P/darling-lol.png $A/darling-lol.png; cp $P/darling-lol.png $A/.DirIcon
cat > $A/darling-lol.desktop <<D
[Desktop Entry]
Type=Application
Name=League of Legends (darling-lol)
Comment=League of Legends for macOS on Darling, rootless
Exec=AppRun
Icon=darling-lol
Terminal=false
Categories=Game;
D
du -sh $A $B
