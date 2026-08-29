"""Wires up the dependency graph, standing in for Spring's component scan /
``@Bean`` configuration classes. A single ``Container`` instance is built at
app startup and stashed on ``app.state``.
"""
from __future__ import annotations

from app.cache.web_search_cache import LocalWebSearchCache
from app.career.service import CareerRecommendationService
from app.config.settings import get_settings
from app.repository.dynamodb_client import create_dynamodb_client
from app.repository.previous_resume_data_repository import DynamoDbPreviousResumeDataRepository
from app.service.smart_parsing_client import OpenAiSmartParsingClient
from app.service.resume_file_parsing import OpenAiResumeFileParser, ResumeFileParsingService
from app.service.smart_parsing_metrics_logger import SmartParsingMetricsLogger
from app.service.smart_parsing_service import SmartParsingService
from app.trace.langsmith_tracer import LangSmithTracer
from app.vector.s3vectors_client import create_s3vectors_client
from app.vector.vector_context_service import VectorContextService
from app.vector.vector_embedder import VectorEmbedder
from app.vector.vector_search_service import VectorSearchService
from app.workflow.engine import StateGraphEngine
from app.workflow.nodes.data_node import DataNode
from app.workflow.nodes.evaluate_node import EvaluateNode
from app.workflow.nodes.reviser_node import ReviserNode
from app.workflow.nodes.schemer.client import OpenAiSchemerClient
from app.workflow.nodes.schemer_node import SchemerNode
from app.workflow.nodes.websearch_node import WebSearchNode


class Container:
    def __init__(self) -> None:
        self.settings = get_settings()

        # --- infra clients ---
        self.dynamodb_client = create_dynamodb_client(self.settings)
        self.s3vectors_client = create_s3vectors_client(self.settings)

        # --- repositories ---
        self.previous_resume_data_repository = DynamoDbPreviousResumeDataRepository(
            self.dynamodb_client, self.settings.dynamodb_tables
        )

        # --- vector search ---
        self.vector_embedder = VectorEmbedder()
        self.vector_search_service = VectorSearchService(self.s3vectors_client)
        self.vector_context_service = VectorContextService(
            self.vector_embedder, self.vector_search_service, self.previous_resume_data_repository
        )

        # --- cache / trace ---
        self.web_search_cache = LocalWebSearchCache()
        self.tracer = LangSmithTracer()

        # --- smart parsing ---
        self.smart_parsing_client = OpenAiSmartParsingClient()
        self.smart_parsing_metrics_logger = SmartParsingMetricsLogger()
        self.smart_parsing_service = SmartParsingService(
            self.smart_parsing_client, self.settings.smart_parsing, self.smart_parsing_metrics_logger
        )
        self.resume_file_parsing_service = ResumeFileParsingService(
            OpenAiResumeFileParser(
                self.settings.openai_api_key,
                self.settings.resume_file_parsing_model,
            )
        )

        # --- career recommendation ---
        self.career_service = CareerRecommendationService(
            previous_resume_data_repository=self.previous_resume_data_repository
        )

        # --- workflow nodes ---
        self.schemer_client = OpenAiSchemerClient()
        self.schemer_node = SchemerNode(self.schemer_client)
        self.web_search_node = WebSearchNode(self.web_search_cache)
        self.data_node = DataNode(self.previous_resume_data_repository)
        self.evaluate_node = EvaluateNode(self.vector_context_service)
        self.reviser_node = ReviserNode()

        self.state_graph_engine = StateGraphEngine(
            self.schemer_node,
            self.web_search_node,
            self.evaluate_node,
            self.reviser_node,
            self.data_node,
            self.tracer,
        )

    async def aclose(self) -> None:
        await self.career_service.aclose()
