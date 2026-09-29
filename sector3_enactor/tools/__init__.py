__all__ = [
    "ConnectorAccount",
    "GatewayContext",
    "ToolGateway",
    "EnactorToolDefinition",
    "ToolRegistry",
    "build_default_registry",
]


def __getattr__(name):
    if name in {"ConnectorAccount", "GatewayContext", "ToolGateway"}:
        from .gateway import ConnectorAccount, GatewayContext, ToolGateway
        return {"ConnectorAccount": ConnectorAccount, "GatewayContext": GatewayContext, "ToolGateway": ToolGateway}[name]
    if name in {"EnactorToolDefinition", "ToolRegistry"}:
        from .registry import EnactorToolDefinition, ToolRegistry
        return {"EnactorToolDefinition": EnactorToolDefinition, "ToolRegistry": ToolRegistry}[name]
    if name == "build_default_registry":
        from .definitions import build_default_registry
        return build_default_registry
    raise AttributeError(name)
