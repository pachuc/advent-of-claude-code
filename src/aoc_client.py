import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


class AdventOfCodeClient:
    """Client for interacting with Advent of Code website."""

    BASE_URL = "https://adventofcode.com"

    def __init__(self, session_token=None):
        """Initialize the client with session token.

        Args:
            session_token: Optional session token. If not provided, reads from AOC_SESSION env var.
        """
        self.session_token = session_token or os.getenv("AOC_SESSION")
        if not self.session_token:
            raise ValueError("Session token must be provided or set in AOC_SESSION environment variable")

        self.session = requests.Session()
        self.session.cookies.set("session", self.session_token)

    def get_puzzle(self, year: int, day: int, part: int) -> str:
        """Fetch puzzle description for a given year, day, and part.

        Args:
            year: The year of the puzzle (e.g., 2024)
            day: The day of the puzzle (1-25)
            part: The part number (1 or 2)

        Returns:
            Puzzle description as markdown string
        """
        url = f"{self.BASE_URL}/{year}/day/{day}"
        response = self.session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article')

        if part == 1:
            article = articles[0]
        elif part == 2:
            article = articles[1]
        else:
            raise ValueError(f"Invalid part: {part}. Must be 1 or 2.")

        # Convert HTML to Markdown
        markdown_content = md(str(article))
        return markdown_content

    def get_input(self, year: int, day: int) -> str:
        """Fetch puzzle input for a given year and day.

        Args:
            year: The year of the puzzle (e.g., 2024)
            day: The day of the puzzle (1-25)

        Returns:
            Puzzle input as string
        """
        url = f"{self.BASE_URL}/{year}/day/{day}/input"
        response = self.session.get(url)
        response.raise_for_status()
        return response.text

    def submit_answer(self, year: int, day: int, part: int, answer: str) -> dict:
        """Submit an answer for a puzzle.

        Args:
            year: The year of the puzzle (e.g., 2024)
            day: The day of the puzzle (1-25)
            part: The part number (1 or 2)
            answer: The answer to submit

        Returns:
            Dictionary with response information
        """
        url = f"{self.BASE_URL}/{year}/day/{day}/answer"
        data = {
            "level": part,
            "answer": answer
        }
        response = self.session.post(url, data=data)
        response.raise_for_status()

        # Parse the response to extract the result message
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.find('article')
        message = article.get_text().strip() if article else response.text

        return {
            "status_code": response.status_code,
            "message": message,
            "raw_html": response.text
        }

    def save_puzzle_to_file(self, year: int, day: int, part: int, output_dir: str = "."):
        """Save puzzle description to a markdown file.

        Args:
            year: The year of the puzzle (e.g., 2024)
            day: The day of the puzzle (1-25)
            part: The part number (1 or 2)
            output_dir: Base directory for saving files
        """
        puzzle_content = self.get_puzzle(year, day, part)

        # Create directory structure with part subdirectory
        part_dir = Path(output_dir) / str(year) / f"day_{day}" / f"part_{part}"
        part_dir.mkdir(parents=True, exist_ok=True)

        # Save to file
        file_path = part_dir / "puzzle.md"
        file_path.write_text(puzzle_content)

        return file_path

    def get_completion_status(self, year: int, day: int) -> dict:
        """Check the completion status of a puzzle day.

        Args:
            year: The year of the puzzle (e.g., 2024)
            day: The day of the puzzle (1-25)

        Returns:
            Dictionary with completion information:
            - part1_complete: bool
            - part2_complete: bool
            - part1_answer: str or None
            - part2_answer: str or None
            - available_parts: int (1 or 2)
        """
        url = f"{self.BASE_URL}/{year}/day/{day}"
        response = self.session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Count article elements to see how many parts are available
        articles = soup.find_all('article')
        available_parts = len(articles)

        # Check for completion text
        page_text = response.text
        both_complete = "Both parts of this puzzle are complete!" in page_text
        part1_complete = "Your puzzle answer was" in page_text or both_complete
        part2_complete = both_complete

        # Extract answers if available
        part1_answer = None
        part2_answer = None

        # Find paragraphs with "Your puzzle answer was"
        answer_paragraphs = soup.find_all('p')
        answer_texts = []
        for p in answer_paragraphs:
            if "Your puzzle answer was" in p.get_text():
                code_tag = p.find('code')
                if code_tag:
                    answer_texts.append(code_tag.get_text().strip())

        if len(answer_texts) >= 1:
            part1_answer = answer_texts[0]
        if len(answer_texts) >= 2:
            part2_answer = answer_texts[1]

        return {
            "part1_complete": part1_complete,
            "part2_complete": part2_complete,
            "part1_answer": part1_answer,
            "part2_answer": part2_answer,
            "available_parts": available_parts
        }

    def save_input_to_file(self, year: int, day: int, part: int, output_dir: str = "."):
        """Save puzzle input to a text file.

        Args:
            year: The year of the puzzle (e.g., 2024)
            day: The day of the puzzle (1-25)
            part: The part number (1 or 2) - input is duplicated for each part
            output_dir: Base directory for saving files
        """
        input_content = self.get_input(year, day)

        # Create directory structure with part subdirectory
        part_dir = Path(output_dir) / str(year) / f"day_{day}" / f"part_{part}"
        part_dir.mkdir(parents=True, exist_ok=True)

        # Save to file
        file_path = part_dir / "input.md"
        file_path.write_text(input_content)

        return file_path
