"""Google Gemini provider."""

from typing import Any, AsyncIterator

from .base import CompletionParams, LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini provider using google-generativeai SDK."""

    def __init__(
        self,
        api_key: str,
        client: Any | None = None,
    ):
        self.api_key = api_key
        self._client = client

    @property
    def client(self) -> Any:
        """Lazily construct the Google GenerativeAI client."""
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError as exc:
                raise ImportError(
                    "google-generativeai package is required to use GeminiProvider. "
                    "Install loom-agent with the gemini extra or add google-generativeai manually."
                ) from exc

            genai.configure(api_key=self.api_key)
            self._client = genai

        return self._client

    async def _complete(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> str:
        """Generate a completion through Google Gemini API."""
        resolved = params or CompletionParams()

        # Convert messages to Gemini format
        contents = self._convert_messages(messages)

        # Create model
        model = self.client.GenerativeModel(resolved.model)

        # Generate content
        response = await model.generate_content_async(
            contents,
            generation_config={
                "temperature": resolved.temperature,
                "max_output_tokens": resolved.max_tokens,
            }
        )

        # Extract text from response
        return self._extract_text(response)

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion chunks from Google Gemini API."""
        resolved = params or CompletionParams()

        # Convert messages to Gemini format
        contents = self._convert_messages(messages)

        # Create model
        model = self.client.GenerativeModel(resolved.model)

        # Stream content
        response = await model.generate_content_async(
            contents,
            generation_config={
                "temperature": resolved.temperature,
                "max_output_tokens": resolved.max_tokens,
            },
            stream=True
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    def _convert_messages(self, messages: list) -> list[dict[str, Any]]:
        """Convert generic chat messages to Gemini format.

        Gemini uses a different message format:
        - role: "user" or "model" (not "assistant")
        - parts: list of content parts
        - system messages are handled separately or prepended to first user message
        """
        system_parts: list[str] = []
        converted: list[dict[str, Any]] = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Collect system messages
            if role == "system":
                system_parts.append(content)
                continue

            # Convert role: "assistant" -> "model"
            gemini_role = "model" if role == "assistant" else "user"

            # Gemini uses "parts" instead of "content"
            converted.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

        # Prepend system messages to first user message if any
        if system_parts and converted:
            system_text = "\n\n".join(system_parts)
            first_msg = converted[0]
            if first_msg["role"] == "user":
                # Prepend system context to first user message
                first_msg["parts"] = [
                    {"text": f"{system_text}\n\n{first_msg['parts'][0]['text']}"}
                ]
            else:
                # Insert system as first user message
                converted.insert(0, {
                    "role": "user",
                    "parts": [{"text": system_text}]
                })

        return converted

    def _extract_text(self, response: Any) -> str:
        """Extract text from Gemini response."""
        try:
            # Gemini response has .text attribute
            if hasattr(response, "text"):
                return response.text.strip()

            # Fallback: try to get from candidates
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    parts = candidate.content.parts
                    text_parts = [part.text for part in parts if hasattr(part, "text")]
                    return "".join(text_parts).strip()

            return ""
        except Exception:
            return ""

