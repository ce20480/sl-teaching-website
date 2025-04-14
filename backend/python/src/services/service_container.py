from typing import Dict, Any, Optional, Type
import logging

from .evaluator import EvaluatorService
from .storage.akave_sdk import AkaveSDK, AkaveConfig
from .reward.xp_reward import XpRewardService
from .contribution_service import ContributionService
from .ml.asl_service import ASLService
from .ml.blur_service import BlurService
from ..core.config import settings

logger = logging.getLogger(__name__)

class ServiceContainer:
    """
    Service container that manages the lifecycle of service instances.
    Implements the singleton pattern to ensure that services are only instantiated once.
    """
    
    _instance = None
    _services = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._services = {}
            logger.info("Initializing service container")
    
    def register(self, service_type: Type, instance: Any):
        """Register a service instance by its type"""
        self._services[service_type] = instance
        logger.info(f"Registered service: {service_type.__name__}")
    
    def get(self, service_type: Type) -> Any:
        """Get a service instance by its type"""
        if service_type not in self._services:
            raise KeyError(f"Service not registered: {service_type.__name__}")
        return self._services[service_type]
    
    def has(self, service_type: Type) -> bool:
        """Check if a service type is registered"""
        return service_type in self._services

# Singleton instance of the service container
_container = None

def get_service_container() -> ServiceContainer:
    """Get the singleton instance of the service container"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container

def initialize_services():
    """Initialize and register all services"""
    container = get_service_container()
    
    # Create evaluator service if not already registered
    if not container.has(EvaluatorService):
        evaluator = EvaluatorService(blur_threshold=35)
        container.register(EvaluatorService, evaluator)

    # Create blur service if not already registered
    if not container.has(BlurService):
        blur_service = BlurService()
        container.register(BlurService, blur_service)
    
    # Create ASL service if not already registered
    if not container.has(ASLService):
        asl_service = ASLService()
        container.register(ASLService, asl_service)
    
    # Create storage SDK if not already registered
    if not container.has(AkaveSDK):
        akave_config = AkaveConfig(host=settings.AKAVE_HOST or "http://localhost:4000")
        akave_sdk = AkaveSDK(akave_config)
        container.register(AkaveSDK, akave_sdk)
    
    # Create reward service if not already registered
    if not container.has(XpRewardService):
        reward_service = XpRewardService()
        container.register(XpRewardService, reward_service)
    
    # Create contribution service if not already registered
    if not container.has(ContributionService):
        evaluator = container.get(EvaluatorService)
        storage_sdk = container.get(AkaveSDK)
        reward_service = container.get(XpRewardService)
        
        contribution_service = ContributionService(
            evaluator=evaluator,
            storage_sdk=storage_sdk,
            reward_service=reward_service,
            default_bucket=settings.DEFAULT_BUCKET,
        )
        container.register(ContributionService, contribution_service)
    
    logger.info("All services initialized")
    return container

def get_evaluator_service() -> EvaluatorService:
    """Get the singleton instance of the evaluator service"""
    container = get_service_container()
    if not container.has(EvaluatorService):
        initialize_services()
    return container.get(EvaluatorService)

def get_asl_service() -> ASLService:
    """Get the singleton instance of the ASL service"""
    container = get_service_container()
    if not container.has(ASLService):
        initialize_services()
    return container.get(ASLService)

def get_blur_service() -> BlurService:
    """Get the singleton instance of the blur service"""
    container = get_service_container()
    if not container.has(BlurService):
        initialize_services()
    return container.get(BlurService)

def get_storage_sdk() -> AkaveSDK:
    """Get the singleton instance of the storage SDK"""
    container = get_service_container()
    if not container.has(AkaveSDK):
        initialize_services()
    return container.get(AkaveSDK)

def get_reward_service() -> XpRewardService:
    """Get the singleton instance of the reward service"""
    container = get_service_container()
    if not container.has(XpRewardService):
        initialize_services()
    return container.get(XpRewardService)

def get_contribution_service() -> ContributionService:
    """Get the singleton instance of the contribution service"""
    container = get_service_container()
    if not container.has(ContributionService):
        initialize_services()
    return container.get(ContributionService) 