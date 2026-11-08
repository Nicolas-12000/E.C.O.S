from __future__ import annotations

import grpc

from app.grpc import ecos_forecast_pb2_grpc
from app.grpc.forecast_servicer import ForecastServicer


class GrpcHandle:
    def __init__(self, server: grpc.aio.Server):
        self._server = server

    async def stop(self, grace: float | None = 5.0) -> None:
        await self._server.stop(grace)


async def serve_grpc_async(port: int) -> GrpcHandle:
    server = grpc.aio.server()
    ecos_forecast_pb2_grpc.add_ForecastServiceServicer_to_server(ForecastServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    return GrpcHandle(server)
