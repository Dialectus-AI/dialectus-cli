"""HTTP client for communicating with Dialectus Engine API."""

import json
import logging
from typing import Any, TYPE_CHECKING, TypedDict

import httpx
import websockets
from websockets.exceptions import ConnectionClosed
from pydantic import BaseModel

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection


class ModelProviderConfig(TypedDict):
    """Configuration for a model provider (simplified for timeout detection)."""
    provider: str


class FullModelConfig(TypedDict):
    """Complete model configuration for debate setup (matches web interface ModelInfo)."""
    name: str
    provider: str
    personality: str
    max_tokens: int
    temperature: float

logger = logging.getLogger(__name__)


class DebateSetupRequest(BaseModel):
    """Request model for debate setup."""

    topic: str
    format: str
    word_limit: int
    models: dict[str, FullModelConfig]
    judge_models: list[str]
    judge_provider: str


class DebateResponse(BaseModel):
    """Response model for debate creation."""

    id: str
    status: str
    config: dict[str, object] | None = None


class ApiClient:
    """HTTP client for Dialectus Engine API."""

    def __init__(
        self,
        base_url: str,
        models_config: dict[str, ModelProviderConfig] | None = None,
        http_timeout_local: float = 120.0,
        http_timeout_remote: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")

        # Determine appropriate timeout based on model providers
        timeout = self._determine_timeout(
            models_config, http_timeout_local, http_timeout_remote
        )
        self.client = httpx.AsyncClient(timeout=timeout)

    def _determine_timeout(
        self,
        models_config: dict[str, ModelProviderConfig] | None,
        timeout_local: float,
        timeout_remote: float,
    ) -> float:
        """Determine appropriate timeout based on model providers."""
        if not models_config:
            return timeout_remote  # Default to remote timeout

        # Check if any models use Ollama (local provider)
        has_ollama = any(
            model_config["provider"] == "ollama"
            for model_config in models_config.values()
        )

        return timeout_local if has_ollama else timeout_remote

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_models(self) -> list[str]:
        """Get available models from the API."""
        response = await self.client.get(f"{self.base_url}/api/models")
        response.raise_for_status()
        data = response.json()
        return data["models"]

    async def create_debate(self, setup: DebateSetupRequest) -> DebateResponse:
        """Create a new debate."""
        response = await self.client.post(
            f"{self.base_url}/api/debates", json=setup.model_dump()
        )
        response.raise_for_status()
        data = response.json()
        return DebateResponse(**data)

    async def start_debate(self, debate_id: str) -> None:
        """Start a debate."""
        response = await self.client.post(
            f"{self.base_url}/api/debates/{debate_id}/start"
        )
        response.raise_for_status()

    async def get_debate_status(self, debate_id: str) -> dict[str, Any]:
        """Get debate status."""
        response = await self.client.get(f"{self.base_url}/api/debates/{debate_id}")
        response.raise_for_status()
        return response.json()

    async def get_debate_transcript(self, debate_id: str) -> dict[str, Any]:
        """Get debate transcript."""
        response = await self.client.get(
            f"{self.base_url}/api/debates/{debate_id}/transcript"
        )
        response.raise_for_status()
        return response.json()

    async def get_transcripts(self, page: int = 1, limit: int = 20) -> dict[str, Any]:
        """Get paginated list of saved transcripts."""
        response = await self.client.get(
            f"{self.base_url}/api/transcripts", params={"page": page, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def get_transcript_by_id(self, transcript_id: int) -> dict[str, Any]:
        """Get a specific transcript by ID."""
        response = await self.client.get(
            f"{self.base_url}/api/transcripts/{transcript_id}"
        )
        response.raise_for_status()
        return response.json()


class DebateStreamHandler:
    """Handle WebSocket debate streaming."""

    def __init__(
        self,
        base_url: str,
        debate_id: str,
        websocket_timeout: float = 60.0,
        message_callback=None,
        judge_callback=None,
    ) -> None:
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.debate_id = debate_id
        self.websocket_timeout = websocket_timeout
        self.websocket: ClientConnection | None = None
        self.messages: list[dict[str, Any]] = []
        self.judge_decision: dict[str, Any] | None = None
        self.is_complete = False
        self.message_callback = message_callback
        self.judge_callback = judge_callback

    async def connect_and_stream(self) -> None:
        """Connect to WebSocket and stream debate messages."""
        uri = f"{self.ws_url}/ws/debate/{self.debate_id}"

        try:
            # Configure WebSocket with configurable timeout
            async with websockets.connect(
                uri,
                open_timeout=self.websocket_timeout,  # Configurable handshake timeout
                close_timeout=10,  # 10 seconds for close
                ping_interval=30,  # Send ping every 30 seconds
                ping_timeout=15,  # Wait 15 seconds for pong
            ) as websocket:
                self.websocket = websocket
                logger.info(f"Connected to debate stream: {self.debate_id}")

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_message(data)

                        if self.is_complete:
                            break

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received: {message}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")

        except ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        message_type = data.get("type")
        logger.debug(f"Received WebSocket message: {message_type}")

        if message_type == "new_message":
            message = data["message"]
            self.messages.append(message)

            # Call real-time callback if provided
            if self.message_callback:
                self.message_callback(message)

        elif message_type == "judge_decision":
            self.judge_decision = data["decision"]
            logger.info("Judge decision received")

            # Call judge callback if provided
            if self.judge_callback:
                logger.info("Calling judge callback")
                self.judge_callback(self.judge_decision)
            else:
                logger.warning("Judge decision received but no callback set")

        elif message_type == "judging_started":
            logger.info("Judging phase started")

        elif message_type == "model_error":
            error_msg = data.get("error", "Unknown model error")
            speaker_id = data.get("speaker_id", "unknown")
            model_name = data.get("model_name", "unknown")
            provider = data.get("provider", "unknown")
            phase = data.get("phase", "unknown")
            exception_type = data.get("exception_type", "Exception")
            exception_message = data.get("exception_message", "")

            logger.error(
                f"MODEL ERROR: {speaker_id} ({model_name}) via {provider} failed in {phase}: {exception_type}: {exception_message}"
            )

            # This should cause the debate to fail immediately
            raise RuntimeError(f"Model failed: {error_msg}")

        elif message_type == "judge_error":
            error_msg = data.get("error", "Unknown judge error")
            logger.error(f"Judge error: {error_msg}")

            # This should cause the debate to fail immediately
            raise RuntimeError(f"Judge failed: {error_msg}")

        elif message_type == "debate_completed":
            self.is_complete = True
            logger.info("Debate completed")

        else:
            logger.debug(f"Unknown message type: {message_type}")
