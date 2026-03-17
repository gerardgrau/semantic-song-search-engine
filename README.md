# Semantic Song Search Engine

Semantic search engine for Viasona-oriented musical content, developed for the Engineering Projects course.

## Project objectives

This project aims to modernize a large-scale song and lyrics search experience by combining a fast traditional search engine with a semantic search pipeline.

### Main goals

- Reduce response time of the traditional search flow to under 1 second.
- Support partial queries and tolerate spelling mistakes.
- Enable semantic search in natural language.
- Support discovery by mood, theme, and song similarity.
- Prepare the system for personalized recommendations and playlist generation.
- Build a maintainable data pipeline for transforming raw source data into application-ready datasets.
- Use MariaDB as the structured relational database for the application layer.

### Functional scope

The platform is planned as a hybrid search system with two complementary engines:

1. **Classic search engine**
	- Fast retrieval over structured song metadata and lyrics.
	- Typo tolerance using classical similarity techniques such as Levenshtein distance.
	- Partial matching and efficient indexing strategies.

2. **Smart search engine**
	- Semantic retrieval based on embeddings and nearest-neighbour style search.
	- Natural-language querying.
	- Similar-song recommendations and emotion-oriented discovery.

### Technical direction

- **ETL in Python** to extract, clean, transform, and load source data.
- **MariaDB** for structured storage and application queries.
- **Custom vector-search-oriented components** for semantic retrieval experiments.
- **PyTorch-based ML experiments** for embedding and similarity models.
- **HTML, CSS, and Python backend integration** for a lightweight MVP frontend.

### Expected outcomes

- A usable prototype integrated around the Viasona search use case.
- A reproducible repository structure for ETL, backend, ML, frontend, and testing.
- A baseline for evaluating latency, usability, and semantic retrieval quality.