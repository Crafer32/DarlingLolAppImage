#!/bin/sh
# Minimal libLLVM for Iridium (Darling's Metal shader compiler), which only uses ~80 functions of
# the LLVM C API: read bitcode, walk the IR and run a few passes. Ubuntu's libLLVM brings every
# backend plus z3, libxml2 and ICU (~195 MB in the AppImage); this one has no backends and no
# external libraries. Built from the exact commit of the container's libllvm23, so it behaves the
# same. Runs inside the build container.
set -eu
COMMIT=$(dpkg-query -W -f '${Version}' libllvm23 | sed -n 's/.*+\([0-9a-f]\{12\}\)-.*/\1/p')
[ -n "$COMMIT" ] || { echo "Could not read the LLVM commit from libllvm23" >&2; exit 1; }
OUT=/build/llvm-min
[ -f "$OUT/.commit" ] && [ "$(cat "$OUT/.commit")" = "$COMMIT" ] && exit 0
cd /build
# llvm/ also includes headers from libc/ (shared math) and third-party/
SRC=$(ls -d /build/llvm-project-$COMMIT*/ 2>/dev/null | head -1)
if [ -z "$SRC" ] || [ ! -d "$SRC/libc" ]; then
	curl -sL "https://github.com/llvm/llvm-project/archive/$COMMIT.tar.gz" |
		tar xz --wildcards --no-wildcards-match-slash "llvm-project-$COMMIT*/llvm" "llvm-project-$COMMIT*/cmake" "llvm-project-$COMMIT*/third-party" "llvm-project-$COMMIT*/libc"
	SRC=$(ls -d /build/llvm-project-$COMMIT*/ | head -1)
fi
cmake -S "$SRC/llvm" -B /build/llvm-min-build -G Ninja \
	-DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$OUT" \
	-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
	-DCMAKE_C_FLAGS='-march=x86-64-v2 -mtune=generic' -DCMAKE_CXX_FLAGS='-march=x86-64-v2 -mtune=generic' \
	-DLLVM_TARGETS_TO_BUILD= -DLLVM_ENABLE_PROJECTS= \
	-DLLVM_BUILD_LLVM_DYLIB=ON -DLLVM_LINK_LLVM_DYLIB=ON \
	-DLLVM_ENABLE_Z3_SOLVER=OFF -DLLVM_ENABLE_LIBXML2=OFF -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF \
	-DLLVM_ENABLE_TERMINFO=OFF -DLLVM_ENABLE_LIBEDIT=OFF -DLLVM_ENABLE_FFI=OFF -DLLVM_ENABLE_LIBPFM=OFF \
	-DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_BUILD_TOOLS=OFF -DLLVM_BUILD_UTILS=OFF \
	-DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_DOCS=OFF
ninja -C /build/llvm-min-build -j"$(nproc)" LLVM
mkdir -p "$OUT/lib"
cp -L /build/llvm-min-build/lib/libLLVM.so.* "$OUT/lib/"
strip --strip-unneeded "$OUT"/lib/libLLVM.so.*
echo "$COMMIT" > "$OUT/.commit"
ls -l "$OUT/lib"
