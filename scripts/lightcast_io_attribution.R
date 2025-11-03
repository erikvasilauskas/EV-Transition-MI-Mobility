# Lightcast Input-Output Attribution Script
#
# This script replicates the Lightcast IO attribution workflow for either
# Michigan (region = "mi") or the United States (region = "us"). It expects the
# cleaned regional matrix and 2024 employment files to live under the directory
# structure described below. Adjust `base_dir` if your files are stored in a
# different location.

# ---- Packages ----
library(dplyr)
library(readr)
library(stringr)
library(tidyr)
library(purrr)
library(tibble)

# ---- NAICS dictionary ----
naics_dict <- tribble(
  ~naics_code, ~naics_name,
  3363, "Motor Vehicle Parts Manufacturing",
  3361, "Motor Vehicle Manufacturing",
  4231, "Motor Vehicle and Motor Vehicle Parts and Supplies Merchant Wholesalers",
  4411, "Automobile Dealers",
  3327, "Machine Shops; Turned Product; and Screw, Nut, and Bolt Manufacturing",
  3261, "Plastics Product Manufacturing",
  4841, "General Freight Trucking",
  4413, "Automotive Parts, Accessories, and Tire Stores",
  3362, "Motor Vehicle Body and Trailer Manufacturing",
  3339, "Other General Purpose Machinery Manufacturing",
  3335, "Metalworking Machinery Manufacturing",
  3315, "Foundries",
  3344, "Semiconductor and Other Electronic Component Manufacturing",
  3336, "Engine, Turbine, and Power Transmission Equipment Manufacturing",
  5413, "Architectural, Engineering, and Related Services",
  3328, "Coating, Engraving, Heat Treating, and Allied Activities",
  3321, "Forging and Stamping",
  3262, "Rubber Product Manufacturing",
  3329, "Other Fabricated Metal Product Manufacturing",
  3255, "Paint, Coating, and Adhesive Manufacturing",
  4235, "Metal and Mineral (except Petroleum) Merchant Wholesalers",
  4238, "Machinery, Equipment, and Supplies Merchant Wholesalers",
  4239, "Miscellaneous Durable Goods Merchant Wholesalers",
  4234, "Professional and Commercial Equipment and Supplies Merchant Wholesalers",
  8111, "Automotive Repair and Maintenance",
  3311, "Iron and Steel Mills and Ferroalloy Manufacturing",
  3359, "Other Electrical Equipment and Component Manufacturing",
  3272, "Glass and Glass Product Manufacturing",
  3326, "Spring and Wire Product Manufacturing",
  3313, "Alumina and Aluminum Production and Processing",
  3312, "Steel Product Manufacturing from Purchased Steel",
  3345, "Navigational, Measuring, Electromedical, and Control Instruments Manufacturing",
  5414, "Specialized Design Services",
  3314, "Nonferrous Metal (except Aluminum) Production and Processing",
  4571, "Gasoline Stations",
  3252, "Resin, Synthetic Rubber, and Artificial and Synthetic Fibers and Filaments Manufacturing",
  5417, "Scientific Research and Development Services",
  4247, "Petroleum and Petroleum Products Merchant Wholesalers",
  4842, "Specialized Freight Trucking"
)

naics_lookup <- naics_dict %>%
  transmute(naics4 = as.character(naics_code), naics_name)

# ======================== CONFIG ========================
# Adjust the base directory if your Lightcast IO files live elsewhere.
base_dir <- "C:/Users/vasilauskas/W.E. Upjohn Institute/Electric Vehicles - Documents/_EV Workforce Hub/Lightcast Job Postings, Occupation Tables, Input-Output"

# Choose "mi" or "us" for the IO matrix you want to analyze.
region <- "us"

# Employment source can differ from the matrix region. Set to "mi" to keep using
# Michigan QCEW employment while looking at national IO shares.
employment_region <- if (region == "us") "mi" else region

# Optionally point directly to a specific employment file (e.g., an aggregated
# supplier list). Leave as NULL to use the default region-based path.
employment_path_override <- "C:/Users/vasilauskas/W.E. Upjohn Institute/Electric Vehicles - Documents/_EV Workforce Hub/Newer Input-output analyses with updated supply chain framework/emp_2024_10.csv"

# Filenames follow a simple pattern; change here only if the actual names differ.
matrix_file <- if (region == "mi") "mi_regional_matrix_cleaned_industries.csv" else "us_regional_matrix_cleaned_industries.csv"
emp_file    <- if (employment_region == "mi") "emp_2024_mi.csv" else "emp_2024_us.csv"

in_dir  <- file.path(base_dir, "inputs", region)
out_dir <- file.path(base_dir, "outputs", region)
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

matrix_path <- file.path(in_dir, matrix_file)
emp_path_default <- file.path(base_dir, "inputs", employment_region, emp_file)
emp_path <- if (is.null(employment_path_override)) emp_path_default else employment_path_override

# Helper to find the first matching column name
pick_column <- function(df, candidates, label, required = TRUE) {
  matches <- intersect(candidates, names(df))
  if (length(matches) == 0) {
    if (required) {
      stop(
        sprintf(
          "Could not locate a %s column. Looked for: %s",
          label,
          paste(candidates, collapse = ", ")
        )
      )
    } else {
      return(NULL)
    }
  }
  matches[1]
}

# ===================== LOAD INPUTS ======================
reg_matrix    <- readr::read_csv(matrix_path, show_col_types = FALSE)
employment_raw <- readr::read_csv(emp_path, show_col_types = FALSE)

# Determine key employment columns (handles both legacy QCEW files and newer supplier summaries)
naics_col <- pick_column(
  employment_raw,
  c("naics4", "NAICS", "naics", "NAICS Code", "naics_code"),
  "NAICS"
)
emp_col <- pick_column(
  employment_raw,
  c("Emp_Dec2024", "EMP_DEC2024", "TOT_EMP", "Employment", "employment", "emp"),
  "employment"
)
title_col <- pick_column(
  employment_raw,
  c("naics_title", "NAICS Title", "NAICS_Name", "naics_name"),
  "NAICS title",
  required = FALSE
)
stage_col <- pick_column(
  employment_raw,
  c("Stage", "stage"),
  "stage",
  required = FALSE
)
sector_col <- pick_column(
  employment_raw,
  c("Sector", "sector", "Segment", "segment"),
  "sector/segment",
  required = FALSE
)

employment_4d <- employment_raw
employment_4d$naics4 <- substr(as.character(employment_4d[[naics_col]]), 1, 4)
employment_4d$emp <- readr::parse_number(as.character(employment_4d[[emp_col]]))

if (!is.null(title_col) && title_col != "naics_title") {
  employment_4d$naics_title <- employment_4d[[title_col]]
}
if (!is.null(stage_col) && stage_col != "Stage") {
  employment_4d$Stage <- employment_4d[[stage_col]]
}
if (!is.null(sector_col) && sector_col != "Sector") {
  employment_4d$Sector <- employment_4d[[sector_col]]
}

employment_4d <- employment_4d %>%
  mutate(
    naics4 = stringr::str_pad(naics4, width = 4, side = "left", pad = "0")
  ) %>%
  filter(!is.na(naics4), naics4 != "", !is.na(emp))

# ===================== PREP MATRIX ======================
reg_matrix <- reg_matrix %>%
  rename(Sector_raw = Sector) %>%
  mutate(Sector = sub("^z[\\.|]", "", Sector_raw))

# Identify buyer columns (any column beginning with z. or z|)
buyer_colnames_all <- grep("^z[\\.|]", names(reg_matrix), value = TRUE)

# Convert buyer columns to numeric (strip commas first)
reg_matrix <- reg_matrix %>%
  mutate(across(all_of(buyer_colnames_all), ~ as.numeric(gsub(",", "", .x))))

# ===================== PART 1: Core Auto buyers ======================
core_auto_4d <- c("3361", "3362", "3363")

buyer_cols_core <- grep(
  paste0("^z[\\.|](", paste0(core_auto_4d, collapse = "|"), ")"),
  names(reg_matrix),
  value = TRUE
)

supplier_tbl <- reg_matrix %>%
  rowwise() %>%
  mutate(
    num_to_set = sum(c_across(all_of(buyer_cols_core)), na.rm = TRUE),
    denom_total = sum(c_across(all_of(buyer_colnames_all)), na.rm = TRUE),
    supplier4 = substr(Sector, 1, 4),
    share_to_set = ifelse(denom_total > 0, num_to_set / denom_total, 0)
  ) %>%
  ungroup() %>%
  group_by(supplier4) %>%
  summarise(
    num_to_set   = sum(num_to_set,   na.rm = TRUE),
    denom_total  = sum(denom_total,  na.rm = TRUE),
    share_to_set = ifelse(denom_total > 0, num_to_set / denom_total, 0),
    .groups = "drop"
  )

# ===================== EMPLOYMENT CLEAN ======================
employment_4d <- employment_4d %>%
  mutate(naics4 = substr(naics4, 1, 4))

# ===================== ATTRIBUTION 1: Core Auto ======================
attrib_jobs <- employment_4d %>%
  inner_join(supplier_tbl, by = c("naics4" = "supplier4")) %>%
  mutate(jobs_attr_to_set = emp * share_to_set) %>%
  arrange(desc(jobs_attr_to_set)) %>%
  left_join(naics_lookup, by = "naics4") %>%
  relocate(naics_name, .after = naics4)

write_csv(attrib_jobs, file.path(out_dir, paste0("auto_attribution_core_auto_", region, ".csv")))

# ===================== ATTRIBUTION 2: Whole supply-chain set ======================
supply_chain_set_4d <- unique(substr(employment_4d$naics4, 1, 4))

buyer_cols_sc <- grep(
  paste0("^z[\\.|](", paste0(supply_chain_set_4d, collapse = "|"), ")"),
  names(reg_matrix),
  value = TRUE
)

supplier_tbl_sc <- reg_matrix %>%
  rowwise() %>%
  mutate(
    num_to_set_sc = sum(c_across(all_of(buyer_cols_sc)), na.rm = TRUE),
    denom_total   = sum(c_across(all_of(buyer_colnames_all)), na.rm = TRUE),
    supplier4     = substr(Sector, 1, 4),
    share_to_set_sc = ifelse(denom_total > 0, num_to_set_sc / denom_total, 0)
  ) %>%
  ungroup() %>%
  group_by(supplier4) %>%
  summarise(
    num_to_set_sc   = sum(num_to_set_sc,   na.rm = TRUE),
    denom_total     = sum(denom_total,     na.rm = TRUE),
    share_to_set_sc = ifelse(denom_total > 0, num_to_set_sc / denom_total, 0),
    .groups = "drop"
  )

attrib_jobs_sc <- employment_4d %>%
  inner_join(supplier_tbl_sc, by = c("naics4" = "supplier4")) %>%
  mutate(jobs_attr_to_supplychain = emp * share_to_set_sc) %>%
  arrange(desc(jobs_attr_to_supplychain)) %>%
  left_join(naics_lookup, by = "naics4") %>%
  relocate(naics_name, .after = naics4)

write_csv(attrib_jobs_sc, file.path(out_dir, paste0("auto_attribution_supplychain_group_", region, ".csv")))

# ===================== ATTRIBUTION 3: Weighted buyer set ======================
buyer_weights <- supplier_tbl %>%
  select(naics4 = supplier4, base_weight = share_to_set)

weighted_buyers <- employment_4d %>%
  distinct(naics4) %>%
  left_join(buyer_weights, by = "naics4") %>%
  mutate(buyer_weight = if_else(naics4 %in% core_auto_4d, 1, coalesce(base_weight, 0))) %>%
  select(naics4, buyer_weight)

buyer_map <- tibble(
  colname = buyer_colnames_all,
  naics4  = substr(sub("^z[\\.|]", "", buyer_colnames_all), 1, 4)
) %>%
  inner_join(weighted_buyers, by = "naics4") %>%
  mutate(buyer_weight = pmin(pmax(buyer_weight, 0), 1))

supplier_tbl_weighted <- reg_matrix %>%
  rowwise() %>%
  mutate(
    num_to_weightedset = sum(
      map2_dbl(buyer_map$colname, buyer_map$buyer_weight, ~ get(.x) * .y),
      na.rm = TRUE
    ),
    denom_total = sum(c_across(all_of(buyer_colnames_all)), na.rm = TRUE),
    supplier4   = substr(Sector, 1, 4),
    share_to_weightedset = ifelse(denom_total > 0, num_to_weightedset / denom_total, 0)
  ) %>%
  ungroup() %>%
  group_by(supplier4) %>%
  summarise(
    num_to_weightedset     = sum(num_to_weightedset, na.rm = TRUE),
    denom_total            = sum(denom_total,        na.rm = TRUE),
    share_to_weightedset   = ifelse(denom_total > 0, num_to_weightedset / denom_total, 0),
    .groups = "drop"
  )

attrib_jobs_weighted <- employment_4d %>%
  inner_join(supplier_tbl_weighted, by = c("naics4" = "supplier4")) %>%
  mutate(jobs_attr_to_weightedset = emp * share_to_weightedset) %>%
  arrange(desc(jobs_attr_to_weightedset)) %>%
  left_join(naics_lookup, by = "naics4") %>%
  relocate(naics_name, .after = naics4)

write_csv(attrib_jobs_weighted, file.path(out_dir, paste0("auto_attribution_weighted_supplychain_", region, ".csv")))
