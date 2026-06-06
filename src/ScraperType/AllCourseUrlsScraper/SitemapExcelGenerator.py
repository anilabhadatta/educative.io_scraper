import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
from urllib.error import URLError
import json
from hashids import Hashids

class SitemapExcelGenerator:
    def __init__(self, configJson, progressQueue=None):
        self.configJson = configJson
        self.progressQueue = progressQueue
        self.general_url = "https://www.educative.io/sitemaps/general/sitemap.xml"
        self.lesson_sitemaps = {
            "pal_lessons": "https://www.educative.io/sitemaps/pal_lessons/sitemap.xml",
            "course_lessons_1": "https://www.educative.io/sitemaps/course_lessons_1/sitemap.xml",
            "course_lessons_2": "https://www.educative.io/sitemaps/course_lessons_2/sitemap.xml"
        }

    def fetch_sitemap(self, url):
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

    def extract_category_and_slug(self, url):
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

    def fetch_path_modules_and_lessons(self, path_slug):
        try:
            print(f"Fetching API for path: {path_slug}")
            req = urllib.request.Request(f'https://www.educative.io/api/collection/{path_slug}', headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read().decode('utf-8'))
            author_id = data['instance']['details']['author_id']
            collection_id = data['instance']['details']['collection_id']
            
            # Educative frontend uses Hashids to encode the path's author_id and collection_id
            hashids = Hashids(salt="", alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
            path_hash = hashids.encode(int(author_id), int(collection_id))
            
            req = urllib.request.Request(f'https://www.educative.io/api/collection/{author_id}/{collection_id}/categories?update_path_item_titles=true', headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            categories_data = json.loads(response.read().decode('utf-8'))
            
            path_modules_key = f"{author_id}_{collection_id}"
            if path_modules_key not in categories_data:
                return [], []
                
            modules = categories_data[path_modules_key]
            modules_list = []
            lessons_list = []
            
            for mod in modules:
                mod_title = mod.get('title', 'Unknown Module')
                mod_author_id = mod.get('author_id')
                mod_collection_id = mod.get('id')
                mod_key = f"{mod_author_id}_{mod_collection_id}"
                
                num_topics = 0
                first_topic_link = ""
                
                if mod_key in categories_data:
                    for category in categories_data[mod_key]:
                        pages = category.get('pages', [])
                        for page in pages:
                            num_topics += 1
                            page_id = page.get('id')
                            lesson_link = f"https://www.educative.io/module/page/{path_hash}/{mod_author_id}/{mod_collection_id}/{page_id}"
                            if not first_topic_link:
                                first_topic_link = lesson_link
                            lessons_list.append({
                                'Path Slug': path_slug,
                                'Module Title': mod_title,
                                'Lesson URL': lesson_link
                            })
                if num_topics > 0:
                    modules_list.append({
                        'Module Title': mod_title,
                        'Number of Topics': num_topics,
                        'Topic Link': first_topic_link
                    })
            return modules_list, lessons_list
        except Exception as e:
            print(f"Error fetching API for path {path_slug}: {e}")
            return [], []

    def start(self):
        general_urls = self.fetch_sitemap(self.general_url)
        general_items = {} 
        for u in general_urls:
            cat, slug = self.extract_category_and_slug(u)
            if cat and slug:
                general_items[(cat, slug)] = u
                
        print(f"Found {len(general_items)} total items in general sitemap.")
        
        lesson_data = []
        for sitemap_name, ls_url in self.lesson_sitemaps.items():
            l_urls = self.fetch_sitemap(ls_url)
            print(f"  Fetched {len(l_urls)} lessons from {sitemap_name}")
            for u in l_urls:
                cat, slug = self.extract_category_and_slug(u)
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
        all_path_lessons = []
        
        if not df_lessons.empty:
            grouped_lessons = df_lessons.groupby(['Category', 'Slug'])
        else:
            grouped_lessons = None
        
        for cat in valid_categories:
            cat_capitalized = cat.capitalize()
            cat_keys = [(c, s) for (c, s) in all_keys if c == cat]
            
            cat_summary_data = []
            for c, slug in cat_keys:
                general_link = general_items.get((c, slug), "")
                
                if grouped_lessons is not None and (cat_capitalized, slug) in grouped_lessons.groups:
                    slug_lessons = grouped_lessons.get_group((cat_capitalized, slug))
                else:
                    slug_lessons = pd.DataFrame()
                
                num_topics = len(slug_lessons)
                
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
                            
                    cat_summary_data.append({
                        'Slug': slug,
                        'General Link': general_link,
                        'Number of Topics': num_topics,
                        'Is PAL Link': is_pal_link,
                        'Topic Link': topic_link
                    })
                elif cat == 'path':
                    modules_list, lessons_list = self.fetch_path_modules_and_lessons(slug)
                    all_path_lessons.extend(lessons_list)
                    
                    if not modules_list:
                        cat_summary_data.append({
                            'Path Slug': slug,
                            'Path General Link': general_link,
                            'Module Title': '',
                            'Number of Topics': 0,
                            'Topic Link': ''
                        })
                    else:
                        for mod in modules_list:
                            cat_summary_data.append({
                                'Path Slug': slug,
                                'Path General Link': general_link,
                                'Module Title': mod['Module Title'],
                                'Number of Topics': mod['Number of Topics'],
                                'Topic Link': mod['Topic Link']
                            })
                else:
                    cat_summary_data.append({
                        'Slug': slug,
                        'General Link': general_link
                    })
                
            df_cat = pd.DataFrame(cat_summary_data)
            if not df_cat.empty:
                if cat == 'courses':
                    df_cat = df_cat.sort_values(by=['Is PAL Link', 'Slug'], ascending=[False, True])
                    df_cat = df_cat[['Slug', 'General Link', 'Number of Topics', 'Is PAL Link', 'Topic Link']]
                elif cat == 'path':
                    df_cat = df_cat.sort_values(by=['Path Slug', 'Module Title'])
                    df_cat = df_cat[['Path Slug', 'Path General Link', 'Module Title', 'Number of Topics', 'Topic Link']]
                else:
                    df_cat = df_cat.sort_values(by=['Slug'])
                    df_cat = df_cat[['Slug', 'General Link']]
                    
            summary_dfs[cat_capitalized] = df_cat
        
        if all_path_lessons:
            df_path_lessons = pd.DataFrame(all_path_lessons)
        else:
            df_path_lessons = pd.DataFrame(columns=['Path Slug', 'Module Title', 'Lesson URL'])
            
        output_file = "educative_sitemap_analysis_updated.xlsx"
        print(f"Writing to {output_file}...")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            if not df_lessons.empty:
                df_lessons.to_excel(writer, sheet_name='Grouped Lessons', index=False)
            if not df_path_lessons.empty:
                df_path_lessons.to_excel(writer, sheet_name='Grouped Path Lessons', index=False)
                
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
                    if header in ['Slug', 'Path Slug']:
                        worksheet.column_dimensions[letter].width = 40
                    elif header == 'Module Title':
                        worksheet.column_dimensions[letter].width = 40
                    elif header == 'Number of Topics':
                        worksheet.column_dimensions[letter].width = 15
                    elif header in ['General Link', 'Path General Link', 'Topic Link', 'Lesson URL']:
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
