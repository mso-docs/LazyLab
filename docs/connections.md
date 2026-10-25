# Local and remote AI connections

The AI server can run on this machine or another reachable machine. In **New investigation → AI server connection**, set the endpoint and model. The same configuration is available through YAML and exported variables:

```bash
export OLLAMA_BASE_URL='https://your-ollama.example'
export OLLAMA_MODEL='model-installed-on-that-server'
```

The endpoint is contacted from the **app host**, not directly from the browser. It must implement Ollama's `/api/chat` structured JSON protocol; model discovery and weight identity use `/api/tags`. A URL path prefix is supported. HTTP and HTTPS are supported, with normal TLS certificate verification. For nonlocal use, choose a connection appropriate for your data and network; do not expose an unrestricted inference service as part of this app setup.

Experiments, datasets, reports and history stay on the app host. Planning and interpretation send the research question, hypotheses, allowed conditions, compact prior experiment specifications and measured result summaries to the selected AI endpoint. Raw dataset arrays are not included in the planning context.

This adapter does not support arbitrary OpenAI/Anthropic API formats, API-key headers or authenticated gateways. Account sign-in to SlothLab is separate from AI-server authentication. Configuring a remote AI endpoint does not move scientific execution to that server, publish the application, or create a cloud account.
