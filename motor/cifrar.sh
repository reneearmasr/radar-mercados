#!/bin/sh
# Cifra el archivo de datos antes de subirlo al repositorio público.
# Uso: sh motor/cifrar.sh <entrada.json> <salida.enc> <clave_hex_64>
# Formato de salida: <iv_hex>:<base64>, que descifra public.cargar_activos() en Supabase.
set -e
IV=$(openssl rand -hex 16)
B64=$(openssl enc -aes-256-cbc -K "$3" -iv "$IV" -in "$1" -a -A)
printf '%s:%s\n' "$IV" "$B64" > "$2"
