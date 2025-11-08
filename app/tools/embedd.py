import torch
import asyncio
import time
import platform # checking OS info
import logging

from typing import Tuple, List
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForMaskedLM, AutoTokenizer

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
  datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Automatic support for choosing device ---
@lru_cache(maxsize = 1)
def _get_compute_device() -> str:
  '''
  The system automatically detects and returns the optimal computing device.
  Returns:
    str: Name of the optimal computing device (e.g., 'cuda', 'mps', 'cpu').
  '''
  if torch.cuda.is_available():
    return 'cuda'
  if torch.backends.mps.is_available() and platform.system() == "Darwin":
    logger.info("MPS backend is available. Using 'mps' as the compute device.")
    return 'mps'

  logger.info("Using 'cpu' as the compute device.")
  return 'cpu'

# --- Func loading model ---
@lru_cache(maxsize = 1)
def _get_dense_embedder() -> SentenceTransformer:
  '''
  Load and cache the model 'all-MiniLM-L6-v2' for dense embedding.
  Returns:
    SentenceTransformer: The loaded SentenceTransformer model.
  '''
  device = _get_compute_device()
  logger.info(f"Loading 'all-MiniLM-L6-v2' model on device: {device}")
  model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device = device)
  logger.info('dense model completed loading.')
  return model

lru_cache(maxsize = 1)
def _get_sparse_embedder() -> Tuple[AutoTokenizer, AutoModelForMaskedLM]:
  '''
  Load and cache the model SPLADE 'naver/splade-cocondenser-ensembledistil' for sparse embedding.'
  '''
  device = _get_compute_device()
  logger.info(f"Loading 'naver/splade-cocondenser-ensembledistil' model on device: {device}")
  tokenizer = AutoTokenizer.from_pretrained('naver/splade-cocondenser-ensembledistil')
  model = AutoModelForMaskedLM.from_pretrained('naver/splade-cocondenser-ensembledistil')

  # Move the model to the chosen device
  model = model.to(device)

  # set the model to 'eval' mode (to disable dropout layers, etc.)
  model.eval()
  logger.info('sparse model completed loading.')
  return tokenizer, model

# --- Class tools for embedding ---
class EmbeddTools:
  '''
  The utility class contains static methods for calculating embedding vectors (dense, sparse, and hybrid).
  '''
  dense_embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
  sparse_embedding_model = "naver/splade-cocondenser-ensembledistil"

  @staticmethod
  def _compute_dense_vector_sync(texts: str) -> List[float]:
    '''
    [SYNC] caculate dense embedding vector
    '''
    start_time = time.perf_counter()
    try:
      embedder = _get_dense_embedder()

      # .encode() method is synchronous
      vector_np = embedder.encode(texts)

      # convert from numpy array to list
      vector_list = vector_np.tolist()

      latency_ms = (time.perf_counter() - start_time) * 1000
      logger.info(f"Dense embedding computed in {latency_ms:.2f} ms (len = {len(vector_list)})")

      return vector_list
    except Exception as e:
      latency_ms = (time.perf_counter() - start_time) * 1000
      logger.error(f"Dense embedding failed after {latency_ms:.2f} ms: {e}", exc_info=True)
      raise

  @staticmethod
  def _compute_sparse_vector_sync(text: str) -> Tuple[List[int], List[float]]:
    '''
    [SYNC] calculate sparse embedding vector
    '''
    start_time = time.perf_counter()
    try:
      tokenizer, embedder = _get_sparse_embedder()
      device = _get_compute_device()

      # Tokenize the input text
      tokens = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        max_length=512,
      ).to(device)

      # calculate the model output (logits)
      with torch.no_grad(): # disable gradient calculation for inference
        outputs = embedder(**tokens)

      logits, attention_mask = outputs.logits, tokens.attention_mask

      # Apply SPLADE transformations (log(1 + relu(logits)) * attention_mask)
      relu_log = torch.log(1 + torch.relu(logits))
      weighted_log = relu_log * attention_mask.unsqueeze(-1)

      # choose activation value maximum in the token dimension
      max_val, _ = torch.max(weighted_log, dim=1)
      vec = max_val.squeeze()

      # extract non-zero indices and values
      indices = vec.nonzero(as_tuple=True)[0]
      values = vec[indices]

      indices_list = indices.detach().cpu().tolist()
      values_list = values.detach().cpu().tolist()

      latency_ms = (time.perf_counter() - start_time) * 1000
      logger.info(f"Sparse embedding computed in {latency_ms:.2f} ms (indices = {len(indices_list)})")

      return indices_list, values_list

    except Exception as e:
      latency_ms = (time.perf_counter() - start_time) * 1000
      logger.error(f"Sparse embedding failed after {latency_ms:.2f} ms: {e}", exc_info=True)
      raise

  @staticmethod
  async def compute_dense_vector(text: str) -> List[float]:
    '''
    [ASYNC] Wrapper for computing dense embedding vector in another thread, avoid clogging the event loop..
    '''
    logger.debug(f"Feed 'compute_dense_vector' for '{text[:20]}...' to the thread pool")
    return await asyncio.to_thread(EmbeddTools._compute_dense_vector_sync, text)

  @staticmethod
  async def compute_sparse_vector(text: str) -> Tuple[List[int], List[float]]:
    '''
    [ASYNC] Wrapper for computing sparse embedding vector in another thread, avoid clogging the event loop..
    '''
    logger.debug(f"Feed 'compute_sparse_vector' for '{text[:20]}...' to the thread pool")
    return await asyncio.to_thread(EmbeddTools._compute_sparse_vector_sync, text)

  @staticmethod
  async def hybrid_embedd_query(text: str) -> Tuple[List[float], List[int], List[float]]:
    '''
    [ASYNC] Calculate both dense and sparse embedding vectors for hybrid search.
    Using asyncio.gather to run both embedding computations concurrently.
    Args:
      text (str): The input text to be embedded.
    '''
    start_time = time.perf_counter()
    logger.debug(f"Starting hybrid embedding for '{text[:20]}...'")

    try:
      # Create tasks
      dense_task = EmbeddTools.compute_dense_vector(text)
      sparse_task = EmbeddTools.compute_sparse_vector(text)

      # Excute 2 tasks, since both func used asyncio.to_thread => gather will run them on 2 diff threads
      dense_vector, (sparse_indices, sparse_values) = await asyncio.gather(dense_task, sparse_task)

      total_time = (time.perf_counter() - start_time) * 1000
      logger.info(f"Hybrid embedding computed in {total_time:.2f} ms (dense len={len(dense_vector)}, sparse indices={len(sparse_indices)})for text_len={len(text)})")

      return dense_vector, sparse_indices, sparse_values
    except Exception as e:
      total_time = (time.perf_counter() - start_time) * 1000
      logger.error(f"Hybrid embedding failed after {total_time:.2f} ms: {e}", exc_info=True)
      raise

  @staticmethod
  def get_embedd_dim() -> int:
    '''
    get the dim of dense vector embedd
    Returns:
      int: The dimension of the dense embedding vector.
    '''
    try:
      # load the model from cache, do not load again
      embedder = _get_dense_embedder()
      dim = embedder.get_sentence_embedding_dimension()
      logger.info(f"Dense embedding dimension: {dim}")
      return dim
    except Exception as e:
      logger.error(f"Failed to get embedding dimension: {e}", exc_info=True)
      raise

# # --- eg runing ---
# async def main():
#     """
#     Hàm main bất đồng bộ để chạy thử các chức năng embedding.
#     """
#     logger.info("--- Bắt đầu chạy thử nghiệm Embedding ---")

#     # Lấy số chiều
#     dim = EmbeddTools.get_embedding_dimension()
#     logger.info(f"Số chiều vector (dense): {dim}")

#     text1 = "Chào mừng bạn đến với AI."
#     text2 = "Hệ thống RAG là gì?"

#     # --- Chạy thử Hybrid (chạy song song) ---
#     logger.info("--- Chạy thử Hybrid Embedding (Song song) ---")
#     results = await asyncio.gather(
#         EmbeddTools.hybrid_embed_query(text1),
#         EmbeddTools.hybrid_embed_query(text2)
#     )

#     dense_vec_1, sparse_idx_1, sparse_val_1 = results[0]
#     logger.info(f"Kết quả Text 1: Dense len={len(dense_vec_1)}, Sparse non-zero={len(sparse_idx_1)}")

#     dense_vec_2, sparse_idx_2, sparse_val_2 = results[1]
#     logger.info(f"Kết quả Text 2: Dense len={len(dense_vec_2)}, Sparse non-zero={len(sparse_idx_2)}")

#     # --- Chạy thử riêng lẻ (để kiểm tra) ---
#     logger.info("--- Chạy thử Dense Embedding (Riêng lẻ) ---")
#     dense_only = await EmbeddTools.compute_dense_vector("Một câu test riêng lẻ.")
#     logger.info(f"Dense only len: {len(dense_only)}")

#     logger.info("--- Chạy thử Sparse Embedding (Riêng lẻ) ---")
#     sparse_only_idx, sparse_only_val = await EmbeddTools.compute_sparse_vector("Một câu test riêng lẻ khác.")
#     logger.info(f"Sparse only non-zero: {len(sparse_only_idx)}")

#     logger.info("--- Thử nghiệm hoàn tất ---")

# if __name__ == "__main__":
#     # Kích hoạt model tải lần đầu tiên
#     logger.info("Đang khởi tạo models (tải lần đầu)...")
#     _get_dense_embedder()
#     _get_sparse_embedder()
#     logger.info("Models đã sẵn sàng.")

#     # Chạy hàm main bất đồng bộ
#     asyncio.run(main())
