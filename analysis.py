import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import re
import os
import sys
import ast
from datetime import datetime#

# Configuration
TODAY_DATE = datetime.now().strftime('%Y%m%d')
PROJECT_NAME = "LangPop"
VERSION = "v1.0"
current_script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_script_path))

RAW_PATH = os.path.join(project_root, "data", "raw")
PROCESSED_PATH = os.path.join(project_root, "data", "processed")
RESULTS_PATH = os.path.join(project_root, "results")

# Languages to filter out for research
TARGET_LANGUAGES = ['Python', 'Java', 'JavaScript', 'C#', 'TypeScript']

os.makedirs(PROCESSED_PATH, exist_ok=True)
os.makedirs(RESULTS_PATH, exist_ok=True)

print(f"--- starting analisys---")

# get the PYPL web data (web scraping)

print("[1/3] getting pypl data...")

try:
    url = "https://raw.githubusercontent.com/pypl/pypl.github.io/master/PYPL/All.js"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Server error: {response.status_code}")

    content = response.text
# Cleaning JavaScript format into Python format

    content_clean = re.sub(r'//.*', '', content)
    content_clean = re.sub(r'new Date\((\d+),(\d+),(\d+)\)', r"'\1-\2-\3'", content_clean)

    match = re.search(r'graphData\s*=\s*(\[.*\])', content_clean, re.DOTALL)
    if not match:
        raise Exception("No 'graphData' list.")

    list_str = match.group(1)
    pypl_list = ast.literal_eval(list_str)

    headers = pypl_list[0]
    data_rows = pypl_list[1:]

    df_pypl_full = pd.DataFrame(data_rows, columns=headers)


    def get_year(date_str):
        try:
            return int(str(date_str).split('-')[0])
        except:
            return None


    df_pypl_full['Year'] = df_pypl_full['Date'].apply(get_year)

    # Filtering of languages
    available_cols = df_pypl_full.columns
    mapped_targets = []
    for lang in TARGET_LANGUAGES:
        if lang in available_cols:
            mapped_targets.append(lang)
        elif lang == 'C#' and 'Csharp' in available_cols:
            mapped_targets.append('Csharp')

    cols_to_keep = ['Year'] + mapped_targets
    # Grouping by year
    df_pypl_yearly = df_pypl_full[cols_to_keep].groupby('Year').mean().reset_index()

    if 'Csharp' in df_pypl_yearly.columns:
        df_pypl_yearly.rename(columns={'Csharp': 'C#'}, inplace=True)

    df_pypl_long = df_pypl_yearly.melt(id_vars=['Year'], var_name='Language', value_name='PYPL_Share')


    df_pypl_long['PYPL_Share'] = df_pypl_long['PYPL_Share'] * 100

    # Filtering years
    df_pypl_long = df_pypl_long[df_pypl_long['Year'].isin([2021, 2022, 2023, 2024, 2025])]

    print("PYPL data ready.")

except Exception as e:
    print(f" error with PYPL data: {e}")
    # Backup data
    backup = []
    for y in range(2021, 2026):
        backup.append({'Year': y, 'Language': 'Python', 'PYPL_Share': 28.0})
    df_pypl_long = pd.DataFrame(backup)

# Stack Overflow data
print(f"\n[2/3] Loading local Stack Overflow CSVs...")

so_results = []
years = [2021, 2022, 2023, 2024, 2025]
files_found = 0

for year in years:
    file_path = os.path.join(RAW_PATH, f"so_{year}.csv")
    if not os.path.exists(file_path):
        print(f"  [!] file missing: so_{year}.csv")
        continue

    print(f"  processing {year}...")
    files_found += 1

    try:
        col_name = 'LanguageHaveWorkedWith'
        try:
            df = pd.read_csv(file_path, usecols=[col_name])
        except ValueError:
            col_name = 'LanguageWorkedWith'
            try:
                df = pd.read_csv(file_path, usecols=[col_name])
                df.rename(columns={col_name: 'LanguageHaveWorkedWith'}, inplace=True)
            except:
                print(f" Can't find language row for {year}.")
                continue


        df_clean = df.dropna(subset=['LanguageHaveWorkedWith'])

        # Calculating number of developers
        total = len(df_clean)

        if total == 0:
            print(f"   No data for: {year}.")
            continue

        for lang in TARGET_LANGUAGES:
            # 3. Looking for languages, watching out for 'Java' vs 'JavaScript'
            pattern = r'(?:^|;)' + re.escape(lang) + r'(?:;|$)'
            count = df_clean['LanguageHaveWorkedWith'].str.contains(pattern, regex=True).sum()

            # 4. Percentage calculation
            perc = (count / total) * 100
            so_results.append({'Year': year, 'Language': lang, 'Percentage': perc})

    except Exception as e:
        print(f"  fault in calculation {year}: {e}")

if files_found == 0:
    print("\n No CVS files found.")
    print(f"Check if files are in the file: {RAW_PATH}")
    sys.exit(1)

df_so = pd.DataFrame(so_results)

#Merging and drawing of results

print(f"\n[3/3] Generating graphs...")

# Merging tables
df_final = pd.merge(df_so, df_pypl_long, on=['Year', 'Language'])

# Saving data
csv_name = f"{TODAY_DATE}_{PROJECT_NAME}_ProcessedData_{VERSION}.csv"
out_csv = os.path.join(PROCESSED_PATH, csv_name)
df_final.to_csv(out_csv, index=False)
print(f"  Data saved to: {out_csv}")

# Settings of graph
plt.figure(figsize=(16, 6))
sns.set_style("whitegrid")

#left graph
ax1 = plt.subplot(1, 2, 1)
sns.lineplot(data=df_final, x='Year', y='Percentage', hue='Language', marker='o', linewidth=2.5, ax=ax1)
ax1.set_title('Professional Usage (Stack Overflow Survey)', fontsize=14)
ax1.set_ylabel('% of Developers', fontsize=12)
ax1.set_xlabel('Year', fontsize=12)
ax1.set_xticks(years)
ax1.set_ylim(0, 80)
ax1.legend(title='Language', bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
ax1.grid(True, which='both', linestyle='--', linewidth=0.5)

# right graph
ax2 = plt.subplot(1, 2, 2)
sns.lineplot(data=df_final, x='Year', y='PYPL_Share', hue='Language', marker='o', linewidth=2.5, linestyle='--', ax=ax2)
ax2.set_title('Search Popularity (PYPL Index)', fontsize=14)
ax2.set_ylabel('% Share of Searches', fontsize=12)
ax2.set_xlabel('Year', fontsize=12)
ax2.set_xticks(years)
ax2.set_ylim(0, df_final['PYPL_Share'].max() * 1.15)
ax2.legend(title='Language', bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
ax2.grid(True, which='both', linestyle='--', linewidth=0.5)

plt.tight_layout()
img_name = f"{TODAY_DATE}_{PROJECT_NAME}_Chart_{VERSION}.png"
out_img = os.path.join(RESULTS_PATH, img_name)
plt.savefig(out_img, bbox_inches='tight', dpi=300)

print(f" All done, image saved to: {out_img}")