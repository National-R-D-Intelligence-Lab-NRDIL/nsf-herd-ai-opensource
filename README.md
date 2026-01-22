# nsf-herd-ai-opensource
# HERD AI Assistant - Open Source R&D

### Project Goal
Replicate the functionality of the Gemini-based MVP using Open Source models (Llama 3, Mistral, etc.) to evaluate performance and privacy trade-offs.

### Workflow (Strictly Follow)
1. **Local Setup:** - Ensure `.streamlit/secrets.toml` is in your `.gitignore`.
   - Use your own API keys/local model endpoints for testing.
2. **Development:**
   - Always create a new branch for work: `git checkout -b feature-name`
   - Do NOT push directly to `main`.
3. **Review Process:**
   - Push your branch to GitHub.
   - Open a **Pull Request (PR)**.
   - Tag @Kalyan8358 for review.
   - Do NOT merge the PR until it has been reviewed and discussed.

### Technical Stack
- Frontend: Streamlit
- Database: SQLite (data/herd.db)
- Inference: [RA to fill in - e.g., Ollama, vLLM, or HuggingFace]
