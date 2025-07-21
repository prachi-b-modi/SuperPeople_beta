import fitz  # PyMuPDF
import argparse
import sys
import os
import base64
import anthropic
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def parse_resume_with_llm(pdf_path):
    """
    Parses a PDF resume using Anthropic Claude Haiku.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        str: The parsed resume data from the LLM.
    """
    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY environment variable not set."

    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        return f"Error opening PDF file: {e}"

    # Render the first page of the PDF to an image
    page = document.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Convert image to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Parse this resume and provide the output in a structured format (e.g., JSON) with fields for contact information, summary, experience, education, and skills.",
                        },
                    ],
                }
            ],
        )
        return message.content[0].text
    except Exception as e:
        return f"Error calling Anthropic API: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a resume in PDF format using an LLM.")
    parser.add_argument("pdf_file", help="The path to the PDF resume file.")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    parsed_text = parse_resume_with_llm(args.pdf_file)
    print(parsed_text)