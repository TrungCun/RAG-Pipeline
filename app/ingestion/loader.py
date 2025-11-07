import pandas as pd
from typing import Optional
import logging

class CSVLoader:
  '''
  A  class loading data from a .csv file.
  '''
  def __init__(self, encoding: str = 'utf-8'):
    '''
    Initializes the CSVloader instance.
    Args:
      encoding: utf-8
    '''
    self.encoding = encoding

  def load_data(self, file_path: str) -> Optional[pd.DataFrame]:
    '''
    Loads data from .csv file to DataFrame.
    Args:
      file_path: path to the .csv file.
    Returns:
      a pandas DataFrame containing the loaded data, or None if loading fails.
    '''
    try:
      logging.info(f'Loading data from: {file_path}')
      df = pd.read_csv(file_path, encoding=self.encoding)
      logging.info(f'Data loaded successfully with shape: {df.shape}, {len(df.columns)} columns and {len(df)} rows.')
      return df
    except FileNotFoundError:
      logging.error(f'File not found: {file_path}')
      return None
    except Exception as e:
      logging.error(f'Error loading data from {file_path}: {e}')
      return None
