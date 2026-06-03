"""
Cross-Camera Matching Module — FAISS + Cosine Similarity.

Source: New_MCMT (best matching logic; identical algorithm in both projects,
New_MCMT has cleaner dual-strategy usage with adaptive thresholds).

Uses FAISS IndexFlatIP (inner product on L2-normalised vectors = cosine sim)
for fast approximate nearest-neighbour search with:
  - Temporal constraints (only match recent embeddings)
  - Adaptive thresholds (stricter for same-camera, looser for cross-camera)
  - Periodic index rebuild from the identity database
"""

import time
import numpy as np
import faiss
from config.config import Config


class CrossCameraMatcher:
    """
    FAISS-based cross-camera person matcher.

    Maintains a FAISS index of all known identity embeddings.
    When a new embedding arrives, queries for matches above the cosine
    similarity threshold within a temporal window.
    """

    def __init__(self):
        self.embedding_dim   = Config.REID_EMBEDDING_DIM
        self.temporal_window = Config.MATCH_TEMPORAL_WINDOW

        # Inner-product index on L2-normalised vectors == cosine similarity
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        # Metadata parallel to FAISS rows: (global_id, camera_id, timestamp)
        self.index_metadata: list = []

        if Config.FAISS_USE_GPU and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
            print("[Matcher] FAISS running on GPU")
        else:
            print("[Matcher] FAISS running on CPU")

        print(f"[Matcher] Thresholds  same-cam={Config.MATCH_THRESHOLD_SAME_CAM}  "
              f"diff-cam={Config.MATCH_THRESHOLD_DIFF_CAM}  "
              f"temporal={self.temporal_window}s")

    def query(self, embedding: np.ndarray, camera_id: int, top_k: int = 5) -> tuple:
        """
        Query the FAISS index for the best matching global ID.

        Args:
            embedding:  L2-normalised 512-D feature vector.
            camera_id:  Camera where the detection originates.
            top_k:      Number of nearest neighbours to inspect.

        Returns:
            (best_global_id, best_similarity) or (None, max_raw_sim).
        """
        if self.index.ntotal == 0:
            return None, 0.0

        query_vec = embedding.reshape(1, -1).astype(np.float32)
        k = min(top_k, self.index.ntotal)
        similarities, indices = self.index.search(query_vec, k)

        current_time   = time.time()
        best_global_id = None
        best_similarity= 0.0
        max_raw_sim    = 0.0

        for sim, idx in zip(similarities[0], indices[0]):
            if idx < 0:
                continue

            meta     = self.index_metadata[idx]
            time_diff= current_time - meta["timestamp"]

            if time_diff > self.temporal_window:
                continue   # stale embedding

            if sim > max_raw_sim:
                max_raw_sim = float(sim)

            # Adaptive threshold: stricter for same-camera to avoid false merges
            threshold = (Config.MATCH_THRESHOLD_SAME_CAM
                         if meta["camera_id"] == camera_id
                         else Config.MATCH_THRESHOLD_DIFF_CAM)

            if sim > best_similarity and sim >= threshold:
                best_similarity = float(sim)
                best_global_id  = meta["global_id"]

        if best_global_id is None:
            return None, max_raw_sim
        return best_global_id, best_similarity

    def add_embedding(self, embedding: np.ndarray, global_id: int, camera_id: int):
        """
        Add an embedding to the FAISS index.

        Args:
            embedding:  L2-normalised 512-D vector.
            global_id:  The global identity ID.
            camera_id:  Camera where the detection was made.
        """
        vec = embedding.reshape(1, -1).astype(np.float32)
        self.index.add(vec)
        self.index_metadata.append({
            "global_id": global_id,
            "camera_id": camera_id,
            "timestamp": time.time(),
        })

    def rebuild_index(self, identities: dict):
        """
        Rebuild the entire FAISS index from the global identity database.

        Called periodically (_rebuild_interval frames) to prune expired entries.

        Args:
            identities: Dict global_id → {'embedding_buffer': list of entry dicts}.
                        Each entry dict has keys 'embedding', 'camera_id', 'timestamp'.
        """
        self.index.reset()
        self.index_metadata.clear()

        current_time = time.time()
        for gid, identity in identities.items():
            for emb_entry in identity.get("embedding_buffer", []):
                if current_time - emb_entry["timestamp"] < Config.IDENTITY_EXPIRY_TIME:
                    vec = emb_entry["embedding"].reshape(1, -1).astype(np.float32)
                    self.index.add(vec)
                    self.index_metadata.append({
                        "global_id": gid,
                        "camera_id": emb_entry.get("camera_id", -1),
                        "timestamp": emb_entry["timestamp"],
                    })

    def get_index_size(self) -> int:
        """Return the number of vectors currently in the FAISS index."""
        return self.index.ntotal
