from bs4 import BeautifulSoup
import re
from typing import Dict, List, Union
from pathlib import Path

def parse_search_results(html_content: Union[str, Path]) -> Dict:
    """
    Parse Indian Kanoon search results HTML to extract:
    1. Total number of cases
    2. All case links on the page
    
    Args:
        html_content: Either HTML string content or path to HTML file
        
    Returns:
        Dictionary containing total_cases and case_links
    """
    # Check if input is a file path or HTML string
    if isinstance(html_content, (str, Path)) and Path(html_content).exists():
        with open(html_content, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract total number of cases
    total_cases = extract_total_cases(soup)
    
    # Extract all case links
    case_links = extract_case_links(soup)
    
    return {
        'total_cases': total_cases,
        'total_on_page': len(case_links),
        'case_links': case_links
    }

def extract_total_cases(soup: BeautifulSoup) -> int:
    """
    Extract total number of cases from the results page.
    Looks for pattern like "1 - 10 of 118"
    """
    # Find the div containing the total count
    results_div = soup.find('div', string=re.compile(r'\d+ - \d+ of \d+'))
    
    if results_div:
        # Extract the text (e.g., "1 - 10 of 118  (0.12 seconds)")
        text = results_div.get_text(strip=True)
        
        # Use regex to extract the total number
        match = re.search(r'of (\d+)', text)
        if match:
            return int(match.group(1))
    
    return 0

def extract_case_links(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract all case links and metadata from the page.
    
    Returns:
        List of dictionaries containing case information
    """
    cases = []
    
    # Find all result divs
    result_divs = soup.find_all('div', class_='result')
    
    for result in result_divs:
        case_info = {}
        
        # Extract case title and link
        title_div = result.find('div', class_='result_title')
        if title_div:
            link_tag = title_div.find('a')
            if link_tag:
                case_info['title'] = link_tag.get_text(strip=True)
                case_info['fragment_url'] = 'https://indiankanoon.org' + link_tag.get('href')
                
                # Extract document ID from URL
                doc_id_match = re.search(r'/docfragment/(\d+)/', link_tag.get('href'))
                if doc_id_match:
                    case_info['doc_id'] = doc_id_match.group(1)
        
        # Extract metadata (court, cites, cited by)
        hlbottom = result.find('div', class_='hlbottom')
        if hlbottom:
            # Court name
            court = hlbottom.find('span', class_='docsource')
            if court:
                case_info['court'] = court.get_text(strip=True)
            
            # Cites count
            cites_link = hlbottom.find('a', class_='cite_tag', string=re.compile(r'Cites \d+'))
            if cites_link:
                cites_match = re.search(r'Cites (\d+)', cites_link.get_text())
                if cites_match:
                    case_info['cites'] = int(cites_match.group(1))
            
            # Cited by count
            cited_by_link = hlbottom.find('a', class_='cite_tag', string=re.compile(r'Cited by \d+'))
            if cited_by_link:
                cited_by_match = re.search(r'Cited by (\d+)', cited_by_link.get_text())
                if cited_by_match:
                    case_info['cited_by'] = int(cited_by_match.group(1))
            
            # Full document link
            full_doc_link = hlbottom.find('a', class_='cite_tag', string='Full Document')
            if full_doc_link:
                case_info['full_doc_url'] = 'https://indiankanoon.org' + full_doc_link.get('href')
            
            # Author (if present)
            author_link = hlbottom.find('a', class_='cite_tag', href=re.compile(r'authorid:'))
            if author_link:
                case_info['author'] = author_link.get_text(strip=True)
        
        if case_info:
            cases.append(case_info)
    
    return cases

def parse_pagination(soup: BeautifulSoup) -> Dict:
    """
    Extract pagination information from the page.
    
    Returns:
        Dictionary with current_page, total_pages, next_page_url
    """
    pagination_info = {
        'current_page': 1,
        'total_pages': 1,
        'next_page_url': None,
        'page_links': []
    }
    
    bottom_div = soup.find('div', class_='bottom')
    if bottom_div:
        # Find all page links
        page_links = bottom_div.find_all('a', href=re.compile(r'pagenum=\d+'))
        
        if page_links:
            # Extract page numbers
            page_numbers = []
            for link in page_links:
                match = re.search(r'pagenum=(\d+)', link.get('href'))
                if match:
                    page_numbers.append(int(match.group(1)) + 1)  # pagenum is 0-indexed
            
            if page_numbers:
                pagination_info['total_pages'] = max(page_numbers)
        
        # Find next page link
        next_link = bottom_div.find('a', string='Next')
        if next_link:
            pagination_info['next_page_url'] = 'https://indiankanoon.org' + next_link.get('href')
    
    return pagination_info

def get_doc_search_results(html_content: Union[str, Path]) -> Dict:
    """
    Get complete parsed results including cases and pagination.
    
    Args:
        html_content: Either HTML string content or path to HTML file
        
    Returns:
        Dictionary containing all parsed data
    """
    # Parse the search results
    results = parse_search_results(html_content)
    
    # Check if input is a file path or HTML string
    if isinstance(html_content, (str, Path)) and Path(html_content).exists():
        with open(html_content, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    pagination = parse_pagination(soup)
    
    # Combine into single dictionary
    return {
        'total_cases': results['total_cases'],
        'total_on_page': results['total_on_page'],
        'cases': results['case_links'],
        'pagination': pagination
    }

# Example usage
if __name__ == "__main__":
    # Get complete results as dictionary
    data = get_doc_search_results('search_results.html')
    
    # Print summary
    print(data)
