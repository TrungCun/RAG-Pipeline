import os
import dspy
import logging
from typing import List, Optional
from app.config import OPENAI_API_KEY, MODEL, TEMPERATURE, MAX_TOKENS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Setup Environment Variables ---
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
logger.info("OPENAI_API_KEY set to environment variable.")

# --- Config DSPy ---
try:
  dspy.configure(
    lm = dspy.LM(
      model = MODEL,
      temperature = TEMPERATURE,
      max_tokens = MAX_TOKENS,
      cache = False
    )
  )
  logger.info(f"DSPy configured successfully with model: {MODEL}, temperature: {TEMPERATURE}, max_tokens: {MAX_TOKENS}")
except Exception as e:
  logger.error(f"Error configuring DSPy: {e}", exc_info=True)
  raise

# --- Define Signature ---
class ReActSignature(dspy.Signature):
  """
  Signature defines input and output fields for an LLM task.
  """
  file_contents: Optional[str] = dspy.InputField(description='', default='')
  user_prompt: Optional[str] = dspy.InputField(description='', default='')
  answer: str = dspy.OutputField()

# --- Define Module ---
class ReActAgent(dspy.Module):
  """
  ReActAgent uses the ReAct (Reasoning and Acting) to process inputs and generate outputs.
  """

  def __init__(self, prompt: str = None, signature_cls: dspy.Signature = None, tools: List[dspy.Tool] =  None):
    """
    Initializes the ReActAgent with a prompt, signature class, and tools.
    Args:
      prompt (str, optional): A custom instruction string (docstring) to "injected" into Signature.
      signature_cls (dspy.Signature): Signature class to use (eg: ReActSignature).
      tools (List[dspy.Tool], optional): A list of tools(tools)
    """

    # Call the constructor of the parent class (dspy.Module)
    super().__init__()
    logger.info("Initializing ReActAgent.......")

    if signature_cls is None:
      logger.warning("No signature_cls provided. Using default ReActSignature.")

    # use the helper func to create a new Signature class automatically if `prompt` is provided.
    self.signature_cls = self._create_signature_with_doc(signature_cls, prompt)

    # Initialize program 'ReAct', This is the core component.
    self.reAct = dspy.ReAct(
      signature = self.signature_cls,
      tools = tools if tools else [],
      max_iters = 3
    )
    logger.info(f"ReActAgent initialized with tools: {len(tools) if tools else 0} and signature_cls: {self.signature_cls}")

  def _create_signature_with_doc(self, base_cls, docstring: str):
    '''
    A helper func using meta-programming to create a new Signature class with a custom docstring.
    '''

    if docstring:
      logger.debug(f'Creating new Signature class from {base_cls.__name__} with custom docstring.')
      return type(base_cls.__name__, (base_cls,), {"__doc__": docstring})
    return base_cls


  async def aforward(self, user_prompt: str, file_contents: str):
    '''
    method aforward is the main method to run the agent
    Args:
      user_prompt (str): The user prompt to process.
      file_contents (str): The contents of the file to process.
    Returns:
      str: The generated answer from dspy.ReAct.acall
    '''
    logger.info(f'ReActAgent .forward called async ')
    logger.debug(f'User prompt: {user_prompt[:100]}...') # Log first 100 chars
    logger.debug(f'File contents: {file_contents[:100]}...') # Log first 100 chars

    try:
      # acall is the async version of call
      result = await self.reAct.acall(
        user_prompt = user_prompt,
        file_contents = file_contents
      )
      logger.info('ReActAgent acall completed successfully.')
      logger.info(f'Generated answer: {result.answer[:100]}...') # Log first 100 chars of answer
      return result

    except Exception as e:
      #logging every exception when calling reAct
      logger.error(f'Error in ReActAgent aforward: {e}', exc_info=True)
      raise