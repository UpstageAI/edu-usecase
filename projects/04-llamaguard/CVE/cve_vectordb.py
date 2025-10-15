#!/usr/bin/env python3
"""
CVE Vector Database
Creates and manages a FAISS-based vector database for CVE data with RAG capabilities.
"""

import numpy as np
import faiss
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CVEEntry:
    """Represents a single CVE entry."""
    cve_id: str
    text: str
    metadata: Dict


class CVEVectorDB:
    """Vector database for CVE data using FAISS."""

    def __init__(self, embedding_dim: int = 384):
        """
        Initialize CVE vector database.

        Args:
            embedding_dim: Dimension of embedding vectors (default: 384 for sentence-transformers)
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.cve_entries: List[CVEEntry] = []
        self.embedder = None

    def _init_embedder(self):
        """Initialize the embedding model."""
        if self.embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                print("Loading sentence transformer model...")
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                print("Model loaded successfully")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )

    def load_from_text_file(self, file_path: str):
        """
        Load CVE data from plain text file.

        Args:
            file_path: Path to CVE text file
        """
        print(f"Loading CVE data from {file_path}...")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split by separator
        entries = content.split("=" * 80)

        # Skip header (first entry)
        for entry in entries[1:]:
            entry = entry.strip()
            if not entry:
                continue

            # Parse entry
            cve_entry = self._parse_cve_entry(entry)
            if cve_entry:
                self.cve_entries.append(cve_entry)

        print(f"Loaded {len(self.cve_entries)} CVE entries")

    def _parse_cve_entry(self, text: str) -> Optional[CVEEntry]:
        """
        Parse a single CVE entry from text.

        Args:
            text: CVE entry text

        Returns:
            CVEEntry object or None if parsing fails
        """
        lines = text.strip().split('\n')
        if not lines:
            return None

        metadata = {}
        cve_id = "UNKNOWN"

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if key == "CVE ID":
                    cve_id = value
                    metadata['cve_id'] = value
                elif key == "Published":
                    metadata['published'] = value
                elif key == "Modified":
                    metadata['modified'] = value
                elif key == "CVSS Score":
                    metadata['cvss'] = value
                elif key == "CWE":
                    metadata['cwe'] = value
                elif key == "Description":
                    metadata['description'] = value

        return CVEEntry(cve_id=cve_id, text=text, metadata=metadata)

    def build_index(self, use_gpu: bool = False):
        """
        Build FAISS index from loaded CVE entries.

        Args:
            use_gpu: Whether to use GPU for indexing (requires faiss-gpu)
        """
        if not self.cve_entries:
            raise ValueError("No CVE entries loaded. Call load_from_text_file first.")

        self._init_embedder()

        print("Generating embeddings...")
        texts = [entry.text for entry in self.cve_entries]

        # Generate embeddings in batches
        batch_size = 32
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.embedder.encode(
                batch,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            embeddings.append(batch_embeddings)

        embeddings = np.vstack(embeddings).astype('float32')
        print(f"Generated embeddings with shape: {embeddings.shape}")

        # Create FAISS index
        print("Building FAISS index...")
        if use_gpu:
            # Use GPU index
            res = faiss.StandardGpuResources()
            self.index = faiss.GpuIndexFlatIP(res, self.embedding_dim)
        else:
            # Use CPU index with inner product (cosine similarity)
            self.index = faiss.IndexFlatIP(self.embedding_dim)

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Add to index
        self.index.add(embeddings)
        print(f"Index built with {self.index.ntotal} vectors")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[CVEEntry, float]]:
        """
        Search for similar CVEs using natural language query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (CVEEntry, score) tuples
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index first.")

        if self.embedder is None:
            self._init_embedder()

        # Encode query
        query_embedding = self.embedder.encode(
            [query],
            convert_to_numpy=True
        ).astype('float32')

        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(query_embedding, top_k)

        # Return results
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < len(self.cve_entries):
                results.append((self.cve_entries[idx], float(score)))

        return results

    def save(self, index_path: str, data_path: str):
        """
        Save index and data to disk.

        Args:
            index_path: Path to save FAISS index
            data_path: Path to save CVE entries
        """
        if self.index is None:
            raise ValueError("No index to save")

        print(f"Saving index to {index_path}...")
        faiss.write_index(self.index, index_path)

        print(f"Saving data to {data_path}...")
        with open(data_path, 'wb') as f:
            pickle.dump(self.cve_entries, f)

        print("Save complete")

    def load(self, index_path: str, data_path: str, use_gpu: bool = False):
        """
        Load index and data from disk.

        Args:
            index_path: Path to FAISS index
            data_path: Path to CVE entries
            use_gpu: Whether to use GPU
        """
        print(f"Loading index from {index_path}...")
        self.index = faiss.read_index(index_path)

        if use_gpu:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, self.index)

        print(f"Loading data from {data_path}...")
        with open(data_path, 'rb') as f:
            self.cve_entries = pickle.load(f)

        print(f"Loaded {len(self.cve_entries)} CVE entries")

    def get_cve_by_id(self, cve_id: str) -> Optional[CVEEntry]:
        """
        Get CVE entry by ID.

        Args:
            cve_id: CVE identifier (e.g., CVE-2021-44228)

        Returns:
            CVEEntry or None if not found
        """
        for entry in self.cve_entries:
            if entry.cve_id == cve_id:
                return entry
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build CVE vector database")
    parser.add_argument(
        "--input", "-i",
        default="cve_database.txt",
        help="Input CVE text file (default: cve_database.txt)"
    )
    parser.add_argument(
        "--index-output", "-o",
        default="cve_index.faiss",
        help="Output FAISS index file (default: cve_index.faiss)"
    )
    parser.add_argument(
        "--data-output", "-d",
        default="cve_data.pkl",
        help="Output CVE data file (default: cve_data.pkl)"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU for indexing"
    )

    args = parser.parse_args()

    # Create and build vector database
    db = CVEVectorDB()
    db.load_from_text_file(args.input)
    db.build_index(use_gpu=args.gpu)
    db.save(args.index_output, args.data_output)

    print("\nVector database created successfully!")
    print(f"To search, use:")
    print(f"  from cve_vectordb import CVEVectorDB")
    print(f"  db = CVEVectorDB()")
    print(f"  db.load('{args.index_output}', '{args.data_output}')")
    print(f"  results = db.search('SQL injection vulnerability')")
