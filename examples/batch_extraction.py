#!/usr/bin/env python3
"""
Batch text extraction script with rate limiting for Gemini API free tier.
Processes 1000 text files within free tier limits:
- 10 RPM (Requests Per Minute)
- 250,000 TPM (Tokens Per Minute)  
- 250 RPD (Requests Per Day)
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import textwrap
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import langextract as lx
import tiktoken  # For token counting estimation

# Load environment variables
load_dotenv()

# Configuration
@dataclass
class RateLimits:
    """Rate limit configuration for Gemini API free tier."""
    requests_per_minute: int = 10
    tokens_per_minute: int = 250_000
    requests_per_day: int = 250
    
    # Safety margins (use 80% of limits to be safe)
    safety_factor: float = 0.8
    
    @property
    def safe_rpm(self) -> int:
        return int(self.requests_per_minute * self.safety_factor)
    
    @property
    def safe_tpm(self) -> int:
        return int(self.tokens_per_minute * self.safety_factor)
    
    @property
    def safe_rpd(self) -> int:
        return int(self.requests_per_day * self.safety_factor)


@dataclass
class ProcessingState:
    """Track processing state for resume capability."""
    total_files: int = 0
    processed_files: int = 0
    failed_files: List[str] = None
    current_date: str = ""
    daily_requests: int = 0
    last_request_time: float = 0
    processing_history: List[Dict] = None
    
    def __post_init__(self):
        if self.failed_files is None:
            self.failed_files = []
        if self.processing_history is None:
            self.processing_history = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProcessingState':
        return cls(**data)


class TokenEstimator:
    """Estimate tokens for rate limiting."""
    
    def __init__(self):
        # Use tiktoken for estimation (GPT-3.5 tokenizer as approximation)
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except:
            self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(self.encoder.encode(text))
    
    def estimate_request_tokens(self, text: str, prompt: str, examples: List) -> int:
        """Estimate total tokens for a request."""
        total = self.estimate_tokens(text)
        total += self.estimate_tokens(prompt)
        
        # Estimate tokens for examples
        for example in examples:
            total += self.estimate_tokens(str(example))
        
        # Add overhead for response (estimate 50% of input)
        total = int(total * 1.5)
        
        return total


class BatchExtractor:
    """Batch extraction with rate limiting and state management."""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        state_file: str = "extraction_state.json",
        log_file: str = "extraction.log"
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.state_file = Path(state_file)
        self.log_file = Path(log_file)
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.rate_limits = RateLimits()
        self.token_estimator = TokenEstimator()
        self.state = self._load_state()
        
        # Model configuration
        self.model_id = "gemini-2.5-flash"  # Using Flash for free tier
        
        # Define extraction configuration
        self.prompt = textwrap.dedent("""
            Extract key entities, concepts, and relationships from the text.
            Identify people, places, organizations, dates, and important concepts.
            Use exact text from the source.
        """)
        
        self.examples = [
            lx.data.ExampleData(
                text="John Smith founded TechCorp in 2020 in San Francisco.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="person",
                        extraction_text="John Smith",
                        attributes={"role": "founder"}
                    ),
                    lx.data.Extraction(
                        extraction_class="organization", 
                        extraction_text="TechCorp",
                        attributes={"type": "company"}
                    ),
                    lx.data.Extraction(
                        extraction_class="date",
                        extraction_text="2020",
                        attributes={"event": "founding"}
                    ),
                    lx.data.Extraction(
                        extraction_class="place",
                        extraction_text="San Francisco",
                        attributes={"type": "city"}
                    ),
                ]
            )
        ]
    
    def _setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_state(self) -> ProcessingState:
        """Load processing state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                state = ProcessingState.from_dict(data)
                self.logger.info(f"Loaded state: {state.processed_files}/{state.total_files} files processed")
                return state
        return ProcessingState()
    
    def _save_state(self):
        """Save processing state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)
    
    def _get_unprocessed_files(self) -> List[Path]:
        """Get list of unprocessed text files."""
        # Get all text files
        all_files = sorted(self.input_dir.glob("*.txt"))
        
        # Get already processed files
        processed_files = set()
        for output_file in self.output_dir.glob("*.jsonl"):
            processed_files.add(output_file.stem)
        
        # Filter unprocessed
        unprocessed = []
        for file in all_files:
            if file.stem not in processed_files and str(file) not in self.state.failed_files:
                unprocessed.append(file)
        
        return unprocessed
    
    def _wait_for_rate_limit(self, tokens_used: int):
        """Wait to respect rate limits."""
        current_time = time.time()
        
        # Check requests per minute
        time_since_last = current_time - self.state.last_request_time
        if time_since_last < 60 / self.rate_limits.safe_rpm:
            wait_time = (60 / self.rate_limits.safe_rpm) - time_since_last
            self.logger.debug(f"Rate limit: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
    
    def _check_daily_limit(self) -> bool:
        """Check if daily limit reached."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Reset counter if new day
        if current_date != self.state.current_date:
            self.state.current_date = current_date
            self.state.daily_requests = 0
            self.logger.info("New day - daily request counter reset")
        
        # Check if limit reached
        if self.state.daily_requests >= self.rate_limits.safe_rpd:
            self.logger.warning(f"Daily limit reached ({self.state.daily_requests}/{self.rate_limits.safe_rpd})")
            return False
        
        return True
    
    def _process_file(self, file_path: Path) -> bool:
        """Process a single file."""
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Estimate tokens
            estimated_tokens = self.token_estimator.estimate_request_tokens(
                text, self.prompt, self.examples
            )
            
            # Check token limit
            if estimated_tokens > self.rate_limits.safe_tpm:
                self.logger.warning(f"File {file_path.name} too large ({estimated_tokens} tokens). Truncating...")
                # Truncate text to fit token limit
                max_chars = int(len(text) * (self.rate_limits.safe_tpm / estimated_tokens) * 0.8)
                text = text[:max_chars]
            
            # Wait for rate limit
            self._wait_for_rate_limit(estimated_tokens)
            
            # Perform extraction
            start_time = time.time()
            result = lx.extract(
                text_or_documents=text,
                prompt_description=self.prompt,
                examples=self.examples,
                model_id=self.model_id
            )
            extraction_time = time.time() - start_time
            
            # Save result
            output_file = self.output_dir / f"{file_path.stem}.jsonl"
            lx.io.save_annotated_documents([result], output_name=str(output_file))
            
            # Update state
            self.state.last_request_time = time.time()
            self.state.daily_requests += 1
            self.state.processed_files += 1
            
            # Log success
            self.logger.info(
                f"Processed {file_path.name} "
                f"({self.state.processed_files}/{self.state.total_files}) "
                f"in {extraction_time:.1f}s - "
                f"Found {len(result.extractions)} entities"
            )
            
            # Record in history
            self.state.processing_history.append({
                "file": file_path.name,
                "timestamp": datetime.now().isoformat(),
                "entities_found": len(result.extractions),
                "processing_time": extraction_time,
                "tokens_estimated": estimated_tokens
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process {file_path.name}: {str(e)}")
            self.state.failed_files.append(str(file_path))
            return False
    
    def run(self):
        """Run batch extraction."""
        self.logger.info("Starting batch extraction...")
        
        # Get files to process
        unprocessed_files = self._get_unprocessed_files()
        
        if not unprocessed_files:
            self.logger.info("No files to process!")
            return
        
        # Update total files count
        if self.state.total_files == 0:
            self.state.total_files = len(unprocessed_files) + self.state.processed_files
        
        self.logger.info(f"Found {len(unprocessed_files)} files to process")
        self.logger.info(f"Daily limit: {self.rate_limits.safe_rpd} requests")
        self.logger.info(f"Estimated days to complete: {len(unprocessed_files) / self.rate_limits.safe_rpd:.1f}")
        
        # Process files
        for file_path in unprocessed_files:
            # Check daily limit
            if not self._check_daily_limit():
                self.logger.info("Daily limit reached. Resume tomorrow!")
                break
            
            # Process file
            success = self._process_file(file_path)
            
            # Save state after each file
            self._save_state()
            
            # Check if should stop
            if self.state.daily_requests >= self.rate_limits.safe_rpd:
                self.logger.info("Daily limit reached. Stopping for today.")
                break
        
        # Final summary
        self._print_summary()
    
    def _print_summary(self):
        """Print processing summary."""
        self.logger.info("\n" + "="*50)
        self.logger.info("PROCESSING SUMMARY")
        self.logger.info("="*50)
        self.logger.info(f"Total files: {self.state.total_files}")
        self.logger.info(f"Processed: {self.state.processed_files}")
        self.logger.info(f"Failed: {len(self.state.failed_files)}")
        self.logger.info(f"Remaining: {self.state.total_files - self.state.processed_files}")
        self.logger.info(f"Today's requests: {self.state.daily_requests}")
        
        if self.state.total_files > self.state.processed_files:
            remaining = self.state.total_files - self.state.processed_files
            days_remaining = remaining / self.rate_limits.safe_rpd
            self.logger.info(f"Estimated days to complete: {days_remaining:.1f}")
        
        if self.state.failed_files:
            self.logger.info(f"\nFailed files:")
            for file in self.state.failed_files[:10]:
                self.logger.info(f"  - {file}")
            if len(self.state.failed_files) > 10:
                self.logger.info(f"  ... and {len(self.state.failed_files) - 10} more")
    
    def retry_failed(self):
        """Retry failed files."""
        if not self.state.failed_files:
            self.logger.info("No failed files to retry")
            return
        
        self.logger.info(f"Retrying {len(self.state.failed_files)} failed files...")
        failed_files = self.state.failed_files.copy()
        self.state.failed_files = []
        
        for file_path in failed_files:
            if not self._check_daily_limit():
                # Add back to failed list if daily limit reached
                self.state.failed_files.extend(failed_files[failed_files.index(file_path):])
                break
            
            self._process_file(Path(file_path))
            self._save_state()
    
    def generate_report(self, output_file: str = "extraction_report.json"):
        """Generate a detailed report of the extraction process."""
        report = {
            "summary": {
                "total_files": self.state.total_files,
                "processed_files": self.state.processed_files,
                "failed_files": len(self.state.failed_files),
                "completion_percentage": (self.state.processed_files / self.state.total_files * 100) 
                                       if self.state.total_files > 0 else 0
            },
            "processing_history": self.state.processing_history,
            "failed_files": self.state.failed_files,
            "statistics": self._calculate_statistics()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Report saved to {output_file}")
    
    def _calculate_statistics(self) -> Dict:
        """Calculate processing statistics."""
        if not self.state.processing_history:
            return {}
        
        processing_times = [h["processing_time"] for h in self.state.processing_history]
        entities_counts = [h["entities_found"] for h in self.state.processing_history]
        
        return {
            "average_processing_time": sum(processing_times) / len(processing_times),
            "total_processing_time": sum(processing_times),
            "average_entities_per_file": sum(entities_counts) / len(entities_counts),
            "total_entities_found": sum(entities_counts)
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch text extraction with rate limiting")
    parser.add_argument("input_dir", help="Directory containing text files")
    parser.add_argument("output_dir", help="Directory for output files")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed files")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    parser.add_argument("--state-file", default="extraction_state.json", help="State file path")
    parser.add_argument("--log-file", default="extraction.log", help="Log file path")
    
    args = parser.parse_args()
    
    # Check API key
    if not os.getenv("LANGEXTRACT_API_KEY"):
        print("Error: LANGEXTRACT_API_KEY not set in environment")
        return 1
    
    # Create extractor
    extractor = BatchExtractor(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        state_file=args.state_file,
        log_file=args.log_file
    )
    
    # Run appropriate action
    if args.report:
        extractor.generate_report()
    elif args.retry_failed:
        extractor.retry_failed()
    else:
        extractor.run()
    
    return 0


if __name__ == "__main__":
    exit(main())