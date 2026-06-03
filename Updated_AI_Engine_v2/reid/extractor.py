"""
Person Re-Identification Module — OSNet-AIN (via torchreid).

Source: New_MCMT (best ReID logic).

Key improvements over baseline OSNet:
  - osnet_ain_x1_0: Attentive Instance Normalization makes embeddings robust
    to cross-camera lighting and domain shifts — critical for multi-camera ReID.
  - Mean-centering before L2 normalization converts cosine similarity into
    Pearson correlation, reducing the effect of style biases.
  - Supports single and batch extraction with GPU acceleration.
  - MobileNetV3 fallback when torchreid is not installed.
"""

import numpy as np
import cv2
import torch
import torch.nn.functional as F
from torchvision import transforms
from config.config import Config

try:
    import torchreid
    TORCHREID_AVAILABLE = True
except ImportError:
    TORCHREID_AVAILABLE = False
    print("[ReID] WARNING: torchreid not installed. "
          "Install with: pip install torchreid")


class ReIDExtractor:
    """
    OSNet-AIN feature extractor for cross-camera person re-identification.

    Produces L2-normalized 512-D embeddings from person crop images.
    """

    def __init__(self):
        """
        Initialise the OSNet-AIN model.
        Pretrained ImageNet weights are downloaded automatically on first run.
        """
        self.device        = Config.DEVICE
        self.input_size    = Config.REID_INPUT_SIZE   # (H, W) = (256, 128)
        self.embedding_dim = Config.REID_EMBEDDING_DIM
        self.batch_size    = Config.REID_BATCH_SIZE
        self.use_fallback_slice = False

        if TORCHREID_AVAILABLE:
            self._init_torchreid()
        else:
            self._init_fallback()

        # ImageNet normalization (torchreid pretrained convention)
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(self.input_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        print(f"[ReID] {Config.REID_MODEL_NAME} loaded on {self.device}, "
              f"embedding_dim={self.embedding_dim}")

    def _init_torchreid(self):
        """Initialise OSNet-AIN via torchreid library."""
        self.model = torchreid.models.build_model(
            name=Config.REID_MODEL_NAME,   # osnet_ain_x1_0
            num_classes=1000,              # not used for feature extraction
            pretrained=True,
        )
        self.model = self.model.to(self.device)
        self.model.eval()

    def _init_fallback(self):
        """
        Fallback: MobileNetV3-small as lightweight feature extractor
        when torchreid is unavailable. Slices output to 512-D.
        """
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
        print("[ReID] Using MobileNetV3-small fallback (torchreid not available)")

        backbone = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
        backbone.classifier = torch.nn.Identity()
        self.model = backbone.to(self.device)
        self.model.eval()
        self.use_fallback_slice = True

    def crop_person(self, frame: np.ndarray, bbox: list) -> np.ndarray:
        """
        Crop a person from the frame using a bounding box.

        Applies boundary clamping and enforces a minimum crop size.

        Args:
            frame: Full BGR frame.
            bbox:  [x1, y1, x2, y2] bounding box.

        Returns:
            Cropped BGR image, or None if the crop is too small.
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        x1 = max(0, x1);  y1 = max(0, y1)
        x2 = min(w, x2);  y2 = min(h, y2)

        if (x2 - x1) < 20 or (y2 - y1) < 40:
            return None

        crop = frame[y1:y2, x1:x2]
        return crop if crop.size > 0 else None

    @torch.no_grad()
    def extract_single(self, crop: np.ndarray):
        """
        Extract a feature embedding from a single person crop.

        Args:
            crop: BGR person crop image.

        Returns:
            L2-normalized 512-D embedding (np.ndarray), or None on failure.
        """
        if crop is None or crop.size == 0:
            return None

        try:
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            tensor = self.transform(rgb).unsqueeze(0).to(self.device)

            features = self.model(tensor)
            if self.use_fallback_slice:
                features = features[:, :self.embedding_dim]

            # Mean-center → L2 normalize (Pearson correlation, removes style bias)
            features = features - features.mean(dim=1, keepdim=True)
            features = F.normalize(features, p=2, dim=1)

            return features.cpu().numpy().flatten()
        except Exception as e:
            print(f"[ReID] Extraction error: {e}")
            return None

    @torch.no_grad()
    def extract_batch(self, crops: list) -> list:
        """
        Extract feature embeddings from a batch of person crops.

        Args:
            crops: List of BGR person crop images (may contain None).

        Returns:
            List of L2-normalized 512-D embeddings; None for failed crops.
        """
        if not crops:
            return []

        tensors      = []
        valid_indices= []

        for i, crop in enumerate(crops):
            if crop is None or crop.size == 0:
                continue
            try:
                rgb    = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                tensor = self.transform(rgb)
                tensors.append(tensor)
                valid_indices.append(i)
            except Exception:
                continue

        if not tensors:
            return [None] * len(crops)

        results = [None] * len(crops)

        for start in range(0, len(tensors), self.batch_size):
            end   = min(start + self.batch_size, len(tensors))
            batch = torch.stack(tensors[start:end]).to(self.device)

            features = self.model(batch)
            if self.use_fallback_slice:
                features = features[:, :self.embedding_dim]

            # Mean-center → L2 normalize
            features = features - features.mean(dim=1, keepdim=True)
            features = F.normalize(features, p=2, dim=1)
            features_np = features.cpu().numpy()

            for j, feat in enumerate(features_np):
                results[valid_indices[start + j]] = feat

        return results
