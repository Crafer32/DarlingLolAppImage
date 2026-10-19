#!/bin/sh
# Minimal ffmpeg 6.1 for the AppImage: decoders, demuxers and parsers only, no external
# libraries. Same sonames as Ubuntu 24.04's ffmpeg (libavcodec.so.60...), which is what
# Darling's native wrappers were built against. Runs inside the build container.
set -eu
V=6.1.1
cd /build
[ -d ffmpeg-$V ] || curl -sL https://ffmpeg.org/releases/ffmpeg-$V.tar.xz | tar xJ
cd ffmpeg-$V
./configure --prefix=/build/ffmpeg-min --enable-shared --disable-static --disable-programs \
	--disable-doc --disable-network --disable-autodetect --disable-encoders --disable-muxers \
	--disable-devices --disable-filters --disable-hwaccels --disable-postproc --disable-avdevice \
	--disable-avfilter --enable-swresample --enable-swscale --enable-zlib \
	--extra-cflags="-O2 -march=x86-64-v2"
make -j"$(nproc)"
make install
