import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
from urllib.error import URLError

def fetch_sitemap(url):
    print(f"Fetching sitemap: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        response = urllib.request.urlopen(req)
        tree = ET.parse(response)
        root = tree.getroot()
        urls = [elem.text for elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        return urls
    except URLError as e:
        print(f"Error fetching {url}: {e}")
        return []

def extract_category_and_slug(url):
    parts = url.split('/')
    if len(parts) < 4:
        return None, None
    valid_categories = ['courses', 'path', 'cloudlabs', 'projects']
    category = None
    slug = None
    for i, part in enumerate(parts):
        if part in valid_categories:
            category = part
            if i + 1 < len(parts):
                slug = parts[i + 1]
            break
    return category, slug

def main():
    general_url = "https://www.educative.io/sitemaps/general/sitemap.xml"
    lesson_sitemaps = {
        "pal_lessons": "https://www.educative.io/sitemaps/pal_lessons/sitemap.xml",
        "course_lessons_1": "https://www.educative.io/sitemaps/course_lessons_1/sitemap.xml",
        "course_lessons_2": "https://www.educative.io/sitemaps/course_lessons_2/sitemap.xml"
    }
    
    general_urls = fetch_sitemap(general_url)
    general_items = {} 
    for u in general_urls:
        cat, slug = extract_category_and_slug(u)
        if cat and slug:
            general_items[(cat, slug)] = u
            
    print(f"Found {len(general_items)} total items in general sitemap.")
    
    lesson_data = []
    for sitemap_name, ls_url in lesson_sitemaps.items():
        l_urls = fetch_sitemap(ls_url)
        print(f"  Fetched {len(l_urls)} lessons from {sitemap_name}")
        for u in l_urls:
            cat, slug = extract_category_and_slug(u)
            if cat and slug:
                lesson_data.append({
                    'Category': cat.capitalize(),
                    'Slug': slug,
                    'Lesson URL': u,
                    'Source Sitemap': sitemap_name
                })
                
    df_lessons = pd.DataFrame(lesson_data)
    if not df_lessons.empty:
        df_lessons = df_lessons.sort_values(by=['Category', 'Slug'])
    
    all_keys = set(general_items.keys())
    if not df_lessons.empty:
        lesson_keys = set(zip(df_lessons['Category'].str.lower(), df_lessons['Slug']))
        all_keys = all_keys.union(lesson_keys)
    
    valid_categories = ['courses', 'path', 'cloudlabs', 'projects']
    summary_dfs = {}
    
    for cat in valid_categories:
        cat_capitalized = cat.capitalize()
        cat_keys = [(c, s) for (c, s) in all_keys if c == cat]
        
        cat_summary_data = []
        for c, slug in cat_keys:
            general_link = general_items.get((c, slug), "")
            
            if not df_lessons.empty:
                slug_lessons = df_lessons[(df_lessons['Category'] == cat_capitalized) & (df_lessons['Slug'] == slug)]
            else:
                slug_lessons = pd.DataFrame()
            
            num_topics = len(slug_lessons)
            
            row_data = {
                'Slug': slug,
                'Number of Topics': num_topics,
                'General Link': general_link
            }
            
            if cat == 'courses':
                topic_link = ""
                is_pal_link = "No"
                
                if num_topics > 0:
                    regular_lessons = slug_lessons[slug_lessons['Source Sitemap'] != 'pal_lessons']
                    if not regular_lessons.empty:
                        topic_link = regular_lessons.iloc[0]['Lesson URL']
                    else:
                        topic_link = slug_lessons.iloc[0]['Lesson URL']
                        
                    pal_lessons_df = slug_lessons[slug_lessons['Source Sitemap'] == 'pal_lessons']
                    if not pal_lessons_df.empty:
                        is_pal_link = "Yes"
                        
                row_data['Topic Link'] = topic_link
                row_data['Is PAL Link'] = is_pal_link
            
            cat_summary_data.append(row_data)
            
        df_cat = pd.DataFrame(cat_summary_data)
        if not df_cat.empty:
            if cat == 'courses':
                # sort by Is PAL Link (Yes first) then Slug
                df_cat = df_cat.sort_values(by=['Is PAL Link', 'Slug'], ascending=[False, True])
                # ensure column order for courses
                df_cat = df_cat[['Slug', 'General Link', 'Number of Topics', 'Is PAL Link', 'Topic Link']]
            else:
                df_cat = df_cat.sort_values(by=['Slug'])
                # ensure column order for others (removed Number of Topics)
                df_cat = df_cat[['Slug', 'General Link']]
                
        summary_dfs[cat_capitalized] = df_cat
    
    output_file = "educative_sitemap_analysis_updated.xlsx"
    print(f"Writing to {output_file}...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        if not df_lessons.empty:
            df_lessons.to_excel(writer, sheet_name='Grouped Lessons', index=False)
        for cat_name, df_cat in summary_dfs.items():
            if not df_cat.empty:
                df_cat.to_excel(writer, sheet_name=f'{cat_name} Links', index=False)
                
        # format columns and wrap text
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.auto_filter.ref = worksheet.dimensions
            for col_idx, col in enumerate(worksheet.columns, 1):
                letter = openpyxl.utils.get_column_letter(col_idx)
                header = str(worksheet.cell(row=1, column=col_idx).value)
                
                # set widths
                if header == 'Slug':
                    worksheet.column_dimensions[letter].width = 40
                elif header == 'Number of Topics':
                    worksheet.column_dimensions[letter].width = 15
                elif header in ['General Link', 'Topic Link', 'Lesson URL']:
                    worksheet.column_dimensions[letter].width = 60
                elif header == 'Is PAL Link':
                    worksheet.column_dimensions[letter].width = 15
                else:
                    worksheet.column_dimensions[letter].width = 30
                    
                # apply alignment
                if header in ['Number of Topics', 'Is PAL Link']:
                    cell_alignment = Alignment(horizontal='center', vertical='top', wrap_text=True)
                else:
                    cell_alignment = Alignment(wrap_text=True, vertical='top')
                    
                for cell in col:
                    cell.alignment = cell_alignment
        
    print("Done! You can find the results in", output_file)

if __name__ == "__main__":
    main()
