"""
Global Identity Database Module.

Source: Updated_AI_Engine_v2 / New_MCMT (best identity management logic).

Key advantage over previous version:
  - IdentityRecord.get_best_match_score() compares against EVERY buffered
    embedding and returns the maximum — more robust than average-only matching
    for identities seen in varying poses / lighting.
  - Dual-strategy matching in main.py / inference_runner.py (FAISS fast +
    DB robust) uses this.
  - is_expired() respects IDENTITY_EXPIRY_TIME (previously disabled).

Maintains a centralized, thread-safe database of all known person identities.
Each identity stores:
    - Global ID (unique, monotonically increasing)
    - Rolling buffer of recent embeddings (Multi-Embedding Buffer)
    - Camera-wise tracking history
    - Timestamps for temporal constraint enforcement
"""

import time
import threading
import numpy as np
from collections import deque
from ai_pipeline.ai_config.config import Config


class IdentityRecord:
    """
    Single globally-tracked person identity.

    Maintains a rolling buffer of the last MAX_EMBEDDINGS_PER_IDENTITY embeddings
    for robust matching via both average and best-match strategies.
    """

    def __init__(self, global_id: int, embedding: np.ndarray, camera_id: int):
        self.global_id   = global_id
        self.created_at  = time.time()
        self.last_seen   = time.time()

        # Multi-Embedding Buffer
        self.embedding_buffer: deque = deque(maxlen=Config.MAX_EMBEDDINGS_PER_IDENTITY)
        self.embedding_buffer.append({
            "embedding": embedding,
            "camera_id": camera_id,
            "timestamp": time.time(),
        })

        # Running L2-normalised average embedding (updated on each addition)
        self._avg_embedding = embedding.copy()

        # Camera-wise tracking history: {camera_id: [(track_id, timestamp), ...]}
        self.camera_history: dict = {}
        self.update_camera_history(camera_id, -1)

        self.total_sightings = 1
        self.cameras_seen: set = {camera_id}

    def add_embedding(self, embedding: np.ndarray, camera_id: int):
        """
        Add a new embedding to the rolling buffer and update the running average.

        Args:
            embedding:  L2-normalised 512-D vector.
            camera_id:  Camera where this was observed.
        """
        self.embedding_buffer.append({
            "embedding": embedding,
            "camera_id": camera_id,
            "timestamp": time.time(),
        })
        self.last_seen       = time.time()
        self.total_sightings += 1
        self.cameras_seen.add(camera_id)

        # Recompute running average and renormalize
        all_embs = [e["embedding"] for e in self.embedding_buffer]
        avg = np.mean(all_embs, axis=0)
        norm = np.linalg.norm(avg)
        self._avg_embedding = avg / norm if norm > 0 else avg

    def get_average_embedding(self) -> np.ndarray:
        """Return the L2-normalised average of all buffered embeddings."""
        return self._avg_embedding

    def get_best_match_score(self, query_embedding: np.ndarray) -> float:
        """
        Best cosine similarity between the query and every buffered embedding.

        More robust than average-only matching — a single clear sighting
        at a different angle or lighting can still produce a strong score.

        Args:
            query_embedding: L2-normalised 512-D vector.

        Returns:
            Maximum cosine similarity across all buffered embeddings.
        """
        best_score = 0.0
        for entry in self.embedding_buffer:
            score = float(np.dot(query_embedding, entry["embedding"]))
            if score > best_score:
                best_score = score
        return best_score

    def update_camera_history(self, camera_id: int, track_id):
        """Record that this identity was seen in a specific camera."""
        if camera_id not in self.camera_history:
            self.camera_history[camera_id] = []
        self.camera_history[camera_id].append((track_id, time.time()))

    def is_expired(self) -> bool:
        """Check if this identity has not been seen for too long."""
        return (time.time() - self.last_seen) > Config.IDENTITY_EXPIRY_TIME

    def to_dict(self) -> dict:
        """Serialise to dict for logging / stats output."""
        return {
            "global_id":       self.global_id,
            "created_at":      self.created_at,
            "last_seen":       self.last_seen,
            "total_sightings": self.total_sightings,
            "cameras_seen":    list(self.cameras_seen),
            "embedding_count": len(self.embedding_buffer),
        }


class GlobalIdentityDatabase:
    """
    Thread-safe global identity database.

    Provides:
        - Register new identities
        - Match query embeddings against all known identities
          (using best-match-in-buffer + adaptive threshold)
        - Update existing identities with new embeddings
        - Prune expired identities
    """

    def __init__(self):
        self._lock         = threading.Lock()
        self._identities: dict = {}          # global_id → IdentityRecord
        self._next_global_id = 1

        # Fast lookup: (camera_id, track_id_str) → global_id
        self._track_to_global: dict = {}

        print("[IdentityDB] Global identity database initialised")

    def register_new_identity(
        self,
        embedding: np.ndarray,
        camera_id: int,
        track_id,
    ) -> int:
        """
        Create a new global identity.

        Args:
            embedding:  L2-normalised 512-D feature vector.
            camera_id:  Camera where the person was first seen.
            track_id:   Local track ID (str after normalisation in callers).

        Returns:
            The newly assigned global ID.
        """
        with self._lock:
            gid = self._next_global_id
            self._next_global_id += 1

            self._identities[gid] = IdentityRecord(gid, embedding, camera_id)
            self._track_to_global[(camera_id, track_id)] = gid
            return gid

    def update_identity(
        self,
        global_id: int,
        embedding: np.ndarray,
        camera_id: int,
        track_id,
    ):
        """
        Update an existing identity with a new embedding observation.

        Args:
            global_id:  The global ID to update.
            embedding:  New L2-normalised embedding.
            camera_id:  Camera where observed.
            track_id:   Local track ID.
        """
        with self._lock:
            if global_id in self._identities:
                record = self._identities[global_id]
                record.add_embedding(embedding, camera_id)
                record.update_camera_history(camera_id, track_id)
                self._track_to_global[(camera_id, track_id)] = global_id

    def find_match(
        self,
        embedding: np.ndarray,
        camera_id: int,
        exclude_global_id: int = None,
    ) -> tuple:
        """
        Find the best matching identity using direct buffer comparison.

        This is the robust complement to FAISS matching (strategy 2).
        Uses best-match-in-buffer and adaptive thresholds.

        Args:
            embedding:          L2-normalised query embedding.
            camera_id:          Camera where the detection occurred.
            exclude_global_id:  Skip this ID (avoid self-matching).

        Returns:
            (best_global_id, best_score) or (None, max_raw_score).
        """
        with self._lock:
            best_gid      = None
            best_score    = 0.0
            max_raw_score = 0.0
            current_time  = time.time()

            for gid, record in self._identities.items():
                if gid == exclude_global_id:
                    continue

                # Temporal constraint
                if (current_time - record.last_seen) > Config.MATCH_TEMPORAL_WINDOW:
                    continue

                score = record.get_best_match_score(embedding)

                if score > max_raw_score:
                    max_raw_score = score

                # Adaptive threshold
                threshold = (Config.MATCH_THRESHOLD_SAME_CAM
                             if camera_id in record.cameras_seen
                             else Config.MATCH_THRESHOLD_DIFF_CAM)

                if score > best_score and score >= threshold:
                    best_score = score
                    best_gid   = gid

            if best_gid is None:
                return None, max_raw_score
            return best_gid, best_score

    def get_global_id_for_track(self, camera_id: int, track_id) -> int:
        """
        Look up the global ID assigned to a (camera_id, track_id) pair.

        Args:
            track_id: Must be a str (normalised by callers with str()).

        Returns:
            Global ID or None if not yet assigned.
        """
        with self._lock:
            return self._track_to_global.get((camera_id, track_id))

    def get_identity(self, global_id: int):
        """Get an IdentityRecord by global ID."""
        with self._lock:
            return self._identities.get(global_id)

    def get_all_identities(self) -> dict:
        """Return a snapshot copy of all identity records."""
        with self._lock:
            return dict(self._identities)

    def prune_expired(self) -> int:
        """
        Remove expired identities and clean up track mappings.

        Returns:
            Number of identities removed.
        """
        with self._lock:
            expired_ids = [
                gid for gid, rec in self._identities.items() if rec.is_expired()
            ]
            for gid in expired_ids:
                del self._identities[gid]
                keys = [k for k, v in self._track_to_global.items() if v == gid]
                for k in keys:
                    del self._track_to_global[k]

            if expired_ids:
                print(f"[IdentityDB] Pruned {len(expired_ids)} expired identities")
            return len(expired_ids)

    def get_stats(self) -> dict:
        """Return database statistics."""
        with self._lock:
            return {
                "total_identities": len(self._identities),
                "active_tracks":    len(self._track_to_global),
                "next_global_id":   self._next_global_id,
            }
