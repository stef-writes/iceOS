from __future__ import annotations

from typing import TYPE_CHECKING

import grpc

from ice_sdk.services.network_service import NetworkService

if TYPE_CHECKING:
    # Real generated modules are only available in a fully generated env.
    from ice_api.proto import network_pb2, network_pb2_grpc  # pragma: no cover
else:  # Fallback so mypy/tests succeed without generated stubs
    import types  # – internal workaround

    network_pb2 = types.ModuleType("network_pb2")
    network_pb2.CreateNetworkSpecResponse = type("CreateNetworkSpecResponse", (), {})
    network_pb2.ListNetworkSpecsResponse = type("ListNetworkSpecsResponse", (), {})
    network_pb2.GetNetworkSpecResponse = type("GetNetworkSpecResponse", (), {})
    class _DynResp:  # noqa: D401 – simple stub
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    network_pb2.ExecuteNetworkResponse = _DynResp

    network_pb2_grpc = types.ModuleType("network_pb2_grpc")
    network_pb2_grpc.NetworkServiceServicer = object  # type: ignore[assignment]
    network_pb2_grpc.add_NetworkServiceServicer_to_server = lambda servicer, server: None  # type: ignore[assignment]

BaseServicer = getattr(network_pb2_grpc, "NetworkServiceServicer", object)

class NetworkGRPCServicer(BaseServicer):  # type: ignore[misc]
    """gRPC adapter that forwards requests to :class:`NetworkService`."""

    def __init__(self, service: NetworkService):
        self._service = service

    # ------------------------------------------------------------------
    # gRPC method handlers ------------------------------------------------
    # ------------------------------------------------------------------

    async def CreateNetworkSpec(self, request, context):  # – protobuf naming
        try:
            spec_id = await self._service.create_network_spec(request.spec)  # type: ignore[arg-type]
            return network_pb2.CreateNetworkSpecResponse(spec_id=spec_id)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover – translate to gRPC error
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return network_pb2.CreateNetworkSpecResponse()  # type: ignore[attr-defined]

    async def ListNetworkSpecs(self, request, context):
        try:
            specs = await self._service.list_network_specs(request.filter)  # type: ignore[attr-defined]
            return network_pb2.ListNetworkSpecsResponse(specs=specs)  # type: ignore[attr-defined]
        except Exception as exc:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return network_pb2.ListNetworkSpecsResponse()  # type: ignore[attr-defined]

    async def GetNetworkSpec(self, request, context):
        try:
            specs = await self._service.list_network_specs(filter=f"id={request.spec_id}")  # type: ignore[attr-defined]
            if not specs:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return network_pb2.GetNetworkSpecResponse()  # type: ignore[attr-defined]
            return network_pb2.GetNetworkSpecResponse(spec=specs[0])  # type: ignore[attr-defined]
        except Exception as exc:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return network_pb2.GetNetworkSpecResponse()  # type: ignore[attr-defined]

    async def ExecuteNetwork(self, request, context):  # noqa: N802 – gRPC naming
        """Execute a network manifest located at *request.manifest_path*."""

        try:
            await self._service.execute(request.manifest_path)  # type: ignore[attr-defined]
            return network_pb2.ExecuteNetworkResponse(success=True)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return network_pb2.ExecuteNetworkResponse(success=False)  # type: ignore[attr-defined]
