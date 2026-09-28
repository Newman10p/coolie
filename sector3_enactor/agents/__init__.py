from .base import BaseEnactorAgent
from .messengers.support_triage import SupportTriageAgent
from .messengers.supply_communications import SupplyCommunicationsAgent
from .designers.graphic_designer import GraphicDesignerAgent
from .builders.web_developer import WebDeveloperAgent
from .marketers.campaign_manager import CampaignManagerAgent
from .seo.seo_specialist import SeoSpecialistAgent
from .commerce.catalog_manager import CatalogManagerAgent
from .commerce.returns_processor import ReturnsProcessorAgent
from .qa.quality_gate_agent import QualityGateAgent
from .analytics.metric_collector import MetricCollectorAgent

ROLE_TO_AGENT_CLASS = {
    "messengers.support_triage": SupportTriageAgent,
    "messengers.supply_communications": SupplyCommunicationsAgent,
    "designers.graphic_designer": GraphicDesignerAgent,
    "builders.web_developer": WebDeveloperAgent,
    "marketers.campaign_manager": CampaignManagerAgent,
    "seo.seo_specialist": SeoSpecialistAgent,
    "commerce.catalog_manager": CatalogManagerAgent,
    "commerce.returns_processor": ReturnsProcessorAgent,
    "qa.quality_gate": QualityGateAgent,
    "analytics.metric_collector": MetricCollectorAgent,
}
