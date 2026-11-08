#!/usr/bin/env bash
# Genera stubs Python desde proto/ (contract-first). Requiere: pip install grpcio-tools
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m grpc_tools.protoc \
  -I "$ROOT/proto" \
  --python_out="$ROOT/backend/app/grpc" \
  --grpc_python_out="$ROOT/backend/app/grpc" \
  "$ROOT/proto/ecos_forecast.proto"
# Imports relativos en grpc_python (paquete app.grpc)
if [[ -f "$ROOT/backend/app/grpc/ecos_forecast_pb2_grpc.py" ]]; then
  sed -i 's/^import ecos_forecast_pb2/from . import ecos_forecast_pb2/' \
    "$ROOT/backend/app/grpc/ecos_forecast_pb2_grpc.py" 2>/dev/null || true
fi
echo "[ok] stubs in backend/app/grpc/"
