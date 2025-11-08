import os
import json
import logging
import redis
from redis.exceptions import RedisError
from typing import Union, Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class RedisTools:
  '''
  a utility class for interacting with Redis, designed to configuration and metadata management.
  '''
  def __init__(self, client: redis.Redis):
    '''
    Initializes the RedisTool with a Redis client.
    Args:
      client (redis.Redis): An instance of the Redis client.
    Raise:
      TypeError: If the provided client is not an instance of redis.Redis.
    '''
    if not isinstance(client, redis.Redis):
      raise TypeError("client must be an instance of redis.Redis")
    self.client = client
    logger.info("RedisTool initialized with provided Redis client.")

  @staticmethod
  def _convert_value(value: str) -> Union[int, float, bool, str, None]:
    '''
    Convert value from string to appropriate type.
    This is private method.
    Args:
      value (str): The string value to convert.
    Returns:
      Union[int, float, bool, str, None]: The converted value.
    '''
    if not isinstance(value, str):
      return value

    low_val = value.lower()

    if low_val in ('none', 'null', ''):
      return None

    if low_val in ('true', "false"):
      return low_val == 'true'

    try:
      if '.' not in value and 'e' not in low_val:
        return int(value)
      return float(value)
    except ValueError:
      logger.debug(f"Value '{value}' is not a number, returning as string.")
      return value

  def add_key_value_to_hash(self, hash_name: str, key: str, value: Any) -> bool:
    '''
    Add a key-value pair to a Redis hash.
    value auto converted to string
    Args:
      hash_name (str): The name of the Redis hash.
      key (str): name feild into hash.
      value (Any): The value to add.
    Returns:
      bool: True if the operation was successful, False otherwise.
    '''

    try:
      str_value = str(value)
      self.client.hset(hash_name, key, str_value)
      logger.info(f"set HASH '{hash_name}' feild '{key}'")
      logger.debug(f"HASH '{hash_name} ['{key}'] = '{str_value}'")
      return True
    except RedisError as e:
      logger.error(f"Failed to set HASH '{hash_name}' feild '{key}': {e}", exc_info=True)
      return False

  def delete_collection(self, collection_name: str) -> bool:
    '''
    delete a collection from Redis
    Args:
      collection_name (srt): The name of the collection to delete.
    Returns:
      bool: True if the operation was successful, False otherwise.
    '''

    try:
      self.client.delete(collection_name)
      logger.info(f"Deleted collection '{collection_name}' from Redis.")
      return True
    except RedisError as e:
      logger.error(f"Failed to delete collection '{collection_name}': {e}", exc_info=True)
      return False

  def modify_value_in_hash(self, hash_name: str, key: str, new_value: Any) -> bool:
    '''
    Modify the value of an existing key in a Redis hash.
    if key not exist, nothing to do

    Args:
      hash_name (str): The name of the Redis hash.
      key (str): The key whose value is to be modified.
      new_value (Any): The new value to set.

    Returns:
      bool: True if the operation was successful, False otherwise.
    '''

    try:
      if self.client.hexists(hash_name, key):
        str_value = str(new_value)
        self.client.hset(hash_name, key, str_value)
        logger.info(f"Modified HASH '{hash_name}' feild '{key}'")
        logger.debug(f"HASH '{hash_name} ['{key}'] = '{str_value}'")
        return True
      else:
        logger.warning(f"Key '{key}' does not exist in HASH '{hash_name}'. No modification made.")
        return False
    except RedisError as e:
      logger.error(f"Failed to modify HASH '{hash_name}' feild '{key}': {e}", exc_info=True)
      return False

  def get_config(self, name: str) -> Optional[Dict[str, Any]]:
    '''
    Get configuration from Redis, supports string type or hash type.
    Args:
      name (str): The name of the configuration key or hash.
    Returns:
      Optional[Dict[str, Any]]: The configuration as a dictionary, or None if not found.
    Raise
      KeyError: if key name not found
      TypeError: if key name is neither string nor hash
    '''

    try:
      key_type = self.client.type(name)
      logger.debug(f"Key '{name}' has type: {key_type}")

      if key_type == "string":
        raw = self.client.get(name)
        if raw is None:
          raise KeyError(f"Key '{name}' not found in Redis.")

        try:
          return json.loads(raw)
        except json.JSONDecodeError:
          # if not json, reurn {value: raw_string}
          logger.debug(f"Key '{name}' is a plain string, not JSON.")
          return {'value': raw}
      elif key_type == "hash":
        data = self.client.hgetall(name)
        if not data:
          raise KeyError(f"Config '{name}' not found or is empty in Redis.")

        converted_data = {key: self._convert_value(value) for key, value in data.items()}

        logger.info(f"converted HASH config '{name}' with {len(converted_data)} fields.")

      elif key_type == "none":
        logger.warning(f"Key '{name}' does not exist in Redis.")
        raise KeyError(f"Key '{name}' not found in Redis.")
      else:
        logger.error(f"Key '{name}' has unsupported type: {key_type}")
        raise TypeError(f"Unsupported key type '{key_type}' for key '{name}'.")
    except RedisError as e:
      logger.error(f"Failed to get config '{name}': {e}", exc_info=True)
      return None

  def get_all_collections(self, pattern: str = "*") -> List[str]:
    '''
    Get all collection names from Redis matching a pattern.
    Args:
      pattern (str): The pattern to match collection names. Defaults to "*".
    Returns:
      List[str]: A list of collection names.
    '''
    try:
      keys = self.client.keys(pattern)
      logger.info(f"Retrieved {len(keys)} collections matching pattern '{pattern}'.")
      return keys
    except RedisError as e:
      logger.error(f"Failed to get collections with pattern '{pattern}': {e}", exc_info=True)
      return []




# # ===================================================================
# # PHẦN SCRIPT: CHẠY THỬ NGHIỆM
# # ===================================================================
# import sys
# from dotenv import load_dotenv

# def setup_logging():
#     """
#     Thiết lập logging cơ bản để in ra console cho mục đích chạy thử.
#     """
#     # Cấu hình logger gốc (root)
#     # logger được định nghĩa ở trên (logging.getLogger(__name__)) sẽ
#     # tự động sử dụng cấu hình này.
#     logging.basicConfig(
#         level=logging.INFO,  # Đặt mức log (có thể đổi thành DEBUG để xem chi tiết)
#         format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#         stream=sys.stdout, # In ra console
#     )
#     # Giảm bớt log ồn ào từ thư viện redis
#     logging.getLogger("redis").setLevel(logging.WARNING)

# def create_redis_client() -> Optional[redis.Redis]:
#     """
#     Hàm Factory: Tải .env, xác thực và tạo một Redis client.
#     """
#     load_dotenv() # Tải biến môi trường từ file .env

#     host = os.getenv("REDIS_HOST")
#     port_str = os.getenv("REDIS_PORT")
#     password = os.getenv("REDIS_PASSWORD")

#     # Xác thực các biến môi trường
#     if not all([host, port_str, password]):
#         logger.error("Thiếu các biến môi trường: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD")
#         return None

#     try:
#         port = int(port_str)
#     except ValueError:
#         logger.error(f"REDIS_PORT không hợp lệ: '{port_str}'. Phải là một số.")
#         return None

#     try:
#         # Khởi tạo client
#         client = redis.Redis(
#             host=host,
#             port=port,
#             username="default", # Bạn có thể đổi cái này thành os.getenv("REDIS_USER", "default")
#             password=password,
#             decode_responses=True # Rất quan trọng
#         )
#         # Kiểm tra kết nối
#         client.ping()
#         logger.info(f"Kết nối Redis tới {host}:{port} thành công.")
#         return client
#     except redis.exceptions.ConnectionError as e:
#         logger.error(f"Không thể kết nối tới Redis: {e}")
#         return None

# # Khối `if __name__ == "__main__":` đảm bảo rằng
# # code bên trong nó CHỈ CHẠY khi bạn thực thi file này trực tiếp.
# # Nó sẽ KHÔNG CHẠY khi file này được import bởi một file khác.
# if __name__ == "__main__":

#     # 1. Cài đặt logging
#     setup_logging()

#     # 2. Tạo client
#     # Sử dụng hàm logger gốc (root) vì logger của mô-đun
#     # có thể chưa được cấu hình
#     main_logger = logging.getLogger(__name__) # Lấy logger sau khi setup
#     main_logger.info("--- Bắt đầu Kịch bản Kiểm tra RedisTools ---")

#     redis_client = create_redis_client()

#     if redis_client:
#         # 3. "Tiêm" (inject) client vào lớp RedisTools
#         # Lưu ý: Chúng ta dùng trực tiếp `RedisTools` vì nó ở trong cùng file
#         tools = RedisTool(client=redis_client)

#         # 4. Sử dụng các phương thức

#         # --- Ví dụ về Hash ---
#         main_logger.info("\n--- Thử nghiệm Hash ---")
#         tools.add_key_value_to_hash("test_config", "timeout", 30)
#         tools.add_key_value_to_hash("test_config", "use_cache", "true")
#         tools.add_key_value_to_hash("test_config", "pi", 3.14159)
#         tools.add_key_value_to_hash("test_config", "greeting", "Xin chào")

#         config_data = tools.get_config("test_config")
#         main_logger.info(f"Lấy config 'test_config': {config_data}")

#         # Kiểm tra kiểu dữ liệu
#         if config_data:
#             main_logger.info(f"Kiểu của 'timeout': {type(config_data.get('timeout'))}")
#             main_logger.info(f"Kiểu của 'use_cache': {type(config_data.get('use_cache'))}")
#             main_logger.info(f"Kiểu của 'pi': {type(config_data.get('pi'))}")
#             main_logger.info(f"Kiểu của 'greeting': {type(config_data.get('greeting'))}")


#         tools.modify_value_in_hash("test_config", "timeout", 45)
#         tools.modify_value_in_hash("test_config", "key_khong_ton_tai", "test") # Sẽ báo warning

#         # --- Ví dụ về String (JSON) ---
#         main_logger.info("\n--- Thử nghiệm String/JSON ---")
#         json_string = '{"user_id": 123, "scopes": ["read", "write"]}'
#         # Dùng client gốc để set, vì RedisTools không có hàm set string
#         redis_client.set("test_json_config", json_string)

#         json_config = tools.get_config("test_json_config")
#         main_logger.info(f"Lấy config 'test_json_config': {json_config}")
#         if json_config:
#             main_logger.info(f"Kiểu của 'scopes': {type(json_config.get('scopes'))}")

#         # --- Thử nghiệm lỗi ---
#         main_logger.info("\n--- Thử nghiệm Lỗi (Mong đợi Cảnh báo) ---")
#         tools.get_config("key_khong_he_ton_tai") # Sẽ log lỗi

#         # --- Dọn dẹp ---
#         main_logger.info("\n--- Dọn dẹp ---")
#         tools.delete_collection("test_config")
#         tools.delete_collection("test_json_config")

#         main_logger.info("\n--- Kịch bản Kiểm tra Hoàn tất ---")

#         # Đóng kết nối
#         redis_client.close()
#         main_logger.info("Đã đóng kết nối Redis.")
#     else:
#         main_logger.error("Không thể khởi tạo client. Hủy bỏ kiểm tra.")