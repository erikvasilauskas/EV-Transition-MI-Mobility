# ---- edu_change_summary_from_detailed.R -------------------------------------
# Extended with percent share of change and base-year shares

library(readxl)
library(dplyr)
library(janitor)
library(stringr)
library(writexl)
library(purrr)

# --- INPUT / OUTPUT -----------------------------------------------------------

in_path  <- "C:/Users/vasilauskas/W.E. Upjohn Institute/Electric Vehicles - Documents/_EV Workforce Hub/MCDA, CAR Data Inputs, 10 Category Supply Chain Framework/Staffing_Patterns_Wide_By_Segment_with_EP_DETAILED.xlsx"
out_path <- sub("\\.xlsx$", "_EDU_CHANGE_SUMMARY.xlsx", in_path, ignore.case = TRUE)

# --- READ ALL SHEETS, TAG WITH SEGMENT ---------------------------------------

sheets <- readxl::excel_sheets(in_path)

read_one <- function(sh) {
  readxl::read_excel(in_path, sheet = sh) %>%
    janitor::clean_names() %>%
    mutate(segment = sh, .before = 1)
}

detailed_all <- purrr::map_dfr(sheets, read_one)

# --- SUMMARIZE BY SEGMENT × EDUCATION GROUP ----------------------------------

seg_edu_summary <- detailed_all %>%
  filter(!is.na(ep_edu_grouped)) %>%   # drop Unknowns entirely
  mutate(
    edu = factor(
      ep_edu_grouped,
      levels = c("BA+", "SC or associate's", "HS or less"),
      ordered = TRUE
    )
  ) %>%
  group_by(segment, edu) %>%
  summarise(
    empl_2021              = sum(empl_2021, na.rm = TRUE),
    empl_2024              = sum(empl_2024, na.rm = TRUE),
    level_change_2021_2024 = sum(level_change_2021_2024, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  group_by(segment) %>%
  mutate(
    total_2021 = sum(empl_2021, na.rm = TRUE),
    total_2024 = sum(empl_2024, na.rm = TRUE),
    total_change = sum(level_change_2021_2024, na.rm = TRUE),
    
    pct_change_2021_2024 = if_else(
      empl_2021 > 0, (empl_2024 / empl_2021 - 1) * 100, NA_real_
    ),
    percent_share_change_21_24 = if_else(
      total_change != 0, level_change_2021_2024 / total_change, NA_real_
    ),
    share_2021 = if_else(total_2021 > 0, empl_2021 / total_2021, NA_real_),
    share_2024 = if_else(total_2024 > 0, empl_2024 / total_2024, NA_real_)
  ) %>%
  ungroup() %>%
  arrange(segment, edu)

# --- ALL SEGMENTS COMBINED ---------------------------------------------------

all_segments_summary <- seg_edu_summary %>%
  group_by(edu) %>%
  summarise(
    empl_2021              = sum(empl_2021, na.rm = TRUE),
    empl_2024              = sum(empl_2024, na.rm = TRUE),
    level_change_2021_2024 = sum(level_change_2021_2024, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    total_2021 = sum(empl_2021, na.rm = TRUE),
    total_2024 = sum(empl_2024, na.rm = TRUE),
    total_change = sum(level_change_2021_2024, na.rm = TRUE),
    pct_change_2021_2024 = if_else(
      empl_2021 > 0, (empl_2024 / empl_2021 - 1) * 100, NA_real_
    ),
    percent_share_change_21_24 = if_else(
      total_change != 0, level_change_2021_2024 / total_change, NA_real_
    ),
    share_2021 = if_else(total_2021 > 0, empl_2021 / total_2021, NA_real_),
    share_2024 = if_else(total_2024 > 0, empl_2024 / total_2024, NA_real_)
  ) %>%
  arrange(edu)

# --- WRITE OUTPUT -------------------------------------------------------------

sanitize_sheetname <- function(x) {
  x %>%
    str_replace_all("[\\[\\]\\:\\*\\?/\\\\]", " ") %>%
    str_squish() %>%
    str_trunc(31, ellipsis = "")
}

sheet_list <- list("All Segments Combined" = all_segments_summary)

for (seg in unique(seg_edu_summary$segment)) {
  df_seg <- seg_edu_summary %>% filter(segment == seg) %>% select(-segment)
  if (nrow(df_seg)) sheet_list[[ sanitize_sheetname(seg) ]] <- df_seg
}

if (length(sheet_list)) {
  writexl::write_xlsx(sheet_list, path = out_path)
  message("Exported EDU summary workbook: ", out_path)
} else {
  message("No EDU summaries to write (empty input?).")
}
