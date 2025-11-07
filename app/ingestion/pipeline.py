import logging
from .loader import CSVLoader
from .cleaner import CSVCleaner

from typing import List, Dict, Any

class IngestionPipeline:
  def __init__(self, loader: CSVLoader, cleaner: CSVCleaner):
    self.loader = loader
    self.cleaner = cleaner

    logging.info('IngestionPipeline initialized with loader and cleaner.')

  def run(self, file_path: str) -> List[Dict[str, Any]]:
    logging.info(f"=== Starting ingestion pipeline for file: {file_path} ===")

    # load
    raw_data = self.loader.load_data(file_path)
    logging.info('Data loaded in pipeline.')
    if raw_data is None:
      logging.error('Loading data failed. Exiting pipeline.')
      return []

    # clean
    clean_data = self.cleaner.clean_data(raw_data)
    logging.info('Data cleaned in pipeline.')
    if clean_data is None:
      logging.error('Cleaning data failed. Exiting pipeline.')
      return []

