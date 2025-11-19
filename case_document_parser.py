from bs4 import BeautifulSoup
import re
from typing import Dict, Union
from pathlib import Path

def parse_case_document(html_content: Union[str, Path]) -> Dict:
    """
    Parse Indian Kanoon case document HTML to extract structured judgment parts.
    
    Args:
        html_content: Either HTML string content or path to HTML file
        
    Returns:
        Dictionary containing structured judgment parts with their content
    """
    # Check if input is a file path or HTML string
    if isinstance(html_content, (str, Path)) and Path(html_content).exists():
        with open(html_content, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Structure mapping from JS file
    structure_names = {
        'Facts': 'Facts',
        'Issue': 'Issues',
        'PetArg': "Petitioner's Arguments",
        'RespArg': "Respondent's Arguments",
        'Section': 'Analysis of the law',
        'Precedent': 'Precedent Analysis',
        'CDiscource': "Court's Reasoning",
        'Conclusion': 'Conclusion'
    }
    
    # Initialize result dictionary with empty strings for each structure
    result = {name: [] for name in structure_names.values()}
    
    # Find the judgments div
    judgments_div = soup.find('div', class_='judgments')
    
    if not judgments_div:
        return result
    
    # Iterate through all children and collect structured content
    for element in judgments_div.children:
        # Skip if not a tag element
        if not hasattr(element, 'attrs'):
            continue
        
        # Get the data-structure attribute
        structure = element.get('data-structure')
        
        if structure and structure in structure_names:
            # Get the full name from mapping
            full_name = structure_names[structure]
            
            # Extract text content and clean it
            text = element.get_text(separator=' ', strip=True)
            
            # Remove hidden text patterns
            text = re.sub(r'Page No\. \d+ of \d+', '', text)
            text = re.sub(r'Signature Not Verified.*?Reason:', '', text, flags=re.DOTALL)
            text = text.strip()
            
            if text:
                result[full_name].append(text)
    
    # Combine all text segments for each category
    final_result = {}
    for key, value in result.items():
        if value:  # Only include categories that have content
            final_result[key] = '\n\n'.join(value)
    
    return final_result


def parse_case_metadata(html_content: Union[str, Path]) -> Dict:
    """
    Extract case metadata like title, court, citations etc.
    
    Args:
        html_content: Either HTML string content or path to HTML file
        
    Returns:
        Dictionary containing case metadata
    """
    # Check if input is a file path or HTML string
    if isinstance(html_content, (str, Path)) and Path(html_content).exists():
        with open(html_content, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    metadata = {}
    
    # Extract title from page title or h2
    title_tag = soup.find('title')
    if title_tag:
        metadata['title'] = title_tag.get_text(strip=True)
    
    # Extract citations info
    citetop = soup.find('span', class_='citetop')
    if citetop:
        cites_match = re.search(r'Cites (\d+)', citetop.get_text())
        cited_by_match = re.search(r'Cited by (\d+)', citetop.get_text())
        
        if cites_match:
            metadata['cites'] = int(cites_match.group(1))
        if cited_by_match:
            metadata['cited_by'] = int(cited_by_match.group(1))
    
    # Extract document structure statistics
    judgments_div = soup.find('div', class_='judgments')
    if judgments_div:
        structure_count = {}
        for element in judgments_div.children:
            if hasattr(element, 'attrs'):
                structure = element.get('data-structure')
                if structure:
                    structure_count[structure] = structure_count.get(structure, 0) + 1
        
        metadata['structure_count'] = structure_count
    
    return metadata


def get_complete_case_data(html_content: Union[str, Path]) -> Dict:
    """
    Get complete parsed case data including metadata and structured content.
    
    Args:
        html_content: Either HTML string content or path to HTML file
        
    Returns:
        Dictionary containing metadata and structured judgment parts
    """
    metadata = parse_case_metadata(html_content)
    structured_content = parse_case_document(html_content)
    
    return {
        'metadata': metadata,
        'structured_content': structured_content
    }


# Example usage
if __name__ == "__main__":
    import json
    
    # Parse the case document
    case_data = get_complete_case_data('case_document.html')
    
    # Print metadata
    print("=" * 80)
    print("CASE METADATA:")
    print("=" * 80)
    print(json.dumps(case_data['metadata'], indent=2))
    print()
    
    # Print structured content summary
    print("=" * 80)
    print("STRUCTURED CONTENT SUMMARY:")
    print("=" * 80)
    for section, content in case_data['structured_content'].items():
        content_preview = content[:200] + "..." if len(content) > 200 else content
        print(f"\n{section}:")
        print(f"  Length: {len(content)} characters")
        print(f"  Preview: {content_preview}")
    
    # Save to JSON file
    with open('case_data.json', 'w', encoding='utf-8') as f:
        json.dump(case_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("Full data saved to case_data.json")
    print("=" * 80)
