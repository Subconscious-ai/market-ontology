Full path 
  ~/subconscious-ai/
  ├── spice-harvester/        ← ~/.hermes/clude-harvester/ (still there; move when convenient)
  │                             github.com/Subconscious-ai/spice-harvester
  │                             • ingest / query / lint / interview / interview-merge
  │                             • docs/INTEGRATION.md ← points at market-ontology
  │
  ├── market-ontology/        ← new, at ~/subconscious-ai/market-ontology/
  │                             github.com/Subconscious-ai/market-ontology
  │                             • @subconscious-ai/market-ontology (npm)
  │                             • market-ontology (PyPI when published)
  │                             • shared source of truth for the POC schema
  │
  └── ai-chatbot/             ← your existing Vercel repo; clone here when ready
                                 depends on @subconscious-ai/market-ontology
                                 reads spice-harvester's output/<slug>/wiki/
                                 writes interview answers back via subprocess

  Everything the ai-chatbot team can now build against

  1. Shared types — pnpm add @subconscious-ai/market-ontology once published, or local path dep before that.
  2. Trigger ingest — bash /path/to/spice-harvester/run.sh <email> from an API route.
  3. Tail progress — SSE off output/<slug>/wiki/log.md (pattern in docs/INTEGRATION.md).
  4. Read wiki — the 7 category pages + ontology.json for chat context.
  5. Write interview answers — bash /path/to/spice-harvester/run.sh <email> --interview '{...json...}' per executive turn, then --interview-merge every N answers to upgrade the
  ontology.
