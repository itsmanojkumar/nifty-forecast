import json; from docx import Document
L=json.load(open("week1_log.json")); d=Document()
d.add_heading("Week 1: Python for Machine Learning & Data Preprocessing",0)
d.add_paragraph("Intern: Manoj Kumar M    Internship: AI Pioneers (Machine Learning)    Dataset: official NSE Nifty Metal daily closing index values")
d.add_heading("1. Objective",1); d.add_paragraph("Load, clean and preprocess a real financial dataset with Python, NumPy and Pandas, and document every step. The cleaned data feeds my Nifty sector forecasting project.")
d.add_heading("2. Dataset",1); d.add_paragraph(f"Source: NSE public archive (daily index close files), Nov 2015 to Oct 2026. {L['rows_raw']} trading days, two columns (date, close). Column types before cleaning: {L['dtypes_before']}.")
d.add_heading("3. Preprocessing steps",1)
for t in [f"Data loading: read the CSV with Pandas; converted the date column from text to datetime and set it as the index.",
 f"Missing values and duplicates: {L['missing_values']} missing values and {L['duplicate_dates']} duplicate dates were found, so nothing was dropped at this stage. Data was sorted by date.",
 f"Gap check: the largest gap between trading days was {L['max_gap_days']} days (weekends and holidays), with no unexplained gaps.",
 f"Feature engineering with NumPy/Pandas: daily log return, 20-day moving average, 20-day volatility and 60-day momentum.",
 f"Outlier handling: {L['outliers_|z|>4']} days had a return z-score above 4. Instead of deleting them, I winsorised returns at the 0.1% and 99.9% quantiles so genuine market shocks are kept but extreme values cannot dominate training.",
 f"Feature selection: kept close, clipped return, MA20, volatility and momentum; dropped the raw return after clipping. Correlation between daily return and 60-day momentum was {L['corr_ret_vs_mom60']}, so they carry different information.",
 f"Encoding categorical variables: weekday and a high/low volatility regime (above/below median volatility) were one-hot encoded with drop_first=True to avoid the dummy variable trap.",
 f"Normalisation: applied StandardScaler (mean {L['scaled_mean_std'][0]}, std {L['scaled_mean_std'][1]}) and MinMaxScaler (range {L['minmax_range'][0]} to {L['minmax_range'][1]}) to the numeric features.",
 f"Rows lost to rolling windows: {L['rows_raw']-L['rows_clean']}; final clean dataset has {L['rows_clean']} rows."]: d.add_paragraph(t,style="List Number")
d.add_heading("4. Exploratory data analysis",1)
c=L["close_summary"]; d.add_paragraph(f"Index level: mean {c['mean']}, median {c['50%']}, min {c['min']}, max {c['max']}. Annualised return {L['ann_return_%']}% with annualised volatility {L['ann_vol_%']}%. Best day {L['best_day_%']}%, worst day {L['worst_day_%']}%.")
w=L["avg_ret_by_weekday_%"]; d.add_paragraph("Average daily return by weekday (%): "+", ".join(f"{k} {v}" for k,v in w.items())+". Tuesday and Wednesday were strongest in this sample, but I treat this as noise rather than a trading rule.")
r=L["avg_ret_by_regime_%"]; d.add_paragraph(f"High-volatility days averaged {r['high_vol']}% and low-volatility days {r['low_vol']}%.")
d.add_heading("5. Key learnings",1); d.add_paragraph("Time series must be sorted and checked for gaps; outliers in financial data are often real events, so clipping is safer than deleting; scalers should be fitted on training data only to avoid leakage when models are trained in later weeks.")
d.add_heading("6. Files",1); d.add_paragraph("week1_preprocessing.py (code), nifty_metal_official.csv (raw), nifty_metal_clean.csv (output), week1_log.json (results).")
d.save("Week1_Report_Data_Preprocessing.docx")
desc=("For Week 1 I cleaned and preprocessed a real financial dataset: the official NSE daily closing values of the Nifty Metal index from November 2015 to October 2026, "
f"{L['rows_raw']} trading days in total. Using Python, NumPy and Pandas, I loaded the data, converted dates to a datetime index, and checked for missing values, duplicates and gaps. "
f"There were no missing values or duplicates, and the largest gap was {L['max_gap_days']} days, which is just weekends and holidays. I then engineered features: daily log return, a 20-day moving average, 20-day volatility and 60-day momentum. "
f"I found {L['outliers_|z|>4']} outlier days using z-scores, and chose to winsorise them at the 0.1% and 99.9% quantiles instead of deleting them, because they are real market shocks. "
"Categorical variables, namely the weekday and a high or low volatility regime, were one-hot encoded with drop_first to avoid the dummy variable trap. "
"Numeric features were normalised with StandardScaler and MinMaxScaler, and I verified the resulting means, standard deviations and ranges. "
f"The final dataset has {L['rows_clean']} rows after removing rows lost to rolling windows. In the exploratory analysis the index shows an annualised return of {L['ann_return_%']}% with annualised volatility of {L['ann_vol_%']}%, "
f"and daily moves ranging from {L['worst_day_%']}% to {L['best_day_%']}%. Weekday averages differed slightly, but I treat that as noise. The cleaned data and code feed my Nifty sector forecasting project, and each step is documented in the attached report.")
open("week1_description.txt","w").write(desc); print(len(desc.split()),"words")
