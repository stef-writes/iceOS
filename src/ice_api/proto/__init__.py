"""Stub package for gRPC proto modules used at type-check time.

This keeps *ice_api* self-contained and avoids relying on the deprecated
``internal_api`` package.  The real generated files should eventually live
here.  For now we just expose placeholder submodules so that *mypy* and the
runtime import system can resolve them.
"""

from types import ModuleType
import sys

network_pb2 = ModuleType("ice_api.proto.network_pb2")
network_pb2_grpc = ModuleType("ice_api.proto.network_pb2_grpc")

# Basic placeholders ---------------------------------------------------------
setattr(network_pb2, "CreateNetworkSpecRequest", object)
setattr(network_pb2, "ListNetworkSpecsRequest", object)
setattr(network_pb2, "GetNetworkSpecRequest", object)
setattr(network_pb2, "CreateNetworkSpecResponse", object)
setattr(network_pb2, "ListNetworkSpecsResponse", object)
setattr(network_pb2, "GetNetworkSpecResponse", object)

setattr(network_pb2_grpc, "NetworkServiceServicer", object)
setattr(network_pb2_grpc, "add_NetworkServiceServicer_to_server", lambda servicer, server: None)

# Register submodules so ``import ice_api.proto.network_pb2`` works -----------
sys.modules[__name__ + ".network_pb2"] = network_pb2
sys.modules[__name__ + ".network_pb2_grpc"] = network_pb2_grpc

__all__ = ["network_pb2", "network_pb2_grpc"] 