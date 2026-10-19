#!/usr/bin/env python3
"""Iridium carga LLVM por la ruta absoluta de la máquina de compilación (HOST_LLVM_LIBNAME).
Para un AppImage portable se cambia por el nombre suelto, que se resuelve con el RUNPATH
de mldr (host-bundle). Mismo tamaño: se rellena con NUL."""
import sys
OLD = b"/usr/lib/llvm-23/lib/libLLVM-23.so"
NEW = b"libLLVM-23.so".ljust(len(OLD), b"\0")
for path in sys.argv[1:]:
    data = open(path, "rb").read()
    n = data.count(OLD)
    if n:
        open(path, "wb").write(data.replace(OLD, NEW))
    print(f"{path}: {n} reemplazos")
