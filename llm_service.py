"""LLM service with optional Google (Gemini) integration.

This module supports three modes:
 - If `USE_GOOGLE_GEMINI` env var is set to `true`, it will attempt to call
   Vertex AI (Gemini) using the Google Cloud SDK.
 - Otherwise it falls back to a lightweight rule-based flow in
   `appointment_flow` (already implemented).

Setup instructions:
 - Install requirements: `pip install -r requirements.txt`
 - Set Google credentials and config if using Gemini:
     - `GOOGLE_APPLICATION_CREDENTIALS` → path to service account JSON
     - `GCP_PROJECT` → GCP project id
     - `GCP_LOCATION` → region (e.g. `us-central1`)
     - `GEMINI_MODEL` → model id (default: `gemini-2.5-pro`)
     - `USE_GOOGLE_GEMINI=true` to enable

Note: this is a best-effort adapter. API usage may require additional
permissions and updated client libraries depending on Google SDK versions.
"""

import os
from typing import Dict
import appointment_flow
import sequrity
import database

USE_GOOGLE = os.getenv("USE_GOOGLE_GEMINI", "false").lower() in ("1", "true", "yes")
GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


class ChatbotService:
    def __init__(self):
        self.google_available = False
        if USE_GOOGLE:
            try:
                # Import lazily to avoid hard dependency when not used
                from google.cloud import aiplatform
                # vertexai imports may be available through aiplatform
                # Initialize client (no-op if already initialized)
                if GCP_PROJECT:
                    aiplatform.init(project=GCP_PROJECT, location=GCP_LOCATION)
                self.aiplatform = aiplatform
                self.google_available = True
            except Exception as e:
                # If import fails, we'll fallback to local flow
                print("Google Vertex AI SDK not available or failed to init:", e)
                self.google_available = False

    def _call_gemini(self, user_message: str) -> str:
        """Call Gemini (Vertex AI) and return generated text.

        This function attempts to use the Vertex AI Python SDK. If the
        environment or SDK is not available it raises RuntimeError.
        """
        if not self.google_available:
            raise RuntimeError("Google Vertex AI SDK not initialized")

        # Best-effort use of aiplatform to call a generative model. The exact
        # API surface may vary by library version; adjust if needed.
        try:
            # Prefer the generative model client if available
            from google.cloud.aiplatform import gapic as aiplatform_gapic

            client = aiplatform_gapic.PredictionServiceClient()

            # Build the endpoint resource name for model predict (this is a
            # generic pattern; depending on model deployment this may vary)
            name = f"projects/{GCP_PROJECT}/locations/{GCP_LOCATION}/models/{GEMINI_MODEL}"

            # Construct a simple predict request payload using text input
            instance = {"content": user_message}
            request = {
                "endpoint": name,
                "instances": [instance],
            }

            # The low-level client expects a proper PredictRequest; using the
            # high-level wrapper may be preferable. We use try/except to guard
            response = client.predict(endpoint=name, instances=[instance])

            # Extract text from response (best-effort parsing)
            predictions = getattr(response, "predictions", None) or []
            if predictions:
                # Predictions may be list of dicts with 'content' or similar
                first = predictions[0]
                if isinstance(first, dict):
                    # Try common keys
                    for k in ("content", "text", "output"):
                        if k in first:
                            return first[k]
                    # Fallback to str conversion
                    return str(first)
                return str(first)

            return "Lo siento, no obtuve respuesta del modelo." 

        except Exception as e:
            # Surface error but allow fallback
            print("Error calling Gemini/Vertex AI:", e)
            raise

    def handle_chat(self, user_id: str, message: str) -> Dict:
        # Check prohibited words first
        for pal in sequrity.palabras_in:
            if pal in message.lower():
                return {
                    "reasoning": f"Palabra prohibida detectada: {pal}",
                    "to_user": sequrity.responses[0],
                    "data": None,
                    "action": None,
                    "is_faq_response": True,
                    "faq_similarity": 0.0,
                }

        # If Google is enabled and available, try Gemini
        if USE_GOOGLE and self.google_available:
            try:
                text = self._call_gemini(message)
                # Save to chat history
                database.add_message_to_chat(user_id, "user", message)
                database.add_message_to_chat(user_id, "assistant", text)

                return {
                    "reasoning": "Respuesta generada por Gemini",
                    "to_user": text,
                    "data": None,
                    "action": None,
                    "is_faq_response": False,
                }
            except Exception:
                # On error, fall through to local flow
                pass

        # Fallback: use rule-based appointment flow
        result = appointment_flow.process_message(user_id, message)
        # Persist chat
        database.add_message_to_chat(user_id, "user", message)
        database.add_message_to_chat(user_id, "assistant", result.get("reply", ""))

        return {
            "reasoning": "Generado por regla/flow",
            "to_user": result.get("reply", ""),
            "data": None,
            "action": None,
        }
