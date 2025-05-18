import base64
import os

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from db.models import GameData


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
    return api_key


def encode_pdf(file_path: str) -> str:
    """Encode PDF file to base64 string"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to encode PDF: {str(e)}")


def parse_game_pdf(pdf_file_path: str) -> GameData:
    """Extract structured data from basketball box score PDF"""
    # Encode PDF
    try:
        base64_string = encode_pdf(pdf_file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to process PDF: {str(e)}")

    # Initialize OpenAI client
    try:
        api_key = get_openai_api_key()
        client = OpenAI(api_key=api_key)
    except ValueError as e:
        raise ValueError(str(e))

    # Parse PDF with OpenAI
    try:
        system_prompt = """
        Extract complete basketball game data from the box score PDF.
        Analyze thoroughly and extract ALL game details, team statistics, and player statistics.
        Be precise with all statistical data and follow the provided schema exactly.
        """

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "file",
                            "file": {
                                "filename": "game_stats.pdf",
                                "file_data": f"data:application/pdf;base64,{base64_string}",
                            },
                        },
                        {"type": "text", "text": "Extract all game data in structured format."},
                    ],
                },
            ],
            response_format=GameData,
        )

        data = completion.choices[0].message.parsed

        if data:
            return data
        else:
            raise ValueError("Failed to parse game data from PDF.")

    except AuthenticationError:
        raise ValueError("Invalid OpenAI API key.")
    except RateLimitError:
        raise RuntimeError("OpenAI API rate limit exceeded. Try again later.")
    except APIError as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to extract data: {str(e)}")
