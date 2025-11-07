import pandas as pd
import logging
from typing import Optional, List

class CSVCleaner:
  '''
  Process Dataframe for RAG:
    -
  '''
  def __init__(self, main_text_column: str, metadata_columns: Optional[List[str]] = None, content_column_name: str = 'rag_content'):
    '''
    Initializes the CSVCleaner instance.
    Args:
      main_text_column: the name of the main text column in the DataFrame.
      content_column_name: the name of the column to store cleaned content.
    '''
    self.main_text_column = main_text_column
    self.metadata_columns = metadata_columns if metadata_columns else []
    self.content_column_name = content_column_name

    self.required_columns = list(set([self.main_text_column] + self.metadata_columns))


  payload_fields = [
      "ID local",
      "ID",
      "Targeted Area",
      "Targeted Field",
      "Targeted Recipient (Org)",
      "Targeted Geography",
      "Targeted Recipient Org. Size",
      "Targeted Career Stage (Eligibility)",
      "Targeted Constellation Requirements",
      "Grant Type",
      "Duration/Intensity/Funding Amount",
      "Financier",
  ]

  def _validate_columns(self, df: pd.Index) -> bool:
    '''
    Check if all required columns are present in the DataFrame
    '''
    missing_columns = [col for col in [self.main_text_column] + self.metadata_columns if col not in df]

  def clean_data(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
    '''
    Cleans the DataFrame for RAG processing.
    Args:
      df: the input pandas DataFrame from loader.py.
    Returns:
      DataFrame with cleaned content column, ready for Chunker or None if cleaning fails.
    '''
    if df is None:
      logging.error('Input DataFrame is None.')
      return None

    logging.info('Starting data cleaning process.')

    # create a copy of the DataFrame to avoid modifying the original
    cleaned_df = df.copy()
    logging.info('Copy dataframe is succes.')


    # process dataframe
    return cleaned_df
    # try:
    #   cleaned_df = cleaned_df[final_columns]
    #   logging.info(f'Data cleaning completed. Final data is: {final_columns}.')
    #   return cleaned_df
    # except KeyError as e:
    #   logging.error(f'Error during data cleaning: {e}')
    #   return None


