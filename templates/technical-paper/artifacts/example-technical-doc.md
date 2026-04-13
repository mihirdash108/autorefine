# Evaluation Methodology: Meridian Search Engine Relevance

## Introduction

This document describes the evaluation methodology used to assess search relevance in Meridian, a domain-specific search engine for legal documents. We measure how well Meridian retrieves relevant results compared to baseline keyword search across a corpus of 50,000 legal filings.

## Methodology

We constructed a benchmark of 200 queries sampled from anonymized user search logs. Each query was independently judged by three legal professionals who labeled the top 20 results as relevant, partially relevant, or not relevant. We computed NDCG@10 and MAP as primary metrics.

Meridian uses a hybrid retrieval approach combining sparse lexical matching with dense semantic embeddings. Results from both retrievers are fused using a learned ranking model. The system was compared against BM25 baseline and a commercial legal search product.

## Results

Meridian achieved an NDCG@10 of 0.74, compared to 0.58 for BM25 baseline and 0.69 for the commercial product. MAP scores were 0.68, 0.51, and 0.63 respectively. Performance improvements were most pronounced on long-tail queries where lexical matching alone fails to capture semantic intent.

On the 40 queries classified as "complex" (multi-clause, requiring cross-reference understanding), Meridian scored 0.71 NDCG@10 versus 0.42 for BM25, representing a 69% improvement.

## Reproduction

To reproduce these results, run the evaluation pipeline against the benchmark dataset using the standard configuration. The benchmark queries and relevance judgments are available upon request. Use the default model weights and retrieval parameters.

## Limitations

Results are specific to the legal domain and may not generalize to other verticals. The benchmark queries were sampled from a single organization's search logs and may not represent the full distribution of legal search needs.
