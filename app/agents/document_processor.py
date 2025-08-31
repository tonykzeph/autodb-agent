from agno.agent import Agent
from agno.tools import tool
from agno.models.google import Gemini
from typing import Dict, Any
import json
import asyncio
import httpx
import logging
import io
from PyPDF2 import PdfReader
from docx import Document

# Configure logging
logger = logging.getLogger(__name__)

# System prompt that defines how to process different file types
DOCUMENT_PROCESSING_PROMPT = """
You are a Document Processing Agent that determines whether uploaded files should continue through the AI processing pipeline.

PROCESSING RULES BY CONTENT TYPE:

## CONTINUE PROCESSING (TEXT DOCUMENTS)
- text/plain (.txt): Continue - text extraction and indexing
- application/pdf (.pdf): Continue - OCR extraction and text indexing
- text/csv (.csv): Continue - basic text processing
- application/vnd.openxmlformats-officedocument.wordprocessingml.document (.docx): Continue - text extraction

## CONTINUE PROCESSING (IMAGES)  
- image/png (.png): Continue - thumbnail generation and basic analysis
- image/jpeg (.jpg): Continue - thumbnail generation and basic analysis

## SKIP PROCESSING (OTHER FILES)
- audio/mpeg (.mp3): Skip - store as-is
- video/mp4 (.mp4): Skip - store as-is  
- video/webm (.webm): Skip - store as-is
- All other file types: Skip - store as-is

## DECISION LOGIC
- If content_type matches text or image formats → Set "should_process": true
- If content_type matches audio, video, or other formats → Set "should_process": false

RESPONSE FORMAT:
Return a JSON object with this structure:
{
  "should_process": true | false,
  "workflow_type": "text_processing" | "image_processing" | "skip_processing",
  "reason": "Brief explanation of the decision"
}

Analyze the provided content_type and return the appropriate processing workflow.

If you determine that processing should continue, use the appropriate tool:
- For text documents: Use the text_parsing_tool
- For image documents: Use the image_analysis_tool
"""

# Tool 1: Enhanced Text Parsing Tool with AI Summarization
@tool
def text_parsing_tool(file_url: str, content_type: str) -> Dict[str, Any]:
    """
    Extract and summarize text content from documents using Gemini AI
    
    Args:
        file_url: URL to the document in R2 storage
        content_type: MIME type of the document
        
    Returns:
        Dict with AI-generated summary and metadata
    """
    try:
        # Download the file content
        response = httpx.get(file_url, timeout=30)
        response.raise_for_status()
        
        # Extract text based on content type
        raw_text = ""
        
        if content_type == "text/plain":
            raw_text = response.text
            
        elif content_type == "application/pdf":
            # Extract text from PDF using PyPDF2
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PdfReader(pdf_file)
            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
            raw_text = "\n".join(text_parts)
            
        elif content_type == "text/csv":
            # For CSV, just treat as plain text
            raw_text = response.text
            
        elif "wordprocessingml" in content_type:
            # Extract text from DOCX using python-docx
            docx_file = io.BytesIO(response.content)
            doc = Document(docx_file)
            text_parts = []
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)
            raw_text = "\n".join(text_parts)
            
        else:
            raw_text = "Unsupported text format"
        
        # Clean and validate extracted text
        raw_text = raw_text.strip()
        word_count = len(raw_text.split()) if raw_text else 0
        
        # Use Gemini to create intelligent summary if we have meaningful text
        if word_count > 5:  # Only summarize if we have substantial content
            summarizer_agent = Agent(
                name="TextSummarizer",
                model=Gemini(id="gemini-2.5-flash"),
                introduction="Expert text summarizer that extracts key information"
            )
            
            summary_prompt = f"""
            Analyze and summarize the following text content. Focus on:
            1. Main topic/subject
            2. Key points or important information  
            3. Document purpose or type
            4. Most relevant details
            
            Keep the summary concise but informative (2-3 sentences max).
            
            Text content:
            {raw_text[:4000]}  # Limit to first 4000 chars to avoid token limits
            """
            
            summary_response = summarizer_agent.run(summary_prompt)
            
            # Extract summary from response
            if hasattr(summary_response, 'content'):
                extracted_text = summary_response.content.strip()
            else:
                extracted_text = str(summary_response).strip()
                
            # Clean up any markdown formatting
            extracted_text = extracted_text.replace('```', '').replace('**', '').strip()
            
        else:
            # For short text or empty content, just use the raw text
            extracted_text = raw_text[:1000] if raw_text else "No meaningful text content found"
        
        result = {
            "success": True,
            "extracted_text": extracted_text[:1000],  # Ensure we don't exceed limits
            "word_count": word_count,
            "content_type": content_type,
            "processing_method": "ai_text_summarization"
        }
        
        logger.info(f"TEXT_PARSING_TOOL OUTPUT: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "content_type": content_type,
            "processing_method": "ai_text_summarization"
        }
        
        logger.error(f"TEXT_PARSING_TOOL ERROR: {json.dumps(error_result, indent=2)}")
        return error_result

# Tool 2: Image Analysis Tool (Sub-Agent)
@tool  
def image_analysis_tool(file_url: str, content_type: str) -> Dict[str, Any]:
    """
    Analyze image content using AI vision model
    
    Args:
        file_url: URL to the image in R2 storage  
        content_type: MIME type of the image
        
    Returns:
        Dict with image analysis results
    """
    try:
        # Create a sub-agent for image analysis
        vision_agent = Agent(
            name="ImageAnalyzer",
            model=Gemini(id="gemini-2.5-flash"),
            introduction="Expert in computer vision and image content analysis"
        )
        
        # Analyze the image
        analysis_prompt = f"""
        Analyze this image from URL: {file_url}
        
        Provide:
        1. Main objects/subjects in the image
        2. Scene description
        3. Text content (if any)
        4. Overall theme/category
        5. Key visual elements
        
        Keep response concise and structured.
        """
        
        # Run the vision analysis
        analysis_result = vision_agent.run(analysis_prompt)
        
        # Extract clean content from RunResponse object
        if hasattr(analysis_result, 'content'):
            clean_description = analysis_result.content.strip()
        else:
            clean_description = str(analysis_result).strip()
            
        # Clean up any markdown formatting
        clean_description = clean_description.replace('```', '').replace('**', '').strip()
        
        result = {
            "success": True,
            "image_description": clean_description,
            "content_type": content_type,
            "processing_method": "ai_vision_analysis",
            "detected_objects": "Analysis completed",
            "scene_type": "Image analyzed"
        }
        
        logger.info(f"IMAGE_ANALYSIS_TOOL OUTPUT: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "content_type": content_type,
            "processing_method": "ai_vision_analysis"
        }
        
        logger.error(f"IMAGE_ANALYSIS_TOOL ERROR: {json.dumps(error_result, indent=2)}")
        return error_result

class DocumentProcessingAgent:
    def __init__(self):
        self.agent = Agent(
            name="DocumentProcessor",
            model=Gemini(id="gemini-2.5-flash"),
            introduction="Expert in file format analysis and automated document processing pipelines",
            system_message=DOCUMENT_PROCESSING_PROMPT,
            tools=[text_parsing_tool, image_analysis_tool],
            show_tool_calls=True
        )
    
    def process_document_metadata(self, content_type: str, file_size: int, filename: str, file_url: str) -> Dict[str, Any]:
        """
        Process document metadata and return processing workflow
        """
        prompt = f"""
        Analyze this uploaded document and determine the processing workflow:
        
        Content Type: {content_type}
        File Size: {file_size} bytes
        Original Filename: {filename}
        File URL: {file_url}
        
        Step 1: Determine if this document should continue processing (text/image) or skip (audio/video/other)
        Step 2: If continuing, use the appropriate tool:
        - For text documents (txt, pdf, csv, docx): Use text_parsing_tool
        - For image documents (png, jpg): Use image_analysis_tool
        
        Based on the content_type, make your decision and use tools if needed.
        """
        
        try:
            logger.info(f"DOCUMENT_PROCESSOR INPUT: content_type={content_type}, file_size={file_size}, filename={filename}")
            
            response = self.agent.run(prompt)
            
            # Extract content field from RunResponse object
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            logger.info(f"Agent response content: {response_text}")
            
            # Parse JSON response from the content
            # Handle markdown code blocks
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            final_result = None
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                try:
                    final_result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    # If JSON parsing fails, create a basic response
                    logger.error(f"JSON parsing error: {e}")
                    final_result = {
                        "should_process": False,
                        "workflow_type": "skip_processing", 
                        "reason": f"Could not parse agent response: {json_str[:200]}"
                    }
            else:
                final_result = {
                    "should_process": False,
                    "workflow_type": "skip_processing",
                    "reason": f"No JSON found in response: {response_text[:200]}"
                }
            
            # Check if the agent executed tools and extract those results
            tool_results = {}
            if hasattr(response, 'tools') and response.tools:
                for tool_execution in response.tools:
                    if tool_execution.tool_name == 'text_parsing_tool':
                        # Parse tool result which is stored as string
                        try:
                            tool_result = eval(tool_execution.result) if isinstance(tool_execution.result, str) else tool_execution.result
                            tool_results.update(tool_result)
                        except:
                            pass
                    elif tool_execution.tool_name == 'image_analysis_tool':
                        try:
                            tool_result = eval(tool_execution.result) if isinstance(tool_execution.result, str) else tool_execution.result
                            tool_results.update(tool_result)
                        except:
                            pass
            
            # Combine decision and tool results
            if tool_results:
                final_result.update(tool_results)
            
            logger.info(f"DOCUMENT_PROCESSOR WORKFLOW OUTPUT: {json.dumps(final_result, indent=2)}")
            return final_result
            
        except Exception as e:
            # Fallback processing decision
            fallback_result = {
                "should_process": False,
                "workflow_type": "skip_processing",
                "reason": f"Agent processing failed: {str(e)}"
            }
            
            logger.error(f"DOCUMENT_PROCESSOR ERROR: {json.dumps(fallback_result, indent=2)}")
            return fallback_result
    
    async def async_process_document_metadata(self, content_type: str, file_size: int, filename: str, file_url: str) -> Dict[str, Any]:
        """
        Async wrapper for document processing
        """
        # Run the synchronous agent in a thread pool if needed
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.process_document_metadata, 
            content_type, 
            file_size, 
            filename,
            file_url
        )