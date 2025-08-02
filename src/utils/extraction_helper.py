"""
Utility functions for LangExtract operations.
"""

import os
from typing import List, Dict, Any, Optional
import json
import langextract as lx
from pathlib import Path

class ExtractionHelper:
    """Helper class for common LangExtract operations."""
    
    def __init__(self, model_id: Optional[str] = None):
        """Initialize helper with model configuration."""
        self.model_id = model_id or os.getenv("DEFAULT_MODEL_ID", "gemini-2.5-flash")
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
        self.output_dir.mkdir(exist_ok=True)
    
    def extract_from_file(
        self, 
        file_path: str, 
        prompt: str, 
        examples: List[lx.data.ExampleData]
    ) -> lx.data.AnnotatedDocument:
        """Extract information from a text file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples,
            model_id=self.model_id
        )
    
    def batch_extract(
        self,
        texts: List[str],
        prompt: str,
        examples: List[lx.data.ExampleData],
        max_workers: int = 4
    ) -> List[lx.data.AnnotatedDocument]:
        """Extract from multiple texts in parallel."""
        results = []
        
        # LangExtract handles parallelization internally
        for text in texts:
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt,
                examples=examples,
                model_id=self.model_id
            )
            results.append(result)
        
        return results
    
    def save_results_with_metadata(
        self,
        results: List[lx.data.AnnotatedDocument],
        output_name: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Save results with additional metadata."""
        output_path = self.output_dir / f"{output_name}.jsonl"
        
        # Save standard results
        lx.io.save_annotated_documents(results, output_name=str(output_path))
        
        # Save metadata separately
        metadata_path = self.output_dir / f"{output_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(output_path)
    
    def create_extraction_report(
        self,
        result: lx.data.AnnotatedDocument
    ) -> Dict[str, Any]:
        """Generate a summary report of extraction results."""
        report = {
            "total_extractions": len(result.extractions),
            "extraction_classes": {},
            "text_coverage": 0,
            "entities": []
        }
        
        # Count by class
        for extraction in result.extractions:
            class_name = extraction.extraction_class
            if class_name not in report["extraction_classes"]:
                report["extraction_classes"][class_name] = 0
            report["extraction_classes"][class_name] += 1
            
            # Add entity details
            report["entities"].append({
                "class": class_name,
                "text": extraction.extraction_text,
                "start": extraction.start_char,
                "end": extraction.end_char,
                "attributes": extraction.attributes
            })
        
        # Calculate text coverage
        covered_chars = set()
        for extraction in result.extractions:
            for i in range(extraction.start_char, extraction.end_char):
                covered_chars.add(i)
        
        if result.text:
            report["text_coverage"] = len(covered_chars) / len(result.text)
        
        return report
    
    @staticmethod
    def load_examples_from_json(file_path: str) -> List[lx.data.ExampleData]:
        """Load few-shot examples from a JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        examples = []
        for item in data:
            extractions = []
            for ext in item.get("extractions", []):
                extractions.append(
                    lx.data.Extraction(
                        extraction_class=ext["extraction_class"],
                        extraction_text=ext["extraction_text"],
                        attributes=ext.get("attributes", {}),
                        start_char=ext.get("start_char", 0),
                        end_char=ext.get("end_char", len(ext["extraction_text"]))
                    )
                )
            
            examples.append(
                lx.data.ExampleData(
                    text=item["text"],
                    extractions=extractions
                )
            )
        
        return examples

# Convenience functions
def quick_extract(text: str, entity_types: List[str]) -> lx.data.AnnotatedDocument:
    """Quick extraction with minimal configuration."""
    helper = ExtractionHelper()
    
    # Build simple prompt
    prompt = f"Extract the following entities: {', '.join(entity_types)}. Use exact text from the source."
    
    # Create basic example
    examples = [
        lx.data.ExampleData(
            text="Sample text for extraction.",
            extractions=[
                lx.data.Extraction(
                    extraction_class=entity_types[0] if entity_types else "entity",
                    extraction_text="Sample",
                    attributes={"example": True}
                )
            ]
        )
    ]
    
    return lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id=helper.model_id
    )