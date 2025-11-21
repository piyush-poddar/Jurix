from curl_cffi import requests
from document_search_parser import get_doc_search_results
from case_document_parser import get_complete_case_data
import json
from pathlib import Path
from ingestion import insert_case_into_db
import time
from db import check_if_docid_exists

# Create output directory
output_dir = Path("scraped_cases")
output_dir.mkdir(exist_ok=True)

s = requests.Session(impersonate="chrome", timeout=300)

base_website_url = "https://indiankanoon.org/"

base_website_response = s.get(base_website_url)
print(base_website_response.status_code)

# sample url for august 2025 supreme court cases
# https://indiankanoon.org/search/?formInput=doctypes%3A%20supremecourt%20fromdate%3A%201-8-2025%20todate%3A%2031-8-2025&pagenum=0

search_url = "https://indiankanoon.org/search/?formInput=doctypes%3A%20supremecourt%20fromdate%3A%201-10-2023%20todate%3A%2031-10-2023&pagenum=1"

response = s.get(search_url)
print(response.status_code)

# Parse search results directly from response
search_results = get_doc_search_results(response.text)

# with open("search_results.json", 'w', encoding='utf-8') as f:
#     json.dump(search_results, f, indent=2, ensure_ascii=False)

while True:
    print(f"Inserting cases of page with URL:\n{search_url}")
    # i = 0
    for i in range(len(search_results["cases"])):
        print(f"Processing case {i+1} of {len(search_results['cases'])}...\n")
        # Get case document
        doc_url = search_results["cases"][i]["full_doc_url"]
        doc_id = search_results["cases"][i]["doc_id"]
        doc_title = search_results["cases"][i]["title"]
        print(f"Document ID: {doc_id}")
        print(f"Title: {doc_title}")
        print(f"URL: {doc_url}")
        # if check_if_docid_exists(doc_id):
        #     print("Document already exists in the database. Skipping...\n")
        #     continue
        doc_response = s.get(doc_url)
        print(f"Status: {doc_response.status_code}")

        # Parse case document directly from response
        print("Parsing case document structure...")
        case_data = get_complete_case_data(doc_response.text)

        # Save structured case data to JSON
        # output_file = output_dir / f"case_{doc_id}.json"
        # with open(output_file, 'w', encoding='utf-8') as f:
        #     json.dump(case_data, f, indent=2, ensure_ascii=False)

        # print(f"\n✅ Case data saved to: {output_file}")

        # Print summary
        print("CASE SUMMARY:")
        # print(f"Title: {case_data['metadata'].get('title', 'N/A')}")
        print("Structured Content Sections:")
        for section, content in case_data['structured_content'].items():
            print(f"  - {section}: {len(content)} characters")
        # print("="*70)

        # Insert case into database
        success = insert_case_into_db(
            doc_id=doc_id,
            case_title=doc_title,
            structured_content=case_data["structured_content"]
        )
        
        if not success:
            print(f"⚠️  Skipping case {doc_id} due to processing errors.\n")
            # time.sleep(3)
            continue
        
        print(f"✅ Case {doc_id} successfully processed and stored.\n")
        print("="*70)
    
    search_url = search_results["pagination"]["next_page_url"]
    if search_url is None:
        print("No more pages to scrape.")
        break
    response = s.get(search_url)
    print(response.status_code)
    search_results = get_doc_search_results(response.text)
    # with open("search_results.json", 'w', encoding='utf-8') as f:
    #     json.dump(search_results, f, indent=2, ensure_ascii=False)
    # print(search_results["pagination"]["next_page_url"])
    
    # f = int(input("enter: "))
    # if not f:
    #     exit()
    # print(f"\nFound {search_results['total_cases']} total cases")
