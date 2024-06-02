import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.firefox import GeckoDriverManager
import re
import pandas as pd
from PyPDF2 import PdfReader

# Set up Firefox options
options = Options()
options.add_argument('--headless')  # Enable headless mode
options.add_argument('--disable-gpu')  # Disable GPU for headless mode


# Set up WebDriver
driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)

def search_pdfs(keyword, max_count):
    search_url = f"https://www.google.com/search?q={keyword}+filetype:pdf+after:2015&hl=en"
    driver.get(search_url)

    pdf_links = set()  # Use a set to avoid duplicate links
    scroll_pause_time = 2
    total_results = 0

    while total_results < max_count:
        # Scroll down to the bottom of the page
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        
        # Wait for the results to load
        time.sleep(scroll_pause_time)
        
        # Get all link elements
        results = driver.find_elements(By.CSS_SELECTOR, 'a')
        
        for result in results:
            href = result.get_attribute('href')
            if href and href.endswith('.pdf') and href not in pdf_links:
                pdf_links.add(href)
                total_results += 1
                print("Found search count: ", total_results)
                if total_results >= max_count:
                    break
        
        # Click the "More results" button if it exists
        try:
            more_results_button = driver.find_element(By.XPATH, '//a[@aria-label="More results"]')
            if more_results_button:
                more_results_button.click()
                time.sleep(scroll_pause_time)  # Wait for new results to load
        except Exception as e:
            print(f"No more results button found: {e}")
            break  # Exit loop if no more results button is found

    return list(pdf_links)

def get_title_from_url(url):
    try:
        driver.get(url)
        time.sleep(2)
        title = driver.title
        return title
    except Exception as e:
        print(f"Failed to retrieve title from {url}: {e}")
        return None

def sanitize_filename(filename):
    return re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')

def get_pdf_page_count(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            page_count = len(reader.pages)
            return page_count
    except Exception as e:
        print(f"Failed to get page size for {file_path}: {e}")
        return None
    
def download_pdfs(pdf_links, download_folder):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    records = []  # List to hold records for the Excel file
    download_count = 0
    
    for link in pdf_links:
        try:
            title = get_title_from_url(link)
            if title:
                filename = sanitize_filename(title) + '.pdf'
            else:
                filename = os.path.basename(link)
            
            title = filename.replace('.pdf', '')
            
            filename = os.path.join(download_folder, filename)
            response = requests.get(link, stream=True)
            response.raise_for_status()

            # filename = os.path.join(download_folder, os.path.basename(link))
            with open(filename, 'wb') as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)
                    
            download_count += 1
            
            page_count = get_pdf_page_count(filename)
            
            print(f"Downloaded {download_count} : {title} , pages {page_count}")
            # Add record to the list
            records.append({'title': title, 'link': link, 'pages': page_count})

        except Exception as e:
            print(f"Failed to download {link}: {e}")
    
    # Save records to an Excel file
    df = pd.DataFrame(records)
    excel_filename = download_folder + '.xlsx'
    df.to_excel(excel_filename, index=False)
    print(f"Saved records {len(records)} to {excel_filename}")

def main():
    while True:
        keyword = input("Enter the search keyword: ")
        max_count = int(input("Enter the maximum number: "))
        # max_count = 1000
        download_folder = keyword.replace(" ", "_") + '_pdfs'  # Replace spaces with underscores for folder name

        pdf_links = search_pdfs(keyword, max_count)
        if pdf_links:
            print(f"Found {len(pdf_links)} PDF links.")
            download_pdfs(pdf_links, download_folder)
        else:
            print("No PDF links found.")
            
    driver.quit()

if __name__ == "__main__":
    main()
