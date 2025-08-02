#!/usr/bin/env python3
"""
Basic LangExtract example demonstrating entity extraction from Shakespeare text.
"""

import os
import textwrap
from dotenv import load_dotenv
import langextract as lx

# Load environment variables
load_dotenv()

def main():
    """Run basic extraction example."""
    
    # Define extraction prompt
    prompt = textwrap.dedent("""\
        Extract characters, emotions, and relationships in order of appearance.
        Use exact text for extractions. Do not paraphrase or overlap entities.
        Provide meaningful attributes for each entity to add context.
    """)
    
    # Define few-shot examples
    examples = [
        lx.data.ExampleData(
            text=(
                "ROMEO. But soft! What light through yonder window breaks? "
                "It is the east, and Juliet is the sun."
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="ROMEO",
                    attributes={"emotional_state": "wonder"},
                ),
                lx.data.Extraction(
                    extraction_class="emotion",
                    extraction_text="But soft!",
                    attributes={"feeling": "gentle awe"},
                ),
                lx.data.Extraction(
                    extraction_class="relationship",
                    extraction_text="Juliet is the sun",
                    attributes={"type": "metaphor", "nature": "romantic"},
                ),
            ],
        )
    ]
    
    # Input text for extraction
    input_text = (
        "Lady Juliet gazed longingly at the stars, her heart aching for Romeo. "
        "'O Romeo, Romeo! Wherefore art thou Romeo?' she cried into the night."
    )
    
    print("🔍 Running LangExtract...")
    print(f"📝 Input text: {input_text}\n")
    
    # Perform extraction
    result = lx.extract(
        text_or_documents=input_text,
        prompt_description=prompt,
        examples=examples,
        model_id=os.getenv("DEFAULT_MODEL_ID", "gemini-2.5-flash"),
    )
    
    # Display results
    print("✅ Extraction complete!\n")
    print(f"Found {len(result.extractions)} entities:\n")
    
    for i, extraction in enumerate(result.extractions, 1):
        print(f"{i}. Class: {extraction.extraction_class}")
        print(f"   Text: '{extraction.extraction_text}'")
        print(f"   Attributes: {extraction.attributes}")
        print()
    
    # Save results
    output_file = "output/basic_extraction_results.jsonl"
    lx.io.save_annotated_documents([result], output_name=output_file)
    print(f"💾 Results saved to: {output_file}")
    
    # Generate visualization
    html_content = lx.visualize(output_file)
    html_file = "output/basic_extraction_visualization.html"
    
    with open(html_file, "w") as f:
        f.write(html_content)
    
    print(f"🎨 Visualization saved to: {html_file}")
    print("\n✨ Example complete! Open the HTML file to see the interactive visualization.")

if __name__ == "__main__":
    main()