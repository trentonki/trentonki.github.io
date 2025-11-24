# scripts/build_full_acs_dataset.py
from config.api_key import CENSUS_API_KEY
import requests
import pandas as pd
import numpy as np
import os

# -------------------------
# CONFIG
# -------------------------
API_KEY = CENSUS_API_KEY
YEAR = "2023"
DATASET = "acs/acs5"
BASE_URL = f"https://api.census.gov/data/{YEAR}/{DATASET}"

OUT_CSV = os.path.join("data", "final_state_dataset.csv")
os.makedirs("data", exist_ok=True)

# -------------------------
# STATE FIPS MAPPING
# -------------------------
STATE_FIPS = {
    "01":"Alabama","02":"Alaska","04":"Arizona","05":"Arkansas","06":"California",
    "08":"Colorado","09":"Connecticut","10":"Delaware","11":"District of Columbia",
    "12":"Florida","13":"Georgia","15":"Hawaii","16":"Idaho","17":"Illinois",
    "18":"Indiana","19":"Iowa","20":"Kansas","21":"Kentucky","22":"Louisiana",
    "23":"Maine","24":"Maryland","25":"Massachusetts","26":"Michigan","27":"Minnesota",
    "28":"Mississippi","29":"Missouri","30":"Montana","31":"Nebraska","32":"Nevada",
    "33":"New Hampshire","34":"New Jersey","35":"New Mexico","36":"New York",
    "37":"North Carolina","38":"North Dakota","39":"Ohio","40":"Oklahoma",
    "41":"Oregon","42":"Pennsylvania","44":"Rhode Island","45":"South Carolina",
    "46":"South Dakota","47":"Tennessee","48":"Texas","49":"Utah","50":"Vermont",
    "51":"Virginia","53":"Washington","54":"West Virginia","55":"Wisconsin",
    "56":"Wyoming"
}

# -------------------------
# URBAN/RURAL PERCENTAGES
# -------------------------
URBAN_RURAL_PCT = {
    "Alabama": {"pct_urban": 0.59, "pct_rural": 0.41},
    "Alaska": {"pct_urban": 0.66, "pct_rural": 0.34},
    "Arizona": {"pct_urban": 0.89, "pct_rural": 0.11},
    "Arkansas": {"pct_urban": 0.56, "pct_rural": 0.44},
    "California": {"pct_urban": 0.95, "pct_rural": 0.05},
    "Colorado": {"pct_urban": 0.88, "pct_rural": 0.12},
    "Connecticut": {"pct_urban": 0.87, "pct_rural": 0.13},
    "Delaware": {"pct_urban": 0.83, "pct_rural": 0.17},
    "District of Columbia": {"pct_urban": 1.0, "pct_rural": 0.0},
    "Florida": {"pct_urban": 0.91, "pct_rural": 0.09},
    "Georgia": {"pct_urban": 0.75, "pct_rural": 0.25},
    "Hawaii": {"pct_urban": 0.93, "pct_rural": 0.07},
    "Idaho": {"pct_urban": 0.72, "pct_rural": 0.28},
    "Illinois": {"pct_urban": 0.87, "pct_rural": 0.13},
    "Indiana": {"pct_urban": 0.72, "pct_rural": 0.28},
    "Iowa": {"pct_urban": 0.64, "pct_rural": 0.36},
    "Kansas": {"pct_urban": 0.67, "pct_rural": 0.33},
    "Kentucky": {"pct_urban": 0.59, "pct_rural": 0.41},
    "Louisiana": {"pct_urban": 0.79, "pct_rural": 0.21},
    "Maine": {"pct_urban": 0.61, "pct_rural": 0.39},
    "Maryland": {"pct_urban": 0.87, "pct_rural": 0.13},
    "Massachusetts": {"pct_urban": 0.92, "pct_rural": 0.08},
    "Michigan": {"pct_urban": 0.73, "pct_rural": 0.27},
    "Minnesota": {"pct_urban": 0.75, "pct_rural": 0.25},
    "Mississippi": {"pct_urban": 0.53, "pct_rural": 0.47},
    "Missouri": {"pct_urban": 0.70, "pct_rural": 0.30},
    "Montana": {"pct_urban": 0.54, "pct_rural": 0.46},
    "Nebraska": {"pct_urban": 0.65, "pct_rural": 0.35},
    "Nevada": {"pct_urban": 0.95, "pct_rural": 0.05},
    "New Hampshire": {"pct_urban": 0.61, "pct_rural": 0.39},
    "New Jersey": {"pct_urban": 0.95, "pct_rural": 0.05},
    "New Mexico": {"pct_urban": 0.78, "pct_rural": 0.22},
    "New York": {"pct_urban": 0.88, "pct_rural": 0.12},
    "North Carolina": {"pct_urban": 0.62, "pct_rural": 0.38},
    "North Dakota": {"pct_urban": 0.57, "pct_rural": 0.43},
    "Ohio": {"pct_urban": 0.77, "pct_rural": 0.23},
    "Oklahoma": {"pct_urban": 0.65, "pct_rural": 0.35},
    "Oregon": {"pct_urban": 0.81, "pct_rural": 0.19},
    "Pennsylvania": {"pct_urban": 0.79, "pct_rural": 0.21},
    "Rhode Island": {"pct_urban": 0.93, "pct_rural": 0.07},
    "South Carolina": {"pct_urban": 0.67, "pct_rural": 0.33},
    "South Dakota": {"pct_urban": 0.56, "pct_rural": 0.44},
    "Tennessee": {"pct_urban": 0.66, "pct_rural": 0.34},
    "Texas": {"pct_urban": 0.84, "pct_rural": 0.16},
    "Utah": {"pct_urban": 0.88, "pct_rural": 0.12},
    "Vermont": {"pct_urban": 0.62, "pct_rural": 0.38},
    "Virginia": {"pct_urban": 0.74, "pct_rural": 0.26},
    "Washington": {"pct_urban": 0.84, "pct_rural": 0.16},
    "West Virginia": {"pct_urban": 0.49, "pct_rural": 0.51},
    "Wisconsin": {"pct_urban": 0.70, "pct_rural": 0.30},
    "Wyoming": {"pct_urban": 0.64, "pct_rural": 0.36},
}

# -------------------------
# HELPERS
# -------------------------
def fetch_census(variables):
    """Fetch ACS variables for all states. Returns DataFrame with 'state' column."""
    var_string = ",".join(variables)
    url = f"{BASE_URL}?get=NAME,{var_string}&for=state:*&key={API_KEY}"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

def safe_int_series(series_like, length):
    """Return an int Series of length `length`. If input is scalar or missing produce zeros."""
    if isinstance(series_like, pd.Series):
        return pd.to_numeric(series_like, errors="coerce").fillna(0).astype(int)
    else:
        return pd.Series([0] * length, dtype=int)

def sum_vars(df, var_list):
    """Sum over a list of columns, treating missing columns as zero."""
    missing_cols = [v for v in var_list if v not in df.columns]
    all_cols = [v if v in df.columns else None for v in var_list]
    return df.reindex(columns=[c for c in all_cols if c is not None], fill_value=0).sum(axis=1).astype(int)

# -------------------------
# VARIABLES TO FETCH
# -------------------------
race_vars = ["B02001_001E","B02001_002E","B02001_003E","B02001_004E","B02001_005E","B02001_006E"]
male_age_vars = [f"B01001_{str(i).zfill(3)}E" for i in range(3,26)]
female_age_vars = [f"B01001_{str(i).zfill(3)}E" for i in range(27,50)]
age_vars = male_age_vars + female_age_vars + ["B01001_001E"]
educ_vars = [f"B15003_{str(i).zfill(3)}E" for i in range(1,26)]
gender_vars = ["B01001_002E","B01001_026E"]

# -------------------------
# FETCH DATA
# -------------------------
print("Fetching race...")
df_race = fetch_census(race_vars).fillna("0")
df_race["state"] = df_race["state"].astype(str).str.zfill(2)

print("Fetching age...")
df_age = fetch_census(age_vars).fillna("0")
df_age["state"] = df_age["state"].astype(str).str.zfill(2)

print("Fetching education...")
df_educ = fetch_census(educ_vars).fillna("0")
df_educ["state"] = df_educ["state"].astype(str).str.zfill(2)

print("Fetching gender...")
df_gender = fetch_census(gender_vars).fillna("0")
df_gender["state"] = df_gender["state"].astype(str).str.zfill(2)

# -------------------------
# CONCATENATE & DEDUP COLUMNS
# -------------------------
big = pd.concat([df_race.set_index("state"),
                 df_age.set_index("state"),
                 df_educ.set_index("state"),
                 df_gender.set_index("state")], axis=1).fillna(0)

# deduplicate columns
cols = pd.Series(big.columns)
for dup in cols[cols.duplicated()].unique():
    dup_idx = cols[cols == dup].index.tolist()
    for i, idx in enumerate(dup_idx[1:], start=1):
        cols[idx] = f"{dup}_{i}"
big.columns = cols

# convert to numeric
for col in big.columns:
    big[col] = pd.to_numeric(big[col], errors="coerce").fillna(0).astype(int)

# -------------------------
# BUILD FINAL DATAFRAME
# -------------------------
final = pd.DataFrame(index=big.index)
final.index.name = "state_fips"
final["state_name"] = final.index.map(STATE_FIPS)
final["total_population"] = big.get("B02001_001E", pd.Series(0, index=big.index)).astype(int)

# -------------------------
# RACE
# -------------------------
white = big.get("B02001_002E", pd.Series(0, index=big.index)).astype(int)
black = big.get("B02001_003E", pd.Series(0, index=big.index)).astype(int)
native = big.get("B02001_004E", pd.Series(0, index=big.index)).astype(int)
asian = big.get("B02001_005E", pd.Series(0, index=big.index)).astype(int)
pacific = big.get("B02001_006E", pd.Series(0, index=big.index)).astype(int)
two_or_more = final["total_population"] - (white+black+native+asian+pacific)
two_or_more = two_or_more.clip(lower=0)

final["pct_white"] = white / final["total_population"]
final["pct_black"] = black / final["total_population"]
final["pct_native"] = native / final["total_population"]
final["pct_asian"] = asian / final["total_population"]
final["pct_two_or_more"] = two_or_more / final["total_population"]

# -------------------------
# GENDER
# -------------------------
male_pop = big.get("B01001_002E", pd.Series(0, index=big.index)).astype(int)
female_pop = big.get("B01001_026E", pd.Series(0, index=big.index)).astype(int)
sex_sum = (male_pop + female_pop).replace({0:1})
final["male_pop"] = male_pop
final["female_pop"] = female_pop
final["pct_male"] = male_pop / sex_sum
final["pct_female"] = female_pop / sex_sum

# -------------------------
# AGE BUCKETS
# -------------------------
vars_18_29 = [f"B01001_{str(i).zfill(3)}E" for i in range(7,12)] + [f"B01001_{str(i).zfill(3)}E" for i in range(31,36)]
vars_30_44 = [f"B01001_{str(i).zfill(3)}E" for i in range(12,15)] + [f"B01001_{str(i).zfill(3)}E" for i in range(36,39)]
vars_45_64 = [f"B01001_{str(i).zfill(3)}E" for i in range(15,19)] + [f"B01001_{str(i).zfill(3)}E" for i in range(39,43)]
vars_65_plus = [f"B01001_{str(i).zfill(3)}E" for i in range(19,26)] + [f"B01001_{str(i).zfill(3)}E" for i in range(43,50)]

age_total = big.get("B01001_001E", pd.Series(1, index=big.index)).astype(int)
final["pct_18_29"] = sum_vars(big, vars_18_29) / age_total
final["pct_30_44"] = sum_vars(big, vars_30_44) / age_total
final["pct_45_64"] = sum_vars(big, vars_45_64) / age_total
final["pct_65_plus"] = sum_vars(big, vars_65_plus) / age_total

# -------------------------
# EDUCATION BUCKETS
# -------------------------
edu_total = big.get("B15003_001E", pd.Series(1, index=big.index)).astype(int)
less_cols = [f"B15003_{str(i).zfill(3)}E" for i in range(2,17)]
some_cols = [f"B15003_{str(i).zfill(3)}E" for i in range(17,21)]
assoc_col = "B15003_021E"
bachelors_col = "B15003_022E"
grad_cols = [f"B15003_{str(i).zfill(3)}E" for i in range(23,26)]

final["pct_hs_or_less"] = sum_vars(big, less_cols) / edu_total
final["pct_some_college"] = sum_vars(big, some_cols) / edu_total
final["pct_assoc"] = big.get(assoc_col, pd.Series(0, index=big.index)).astype(int) / edu_total
final["pct_bachelor"] = big.get(bachelors_col, pd.Series(0, index=big.index)).astype(int) / edu_total
final["pct_grad"] = sum_vars(big, grad_cols) / edu_total

# -------------------------
# URBAN/RURAL
# -------------------------
urban_pop = []
rural_pop = []
pct_urban_list = []
pct_rural_list = []

for fips, row in final.iterrows():
    state_name = STATE_FIPS.get(fips)
    if state_name is None:
        print(f"Skipping unknown FIPS {fips}")
        continue
    total = int(row["total_population"])
    p = URBAN_RURAL_PCT.get(state_name)
    if p is None:
        raise RuntimeError(f"No urban/rural percentage for {state_name}")
    u = int(round(p["pct_urban"] * total))
    r = total - u
    urban_pop.append(u)
    rural_pop.append(r)
    pct_urban_list.append(p["pct_urban"])
    pct_rural_list.append(p["pct_rural"])

# align length to index
final["urban_pop"] = pd.Series(urban_pop, index=final.index[:len(urban_pop)])
final["rural_pop"] = pd.Series(rural_pop, index=final.index[:len(rural_pop)])
final["pct_urban"] = pd.Series(pct_urban_list, index=final.index[:len(pct_urban_list)])
final["pct_rural"] = pd.Series(pct_rural_list, index=final.index[:len(pct_rural_list)])

# -------------------------
# FINAL COLUMN ORDER
# -------------------------
cols = [
    "state_fips","state_name","total_population",
    "pct_white","pct_black","pct_native","pct_asian","pct_two_or_more",
    "male_pop","female_pop","pct_male","pct_female",
    "pct_18_29","pct_30_44","pct_45_64","pct_65_plus",
    "pct_hs_or_less","pct_some_college","pct_assoc","pct_bachelor","pct_grad",
    "urban_pop","rural_pop","pct_urban","pct_rural"
]

for c in cols:
    if c not in final.columns:
        final[c] = 0

final = final.reset_index(drop=True)
final = final[cols]

# -------------------------
# SAVE
# -------------------------
if "state_fips" in final.columns:
    final = final.drop(columns=["state_fips"])
final.to_csv(OUT_CSV, index=False)
print("Wrote", OUT_CSV, "shape:", final.shape)