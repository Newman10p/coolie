__all__ = [
    "ApprovalPolicy",
    "AuthorizationEngine",
    "BudgetPolicy",
    "CommunicationPolicy",
    "ContentSafetyPolicy",
    "CustomerDataPolicy",
    "MarketingPolicy",
    "ProductionPolicy",
]


def __getattr__(name):
    if name == "ApprovalPolicy":
        from .approval_policy import ApprovalPolicy
        return ApprovalPolicy
    if name == "AuthorizationEngine":
        from .authorization_engine import AuthorizationEngine
        return AuthorizationEngine
    if name == "BudgetPolicy":
        from .budget_policy import BudgetPolicy
        return BudgetPolicy
    if name == "CommunicationPolicy":
        from .communication_policy import CommunicationPolicy
        return CommunicationPolicy
    if name == "ContentSafetyPolicy":
        from .content_safety_policy import ContentSafetyPolicy
        return ContentSafetyPolicy
    if name == "CustomerDataPolicy":
        from .customer_data_policy import CustomerDataPolicy
        return CustomerDataPolicy
    if name == "MarketingPolicy":
        from .marketing_policy import MarketingPolicy
        return MarketingPolicy
    if name == "ProductionPolicy":
        from .production_policy import ProductionPolicy
        return ProductionPolicy
    raise AttributeError(name)
