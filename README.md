# 42Gpt
To Run :
```bash
cd ./42Gpt-RetrievalPipeline
sh ./launch42Gpt.sh
```

## What is 42Gpt ?
Assistant Q/R pour les étudiants de 42 Paris, basé sur un wiki Markdown local.

## Goals
Répondre précisément aux questions étudiantes en s'appuyant uniquement sur la doc officielle, sans hallucination.

## Tech Stack
Python · Ollama (mistral) · Markdown · index.md comme retrieval (pas d'embeddings).

## Ingestion Pipeline
Récupère, met à jour, formate en `.md` et indexe les docs sources. 

## Retrieval Pipeline
2 appels LLM : (1) lit `index.md` → renvoie les paths pertinents, (2) lit les docs ciblés → produit la réponse finale.

## Lab
Monitoring, tests, auto-génération de Q/A pour évaluer la pipeline. (Placeholder.)
